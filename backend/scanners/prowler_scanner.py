import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path

from scanners.base import FindingData, ScannerResult

logger = logging.getLogger(__name__)

_PROWLER_BIN = Path(__file__).parent.parent / ".prowler-venv" / "bin" / "prowler"

_SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
}

_FAIL_STATUSES = {"fail", "fail_manual", "muted"}


async def run(target: str = "aws", config: dict | None = None) -> ScannerResult:
    cfg = config or {}
    timeout = cfg.get("timeout", 600)
    services = cfg.get("services", ["iam", "s3", "ec2", "guardduty", "cloudtrail"])

    if not _PROWLER_BIN.exists():
        return ScannerResult(error=f"Prowler venv not found at {_PROWLER_BIN}")

    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or cfg.get("aws_access_key_id", "")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or cfg.get("aws_secret_access_key", "")
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    if not aws_key or not aws_secret:
        return ScannerResult(
            error="AWS credentials not set — add AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY to .env"
        )

    with tempfile.TemporaryDirectory() as outdir:
        out_name = "prowler-scan"
        cmd = [
            str(_PROWLER_BIN), "aws",
            "--output-formats", "json-ocsf",
            "--no-banner",
            "--ignore-exit-code-3",
            "--region", aws_region,
            "--service", *services,
            "--output-directory", outdir,
            "--output-filename", out_name,
        ]

        env = {
            **os.environ,
            "AWS_ACCESS_KEY_ID": aws_key,
            "AWS_SECRET_ACCESS_KEY": aws_secret,
            "AWS_DEFAULT_REGION": aws_region,
        }

        logger.info("prowler: services=%s region=%s", services, aws_region)
        start = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except FileNotFoundError:
            return ScannerResult(error="Prowler binary not found")
        except asyncio.TimeoutError:
            return ScannerResult(error=f"Prowler timed out after {timeout}s")

        duration = time.monotonic() - start
        logger.info("prowler: rc=%s duration=%.1fs stderr=%s",
                    proc.returncode, duration, stderr.decode()[:300])

        if proc.returncode not in (0, 3):
            return ScannerResult(
                duration_seconds=duration,
                error=f"prowler exited {proc.returncode}: {stderr.decode()[:2000]}",
            )

        out_file = Path(outdir) / f"{out_name}.ocsf.json"
        if not out_file.exists():
            return ScannerResult(
                duration_seconds=duration,
                error="Prowler produced no output file",
            )

        raw = out_file.read_text()
        findings = _parse_ocsf(raw)
        return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_ocsf(raw: str) -> list[FindingData]:
    findings: list[FindingData] = []
    if not raw.strip():
        return findings

    try:
        records = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("prowler: JSON parse failed: %s", exc)
        return findings

    if not isinstance(records, list):
        records = [records]

    for record in records:
        status = (record.get("status_code") or "").lower()
        if status not in _FAIL_STATUSES:
            continue

        raw_sev = (record.get("severity") or "Informational").lower()
        severity = _SEVERITY_MAP.get(raw_sev, "info")

        metadata = record.get("metadata") or {}
        check_id = metadata.get("event_code") or "unknown"

        finding_info = record.get("finding_info") or {}
        title = finding_info.get("title") or check_id
        description = finding_info.get("desc") or title

        resources = record.get("resources") or [{}]
        resource = resources[0]
        resource_uid = resource.get("uid") or resource.get("name") or "unknown"
        region = resource.get("region") or "global"

        cloud = record.get("cloud") or {}
        account = (cloud.get("account") or {}).get("uid") or ""

        remediation = _extract_remediation(record.get("remediation"))
        service = (record.get("api") or {}).get("service") or check_id.split("_")[0]

        findings.append(FindingData(
            category="cloud",
            severity=severity,
            title=f"{check_id} — {resource_uid} ({region})",
            description=f"{title}\n\nResource: {resource_uid}\nAccount: {account}\nRegion: {region}\n\n{description}",
            remediation=remediation,
            raw={
                "check_id": check_id,
                "service": service,
                "resource": resource_uid,
                "region": region,
                "account": account,
                "status": status,
                "severity": raw_sev,
            },
        ))

    return findings


def _extract_remediation(rem: object) -> str | None:
    if not rem:
        return None
    if isinstance(rem, str):
        return rem
    if isinstance(rem, dict):
        text = rem.get("desc") or rem.get("recommendation") or ""
        refs = rem.get("references") or []
        url = refs[0] if refs else ""
        return f"{text} {url}".strip() or None
    return None
