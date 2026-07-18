import asyncio
import json
import logging
import time

from scanners.base import FindingData, ScannerResult

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "UNKNOWN": "info",
}


async def run(target: str, config: dict | None = None) -> ScannerResult:
    """Scan a container image or filesystem path with Trivy.

    target: container image ref (e.g. 'python:3.12-slim') or 'fs:/path/to/dir'
    """
    cfg = config or {}
    timeout = cfg.get("timeout", 300)
    start = time.monotonic()

    if target.startswith("fs:"):
        scan_type = "fs"
        scan_target = target[3:]
    else:
        scan_type = "image"
        scan_target = target

    cmd = [
        "trivy", scan_type,
        "--format", "json",
        "--quiet",
        "--no-progress",
        scan_target,
    ]

    logger.info("trivy: cmd=%s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except FileNotFoundError:
        return ScannerResult(error="trivy not installed")
    except asyncio.TimeoutError:
        return ScannerResult(error=f"trivy timed out after {timeout}s")

    duration = time.monotonic() - start
    raw = stdout.decode()

    logger.info(
        "trivy: rc=%s duration=%.1fs stdout=%d bytes stderr=%s",
        proc.returncode, duration, len(raw), stderr.decode()[:500],
    )

    if proc.returncode not in (0, 1):
        return ScannerResult(
            raw_output=stderr.decode(),
            duration_seconds=duration,
            error=f"trivy exited {proc.returncode}: {stderr.decode()[:2000]}",
        )

    findings = _parse_json(raw, scan_target)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_json(raw: str, target: str) -> list[FindingData]:
    findings: list[FindingData] = []
    if not raw.strip():
        return findings

    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("trivy: failed to parse JSON: %s", exc)
        return findings

    results = report.get("Results", [])
    for result in results:
        target_name = result.get("Target", target)
        result_type = result.get("Type", "")

        for vuln in result.get("Vulnerabilities") or []:
            cve_id = vuln.get("VulnerabilityID", "UNKNOWN")
            pkg = vuln.get("PkgName", "unknown")
            installed = vuln.get("InstalledVersion", "?")
            fixed = vuln.get("FixedVersion", "")
            raw_sev = vuln.get("Severity", "UNKNOWN")
            severity = _SEVERITY_MAP.get(raw_sev, "info")
            title = vuln.get("Title") or f"{cve_id} in {pkg}"
            description = vuln.get("Description") or title
            cvss_score = _extract_cvss(vuln)

            remediation = None
            if fixed:
                remediation = f"Upgrade {pkg} from {installed} to {fixed}"

            findings.append(FindingData(
                category="container",
                severity=severity,
                title=f"{cve_id} — {pkg} {installed} ({result_type})",
                description=f"{title}\n\nTarget: {target_name}\n{description}",
                remediation=remediation,
                raw={
                    "cve_id": cve_id,
                    "pkg": pkg,
                    "installed": installed,
                    "fixed": fixed,
                    "severity": raw_sev,
                    "cvss": cvss_score,
                    "target": target_name,
                    "type": result_type,
                },
            ))

        for secret in result.get("Secrets") or []:
            rule_id = secret.get("RuleID", "secret")
            category = secret.get("Category", "secret")
            match = secret.get("Match", "")

            findings.append(FindingData(
                category="secrets",
                severity="high",
                title=f"Secret detected — {rule_id} in {target_name}",
                description=f"Category: {category}\nMatch (redacted): {match[:80]}",
                remediation="Remove secret from image/repo and rotate credentials.",
                raw={"rule_id": rule_id, "category": category, "target": target_name},
            ))

        for mis in result.get("Misconfigurations") or []:
            mis_id = mis.get("ID", "MISC")
            raw_sev = mis.get("Severity", "UNKNOWN")
            severity = _SEVERITY_MAP.get(raw_sev, "info")
            mis_title = mis.get("Title", mis_id)
            mis_desc = mis.get("Description", "")
            resolution = mis.get("Resolution", "")

            findings.append(FindingData(
                category="misconfiguration",
                severity=severity,
                title=f"{mis_id} — {mis_title}",
                description=f"Target: {target_name}\n{mis_desc}",
                remediation=resolution or None,
                raw={"id": mis_id, "severity": raw_sev, "target": target_name},
            ))

    return findings


def _extract_cvss(vuln: dict) -> float | None:
    for source in ("nvd", "ghsa", "redhat"):
        try:
            return vuln["CVSS"][source]["V3Score"]
        except (KeyError, TypeError):
            pass
    return None
