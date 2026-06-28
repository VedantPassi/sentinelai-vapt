from __future__ import annotations

import asyncio
import uuid

from celery import Celery

from core.config import settings

celery_app = Celery(
    "sentinel_agents",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


@celery_app.task(name="workers.agent_worker.run_agent_task", bind=True, max_retries=1)
def run_agent_task(self, scan_id: str, target_url: str, target_type: str, config: dict) -> dict:
    return asyncio.run(_run(scan_id, target_url, target_type, config))


async def _run(scan_id: str, target_url: str, target_type: str, config: dict) -> dict:
    from datetime import datetime, timezone

    from sqlalchemy import select

    from agents.runtime import run_agent_scan
    from core.db import AsyncSessionLocal
    from models.models import Finding, ScanJob

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            return {"error": "scan not found"}

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.config = {**(scan.config or {}), "progress_events": []}
        await db.commit()

    try:
        final_state = await run_agent_scan(scan_id, target_url, target_type, config)
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id)))
            scan = result.scalar_one_or_none()
            if scan:
                scan.status = "failed"
                scan.completed_at = datetime.now(timezone.utc)
                scan.config = {**(scan.config or {}), "error": str(exc)}
                await db.commit()
        return {"error": str(exc)}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            return {"error": "scan disappeared"}

        events = [
            {"node": e.node, "status": e.status, "message": e.message, "timestamp": e.timestamp}
            for e in final_state.get("progress_events", [])
        ]
        scan.status = "completed" if not final_state.get("error") else "failed"
        scan.completed_at = datetime.now(timezone.utc)
        scan.config = {**(scan.config or {}), "progress_events": events,
                       "error": final_state.get("error")}
        await db.commit()

        for fd in final_state.get("findings", []):
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

    return {
        "findings": len(final_state.get("findings", [])),
        "status": scan.status,
    }
