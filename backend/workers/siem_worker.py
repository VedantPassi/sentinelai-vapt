from __future__ import annotations

import asyncio
import logging

from workers.agent_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.siem_worker.ship_to_siem", bind=True, max_retries=2)
def ship_to_siem(self, scan_id: str) -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_ship(scan_id))
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _ship(scan_id: str) -> dict:
    import uuid
    from datetime import timezone

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from core.config import settings
    from core.siem_client import forward_to_siem
    from models.models import Finding, ScanJob, Target

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as db:
            scan_result = await db.execute(
                select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id))
            )
            scan = scan_result.scalar_one_or_none()
            if not scan:
                logger.warning("ship_to_siem: scan %s not found", scan_id)
                return {"error": "scan not found"}

            target_result = await db.execute(
                select(Target).where(Target.id == scan.target_id)
            )
            target = target_result.scalar_one_or_none()

            findings_result = await db.execute(
                select(Finding).where(Finding.scan_id == uuid.UUID(scan_id))
            )
            findings = list(findings_result.scalars().all())

        if not findings:
            logger.info("ship_to_siem: no findings for scan %s", scan_id)
            return {"shipped": 0}

        events = [
            {
                "scan_id": scan_id,
                "target_url": target.url if target else "",
                "target_name": target.name if target else "",
                "scan_type": scan.scan_type,
                "finding_id": str(f.id),
                "title": f.title,
                "category": f.category,
                "severity": f.severity,
                "status": f.status,
                "srs_score": f.srs_score,
                "remediation": f.remediation or "",
                "timestamp": f.created_at.replace(tzinfo=timezone.utc).isoformat()
                if f.created_at
                else "",
            }
            for f in findings
        ]

        await forward_to_siem(events)
        logger.info("ship_to_siem: shipped %d findings for scan %s", len(events), scan_id)
        return {"shipped": len(events)}

    finally:
        await engine.dispose()
