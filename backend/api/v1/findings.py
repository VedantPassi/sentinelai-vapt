from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user, require_analyst
from core.llm import LLMError, llm_complete
from models.models import Finding, ScanJob, Target, User
from scoring.classifier import classify_finding
from scoring.srs import compute_srs
from scanners.base import FindingData

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingDetailResponse(BaseModel):
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
    validation_reasoning: str

    model_config = {"from_attributes": True}


class FindingUpdate(BaseModel):
    status: Literal["open", "confirmed", "false_positive", "fixed"] | None = None
    remediation: str | None = None


async def _get_finding_or_404(
    finding_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Finding:
    result = await db.execute(
        select(Finding)
        .join(ScanJob, Finding.scan_id == ScanJob.id)
        .join(Target, ScanJob.target_id == Target.id)
        .where(Finding.id == finding_id, Target.org_id == org_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding


@router.get("/{finding_id}", response_model=FindingDetailResponse)
async def get_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingDetailResponse:
    finding = await _get_finding_or_404(finding_id, current_user.org_id, db)
    return FindingDetailResponse.model_validate(finding)


@router.patch("/{finding_id}", response_model=FindingDetailResponse)
async def update_finding(
    finding_id: uuid.UUID,
    body: FindingUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> FindingDetailResponse:
    finding = await _get_finding_or_404(finding_id, current_user.org_id, db)

    if body.status is not None:
        finding.status = body.status
        finding.confirmed = body.status == "confirmed"

    if body.remediation is not None:
        finding.remediation = body.remediation

    # fetch asset_criticality for SRS recompute
    target_result = await db.execute(
        select(Target)
        .join(ScanJob, Target.id == ScanJob.target_id)
        .where(ScanJob.id == finding.scan_id)
    )
    target = target_result.scalar_one_or_none()
    asset_score = round((target.asset_criticality or 0.0) * 100) if target else 0

    finding.srs_score = compute_srs(
        finding.severity, 0, asset_score, finding.status
    )

    await db.commit()
    await db.refresh(finding)
    return FindingDetailResponse.model_validate(finding)


_VALIDATE_SYSTEM = """You are a senior penetration tester reviewing a single automated scanner finding.
Classify it as "confirmed" (real vulnerability) or "false_positive" (scanner noise).
Assign risk_score 0-100. Output JSON only."""

_VALIDATE_PROMPT = """Target: {url}

Finding:
- Title: {title}
- Severity: {severity}
- Category: {category}
- Description: {description}

Return JSON:
{{"status": "confirmed" | "false_positive", "risk_score": <0-100>, "reasoning": "<one sentence>"}}"""


@router.post("/{finding_id}/validate", response_model=FindingDetailResponse)
async def validate_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> FindingDetailResponse:
    finding = await _get_finding_or_404(finding_id, current_user.org_id, db)

    # fetch target URL + asset_criticality
    target_result = await db.execute(
        select(Target)
        .join(ScanJob, Target.id == ScanJob.target_id)
        .where(ScanJob.id == finding.scan_id)
    )
    target = target_result.scalar_one_or_none()
    target_url = target.url if target else "unknown"
    asset_score = round((target.asset_criticality or 0.0) * 100) if target else 0

    # rules-based pre-check
    fd = FindingData(
        category=finding.category,
        severity=finding.severity,
        title=finding.title,
        description=finding.description or "",
        status=finding.status,
        risk_score=0,
    )
    target_type = target.type if target else "web"
    rules_verdict = classify_finding(fd, target_type)

    if rules_verdict:
        new_status = rules_verdict
        risk_score = 0
        reasoning = "rules-based: auto-classified"
    else:
        prompt = _VALIDATE_PROMPT.format(
            url=target_url,
            title=finding.title,
            severity=finding.severity,
            category=finding.category,
            description=finding.description or "",
        )
        try:
            import json
            raw = await llm_complete(prompt, system=_VALIDATE_SYSTEM, model_tier="standard")
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            new_status = data.get("status", "open")
            risk_score = int(data.get("risk_score", 0))
            reasoning = data.get("reasoning", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM validation unavailable — try again later",
            )

    finding.status = new_status
    finding.confirmed = new_status == "confirmed"
    finding.validation_reasoning = reasoning
    finding.srs_score = compute_srs(finding.severity, risk_score, asset_score, new_status)

    await db.commit()
    await db.refresh(finding)
    return FindingDetailResponse.model_validate(finding)
