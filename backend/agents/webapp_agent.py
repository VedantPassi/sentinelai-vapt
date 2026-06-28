from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import json
import anthropic

from agents.state import AgentState, ProgressEvent
from core.config import settings
from scanners.base import FindingData
from scanners import nuclei_scanner, zap_scanner

logger = logging.getLogger(__name__)

_ENRICH_PROMPT = """You are a security analyst reviewing scan findings for target {url}.

Attack plan context:
{attack_plan_summary}

Raw findings from automated scanners:
{findings_json}

For each finding, output a JSON array of enriched findings with this schema:
[
  {{
    "title": "finding title",
    "severity": "critical|high|medium|low|info",
    "category": "web",
    "description": "original description + why this matters given the attack plan",
    "mitre_id": "T1234 or null",
    "remediation": "specific fix recommendation"
  }}
]

Return JSON array only. Keep all findings — do not drop any."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="webapp", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "webapp"
    state["progress_events"].append(_event("started", "Web app agent starting"))

    target_url = state["target_url"]

    # Run ZAP + Nuclei in parallel
    state["progress_events"].append(_event("started", "Running ZAP + Nuclei scans in parallel"))
    zap_result, nuclei_result = await asyncio.gather(
        zap_scanner.run(target_url, state.get("config") or {}),
        nuclei_scanner.run(target_url, state.get("config") or {}),
        return_exceptions=True,
    )

    raw_findings: list[FindingData] = []
    if not isinstance(zap_result, Exception):
        raw_findings.extend(zap_result.findings)
        if zap_result.error:
            logger.warning("ZAP error: %s", zap_result.error)
    else:
        logger.warning("ZAP exception: %s", zap_result)

    if not isinstance(nuclei_result, Exception):
        raw_findings.extend(nuclei_result.findings)
        if nuclei_result.error:
            logger.warning("Nuclei error: %s", nuclei_result.error)
    else:
        logger.warning("Nuclei exception: %s", nuclei_result)

    state["progress_events"].append(
        _event("started", f"{len(raw_findings)} raw findings — enriching with Claude")
    )

    enriched = await _enrich(raw_findings, state)
    state["findings"].extend(enriched)

    state["progress_events"].append(
        _event("completed", f"Web app agent done — {len(enriched)} findings stored")
    )
    return state


async def _enrich(findings: list[FindingData], state: AgentState) -> list[FindingData]:
    if not findings:
        return []

    if not settings.anthropic_api_key:
        logger.warning("No API key — skipping Claude enrichment")
        return findings

    plan = state.get("attack_plan")
    plan_summary = plan.summary if plan else "No attack plan available"

    findings_json = json.dumps([
        {"title": f.title, "severity": f.severity,
         "category": f.category, "description": f.description}
        for f in findings
    ], indent=2)

    prompt = _ENRICH_PROMPT.format(
        url=state["target_url"],
        attack_plan_summary=plan_summary,
        findings_json=findings_json,
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])

        enriched: list[FindingData] = []
        for item in data:
            enriched.append(FindingData(
                category=item.get("category", "web"),
                severity=item.get("severity", "info"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                remediation=item.get("remediation"),
                raw={"mitre_id": item.get("mitre_id")},
            ))
        return enriched
    except Exception as exc:
        logger.error("Claude enrichment failed: %s", exc)
        return findings
