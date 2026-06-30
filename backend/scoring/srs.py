from __future__ import annotations

_SEVERITY_MAP = {
    "critical": 100,
    "high": 75,
    "medium": 50,
    "low": 25,
    "info": 0,
}

_CONFIDENCE_MAP = {
    "confirmed": 100,
    "open": 50,
    "false_positive": 0,
}


def compute_srs(
    severity: str,
    exploitability: int,
    asset_criticality: int,
    status: str,
) -> int:
    """
    Security Risk Score (0–100).

    Weights: severity 40%, exploitability 30%, asset criticality 20%, confidence 10%.
    False positives always score 0.
    """
    if status == "false_positive":
        return 0

    sev = _SEVERITY_MAP.get(severity.lower(), 0)
    expl = max(0, min(100, exploitability))
    asset = max(0, min(100, asset_criticality))
    conf = _CONFIDENCE_MAP.get(status, 50)

    score = (sev * 0.40) + (expl * 0.30) + (asset * 0.20) + (conf * 0.10)
    return round(score)
