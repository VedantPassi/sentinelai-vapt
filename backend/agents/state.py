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


class AgentState(TypedDict):
    scan_id: str
    target_url: str
    target_type: str  # web | api | network
    config: dict[str, Any]
    recon_data: ReconData | None
    attack_plan: AttackPlan | None
    findings: list[FindingData]
    current_node: str
    progress_events: list[ProgressEvent]
    error: str | None
