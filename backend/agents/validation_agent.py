from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.llm import LLMError, llm_complete
from scanners.base import FindingData

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 10

_SYSTEM = """You are a senior penetration tester reviewing automated scanner output.
Classify each finding as real ("confirmed") or noise ("false_positive").
Assign risk_score 0-100 (0=no risk, 100=critical exploitable vuln).
Be skeptical — scanners over-report. Output JSON only."""

_PROMPT = """Target: {url}

Findings to validate:
{findings_json}

Return a JSON array with one object per finding, in the same order:
[
  {{
    "id": <original index>,
    "status": "confirmed" | "false_positive",
    "risk_score": <0-100>,
    "reasoning": "<one sentence>"
  }}
]

Return JSON only. No explanation outside the array."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="validator", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "validator"
    findings = state.get("findings", [])

    if not findings:
        state["progress_events"].append(_event("completed", "No findings to validate"))
        return state

    state["progress_events"].append(
        _event("started", f"Validating {len(findings)} findings via LLM")
    )

    validated = await _validate_all(findings, state["target_url"])
    state["findings"] = validated

    confirmed = sum(1 for f in validated if f.status == "confirmed")
    fp = sum(1 for f in validated if f.status == "false_positive")
    state["progress_events"].append(
        _event("completed", f"Validation done — {confirmed} confirmed, {fp} false positives")
    )
    return state


async def _validate_all(findings: list[FindingData], url: str) -> list[FindingData]:
    results = list(findings)
    chunks = [findings[i:i + _CHUNK_SIZE] for i in range(0, len(findings), _CHUNK_SIZE)]
    offset = 0

    for chunk in chunks:
        try:
            await _validate_chunk(chunk, offset, url, results)
        except LLMError as exc:
            logger.warning("Validation LLM failed for chunk at offset %d: %s", offset, exc)
        offset += len(chunk)

    return results


async def _validate_chunk(
    chunk: list[FindingData],
    offset: int,
    url: str,
    results: list[FindingData],
) -> None:
    findings_json = json.dumps([
        {
            "id": offset + i,
            "title": f.title,
            "severity": f.severity,
            "category": f.category,
            "description": f.description,
        }
        for i, f in enumerate(chunk)
    ], indent=2)

    prompt = _PROMPT.format(url=url, findings_json=findings_json)
    raw = await llm_complete(prompt, system=_SYSTEM, model_tier="standard")

    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise LLMError(f"No JSON array in LLM response: {raw[:200]}")

    data = json.loads(raw[start:end])
    for item in data:
        idx = item.get("id")
        if idx is None or not (0 <= idx < len(results)):
            logger.warning("Validation response has out-of-range id: %s", idx)
            continue
        results[idx].status = item.get("status", "open")
        results[idx].risk_score = int(item.get("risk_score", 0))
        results[idx].validation_reasoning = item.get("reasoning", "")
