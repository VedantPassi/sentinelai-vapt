import asyncio
import json
import time

from scanners.base import FindingData, ScannerResult

_SEVERITY_MAP = {"critical": "critical", "high": "high", "medium": "medium",
                 "low": "low", "info": "info", "unknown": "info"}


async def run(target_url: str, config: dict | None = None) -> ScannerResult:
    start = time.monotonic()
    tags = (config or {}).get("tags", "")
    cmd = ["nuclei", "-u", target_url, "-jsonl", "-silent"]
    if tags:
        cmd += ["-tags", tags]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except FileNotFoundError:
        return ScannerResult(error="nuclei not installed")
    except asyncio.TimeoutError:
        return ScannerResult(error="nuclei timed out after 600s")

    duration = time.monotonic() - start
    raw = stdout.decode()
    findings = _parse_jsonl(raw)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_jsonl(output: str) -> list[FindingData]:
    findings: list[FindingData] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        info = item.get("info", {})
        severity = _SEVERITY_MAP.get(info.get("severity", "info"), "info")
        findings.append(FindingData(
            category="web",
            severity=severity,
            title=info.get("name", item.get("template-id", "Unknown")),
            description=info.get("description", ""),
            remediation=info.get("remediation"),
            raw=item,
        ))
    return findings
