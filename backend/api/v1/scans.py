import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
from models.models import Finding, ScanJob, Target, User
from workers.scan_worker import run_scan

router = APIRouter(prefix="/scans", tags=["scans"])


class ScanCreate(BaseModel):
    target_id: uuid.UUID
    scan_type: str  # web | api | network | sast | secrets
    config: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    status: str
    scan_type: str
    config: dict[str, Any] | None

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    category: str
    severity: str
    title: str
    description: str
    srs_score: float | None
    status: str
    confirmed: bool
    poc_evidence: str | None
    remediation: str | None

    model_config = {"from_attributes": True}


async def _get_scan_or_404(scan_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> ScanJob:
    result = await db.execute(
        select(ScanJob)
        .join(Target, ScanJob.target_id == Target.id)
        .where(ScanJob.id == scan_id, Target.org_id == org_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanJob:
    target_result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.org_id == current_user.org_id)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    scan = ScanJob(
        id=uuid.uuid4(),
        target_id=body.target_id,
        status="pending",
        scan_type=body.scan_type,
        config=body.config,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    run_scan.delay(str(scan.id), target.url, body.scan_type, body.config or {})

    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanJob:
    return await _get_scan_or_404(scan_id, current_user.org_id, db)


@router.get("/{scan_id}/findings", response_model=list[FindingResponse])
async def get_findings(
    scan_id: uuid.UUID,
    severity: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Finding]:
    await _get_scan_or_404(scan_id, current_user.org_id, db)

    q = select(Finding).where(Finding.scan_id == scan_id)
    if severity:
        q = q.where(Finding.severity == severity)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    return list(result.scalars().all())
