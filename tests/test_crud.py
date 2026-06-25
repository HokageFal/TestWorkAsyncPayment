import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.outbox import create_outbox_event, get_unpublished_events, mark_event_published
from app.crud.payment import create_payment, get_payment_by_id, update_payment_status_atomic
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentCreate


def _create_data(**kwargs) -> PaymentCreate:
    defaults = dict(
        amount=Decimal("99.99"),
        currency="RUB",
        description="Test",
        webhook_url="https://example.com/hook",  # type: ignore[arg-type]
    )
    defaults.update(kwargs)
    return PaymentCreate(**defaults)


async def test_create_payment_new(db_session: AsyncSession):
    data = _create_data()
    idem = str(uuid.uuid4())
    payment, is_new = await create_payment(db_session, data, idem)
    assert is_new is True
    assert payment.idempotency_key == idem
    assert payment.status == PaymentStatus.PENDING


async def test_create_payment_idempotency(db_session: AsyncSession):
    idem = str(uuid.uuid4())
    data = _create_data()
    p1, new1 = await create_payment(db_session, data, idem)
    await db_session.flush()
    p2, new2 = await create_payment(db_session, data, idem)
    assert new1 is True
    assert new2 is False
    assert p1.id == p2.id


async def test_get_payment_by_id_exists(db_session: AsyncSession):
    idem = str(uuid.uuid4())
    payment, _ = await create_payment(db_session, _create_data(), idem)
    await db_session.flush()
    found = await get_payment_by_id(db_session, payment.id)
    assert found is not None
    assert found.id == payment.id


async def test_get_payment_by_id_not_found(db_session: AsyncSession):
    result = await get_payment_by_id(db_session, uuid.uuid4())
    assert result is None


async def test_update_payment_status_atomic_success(db_session: AsyncSession):
    payment, _ = await create_payment(db_session, _create_data(), str(uuid.uuid4()))
    await db_session.flush()
    updated = await update_payment_status_atomic(db_session, payment.id, PaymentStatus.SUCCEEDED)
    assert updated is True


async def test_update_payment_status_atomic_already_processed(db_session: AsyncSession):
    payment, _ = await create_payment(db_session, _create_data(), str(uuid.uuid4()))
    await db_session.flush()
    await update_payment_status_atomic(db_session, payment.id, PaymentStatus.SUCCEEDED)
    # second update should return False — race condition protection
    updated_again = await update_payment_status_atomic(db_session, payment.id, PaymentStatus.FAILED)
    assert updated_again is False


async def test_create_outbox_event(db_session: AsyncSession):
    agg_id = uuid.uuid4()
    event = await create_outbox_event(db_session, agg_id, "payment.created", {"key": "val"})
    assert event.published is False
    assert event.event_type == "payment.created"
    assert event.aggregate_id == agg_id


async def test_get_unpublished_events(db_session: AsyncSession):
    agg_id = uuid.uuid4()
    await create_outbox_event(db_session, agg_id, "payment.created", {})
    await db_session.flush()
    events = await get_unpublished_events(db_session, batch_size=10)
    assert any(e.aggregate_id == agg_id for e in events)


async def test_mark_event_published(db_session: AsyncSession):
    agg_id = uuid.uuid4()
    event = await create_outbox_event(db_session, agg_id, "payment.created", {})
    await db_session.flush()
    await mark_event_published(db_session, event.id)
    await db_session.flush()
    events = await get_unpublished_events(db_session, batch_size=10)
    assert not any(e.id == event.id for e in events)
