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
