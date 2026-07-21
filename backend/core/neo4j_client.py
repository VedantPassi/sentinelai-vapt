from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from core.config import get_settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


def _get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        s = get_settings()
        _driver = AsyncGraphDatabase.driver(
            s.neo4j_uri,
            auth=(s.neo4j_user, s.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def run_query(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    driver = _get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, params or {})
        return [record.data() async for record in result]


async def run_write(cypher: str, params: dict[str, Any] | None = None) -> None:
    driver = _get_driver()
    async with driver.session() as session:
        await session.execute_write(_run_tx, cypher, params or {})


async def _run_tx(tx, cypher: str, params: dict) -> None:
    await tx.run(cypher, params)
