import asyncio
import logging

from httpx import AsyncClient, HTTPError, TimeoutException

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (1.0, 2.0, 4.0)
_TIMEOUT = 10.0


async def send_webhook(
    client: AsyncClient,
    url: str,
    payload: dict,
    event_id: str,
) -> bool:
    last_exc: Exception | None = None
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            response = await client.post(
                url,
                json=payload,
                timeout=_TIMEOUT,
                headers={"X-Event-ID": event_id},
            )
            response.raise_for_status()
            logger.info("Webhook delivered (attempt %d): %s", attempt, url)
            return True
        except (HTTPError, TimeoutException) as exc:
            last_exc = exc
            logger.warning(
                "Webhook attempt %d/%d failed (%s): %s",
                attempt, len(_RETRY_DELAYS), url, exc,
            )
            if attempt < len(_RETRY_DELAYS):
                await asyncio.sleep(delay)

    logger.error("Webhook permanently failed for %s: %s", url, last_exc)
    return False
