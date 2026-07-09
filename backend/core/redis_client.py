from __future__ import annotations

import re

import redis
import redis.asyncio as aioredis

from core.config import settings

_EVENTS_URL = re.sub(r"/\d+$", "/3", settings.redis_url)
_client: aioredis.Redis | None = None
_sync_client: redis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(_EVENTS_URL, decode_responses=True)
    return _client


def get_redis_sync() -> redis.Redis:
    """Sync client for the Celery worker path — avoids binding to an
    event loop that gets closed between task runs (each run_agent_task
    creates and closes its own loop)."""
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(_EVENTS_URL, decode_responses=True)
    return _sync_client
