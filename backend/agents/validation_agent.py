from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.events import publish_scan_event_sync
from core.llm import LLMError, llm_complete
from scanners.base import FindingData
from scoring.classifier import classify_finding

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
    target_type = state.get("target_type", "web")

    if not findings:
        state["progress_events"].append(_event("completed", "No findings to validate"))
        return state

    # Container CVEs are CVSS-scored by Trivy — skip LLM validation
    if target_type == "container":
        for f in findings:
            if f.status == "open":
                f.status = "confirmed"
                f.validation_reasoning = "auto-confirmed: CVE with CVSS score"
        confirmed = sum(1 for f in findings if f.status == "confirmed")
        state["progress_events"].append(
            _event("completed", f"Validation skipped for container scan — {confirmed} CVEs confirmed")
        )
        return state

    state["progress_events"].append(
        _event("started", f"Validating {len(findings)} findings via LLM")
    )

    validated = await _validate_all(
        findings,
        state["target_url"],
        target_type,
        state.get("scan_id", ""),
    )
    state["findings"] = validated

    confirmed = sum(1 for f in validated if f.status == "confirmed")
    fp = sum(1 for f in validated if f.status == "false_positive")
    state["progress_events"].append(
        _event("completed", f"Validation done — {confirmed} confirmed, {fp} false positives")
    )
    return state


async def _validate_all(
    findings: list[FindingData],
    url: str,
    target_type: str = "web",
    scan_id: str = "",
) -> list[FindingData]:
    results = list(findings)

    # rules-based pre-filter — avoids LLM call for obvious noise
    for fd in results:
        verdict = classify_finding(fd, target_type)
        if verdict:
            fd.status = verdict
            fd.validation_reasoning = "rules-based: auto-classified"

    to_validate_indices = [i for i, fd in enumerate(results) if fd.status == "open"]
    llm_findings = [results[i] for i in to_validate_indices]
    total_llm = len(llm_findings)

    chunks = [llm_findings[i:i + _CHUNK_SIZE] for i in range(0, total_llm, _CHUNK_SIZE)]
    offset = 0

    for chunk in chunks:
        try:
            await _validate_chunk(chunk, offset, url, results, to_validate_indices)
        except LLMError as exc:
            logger.warning("Validation LLM failed for chunk at offset %d: %s", offset, exc)
        offset += len(chunk)

        # Publish real-time progress after each chunk so the terminal stays active
        if scan_id and total_llm:
            evt = _event(
                "running",
                f"Validated {min(offset, total_llm)}/{total_llm} findings…",
            )
            publish_scan_event_sync(scan_id, asdict(evt))

    return results


async def _validate_chunk(
    chunk: list[FindingData],
    offset: int,
    url: str,
    results: list[FindingData],
    to_validate_indices: list[int],
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
        chunk_idx = item.get("id")
        if chunk_idx is None or not (0 <= offset + chunk_idx < len(to_validate_indices)):
            logger.warning("Validation response has out-of-range id: %s", chunk_idx)
            continue
        results_idx = to_validate_indices[offset + chunk_idx]
        results[results_idx].status = item.get("status", "open")
        results[results_idx].risk_score = int(item.get("risk_score", 0))
        results[results_idx].validation_reasoning = item.get("reasoning", "")
