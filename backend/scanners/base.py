from dataclasses import dataclass, field
from typing import Any


@dataclass
class FindingData:
    category: str
    severity: str  # critical | high | medium | low | info
    title: str
    description: str
    srs_score: float | None = None
    poc_evidence: str | None = None
    remediation: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    status: str = "open"  # open | confirmed | false_positive
    risk_score: int = 0
    validation_reasoning: str = ""


@dataclass
class ScannerResult:
    findings: list[FindingData] = field(default_factory=list)
    raw_output: str = ""
    duration_seconds: float = 0.0
    error: str | None = None
