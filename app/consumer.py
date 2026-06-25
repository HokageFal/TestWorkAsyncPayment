import asyncio
import logging
import random
import uuid

from faststream.middlewares.acknowledgement.config import AckPolicy

from app.broker.setup import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, broker
from app.crud.payment import update_payment_status_atomic
from app.database import AsyncSessionFactory
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentEvent

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


@broker.subscriber(
    PAYMENTS_QUEUE,
    exchange=PAYMENTS_EXCHANGE,
    ack_policy=AckPolicy.REJECT_ON_ERROR,
)
async def handle_payment(event: PaymentEvent) -> None:
    """
    3 retries with exponential backoff.
    On exhaustion: raise → REJECT → DLQ.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            await _process(event)
            return
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = 2 ** (attempt - 1)  # 1s, 2s
                logger.warning(
                    "Retry %d/%d for payment %s (delay=%ds): %s",
                    attempt, _MAX_RETRIES, event.payment_id, delay, exc,
                )
                await asyncio.sleep(delay)

    logger.error(
        "Payment %s failed after %d attempts", event.payment_id, _MAX_RETRIES
    )
    assert last_exc is not None  # loop ran ≥ 1 iterations
    raise last_exc


async def _process(event: PaymentEvent) -> None:
    # Simulate processing: 2-5 seconds
    await asyncio.sleep(random.uniform(2, 5))

    # 90% success / 10% failure
    success = random.random() < 0.9
    new_status = PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED

    async with AsyncSessionFactory() as session:
        updated = await update_payment_status_atomic(
            session, event.payment_id, new_status
        )
        await session.commit()

    if not updated:
        logger.warning(
            "Payment %s already processed, skipping webhook", event.payment_id
        )
        return

    logger.info("Payment %s → %s", event.payment_id, new_status)

    # Send webhook using the shared http_client
    from app.http_client import http_client  # noqa: PLC0415
    if http_client is not None:
        from app.services.webhook import send_webhook  # noqa: PLC0415
        await send_webhook(
            http_client,
            url=event.webhook_url,
            payload={
                "payment_id": str(event.payment_id),
                "status": str(new_status),
                "currency": event.currency,
                "amount": str(event.amount),
            },
            event_id=str(event.payment_id),
        )


if __name__ == "__main__":
    import asyncio as _asyncio
    from faststream import FastStream
    _asyncio.run(FastStream(broker).run())
