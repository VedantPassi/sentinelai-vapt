import asyncio
import json
import time

from scanners.base import FindingData, ScannerResult

_SEVERITY_MAP = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}


async def run(target_path: str, config: dict | None = None) -> ScannerResult:
    start = time.monotonic()
    ruleset = (config or {}).get("ruleset", "auto")

    cmd = ["semgrep", "--config", ruleset, "--json", target_path]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except FileNotFoundError:
        return ScannerResult(error="semgrep not installed")
    except asyncio.TimeoutError:
        return ScannerResult(error="semgrep timed out after 300s")

    duration = time.monotonic() - start
    raw = stdout.decode()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ScannerResult(raw_output=raw, duration_seconds=duration,
                             error="semgrep output not valid JSON")

    findings = _parse(data)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse(data: dict) -> list[FindingData]:
    findings: list[FindingData] = []
    for result in data.get("results", []):
        extra = result.get("extra", {})
        severity = _SEVERITY_MAP.get(extra.get("severity", "INFO"), "low")
        path = result.get("path", "")
        line = result.get("start", {}).get("line", 0)
        findings.append(FindingData(
            category="sast",
            severity=severity,
            title=extra.get("message", result.get("check_id", "Unknown")),
            description=f"{path}:{line} — {extra.get('message', '')}",
            remediation=extra.get("fix"),
            raw=result,
        ))
    return findings
