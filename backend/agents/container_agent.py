from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.llm import LLMError, llm_complete
from scanners.base import FindingData
from scanners import trivy_scanner

logger = logging.getLogger(__name__)

_ENRICH_PROMPT = """You are a container security expert reviewing Trivy CVE scan results.

Image: {image}
Top critical/high CVEs:
{cves_json}

For each CVE, provide:
1. Real-world exploitability context (is it network-exploitable? requires auth? already in CISA KEV?)
2. Blast radius if exploited in a production container
3. One-line remediation

Return JSON array:
[
  {{
    "cve_id": "CVE-XXXX-YYYY",
    "pkg": "package-name",
    "exploitability": "brief context — network/local, auth required, CISA KEV status",
    "blast_radius": "what attacker gains",
    "remediation": "specific fix"
  }}
]

Return JSON array only. Cover all CVEs provided."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="container", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "container"
    state["progress_events"].append(_event("started", "Container agent starting"))

    image_ref = state["target_url"]
    config = state.get("config") or {}

    state["progress_events"].append(_event("started", f"Running Trivy on {image_ref}"))
    result = await trivy_scanner.run(image_ref, config)

    if result.error:
        state["progress_events"].append(_event("failed", f"Trivy error: {result.error}"))
        return state

    all_findings = result.findings
    state["progress_events"].append(
        _event("started", f"Trivy complete — {len(all_findings)} findings, enriching top CVEs with LLM")
    )

    enriched_map = await _enrich_top_cves(all_findings, image_ref)

    for f in all_findings:
        cve_id = f.raw.get("cve_id", "")
        if cve_id in enriched_map:
            info = enriched_map[cve_id]
            f.validation_reasoning = (
                f"Exploitability: {info.get('exploitability', '')}\n"
                f"Blast radius: {info.get('blast_radius', '')}"
            )
            if info.get("remediation"):
                f.remediation = info["remediation"]

    state["findings"].extend(all_findings)
    state["progress_events"].append(
        _event(
            "completed",
            f"Container agent done — {len(all_findings)} CVEs/misconfigs "
            f"({sum(1 for f in all_findings if f.severity in ('critical', 'high'))} critical/high)",
        )
    )
    return state


async def _enrich_top_cves(findings: list[FindingData], image: str) -> dict[str, dict]:
    critical_high = [
        f for f in findings if f.severity in ("critical", "high") and f.raw.get("cve_id")
    ]
    top = critical_high[:20]

    if not top:
        return {}

    cves_json = json.dumps(
        [
            {
                "cve_id": f.raw.get("cve_id"),
                "pkg": f.raw.get("pkg"),
                "installed": f.raw.get("installed"),
                "fixed": f.raw.get("fixed"),
                "cvss": f.raw.get("cvss"),
            }
            for f in top
        ],
        indent=2,
    )

    prompt = _ENRICH_PROMPT.format(image=image, cves_json=cves_json)

    try:
        raw = await llm_complete(prompt)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])
        return {item["cve_id"]: item for item in data if "cve_id" in item}
    except LLMError as exc:
        logger.warning("Container LLM enrichment skipped: %s", exc)
        return {}
    except Exception as exc:
        logger.error("Container enrichment parse failed: %s", exc)
        return {}
