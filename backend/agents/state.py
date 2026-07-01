from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypedDict

from scanners.base import FindingData


@dataclass
class ReconData:
    subdomains: list[str] = field(default_factory=list)
    open_ports: list[dict[str, Any]] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    dns_records: dict[str, list[str]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackVector:
    technique: str
    mitre_id: str
    description: str
    priority: int


@dataclass
class AttackPlan:
    vectors: list[AttackVector] = field(default_factory=list)
    summary: str = ""
    raw_response: str = ""


@dataclass
class ProgressEvent:
    node: str
    status: str  # started | completed | failed
    message: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ChainStep:
    step: int
    action: str
    mitre_id: str
    finding_id: str | None = None


@dataclass
class AttackChain:
    title: str
    description: str
    impact: str  # critical | high | medium | low
    likelihood: str  # high | medium | low
    mitre_ids: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    steps: list[ChainStep] = field(default_factory=list)


class AgentState(TypedDict):
    scan_id: str
    target_url: str
    target_type: str  # web | api | network
    config: dict[str, Any]
    recon_data: ReconData | None
    attack_plan: AttackPlan | None
    findings: list[FindingData]
    attack_chains: list[AttackChain]
    current_node: str
    progress_events: list[ProgressEvent]
    error: str | None
