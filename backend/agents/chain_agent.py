from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, AttackChain, ChainStep, ProgressEvent
from core.llm import LLMError, llm_complete

logger = logging.getLogger(__name__)

_MAX_FINDINGS = 20

_SYSTEM = """You are an expert penetration tester modeling realistic multi-step attack chains.
Given a set of confirmed vulnerabilities, identify how an attacker would chain them together.
Focus on realistic, exploitable paths — not theoretical sequences.
Output JSON only."""

_PROMPT = """Target: {url}
Tech stack: {tech_stack}

Confirmed vulnerabilities:
{findings_json}

Identify 1–5 realistic multi-step attack chains an attacker could execute against this target.
Each chain must reference specific vulnerability IDs from the list above.

Return a JSON array:
[
  {{
    "title": "short chain title",
    "description": "2-3 sentence narrative of the attack path",
    "impact": "critical|high|medium|low",
    "likelihood": "high|medium|low",
    "mitre_ids": ["T1234", "T1234.001"],
    "finding_ids": ["<uuid>", "<uuid>"],
    "steps": [
      {{
        "step": 1,
        "action": "what the attacker does",
        "mitre_id": "T1234",
        "finding_id": "<uuid or null>"
      }}
    ]
  }}
]

Return JSON only. No explanation outside the array."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="chain", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "chain"

    confirmed = [f for f in state.get("findings", []) if f.status == "confirmed"]

    if not confirmed:
        state["progress_events"].append(
            _event("completed", "No confirmed findings — chain discovery skipped")
        )
        return state

    state["progress_events"].append(
        _event("started", f"Discovering attack chains from {len(confirmed)} confirmed findings")
    )

    # cap at 20 highest-risk findings
    top = sorted(confirmed, key=lambda f: f.risk_score, reverse=True)[:_MAX_FINDINGS]

    recon = state.get("recon_data")
    tech_stack = ", ".join(recon.technologies) if recon and recon.technologies else "unknown"

    findings_json = json.dumps([
        {
            "id": str(i),
            "title": f.title,
            "severity": f.severity,
            "category": f.category,
            "description": f.description,
            "risk_score": f.risk_score,
        }
        for i, f in enumerate(top)
    ], indent=2)

    prompt = _PROMPT.format(
        url=state["target_url"],
        tech_stack=tech_stack,
        findings_json=findings_json,
    )

    try:
        raw = await llm_complete(prompt, system=_SYSTEM, model_tier="reasoning")
        chains = _parse_chains(raw)
    except LLMError as exc:
        logger.warning("Chain agent LLM failed: %s", exc)
        chains = []

    state["attack_chains"] = chains
    state["progress_events"].append(
        _event("completed", f"Chain discovery done — {len(chains)} attack chain(s) identified")
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
