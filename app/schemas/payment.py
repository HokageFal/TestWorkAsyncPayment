import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=4)
    currency: str = Field(pattern=r"^(RUB|USD|EUR)$")  # TZ: «Валюта (RUB, USD, EUR)»
    description: str | None = None
    metadata: dict | None = Field(default=None)
    webhook_url: HttpUrl

    model_config = ConfigDict(populate_by_name=True)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    currency: str
    description: str | None
    status: str
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class PaymentEvent(BaseModel):
    """Message published to RabbitMQ via Outbox."""
    model_config = ConfigDict(frozen=True)

    payment_id: uuid.UUID
    amount: Decimal
    currency: str
    webhook_url: str
