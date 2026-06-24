import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate


async def create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> tuple[Payment, bool]:
    """
    Returns (payment, is_new).
    is_new=False — duplicate by idempotency_key.
    INSERT ON CONFLICT DO NOTHING — atomic, no separate SELECT.
    """
    stmt = (
        pg_insert(Payment)
        .values(
            id=uuid.uuid4(),
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            extra_data=data.metadata,
            webhook_url=str(data.webhook_url),
            idempotency_key=idempotency_key,
            status=PaymentStatus.PENDING,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(Payment)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None:
        return row, True
    # ON CONFLICT fired — fetch existing
    existing = await session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    return existing, False  # type: ignore[return-value]


async def get_payment_by_id(
    session: AsyncSession,
    payment_id: uuid.UUID,
) -> Payment | None:
    return await session.scalar(
        select(Payment).where(Payment.id == payment_id)
    )


async def update_payment_status_atomic(
    session: AsyncSession,
    payment_id: uuid.UUID,
    new_status: PaymentStatus,
) -> bool:
    """
    Atomic update: UPDATE WHERE status=PENDING RETURNING id.
    Returns True if updated, False if already processed.
    Race condition protected — no separate SELECT.
    """
    result = await session.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
        .values(status=new_status)
        .returning(Payment.id)
    )
    return result.scalar_one_or_none() is not None
