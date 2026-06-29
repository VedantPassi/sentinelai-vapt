import asyncio
import json
import time
import uuid

from scanners.base import FindingData, ScannerResult

_RISK_MAP = {"High": "high", "Medium": "medium", "Low": "low", "Informational": "info"}


async def run(target_url: str, config: dict | None = None) -> ScannerResult:
    start = time.monotonic()
    run_id = uuid.uuid4().hex
    host_dir = f"/tmp/zap-{run_id}"
    container_report = "/zap/wrk/report.json"

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{host_dir}:/zap/wrk",
        "ghcr.io/zaproxy/zaproxy:stable",
        "zap-baseline.py",
        "-t", target_url,
        "-J", container_report,
        "-I",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except FileNotFoundError:
        return ScannerResult(error="docker not installed or not in PATH")
    except asyncio.TimeoutError:
        return ScannerResult(error="ZAP scan timed out after 600s")

    duration = time.monotonic() - start
    raw = stdout.decode() + stderr.decode()

    try:
        with open(f"{host_dir}/report.json") as f:
            report = json.load(f)
        findings = _parse_report(report)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return ScannerResult(raw_output=raw, duration_seconds=duration,
                             error=f"ZAP report parse failed: {exc}")

    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_report(report: dict) -> list[FindingData]:
    findings: list[FindingData] = []
    for site in report.get("site", []):
        for alert in site.get("alerts", []):
            risk = alert.get("riskdesc", "Informational").split(" ")[0]
            severity = _RISK_MAP.get(risk, "info")
            findings.append(FindingData(
                category="web",
                severity=severity,
                title=alert.get("alert", "Unknown"),
                description=alert.get("desc", ""),
                remediation=alert.get("solution"),
                raw=alert,
            ))
    return findings
