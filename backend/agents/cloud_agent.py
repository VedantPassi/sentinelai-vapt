from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.llm import LLMError, llm_complete
from scanners.base import FindingData
from scanners import prowler_scanner

logger = logging.getLogger(__name__)

_ENRICH_PROMPT = """You are a cloud security expert reviewing AWS Prowler findings.

Account/Region: {account}
Top critical/high findings:
{findings_json}

For each finding, provide:
1. Real-world exploitability: can an external attacker reach this? Or requires internal access?
2. Business impact if exploited
3. Specific remediation command or console step

Return JSON array:
[
  {{
    "check_id": "the check_id",
    "exploitability": "external/internal/requires-auth — brief context",
    "business_impact": "what attacker gains or what data is at risk",
    "remediation": "specific fix — CLI command or console step"
  }}
]

Return JSON array only."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="cloud", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "cloud"
    state["progress_events"].append(_event("started", "Cloud agent starting — running Prowler"))

    config = state.get("config") or {}
    services = config.get("services") or config.get("cloud_services") or ["iam", "s3", "ec2", "guardduty", "cloudtrail"]

    state["progress_events"].append(
        _event("started", f"Prowler scanning services: {', '.join(services)}")
    )

    result = await prowler_scanner.run(config={"services": services, **config})

    if result.error:
        state["progress_events"].append(_event("failed", f"Prowler error: {result.error}"))
        return state

    all_findings = result.findings
    critical_high = [f for f in all_findings if f.severity in ("critical", "high")]

    state["progress_events"].append(
        _event(
            "started",
            f"Prowler done — {len(all_findings)} findings ({len(critical_high)} critical/high), enriching top findings",
        )
    )

    enriched_map = await _enrich(critical_high[:15], state)

    for f in all_findings:
        check_id = f.raw.get("check_id", "")
        if check_id in enriched_map:
            info = enriched_map[check_id]
            f.validation_reasoning = (
                f"Exploitability: {info.get('exploitability', '')}\n"
                f"Business impact: {info.get('business_impact', '')}"
            )
            if info.get("remediation"):
                f.remediation = info["remediation"]

    state["findings"].extend(all_findings)
    state["progress_events"].append(
        _event(
            "completed",
            f"Cloud agent done — {len(all_findings)} findings, "
            f"{len(critical_high)} critical/high, {len(enriched_map)} LLM-enriched",
        )
    )
    return state


async def _enrich(findings: list[FindingData], state: AgentState) -> dict[str, dict]:
    if not findings:
        return {}

    account = ""
    for f in findings:
        if f.raw.get("account"):
            account = f"{f.raw['account']} / {f.raw.get('region', 'us-east-1')}"
            break

    findings_json = json.dumps(
        [
            {
                "check_id": f.raw.get("check_id"),
                "title": f.title,
                "severity": f.severity,
                "service": f.raw.get("service"),
                "resource": f.raw.get("resource"),
                "description": f.description[:300],
            }
            for f in findings
        ],
        indent=2,
    )

    prompt = _ENRICH_PROMPT.format(account=account or "unknown", findings_json=findings_json)

    try:
        raw = await llm_complete(prompt)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])
        return {item["check_id"]: item for item in data if "check_id" in item}
    except LLMError as exc:
        logger.warning("Cloud LLM enrichment skipped: %s", exc)
        return {}
    except Exception as exc:
        logger.error("Cloud enrichment parse failed: %s", exc)
        return {}
