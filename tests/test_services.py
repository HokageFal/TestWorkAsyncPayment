import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.payment import create_payment
from app.exceptions import PaymentNotFound
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentCreate
from app.services.payment import PaymentService


def _data(**kw) -> PaymentCreate:
    d = dict(amount=Decimal("50.00"), currency="USD", webhook_url="https://example.com/")  # type: ignore[arg-type]
    d.update(kw)
    return PaymentCreate(**d)


async def test_service_create_new(db_session: AsyncSession):
    svc = PaymentService(db_session)
    resp, is_new = await svc.create(_data(), str(uuid.uuid4()))
    assert is_new is True
    assert resp.status == "pending"
    assert resp.amount == Decimal("50.00")


async def test_service_create_duplicate(db_session: AsyncSession):
    idem = str(uuid.uuid4())
    svc = PaymentService(db_session)
    resp1, new1 = await svc.create(_data(), idem)
    await db_session.flush()
    resp2, new2 = await svc.create(_data(), idem)
    assert new1 is True
    assert new2 is False
    assert resp1.id == resp2.id


async def test_service_get_existing(db_session: AsyncSession):
    svc = PaymentService(db_session)
    resp, _ = await svc.create(_data(), str(uuid.uuid4()))
    await db_session.flush()
    fetched = await svc.get(resp.id)
    assert fetched.id == resp.id
    assert fetched.currency == "USD"


async def test_service_get_not_found(db_session: AsyncSession):
    svc = PaymentService(db_session)
    with pytest.raises(PaymentNotFound):
        await svc.get(uuid.uuid4())
