from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user, require_admin, require_analyst
from models.models import ScheduledScan, Target, User

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    target_id: str
    scan_type: str = "web"
    interval_hours: float = Field(default=24.0, ge=0.5, le=8760.0)
    config: dict[str, Any] = {}


class SchedulePatch(BaseModel):
    is_active: bool | None = None
    interval_hours: float | None = Field(default=None, ge=0.5, le=8760.0)
    config: dict[str, Any] | None = None


class ScheduleResponse(BaseModel):
    id: str
    target_id: str
    scan_type: str
    interval_hours: float
    is_active: bool
    last_run_at: str | None
    next_run_at: str
    created_at: str


def _serialize(s: ScheduledScan) -> ScheduleResponse:
    return ScheduleResponse(
        id=str(s.id),
        target_id=str(s.target_id),
        scan_type=s.scan_type,
        interval_hours=s.interval_hours,
        is_active=s.is_active,
        last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
        next_run_at=s.next_run_at.isoformat(),
        created_at=s.created_at.isoformat(),
    )


async def _get_target_or_403(target_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Target:
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.org_id == org_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=403, detail="Target not found or access denied")
    return target


async def _get_schedule_or_404(
    schedule_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> ScheduledScan:
    result = await db.execute(
        select(ScheduledScan)
        .join(Target, ScheduledScan.target_id == Target.id)
        .where(ScheduledScan.id == schedule_id, Target.org_id == org_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> ScheduleResponse:
    target_id = uuid.UUID(payload.target_id)
    await _get_target_or_403(target_id, current_user.org_id, db)

    now = datetime.now(timezone.utc)
    sched = ScheduledScan(
        id=uuid.uuid4(),
        target_id=target_id,
        scan_type=payload.scan_type,
        interval_hours=payload.interval_hours,
        config=payload.config or None,
        is_active=True,
        next_run_at=now + timedelta(hours=payload.interval_hours),
    )
    db.add(sched)
    await db.commit()
    return _serialize(sched)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScheduleResponse]:
    result = await db.execute(
        select(ScheduledScan)
        .join(Target, ScheduledScan.target_id == Target.id)
        .where(Target.org_id == current_user.org_id)
        .order_by(ScheduledScan.created_at.desc())
    )
    return [_serialize(s) for s in result.scalars().all()]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScheduleResponse:
    return _serialize(await _get_schedule_or_404(schedule_id, current_user.org_id, db))


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    payload: SchedulePatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> ScheduleResponse:
    sched = await _get_schedule_or_404(schedule_id, current_user.org_id, db)

    if payload.is_active is not None:
        sched.is_active = payload.is_active
    if payload.interval_hours is not None:
        sched.interval_hours = payload.interval_hours
        sched.next_run_at = datetime.now(timezone.utc) + timedelta(hours=payload.interval_hours)
    if payload.config is not None:
        sched.config = payload.config

    await db.commit()
    return _serialize(sched)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    sched = await _get_schedule_or_404(schedule_id, current_user.org_id, db)
    await db.delete(sched)
    await db.commit()
