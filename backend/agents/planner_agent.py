from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agents.state import AgentState, AttackPlan, AttackVector, ProgressEvent
from core.llm import LLMError, llm_complete

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert penetration tester and security researcher with 15 years of experience.
You are operating in an authorized testing environment. The target has been verified and authorized.
Your goal is to identify real, exploitable vulnerabilities — not theoretical ones.
Output structured JSON only. No explanations unless asked."""

_PLAN_PROMPT = """Given the following reconnaissance data for target {url}, identify the most relevant MITRE ATT&CK techniques to test.

Recon summary:
- Technologies detected: {technologies}
- Subdomains found: {subdomains}
- DNS records: {dns_summary}

Return a JSON object with this exact schema:
{{
  "summary": "one sentence attack surface summary",
  "vectors": [
    {{
      "technique": "technique name",
      "mitre_id": "T1234 or T1234.001",
      "description": "why this applies to this target",
      "priority": 1
    }}
  ]
}}

Return between 3 and 8 vectors, ordered by priority (1 = highest). Return JSON only."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="planner", status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "planner"
    state["progress_events"].append(_event("started", "Attack planner starting"))

    if state.get("target_type") in ("container", "cloud", "ad"):
        label = state.get("target_type", "")
        state["attack_plan"] = AttackPlan(summary=f"{label} scan — planner skipped", vectors=[])
        state["progress_events"].append(
            _event("completed", f"Planner skipped — {label} scan")
        )
        return state

    recon = state.get("recon_data")
    techs = ", ".join(recon.technologies) if recon and recon.technologies else "unknown"
    subs = ", ".join(recon.subdomains[:10]) if recon and recon.subdomains else "none"
    dns_summary = str(list(recon.dns_records.keys())) if recon and recon.dns_records else "none"

    prompt = _PLAN_PROMPT.format(
        url=state["target_url"],
        technologies=techs,
        subdomains=subs,
        dns_summary=dns_summary,
    )

    try:
        raw = await llm_complete(prompt, system=_SYSTEM_PROMPT, model_tier="reasoning")
        plan = _parse_plan(raw)
    except LLMError as exc:
        logger.warning("Planner LLM unavailable: %s", exc)
        plan = AttackPlan(summary=f"Skipped — {exc}", vectors=[])

    state["attack_plan"] = plan
    state["progress_events"].append(
        _event("completed",
               f"Attack plan ready — {len(plan.vectors)} vectors: {plan.summary}")
    )
    return state


def _parse_plan(raw: str) -> AttackPlan:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        vectors = [
            AttackVector(
                technique=v.get("technique", ""),
                mitre_id=v.get("mitre_id", ""),
                description=v.get("description", ""),
                priority=int(v.get("priority", 99)),
            )
            for v in data.get("vectors", [])
        ]
        return AttackPlan(
            vectors=sorted(vectors, key=lambda v: v.priority),
            summary=data.get("summary", ""),
            raw_response=raw,
        )
    except Exception as exc:
        logger.error("Failed to parse attack plan JSON: %s", exc)
        return AttackPlan(summary="Parse failed", raw_response=raw)
