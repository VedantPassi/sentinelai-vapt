import asyncio
import json
import logging
import os
import time
from pathlib import Path

from scanners.base import FindingData, ScannerResult

logger = logging.getLogger(__name__)

_PROWLER_VENV = Path(__file__).parent.parent / ".prowler-venv" / "bin" / "prowler"

_SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
}


async def run(target: str = "aws", config: dict | None = None) -> ScannerResult:
    """Run Prowler against AWS account. target is ignored (uses env creds)."""
    cfg = config or {}
    timeout = cfg.get("timeout", 600)
    services = cfg.get("services", ["iam", "s3", "ec2", "guardduty", "cloudtrail"])
    checks_filter = cfg.get("checks")

    if not _PROWLER_VENV.exists():
        return ScannerResult(error=f"Prowler venv not found at {_PROWLER_VENV}")

    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or cfg.get("aws_access_key_id")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or cfg.get("aws_secret_access_key")
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    if not aws_key or not aws_secret:
        return ScannerResult(error="AWS credentials not set — add AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY to .env")

    cmd = [
        str(_PROWLER_VENV),
        "aws",
        "--output-formats", "json-ocsf",
        "--no-banner",
        "--ignore-exit-code-3",
        "-r", aws_region,
        "-s", *services,
    ]

    if checks_filter:
        cmd += ["-c", *checks_filter]

    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": aws_key,
        "AWS_SECRET_ACCESS_KEY": aws_secret,
        "AWS_DEFAULT_REGION": aws_region,
    }

    logger.info("prowler: cmd=%s", " ".join(cmd[:8]) + " ...")
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except FileNotFoundError:
        return ScannerResult(error="Prowler binary not found")
    except asyncio.TimeoutError:
        return ScannerResult(error=f"Prowler timed out after {timeout}s")

    duration = time.monotonic() - start
    raw = stdout.decode()

    logger.info(
        "prowler: rc=%s duration=%.1fs stdout=%d bytes stderr=%s",
        proc.returncode, duration, len(raw), stderr.decode()[:300],
    )

    if proc.returncode not in (0, 3):
        return ScannerResult(
            raw_output=stderr.decode(),
            duration_seconds=duration,
            error=f"prowler exited {proc.returncode}: {stderr.decode()[:2000]}",
        )

    findings = _parse_ocsf(raw)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_ocsf(raw: str) -> list[FindingData]:
    findings: list[FindingData] = []
    if not raw.strip():
        return findings

    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        status = record.get("status", "").lower()
        if status in ("pass", "manual", "not_available"):
            continue

        raw_sev = (record.get("severity") or "informational").lower()
        severity = _SEVERITY_MAP.get(raw_sev, "info")

        check_id = record.get("check_id", "unknown")
        title = record.get("check_title") or check_id
        resource = record.get("resource_uid") or record.get("resource_name") or "unknown"
        region = record.get("region") or "global"
        description = record.get("description") or title
        remediation = _extract_remediation(record)
        service = record.get("service_name") or "aws"
        account = record.get("cloud", {}).get("account", {}).get("uid", "")

        findings.append(FindingData(
            category="cloud",
            severity=severity,
            title=f"{check_id} — {resource} ({region})",
            description=f"{title}\n\nResource: {resource}\nAccount: {account}\nRegion: {region}\n\n{description}",
            remediation=remediation,
            raw={
                "check_id": check_id,
                "service": service,
                "resource": resource,
                "region": region,
                "account": account,
                "status": status,
                "severity": raw_sev,
            },
        ))

    return findings


def _extract_remediation(record: dict) -> str | None:
    rem = record.get("remediation")
    if not rem:
        return None
    if isinstance(rem, str):
        return rem
    if isinstance(rem, dict):
        text = rem.get("recommendation") or rem.get("text") or ""
        url = rem.get("url") or ""
        return f"{text} {url}".strip() or None
    return None
