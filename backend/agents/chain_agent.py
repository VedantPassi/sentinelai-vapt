from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, AttackChain, ChainStep, ProgressEvent
from core.llm import LLMError, llm_complete
from scanners.base import FindingData

logger = logging.getLogger(__name__)

_MAX_FINDINGS = 30

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_SYSTEM = """You are an expert penetration tester modeling realistic multi-step attack chains.
Given confirmed and high-severity vulnerabilities across multiple attack surfaces, identify
how an attacker would chain them together to achieve their objectives.
Model cross-surface kill chains: pivot from network → web → container → secrets where possible.
Focus on realistic, exploitable paths. Output JSON only."""

_PROMPT = """Target: {url}
Tech stack: {tech_stack}
Scan surfaces: {surfaces}

Vulnerabilities by surface:
{findings_json}

MITRE ATT&CK kill chain stages to consider:
- Initial Access (T1190, T1133, T1078)
- Execution (T1059, T1203)
- Persistence (T1098, T1543)
- Privilege Escalation (T1068, T1548)
- Lateral Movement (T1021, T1570)
- Collection / Exfiltration (T1005, T1048)

Identify 1–5 realistic multi-step attack chains. Prioritize chains that:
1. Pivot across multiple surfaces (network → web → container → secrets)
2. Escalate privileges or access
3. Are achievable with the specific vulnerabilities listed

Return a JSON array:
[
  {{
    "title": "short chain title",
    "description": "2-3 sentence narrative of the full attack path including surface pivots",
    "impact": "critical|high|medium|low",
    "likelihood": "high|medium|low",
    "mitre_ids": ["T1190", "T1068"],
    "finding_ids": ["<uuid>", "<uuid>"],
    "steps": [
      {{
        "step": 1,
        "action": "what the attacker does",
        "mitre_id": "T1190",
        "finding_id": "<uuid or null>",
        "surface": "web|network|container|secrets|unknown"
      }}
    ]
  }}
]

Return JSON only. No explanation outside the array."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="chain", status=status, message=message, timestamp=_ts())


def _select_findings(findings: list[FindingData]) -> list[FindingData]:
    eligible = [
        f for f in findings
        if f.status == "confirmed"
        or (f.status == "open" and f.severity in ("critical", "high"))
    ]
    return sorted(
        eligible,
        key=lambda f: (_SEVERITY_RANK.get(f.severity, 4), -f.risk_score),
    )[:_MAX_FINDINGS]


def _group_by_surface(findings: list[FindingData]) -> dict[str, list[FindingData]]:
    groups: dict[str, list[FindingData]] = {}
    for f in findings:
        surface = f.category if f.category in ("web", "network", "container", "secrets", "misconfiguration") else "other"
        groups.setdefault(surface, []).append(f)
    return groups


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "chain"

    top = _select_findings(state.get("findings", []))

    if not top:
        state["progress_events"].append(
            _event("completed", "No eligible findings — chain discovery skipped")
        )
        return state

    confirmed_count = sum(1 for f in top if f.status == "confirmed")
    open_count = len(top) - confirmed_count
    state["progress_events"].append(
        _event(
            "started",
            f"Chain discovery v2 — {len(top)} findings "
            f"({confirmed_count} confirmed, {open_count} high-severity open) "
            f"across {len(set(f.category for f in top))} surfaces",
        )
    )

    grouped = _group_by_surface(top)
    surfaces = ", ".join(sorted(grouped.keys()))

    recon = state.get("recon_data")
    tech_stack = ", ".join(recon.technologies) if recon and recon.technologies else "unknown"

    findings_by_surface = {}
    for surface, flist in grouped.items():
        findings_by_surface[surface] = [
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity,
                "status": f.status,
                "description": f.description,
                "risk_score": f.risk_score,
                "validation_reasoning": f.validation_reasoning or "",
                "remediation": f.remediation or "",
            }
            for f in flist
        ]

    prompt = _PROMPT.format(
        url=state["target_url"],
        tech_stack=tech_stack,
        surfaces=surfaces,
        findings_json=json.dumps(findings_by_surface, indent=2),
    )

    try:
        raw = await llm_complete(prompt, system=_SYSTEM, model_tier="reasoning")
        chains = _parse_chains(raw)
    except LLMError as exc:
        logger.warning("Chain agent v2 LLM failed: %s", exc)
        chains = []

    state["attack_chains"] = chains

    cross_surface = sum(
        1 for c in chains
        if len(set(s.surface for s in c.steps if s.surface)) > 1
    )
    state["progress_events"].append(
        _event(
            "completed",
            f"Chain discovery v2 done — {len(chains)} chain(s), "
            f"{cross_surface} cross-surface",
        )
    )
    return state


def _parse_chains(raw: str) -> list[AttackChain]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(raw[start:end])
        chains = []
        for item in data:
            steps = [
                ChainStep(
                    step=s.get("step", i + 1),
                    action=s.get("action", ""),
                    mitre_id=s.get("mitre_id", ""),
                    finding_id=s.get("finding_id"),
                    surface=s.get("surface"),
                )
                for i, s in enumerate(item.get("steps", []))
            ]
            chains.append(AttackChain(
                title=item.get("title", ""),
                description=item.get("description", ""),
                impact=item.get("impact", "medium"),
                likelihood=item.get("likelihood", "medium"),
                mitre_ids=item.get("mitre_ids", []),
                finding_ids=item.get("finding_ids", []),
                steps=steps,
            ))
        return chains
    except Exception as exc:
        logger.error("Failed to parse attack chains: %s", exc)
        return []
