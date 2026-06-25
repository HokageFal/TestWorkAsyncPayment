import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://payments:payments@postgres:5432/payments")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
os.environ.setdefault("API_KEY", "changeme")

from app.database import Base, get_db
from app.main import app
from app.models.outbox import OutboxEvent  # noqa: F401 — registers model
from app.models.payment import Payment, PaymentStatus  # noqa: F401 — registers model

TEST_DB_URL = os.environ["DATABASE_URL"]

test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Sync fixture: creates tables once, then disposes engine pool so
    function-scoped async fixtures get fresh connections in their own loop."""
    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await test_engine.dispose()

    asyncio.run(_setup())
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.connect() as conn:
        await conn.begin()
        nested = await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False, autoflush=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch.object(app.router, "lifespan_context", None),  # skip lifespan for speed
    ):
        pass  # lifespan still runs; broker calls are mocked below

    from app.broker.setup import broker

    with (
        patch.object(broker, "start", new_callable=AsyncMock),
        patch.object(broker, "declare_exchange", new_callable=AsyncMock),
        patch.object(broker, "declare_queue", new_callable=AsyncMock),
        patch.object(broker, "stop", new_callable=AsyncMock),
        patch("app.main.run_outbox_relay", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def api_key() -> str:
    return "changeme"


@pytest.fixture
def payment_payload() -> dict:
    return {
        "amount": "100.50",
        "currency": "RUB",
        "description": "Test payment",
        "webhook_url": "https://httpbin.org/post",
    }


@pytest.fixture
def idempotency_key() -> str:
    return str(uuid.uuid4())


def make_payment(**kwargs) -> Payment:
    defaults = dict(
        id=uuid.uuid4(),
        amount=Decimal("100.50"),
        currency="RUB",
        description="Test",
        extra_data=None,
        status=PaymentStatus.PENDING,
        idempotency_key=str(uuid.uuid4()),
        webhook_url="https://httpbin.org/post",
    )
    defaults.update(kwargs)
    p = Payment.__new__(Payment)
    for k, v in defaults.items():
        object.__setattr__(p, k, v)
    return p
