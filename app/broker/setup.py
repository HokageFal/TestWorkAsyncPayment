import os

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType


PAYMENTS_EXCHANGE = RabbitExchange(
    name="payments.exchange",
    type=ExchangeType.DIRECT,
    durable=True,
)

DLQ_EXCHANGE = RabbitExchange(
    name="payments.dlq.exchange",
    type=ExchangeType.DIRECT,
    durable=True,
)

DLQ_QUEUE = RabbitQueue(
    name="payments.dead",
    durable=True,
    arguments={"x-message-ttl": 604_800_000},  # 7 days — operational default
)

PAYMENTS_QUEUE = RabbitQueue(
    name="payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "payments.dlq.exchange",
        "x-dead-letter-routing-key": "payments.dead",
    },
)

broker = RabbitBroker(
    url=os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/"),
)
