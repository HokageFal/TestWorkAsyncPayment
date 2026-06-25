import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import app.http_client as _http_client_module
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.payments import router as payments_router
from app.broker.setup import (
    DLQ_EXCHANGE,
    DLQ_QUEUE,
    PAYMENTS_EXCHANGE,
    PAYMENTS_QUEUE,
    broker,
)
from app.database import AsyncSessionFactory
from app.workers.outbox_relay import run_outbox_relay

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await broker.start()
    await broker.declare_exchange(PAYMENTS_EXCHANGE)
    await broker.declare_exchange(DLQ_EXCHANGE)
    await broker.declare_queue(PAYMENTS_QUEUE)
    await broker.declare_queue(DLQ_QUEUE)

    _http_client_module.http_client = AsyncClient(timeout=10.0)

    relay_task = asyncio.create_task(
        run_outbox_relay(AsyncSessionFactory, broker),
        name="outbox-relay",
    )

    logger.info("Application started")
    yield

    relay_task.cancel()
    try:
        await asyncio.wait_for(relay_task, timeout=10.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    if _http_client_module.http_client is not None:
        await _http_client_module.http_client.aclose()
    await broker.close()
    logger.info("Application stopped")


app = FastAPI(title="Payments API", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(payments_router)
