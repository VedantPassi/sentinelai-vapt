from __future__ import annotations

from scanners.base import FindingData

_NOISE_TITLE_FRAGMENTS = (
    "test page",
    "default page",
    "welcome to",
    "tech-detect",
    "technologies",
)


def classify_finding(fd: FindingData, target_type: str = "web") -> str | None:
    """
    Deterministic pre-filter. Returns "false_positive" if a rule fires, None otherwise.
    Runs before LLM validation to avoid burning tokens on obvious noise.
    """
    # Rule 1: info severity is never exploitable
    if fd.severity.lower() == "info":
        return "false_positive"

    # Rule 2: missing-header findings only matter for web targets
    if fd.category.lower() == "missing-header" and target_type not in ("web", "api"):
        return "false_positive"

    # Rule 3: scanner noise on default/test server pages
    title_lower = fd.title.lower()
    if any(frag in title_lower for frag in _NOISE_TITLE_FRAGMENTS):
        return "false_positive"

    # Rule 4: scanner assigned zero risk on low/info — contradictory finding
    if fd.risk_score == 0 and fd.severity.lower() in ("low", "info"):
        return "false_positive"

    # Rule 5: placeholder description — scanner didn't populate it
    if len(fd.description.strip()) < 20:
        return "false_positive"

    return None
