import asyncio
import logging

from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.broker.setup import PAYMENTS_QUEUE
from app.crud.outbox import get_unpublished_events, mark_event_published

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 1.0  # seconds


async def run_outbox_relay(
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
) -> None:
    """
    Long-running background task. Cancelled via task.cancel() in lifespan.
    """
    logger.info("Outbox relay started")
    while True:
        try:
            await _poll_once(session_factory, broker)
        except asyncio.CancelledError:
            logger.info("Outbox relay stopped")
            return
        except Exception:
            logger.exception("Outbox relay cycle failed")
        await asyncio.sleep(_POLL_INTERVAL)


async def _poll_once(
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            events = await get_unpublished_events(session)
            for event in events:
                await broker.publish(
                    message=event.payload,
                    exchange=None,
                    routing_key=PAYMENTS_QUEUE.name,
                    persist=True,
                    message_id=str(event.id),
                )
                await mark_event_published(session, event.id)
