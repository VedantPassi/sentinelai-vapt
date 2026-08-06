from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from models.models import Finding


@dataclass
class Control:
    id: str
    name: str
    description: str
    match: Callable[[Finding], bool]


@dataclass
class ControlResult:
    control: Control
    status: str  # NON-COMPLIANT | REVIEW | COMPLIANT
    findings: list[Finding] = field(default_factory=list)


def _kw(f: Finding, *words: str) -> bool:
    text = f"{f.title or ''} {f.description or ''}".lower()
    return any(w in text for w in words)


def _cat(f: Finding, *cats: str) -> bool:
    return (f.category or "").lower() in cats


def _sev(f: Finding, *sevs: str) -> bool:
    return (f.severity or "").lower() in sevs


# ── SOC2 Trust Services Criteria ─────────────────────────────────────────────

_SOC2_CONTROLS: list[Control] = [
    Control(
        "CC6.1",
        "Logical Access Controls",
        "Logical access security software, infrastructure, and architectures are implemented.",
        lambda f: _cat(f, "ad", "web", "api") or _kw(f, "auth", "login", "password", "credential", "session", "privilege", "admin"),
    ),
    Control(
        "CC6.2",
        "User Provisioning",
        "New internal and external users are registered and authorized before access is granted.",
        lambda f: _cat(f, "ad") or _kw(f, "account", "provisioning", "group membership", "acl", "dacl", "permission"),
    ),
    Control(
        "CC6.6",
        "Threats from Outside",
        "Logical access security measures restrict access from outside the entity's boundaries.",
        lambda f: _cat(f, "network", "web", "api") or _kw(f, "injection", "xss", "ssrf", "rce", "exposure", "open port", "vulnerability"),
    ),
    Control(
        "CC6.7",
        "Data Transmission Integrity",
        "Transmission integrity and encryption requirements are met.",
        lambda f: _kw(f, "tls", "ssl", "https", "cipher", "certificate", "cleartext", "plaintext", "encryption"),
    ),
    Control(
        "CC7.1",
        "System Monitoring",
        "Detection and monitoring tools are implemented to identify anomalies.",
        lambda f: _sev(f, "critical", "high"),
    ),
    Control(
        "CC7.2",
        "Security Event Evaluation",
        "Detected security events are evaluated to determine impact.",
        lambda f: _sev(f, "critical", "high") or _cat(f, "ad", "cloud"),
    ),
    Control(
        "CC8.1",
        "Change Management",
        "Changes to infrastructure, data, software, and procedures are authorized.",
        lambda f: _cat(f, "container") or _kw(f, "configuration", "misconfiguration", "default", "outdated", "cve"),
    ),
    Control(
        "CC9.2",
        "Risk Assessment",
        "The entity identifies, assesses, and communicates risks.",
        lambda f: _sev(f, "critical", "high", "medium"),
    ),
]

# ── ISO 27001:2022 Annex A ────────────────────────────────────────────────────

_ISO27001_CONTROLS: list[Control] = [
    Control(
        "A.5.23",
        "Information Security for Cloud Services",
        "Processes for acquisition, use, management and exit from cloud services.",
        lambda f: _cat(f, "cloud") or _kw(f, "aws", "azure", "gcp", "s3", "iam", "bucket"),
    ),
    Control(
        "A.8.8",
        "Management of Technical Vulnerabilities",
        "Technical vulnerabilities are identified, evaluated, and remediated.",
        lambda f: _kw(f, "cve", "vulnerability", "patch", "outdated", "unpatched"),
    ),
    Control(
        "A.9.1",
        "Access Control Policy",
        "An access control policy is established and implemented.",
        lambda f: _cat(f, "ad") or _kw(f, "privilege", "access control", "permission", "authorization", "acl"),
    ),
    Control(
        "A.9.4",
        "System and Application Access Control",
        "Access to systems and applications is restricted per access control policy.",
        lambda f: _cat(f, "web", "api") or _kw(f, "auth", "session", "login", "bola", "bfla", "broken access"),
    ),
    Control(
        "A.10.1",
        "Cryptographic Controls",
        "A policy on the use of cryptographic controls for protection of information.",
        lambda f: _kw(f, "tls", "ssl", "cipher", "encryption", "certificate", "key", "secret", "cleartext"),
    ),
    Control(
        "A.12.1",
        "Operational Security",
        "Operating procedures are documented and implemented.",
        lambda f: _cat(f, "network", "container") or _kw(f, "open port", "firewall", "network", "misconfiguration"),
    ),
    Control(
        "A.14.2",
        "Security in Development",
        "Security is designed and implemented within development lifecycle.",
        lambda f: _cat(f, "web", "api") or _kw(f, "injection", "xss", "rce", "code", "sast", "insecure"),
    ),
    Control(
        "A.16.1",
        "Incident Management",
        "Information security incidents are managed consistently and effectively.",
        lambda f: _sev(f, "critical", "high"),
    ),
]

