import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.payment import PaymentCreate, PaymentEvent, PaymentResponse


def test_payment_create_valid():
    p = PaymentCreate(
        amount=Decimal("100.50"),
        currency="RUB",
        description="Test",
        webhook_url="https://example.com/webhook",
    )
    assert p.amount == Decimal("100.50")
    assert p.currency == "RUB"


def test_payment_create_invalid_amount_zero():
    with pytest.raises(ValidationError):
        PaymentCreate(amount=Decimal("0"), currency="RUB", webhook_url="https://example.com/")


def test_payment_create_invalid_amount_negative():
    with pytest.raises(ValidationError):
        PaymentCreate(amount=Decimal("-1"), currency="RUB", webhook_url="https://example.com/")


def test_payment_create_invalid_currency():
    with pytest.raises(ValidationError):
        PaymentCreate(amount=Decimal("10"), currency="GBP", webhook_url="https://example.com/")


@pytest.mark.parametrize("currency", ["RUB", "USD", "EUR"])
def test_payment_create_valid_currencies(currency: str):
    p = PaymentCreate(amount=Decimal("1"), currency=currency, webhook_url="https://example.com/")
    assert p.currency == currency


def test_payment_create_missing_webhook_url():
    with pytest.raises(ValidationError):
        PaymentCreate(amount=Decimal("10"), currency="RUB")  # type: ignore[call-arg]


def test_payment_event_frozen():
    event = PaymentEvent(
        payment_id=uuid.uuid4(),
        amount=Decimal("50"),
        currency="USD",
        webhook_url="https://example.com/",
    )
    with pytest.raises(ValidationError):
        event.currency = "RUB"  # type: ignore[misc]


def test_payment_response_from_dict():
    import datetime

    data = {
        "id": uuid.uuid4(),
        "amount": Decimal("200"),
        "currency": "EUR",
        "description": None,
        "status": "pending",
        "idempotency_key": "key-1",
        "webhook_url": "https://example.com/",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "processed_at": None,
    }

    class FakePayment:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    resp = PaymentResponse.model_validate(FakePayment(**data))
    assert resp.currency == "EUR"
    assert resp.status == "pending"
