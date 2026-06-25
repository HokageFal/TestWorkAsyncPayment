from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.webhook import send_webhook


@pytest.fixture
def http_client() -> AsyncClient:
    return AsyncClient()


@respx.mock
async def test_webhook_success_first_attempt(http_client: AsyncClient):
    respx.post("https://example.com/hook").mock(return_value=Response(200))
    result = await send_webhook(http_client, "https://example.com/hook", {"k": "v"}, "evt-1")
    assert result is True
    assert respx.calls.call_count == 1


@respx.mock
async def test_webhook_success_on_third_attempt(http_client: AsyncClient):
    respx.post("https://example.com/hook").mock(
        side_effect=[Response(500), Response(500), Response(200)]
    )
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await send_webhook(http_client, "https://example.com/hook", {"k": "v"}, "evt-2")
    assert result is True
    assert respx.calls.call_count == 3


@respx.mock
async def test_webhook_all_attempts_fail(http_client: AsyncClient):
    respx.post("https://example.com/hook").mock(return_value=Response(500))
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await send_webhook(http_client, "https://example.com/hook", {"k": "v"}, "evt-3")
    assert result is False
    assert respx.calls.call_count == 3