# ── PCI-DSS v4 ────────────────────────────────────────────────────────────────

_PCI_CONTROLS: list[Control] = [
    Control(
        "Req 1",
        "Network Security Controls",
        "Install and maintain network security controls.",
        lambda f: _cat(f, "network") or _kw(f, "firewall", "network", "port", "open port", "topology"),
    ),
    Control(
        "Req 2",
        "Secure Configurations",
        "Apply secure configurations to all system components.",
        lambda f: _cat(f, "container", "network") or _kw(f, "default", "misconfiguration", "hardening", "baseline"),
    ),
    Control(
        "Req 3",
        "Protect Stored Data",
        "Protect stored account data.",
        lambda f: _kw(f, "secret", "api key", "token", "credential", "password", "plaintext", "storage"),
    ),
    Control(
        "Req 4",
        "Protect Data in Transit",
        "Protect cardholder data with strong cryptography during transmission.",
        lambda f: _kw(f, "tls", "ssl", "https", "cipher", "cleartext", "plaintext", "certificate"),
    ),
    Control(
        "Req 6",
        "Secure Systems and Software",
        "Develop and maintain secure systems and software.",
        lambda f: _cat(f, "web", "api") or _kw(f, "injection", "xss", "csrf", "rce", "vulnerability", "cve", "insecure"),
    ),
    Control(
        "Req 7",
        "Restrict Access",
        "Restrict access to system components based on business need.",
        lambda f: _cat(f, "ad") or _kw(f, "privilege", "authorization", "permission", "access control"),
    ),
    Control(
        "Req 8",
        "Identify and Authenticate Users",
        "Identify users and authenticate access to system components.",
        lambda f: _kw(f, "auth", "login", "password", "credential", "mfa", "session", "brute force"),
    ),
    Control(
        "Req 10",
        "Log and Monitor",
        "Log and monitor all access to system components and cardholder data.",
        lambda f: _sev(f, "critical", "high") or _kw(f, "logging", "monitoring", "audit", "log"),
    ),
    Control(
        "Req 11",
        "Test Security Regularly",
        "Test security of systems and networks regularly.",
        lambda f: _sev(f, "critical", "high", "medium"),
    ),
]

FRAMEWORKS: dict[str, list[Control]] = {
    "soc2": _SOC2_CONTROLS,
    "iso27001": _ISO27001_CONTROLS,
    "pci-dss": _PCI_CONTROLS,
}

FRAMEWORK_NAMES: dict[str, str] = {
    "soc2": "SOC 2 Type II — Trust Services Criteria",
    "iso27001": "ISO/IEC 27001:2022 — Annex A Controls",
    "pci-dss": "PCI-DSS v4.0 — Requirements",
}


def evaluate_framework(framework: str, findings: list[Finding]) -> list[ControlResult]:
    controls = FRAMEWORKS.get(framework, [])
    results: list[ControlResult] = []
    actionable = [f for f in findings if f.status != "false_positive"]

    for control in controls:
        matched = [f for f in actionable if control.match(f)]
        if not matched:
            status = "COMPLIANT"
        elif any(f.status == "confirmed" for f in matched):
            status = "NON-COMPLIANT"
        else:
            status = "REVIEW"
        results.append(ControlResult(control=control, status=status, findings=matched))

    return results
