import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


async def create_outbox_event(
    session: AsyncSession,
    aggregate_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> OutboxEvent:
    event = OutboxEvent(
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        published=False,
    )
    session.add(event)
    return event


async def get_unpublished_events(
    session: AsyncSession,
    batch_size: int = 50,
) -> list[OutboxEvent]:
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published.is_(False))
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def mark_event_published(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> None:
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(published=True)
    )
