from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

celery_app = Celery(
    "sentinel_agents",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


@asynccontextmanager
async def _make_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh engine + session bound to the current event loop."""
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await engine.dispose()


@celery_app.task(name="workers.agent_worker.run_agent_task", bind=True, max_retries=1)
def run_agent_task(self, scan_id: str, target_url: str, target_type: str, config: dict) -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run(scan_id, target_url, target_type, config))
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _run(scan_id: str, target_url: str, target_type: str, config: dict) -> dict:
    from datetime import datetime, timezone

    from sqlalchemy import select

    from agents.runtime import run_agent_scan
    from models.models import Finding, ScanJob, Target
    from scoring.srs import compute_srs

    async with _make_session() as db:
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
        async with _make_session() as db:
            result = await db.execute(select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id)))
            scan = result.scalar_one_or_none()
            if scan:
                scan.status = "failed"
                scan.completed_at = datetime.now(timezone.utc)
                scan.config = {**(scan.config or {}), "error": str(exc)}
                await db.commit()
        return {"error": str(exc)}

    async with _make_session() as db:
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

        target_result = await db.execute(select(Target).where(Target.id == scan.target_id))
        target = target_result.scalar_one_or_none()
        asset_score = round((target.asset_criticality or 0.0) * 100) if target else 0

        for fd in final_state.get("findings", []):
            fd_status = fd.status if fd.status in ("confirmed", "false_positive") else "open"
            finding = Finding(
                id=uuid.uuid4(),
                scan_id=uuid.UUID(scan_id),
                category=fd.category,
                severity=fd.severity,
                title=fd.title,
                description=fd.description,
                srs_score=compute_srs(fd.severity, fd.risk_score, asset_score, fd_status),
                poc_evidence=fd.poc_evidence,
                remediation=fd.remediation,
                status=fd_status,
                confirmed=fd_status == "confirmed",
            )
            db.add(finding)
        await db.commit()

    return {
        "findings": len(final_state.get("findings", [])),
        "status": scan.status,
    }
