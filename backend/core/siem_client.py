from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


async def _send_to_splunk(events: list[dict[str, Any]]) -> None:
    if not settings.splunk_hec_url or not settings.splunk_hec_token:
        return

    payload = "\n".join(
        json.dumps({
            "event": event,
            "index": settings.splunk_index,
            "sourcetype": "sentinelai:finding",
        })
        for event in events
    )
    headers = {"Authorization": f"Splunk {settings.splunk_hec_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                settings.splunk_hec_url.rstrip("/") + "/services/collector/event",
                headers=headers,
                content=payload,
            )
            resp.raise_for_status()
            logger.info("Splunk HEC: shipped %d events", len(events))
    except httpx.HTTPError as exc:
        logger.warning("Splunk HEC failed: %s", exc)


async def _send_to_elasticsearch(events: list[dict[str, Any]]) -> None:
    if not settings.es_url:
        return

    lines: list[str] = []
    for event in events:
        lines.append(json.dumps({"index": {"_index": settings.es_index}}))
        lines.append(json.dumps(event))
    payload = "\n".join(lines) + "\n"

    auth = None
    if settings.es_user and settings.es_password:
        auth = (settings.es_user, settings.es_password)

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                settings.es_url.rstrip("/") + "/_bulk",
                headers={"Content-Type": "application/x-ndjson"},
                content=payload,
                auth=auth,
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("errors"):
                logger.warning("Elasticsearch bulk reported errors: %s", body)
            else:
                logger.info("Elasticsearch: shipped %d events", len(events))
    except httpx.HTTPError as exc:
        logger.warning("Elasticsearch failed: %s", exc)


async def forward_to_siem(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    if settings.splunk_hec_url:
        await _send_to_splunk(events)
    if settings.es_url:
        await _send_to_elasticsearch(events)
