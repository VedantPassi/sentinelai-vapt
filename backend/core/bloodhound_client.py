from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_token: str | None = None
_token_expires: float = 0.0


async def _get_token() -> str:
    global _token, _token_expires
    if _token and time.monotonic() < _token_expires - 60:
        return _token

    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.post(
            f"{settings.bloodhound_url}/api/v2/login",
            json={
                "login_method": "secret",
                "username": settings.bloodhound_user,
                "secret": settings.bloodhound_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        _token = data["session_token"]
        # token valid 8h — cache for 7h55m
        _token_expires = time.monotonic() + 7 * 3600 + 55 * 60

    return _token


async def get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    token = await _get_token()
    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.get(
            f"{settings.bloodhound_url}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()


async def post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    token = await _get_token()
    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.post(
            f"{settings.bloodhound_url}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


async def get_attack_paths(limit: int = 10) -> list[dict[str, Any]]:
    """Fetch shortest paths to Domain Admins."""
    try:
        data = await get("/api/v2/attack-paths", params={"limit": limit})
        return data.get("data", {}).get("paths", []) or []
    except Exception as exc:
        logger.warning("BloodHound get_attack_paths failed: %s", exc)
        return []


async def get_domain_stats() -> dict[str, Any]:
    """High-level AD domain statistics."""
    try:
        data = await get("/api/v2/available-domains")
        domains = data.get("data", []) or []
        return domains[0] if domains else {}
    except Exception as exc:
        logger.warning("BloodHound get_domain_stats failed: %s", exc)
        return {}


async def search_nodes(query: str, node_type: str | None = None) -> list[dict[str, Any]]:
    """Search AD nodes by name."""
    params: dict[str, Any] = {"q": query, "limit": 20}
    if node_type:
        params["type"] = node_type
    try:
        data = await get("/api/v2/search", params=params)
        return data.get("data", []) or []
    except Exception as exc:
        logger.warning("BloodHound search failed: %s", exc)
        return []


async def get_node_shortest_paths(node_id: str, node_type: str) -> list[dict[str, Any]]:
    """Get shortest paths from a node to Domain Admins."""
    try:
        data = await get(
            f"/api/v2/graph-search",
            params={"object_id": node_id, "node_type": node_type},
        )
        return data.get("data", {}).get("paths", []) or []
    except Exception as exc:
        logger.warning("BloodHound node paths failed: %s", exc)
        return []
