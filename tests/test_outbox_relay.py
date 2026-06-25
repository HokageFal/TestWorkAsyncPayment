import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.outbox_relay import _poll_once, run_outbox_relay


def _make_session_mock() -> AsyncMock:
    """AsyncSession mock where begin() is a sync call returning an async context manager."""
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__ = AsyncMock(return_value=None)
    mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.begin = MagicMock(return_value=mock_begin_ctx)
    return mock_session


def _make_factory_mock(session: AsyncMock) -> MagicMock:
    """async_sessionmaker mock that yields the given session via async with."""
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_factory


async def test_poll_once_publishes_and_marks(mocker):
    event_id = uuid.uuid4()
    fake_event = MagicMock()
    fake_event.id = event_id
    fake_event.payload = {"payment_id": str(uuid.uuid4())}

    mock_session = _make_session_mock()
    mock_factory = _make_factory_mock(mock_session)
    mock_broker = AsyncMock()

    mocker.patch("app.workers.outbox_relay.get_unpublished_events", return_value=[fake_event])
    mocker.patch("app.workers.outbox_relay.mark_event_published", return_value=None)

    await _poll_once(mock_factory, mock_broker)

    mock_broker.publish.assert_awaited_once()
    call_kwargs = mock_broker.publish.call_args.kwargs
    assert call_kwargs["message"] == fake_event.payload


async def test_poll_once_no_events(mocker):
    mock_session = _make_session_mock()
    mock_factory = _make_factory_mock(mock_session)
    mock_broker = AsyncMock()

    mocker.patch("app.workers.outbox_relay.get_unpublished_events", return_value=[])

    await _poll_once(mock_factory, mock_broker)
    mock_broker.publish.assert_not_awaited()


async def test_run_outbox_relay_stops_on_cancel(mocker):
    mock_factory = MagicMock()
    mock_broker = AsyncMock()

    call_count = 0

    async def fake_poll(sf, b):
        nonlocal call_count
        call_count += 1
        raise asyncio.CancelledError()

    mocker.patch("app.workers.outbox_relay._poll_once", side_effect=fake_poll)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    await run_outbox_relay(mock_factory, mock_broker)
    assert call_count == 1
