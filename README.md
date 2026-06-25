# Payments Service

Асинхронный микросервис обработки платежей.

## Стек

FastAPI · SQLAlchemy 2.0 async · PostgreSQL · RabbitMQ (FastStream) · Alembic · Docker

## Быстрый старт

```bash
cp .env.example .env
docker-compose up --build
```

Миграции применяются автоматически при старте сервиса `migrations`.

## API

### Аутентификация

Все запросы требуют заголовок `X-API-Key`. Значение берётся из `.env` → `API_KEY` (по умолчанию `changeme`).

### Создать платёж

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: changeme" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.50",
    "currency": "RUB",
    "description": "Тестовый платёж",
    "webhook_url": "https://httpbin.org/post",
    "metadata": {"order_id": "123"}
  }'
```

Ответ: `202 Accepted` + `payment_id`, `status: pending`, `created_at`.

### Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/{payment_id} \
  -H "X-API-Key: changeme"
```

## Idempotency

Повторный POST с тем же `Idempotency-Key` вернёт `202` с тем же `payment_id` — дубль не создаётся.

## Обработка платежей

После создания платёж публикуется в очередь RabbitMQ `payments.new` через Outbox pattern.
Consumer обрабатывает его за 2–5 секунд (90% успех / 10% ошибка) и отправляет webhook.

## Dead Letter Queue

Сообщения, не обработанные после 3 попыток, попадают в `payments.dead`.  
Мониторинг: [http://localhost:15672](http://localhost:15672) (guest / guest).

## Сервисы

| Сервис     | Порт  | Описание                    |
|------------|-------|-----------------------------|
| api        | 8000  | FastAPI HTTP API             |
| postgres   | —     | PostgreSQL (внутренний)      |
| rabbitmq   | 15672 | RabbitMQ Management UI       |
| consumer   | —     | FastStream consumer          |
| migrations | —     | Alembic (one-shot)           |

## Переменные окружения

Скопируй `.env.example` в `.env` и при необходимости измени значения:

| Переменная          | Описание                        |
|---------------------|---------------------------------|
| `DATABASE_URL`      | PostgreSQL connection string     |
| `RABBITMQ_URL`      | RabbitMQ AMQP URL               |
| `API_KEY`           | Статический ключ для X-API-Key  |
