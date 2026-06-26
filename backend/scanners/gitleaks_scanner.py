import asyncio
import json
import time

from scanners.base import FindingData, ScannerResult


async def run(target_path: str, config: dict | None = None) -> ScannerResult:
    start = time.monotonic()

    cmd = ["gitleaks", "detect", "--source", target_path, "--report-format", "json",
           "--report-path", "/dev/stdout", "--no-banner"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except FileNotFoundError:
        return ScannerResult(error="gitleaks not installed")
    except asyncio.TimeoutError:
        return ScannerResult(error="gitleaks timed out after 120s")

    duration = time.monotonic() - start
    raw = stdout.decode()

    if not raw.strip():
        return ScannerResult(raw_output="No leaks found", duration_seconds=duration)

    try:
        leaks = json.loads(raw)
    except json.JSONDecodeError:
        return ScannerResult(raw_output=raw, duration_seconds=duration,
                             error="gitleaks output not valid JSON")

    findings = _parse(leaks)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse(leaks: list) -> list[FindingData]:
    findings: list[FindingData] = []
    for leak in leaks:
        rule = leak.get("RuleID", "unknown-rule")
        file_path = leak.get("File", "")
        line = leak.get("StartLine", 0)
        findings.append(FindingData(
            category="secrets",
            severity="high",
            title=f"Secret detected: {leak.get('Description', rule)}",
            description=f"Rule '{rule}' matched in {file_path}:{line}. "
                        f"Commit: {leak.get('Commit', 'unknown')[:8]}.",
            remediation="Rotate the exposed secret immediately. Remove from git history with git-filter-repo.",
            raw=leak,
        ))
    return findings
