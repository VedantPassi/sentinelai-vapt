from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core import bloodhound_client as bh
from core.llm import LLMError, llm_complete
from scanners.base import FindingData

logger = logging.getLogger(__name__)

_ENRICH_PROMPT = """You are an Active Directory penetration tester reviewing BloodHound attack path data.

Domain: {domain}
Attack paths to Domain Admins:
{paths_json}

For each path, provide:
1. Attack narrative: how would a real attacker traverse this path?
2. Pivots required: list credential/permission hops
3. Priority: should this be fixed immediately or can it wait? Why?

Return JSON array:
[
  {{
    "path_id": "the path_id",
    "attack_narrative": "step-by-step how attacker moves",
    "pivots": ["hop1 -> hop2", "hop2 -> hop3"],
    "priority": "immediate|high|medium",
    "priority_reason": "brief justification"
  }}
]

Return JSON array only."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="bloodhound", status=status, message=message, timestamp=_ts())


def _path_to_finding(nodes: list[dict], edges: list[dict], path_idx: int) -> FindingData:
    if not nodes:
        return FindingData(
            category="ad",
            severity="medium",
            title=f"AD Attack Path #{path_idx} (no data)",
            description="BloodHound returned a path with no node data.",
            remediation="Re-run BloodHound data collection.",
            raw={"path_id": f"path_{path_idx}"},
        )

    src_name = nodes[0].get("label", nodes[0].get("name", "unknown"))
    dst_name = nodes[-1].get("label", nodes[-1].get("name", "Domain Admins"))
    edge_labels = [e.get("label", e.get("kind", "?")) for e in edges]
    hop_desc = " → ".join(edge_labels) if edge_labels else "unknown ACEs"

    return FindingData(
        category="ad",
        severity="critical",
        title=f"AD Privilege Escalation: {src_name} → {dst_name}",
        description=(
            f"BloodHound discovered a {len(nodes)-1}-hop attack path from "
            f"'{src_name}' to '{dst_name}' via ACEs: {hop_desc}. "
            f"This path allows privilege escalation to Domain Admin without brute-force."
        ),
        remediation=(
            "Remove excessive ACE grants (WriteDACL/GenericAll) from non-privileged accounts. "
            "Enable Protected Users group for DA accounts. "
            "Run BloodHound regularly to detect new paths."
        ),
        raw={
            "path_id": f"path_{path_idx}",
            "hops": len(nodes) - 1,
            "src_node": src_name,
            "dst_node": dst_name,
            "edge_types": edge_labels,
            "nodes": nodes,
            "edges": edges,
        },
    )


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "bloodhound"
    state["progress_events"].append(_event("started", "BloodHound agent starting — querying AD attack paths"))

    try:
        domain_stats = await bh.get_domain_stats()
        domain_name = domain_stats.get("name", "unknown")
        state["progress_events"].append(_event("started", f"Connected to domain: {domain_name}"))

        paths = await bh.get_attack_paths(limit=10)
        hvt = await bh.get_high_value_targets()

        state["progress_events"].append(
            _event("started", f"Found {len(paths)} attack paths, {len(hvt)} high-value targets")
        )

        findings: list[FindingData] = []
        for idx, path in enumerate(paths):
            f = _path_to_finding(path.get("nodes", []), path.get("edges", []), idx)
            findings.append(f)

        if not findings:
            state["progress_events"].append(
                _event(
                    "completed",
                    "No attack paths to Domain Admins found — AD may be clean or data not ingested yet",
                )
            )
            return state

        enriched_map = await _enrich(findings, domain_name)

        for f in findings:
            pid = f.raw.get("path_id", "")
            if pid in enriched_map:
                info = enriched_map[pid]
                f.validation_reasoning = (
                    f"Attack narrative: {info.get('attack_narrative', '')}\n"
                    f"Priority: {info.get('priority', '')} — {info.get('priority_reason', '')}"
                )
                if info.get("pivots"):
                    f.poc_evidence = json.dumps(info["pivots"])

        state["findings"].extend(findings)
        state["progress_events"].append(
            _event(
                "completed",
                f"BloodHound agent done — {len(findings)} attack path findings, "
                f"{len(enriched_map)} LLM-enriched",
            )
        )

    except Exception as exc:
        logger.error("BloodHound agent failed: %s", exc)
        state["progress_events"].append(_event("failed", f"BloodHound error: {exc}"))

    return state


async def _enrich(findings: list[FindingData], domain: str) -> dict[str, dict]:
    if not findings:
        return {}

    paths_json = json.dumps(
        [
            {
                "path_id": f.raw.get("path_id"),
                "title": f.title,
                "hops": f.raw.get("hops"),
                "src": f.raw.get("src_node"),
                "dst": f.raw.get("dst_node"),
                "edge_types": f.raw.get("edge_types", []),
            }
            for f in findings
        ],
        indent=2,
    )

    prompt = _ENRICH_PROMPT.format(domain=domain, paths_json=paths_json)

    try:
        raw = await llm_complete(prompt)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])
        return {item["path_id"]: item for item in data if "path_id" in item}
    except LLMError as exc:
        logger.warning("BloodHound LLM enrichment skipped: %s", exc)
        return {}
    except Exception as exc:
        logger.error("BloodHound enrichment parse failed: %s", exc)
        return {}
