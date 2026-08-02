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


def _to_list(v: Any) -> list[dict[str, Any]]:
    """BH CE returns nodes/edges as dicts keyed by string IDs — normalize to list."""
    if isinstance(v, dict):
        return list(v.values())
    return v or []


async def _cypher(query: str) -> list[dict[str, Any]]:
    """Run a Cypher query via BloodHound CE graph endpoint."""
    try:
        data = await post("/api/v2/graphs/cypher", {"query": query})
        return _to_list(data.get("data", {}).get("nodes"))
    except Exception as exc:
        logger.warning("BloodHound cypher failed: %s", exc)
        return []


async def _cypher_raw(query: str) -> dict[str, Any]:
    try:
        data = await post("/api/v2/graphs/cypher", {"query": query})
        return data.get("data", {}) or {}
    except Exception as exc:
        logger.warning("BloodHound cypher_raw failed: %s", exc)
        return {}


async def get_attack_paths(limit: int = 10) -> list[dict[str, Any]]:
    """Shortest paths from any non-DA user to Domain Admins group."""
    query = f"""
    MATCH p=shortestPath((u:User)-[*1..10]->(g:Group))
    WHERE g.name CONTAINS 'DOMAIN ADMINS'
    AND NOT u.name CONTAINS 'DOMAIN ADMINS'
    RETURN p LIMIT {limit}
    """
    try:
        raw = await _cypher_raw(query)
        edges = _to_list(raw.get("edges"))
        nodes = _to_list(raw.get("nodes"))
        paths: list[dict[str, Any]] = []
        if nodes:
            paths.append({"nodes": nodes, "edges": edges})
        return paths
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


async def get_node_shortest_paths(node_id: str, node_type: str = "User") -> list[dict[str, Any]]:
    """Shortest paths from a specific node to Domain Admins."""
    query = f"""
    MATCH p=shortestPath((src:{node_type})-[*1..10]->(g:Group))
    WHERE src.objectid = '{node_id}'
    AND g.name CONTAINS 'DOMAIN ADMINS'
    RETURN p LIMIT 5
    """
    try:
        raw = await _cypher_raw(query)
        return [{"nodes": _to_list(raw.get("nodes")), "edges": _to_list(raw.get("edges"))}]
    except Exception as exc:
        logger.warning("BloodHound node paths failed: %s", exc)
        return []


async def get_high_value_targets() -> list[dict[str, Any]]:
    """Users/computers with most inbound attack paths (choke points)."""
    query = """
    MATCH (n)
    WHERE n.admincount = true
    RETURN n.name as name, n.objectid as id, labels(n)[0] as type
    ORDER BY name LIMIT 20
    """
    return await _cypher(query)
