from __future__ import annotations

import re

import redis.asyncio as aioredis

from core.config import settings

_EVENTS_URL = re.sub(r"/\d+$", "/3", settings.redis_url)
_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(_EVENTS_URL, decode_responses=True)
    return _client
