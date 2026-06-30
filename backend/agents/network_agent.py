from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.llm import LLMError, llm_complete
from scanners.base import FindingData
from scanners import gitleaks_scanner, nmap_scanner

logger = logging.getLogger(__name__)

_CVE_PROMPT = """You are a security analyst reviewing network scan results.

Target: {url}
Open ports and services found by Nmap:
{services_json}

For each service, identify known CVEs or misconfigurations that are commonly exploitable.
Return a JSON array:
[
  {{
    "title": "vulnerability title",
    "severity": "critical|high|medium|low|info",
    "port": 22,
    "service": "ssh",
    "description": "what the risk is and why",
    "mitre_id": "T1190 or similar",
    "remediation": "specific fix"
  }}
]

Focus on high-confidence, real risks only. Return JSON array only."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="network", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "network"
    state["progress_events"].append(_event("started", "Network agent starting"))

    target_url = state["target_url"]
    config = state.get("config") or {}

    # Run Nmap
    state["progress_events"].append(_event("started", "Running Nmap scan"))
    nmap_result = await nmap_scanner.run(target_url, config)

    raw_findings: list[FindingData] = []
    if nmap_result.error:
        logger.warning("Nmap error: %s", nmap_result.error)
    else:
        raw_findings.extend(nmap_result.findings)

    # Run Gitleaks if repo_path provided
    repo_path = config.get("repo_path")
    if repo_path:
        state["progress_events"].append(_event("started", f"Running Gitleaks on {repo_path}"))
        gl_result = await gitleaks_scanner.run(repo_path, config)
        if gl_result.error:
            logger.warning("Gitleaks error: %s", gl_result.error)
        else:
            raw_findings.extend(gl_result.findings)

    state["progress_events"].append(
        _event("started", f"{len(raw_findings)} raw findings — CVE mapping with Claude")
    )

    enriched = await _map_cves(nmap_result.findings, state)
    # Append gitleaks findings directly (no CVE enrichment needed — already descriptive)
    gitleaks_findings = [f for f in raw_findings if f.category == "secrets"]
    state["findings"].extend(enriched + gitleaks_findings)

    state["progress_events"].append(
        _event("completed",
               f"Network agent done — {len(enriched)} network findings, "
               f"{len(gitleaks_findings)} secret findings")
    )
    return state


async def _map_cves(findings: list[FindingData], state: AgentState) -> list[FindingData]:
    if not findings:
        return []

    services_json = json.dumps([
        {"port": f.raw.get("port"), "service": f.raw.get("service"),
         "version": f.raw.get("version"), "host": f.raw.get("host")}
        for f in findings
    ], indent=2)

    prompt = _CVE_PROMPT.format(url=state["target_url"], services_json=services_json)

    try:
        raw = await llm_complete(prompt)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])

        enriched: list[FindingData] = []
        for item in data:
            enriched.append(FindingData(
                category="network",
                severity=item.get("severity", "info"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                remediation=item.get("remediation"),
                raw={"port": item.get("port"), "service": item.get("service"),
                     "mitre_id": item.get("mitre_id")},
            ))
        return enriched
    except LLMError as exc:
        logger.warning("LLM CVE mapping skipped: %s", exc)
        return findings
    except Exception as exc:
        logger.error("CVE mapping parse failed: %s", exc)
        return findings
