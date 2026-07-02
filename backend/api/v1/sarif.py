from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
from models.models import Finding, ScanJob, Target, User

router = APIRouter(prefix="/agent-scans", tags=["sarif"])

_SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}


async def _get_scan_or_404(scan_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> ScanJob:
    result = await db.execute(
        select(ScanJob)
        .join(Target, ScanJob.target_id == Target.id)
        .where(ScanJob.id == scan_id, Target.org_id == org_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/sarif")
async def get_sarif(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    scan = await _get_scan_or_404(scan_id, current_user.org_id, db)

    target_result = await db.execute(select(Target).where(Target.id == scan.target_id))
    target = target_result.scalar_one_or_none()
    target_url = target.url if target else ""

    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()

    rules: dict[str, dict] = {}
    results = []

    for f in findings:
        rule_id = f.category
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": rule_id,
                "shortDescription": {"text": f.title},
                "properties": {"severity": f.severity},
            }
        results.append({
            "ruleId": rule_id,
            "level": _SEVERITY_MAP.get(f.severity, "warning"),
            "message": {"text": f.description},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": target_url},
                    }
                }
            ],
            "properties": {
                "status": f.status,
                "confirmed": f.confirmed,
                "srs_score": f.srs_score,
                "remediation": f.remediation,
            },
        })

    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "SentinelAI",
                        "informationUri": "https://github.com/vedantpassi/sentinelai-vapt",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }

    return JSONResponse(
        content=sarif,
        headers={
            "Content-Disposition": f'attachment; filename="sarif-{scan_id}.sarif"',
        },
    )
