from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


async def publish_scan_event(scan_id: str, event: dict) -> None:
    try:
        from core.redis_client import get_redis
        await get_redis().publish(f"scan:{scan_id}", json.dumps(event))
    except Exception as exc:
        logger.warning("Failed to publish scan event for %s: %s", scan_id, exc)


def publish_scan_event_sync(scan_id: str, event: dict) -> None:
    """Use from the Celery worker path — sync client avoids binding to an
    asyncio event loop that gets torn down between task runs."""
    try:
        from core.redis_client import get_redis_sync
        get_redis_sync().publish(f"scan:{scan_id}", json.dumps(event))
    except Exception as exc:
        logger.warning("Failed to publish scan event for %s: %s", scan_id, exc)
