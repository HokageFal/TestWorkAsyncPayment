import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.outbox import create_outbox_event
from app.crud.payment import create_payment, get_payment_by_id
from app.exceptions import PaymentNotFound
from app.schemas.payment import PaymentCreate, PaymentEvent, PaymentResponse


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        data: PaymentCreate,
        idempotency_key: str,
    ) -> tuple[PaymentResponse, bool]:
        payment, is_new = await create_payment(
            self._session, data, idempotency_key
        )
        if is_new:
            # flush to get generated id before outbox write
            await self._session.flush()
            event_payload = PaymentEvent(
                payment_id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                webhook_url=payment.webhook_url,
            ).model_dump(mode="json")
            await create_outbox_event(
                self._session,
                aggregate_id=payment.id,
                event_type="payment.created",
                payload=event_payload,
            )
        return PaymentResponse.model_validate(payment), is_new

    async def get(self, payment_id: uuid.UUID) -> PaymentResponse:
        payment = await get_payment_by_id(self._session, payment_id)
        if payment is None:
            raise PaymentNotFound(str(payment_id))
        return PaymentResponse.model_validate(payment)
