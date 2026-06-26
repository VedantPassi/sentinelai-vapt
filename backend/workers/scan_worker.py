import asyncio
import uuid
from datetime import datetime, timezone

from celery import Celery

from core.config import settings

celery_app = Celery(
    "sentinel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


@celery_app.task(name="workers.scan_worker.run_scan", bind=True, max_retries=2)
def run_scan(self, scan_id: str, target_url: str, scan_type: str, config: dict) -> dict:
    return asyncio.run(_run(scan_id, target_url, scan_type, config))


async def _run(scan_id: str, target_url: str, scan_type: str, config: dict) -> dict:
    from sqlalchemy import select

    from core.db import AsyncSessionLocal
    from models.models import Finding, ScanJob
    from scanners.base import ScannerResult

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            return {"error": "scan not found"}

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        await db.commit()

        scanner_result: ScannerResult = await _dispatch(scan_type, target_url, config)

        scan.status = "failed" if scanner_result.error else "completed"
        scan.completed_at = datetime.now(timezone.utc)
        await db.commit()

        if scanner_result.error:
            return {"error": scanner_result.error}

        for fd in scanner_result.findings:
            finding = Finding(
                id=uuid.uuid4(),
                scan_id=uuid.UUID(scan_id),
                category=fd.category,
                severity=fd.severity,
                title=fd.title,
                description=fd.description,
                srs_score=fd.srs_score,
                poc_evidence=fd.poc_evidence,
                remediation=fd.remediation,
                status="open",
                confirmed=False,
            )
            db.add(finding)

        await db.commit()
        return {"findings": len(scanner_result.findings), "duration": scanner_result.duration_seconds}


async def _dispatch(scan_type: str, target_url: str, config: dict):
    from scanners import (
        gitleaks_scanner,
        nmap_scanner,
        nuclei_scanner,
        semgrep_scanner,
        zap_scanner,
    )
    from scanners.base import ScannerResult

    dispatch = {
        "web": zap_scanner.run,
        "api": nuclei_scanner.run,
        "network": nmap_scanner.run,
        "sast": semgrep_scanner.run,
        "secrets": gitleaks_scanner.run,
    }

    runner = dispatch.get(scan_type)
    if not runner:
        return ScannerResult(error=f"Unknown scan_type: {scan_type}")

    return await runner(target_url, config)
