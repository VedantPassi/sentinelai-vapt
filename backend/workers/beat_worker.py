from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from workers.agent_worker import celery_app

logger = logging.getLogger(__name__)

celery_app.conf.beat_schedule = {
    "check-due-schedules": {
        "task": "workers.beat_worker.check_due_schedules",
        "schedule": 60.0,
    }
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="workers.beat_worker.check_due_schedules")
def check_due_schedules() -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_check())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _check() -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from core.config import settings
    from models.models import ScheduledScan, ScanJob, Target

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    triggered = 0

    try:
        async with factory() as db:
            result = await db.execute(
                select(ScheduledScan)
                .join(Target, ScheduledScan.target_id == Target.id)
                .where(ScheduledScan.is_active.is_(True))
                .where(ScheduledScan.next_run_at <= now)
            )
            due: list[ScheduledScan] = list(result.scalars().all())

        for sched in due:
            async with factory() as db:
                target_result = await db.execute(
                    select(Target).where(Target.id == sched.target_id)
                )
                target = target_result.scalar_one_or_none()
                if not target:
                    continue

                scan = ScanJob(
                    id=uuid.uuid4(),
                    target_id=sched.target_id,
                    status="pending",
                    scan_type=sched.scan_type,
                    config={**(sched.config or {}), "scheduled_scan_id": str(sched.id)},
                )
                db.add(scan)
                await db.commit()

                sched_result = await db.execute(
                    select(ScheduledScan).where(ScheduledScan.id == sched.id)
                )
                sched_row = sched_result.scalar_one()
                sched_row.last_run_at = now
                sched_row.next_run_at = now + timedelta(hours=sched.interval_hours)
                await db.commit()

                celery_app.send_task(
                    "workers.agent_worker.run_agent_task",
                    args=[str(scan.id), target.url, sched.scan_type, sched.config or {}],
                )
                triggered += 1
                logger.info("Scheduled scan triggered: sched=%s scan=%s", sched.id, scan.id)

    finally:
        await engine.dispose()

    return {"triggered": triggered, "checked_at": now.isoformat()}
