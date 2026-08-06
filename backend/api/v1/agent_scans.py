from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, require_analyst
from core.db import get_db
from core.redis_client import get_redis
from core.security import decode_access_token
from models.models import AttackChain, Finding, ScanJob, Target, User
from workers.agent_worker import run_agent_task

router = APIRouter(prefix="/agent-scans", tags=["agent-scans"])


class AgentScanCreate(BaseModel):
    target_id: str
    target_url: str
    target_type: str = "web"  # web | api | network
    config: dict[str, Any] = {}


class AgentScanResponse(BaseModel):
    id: str
    status: str
    target_url: str
    target_type: str
    created_at: str
    progress_events: list[dict] = []
    error: str | None = None


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


@router.post("", response_model=AgentScanResponse, status_code=201)
async def create_agent_scan(
    payload: AgentScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> AgentScanResponse:
    # Verify target belongs to this org
    target_result = await db.execute(
        select(Target).where(
            Target.id == uuid.UUID(payload.target_id),
            Target.org_id == current_user.org_id,
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    scan_id = uuid.uuid4()
    scan = ScanJob(
        id=scan_id,
        target_id=uuid.UUID(payload.target_id),
        scan_type=f"agent_{payload.target_type}",
        status="pending",
        config={"target_url": payload.target_url, "target_type": payload.target_type,
                **payload.config},
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    run_agent_task.delay(
        str(scan_id),
        payload.target_url,
        payload.target_type,
        payload.config,
    )

    created_at = (scan.started_at or scan.completed_at or scan.created_at).isoformat()
    return AgentScanResponse(
        id=str(scan.id),
        status=scan.status,
        target_url=payload.target_url,
        target_type=payload.target_type,
        created_at=created_at,
    )


@router.get("", response_model=list[AgentScanResponse])
async def list_agent_scans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentScanResponse]:
    result = await db.execute(
        select(ScanJob, Target)
        .join(Target, ScanJob.target_id == Target.id)
        .where(Target.org_id == current_user.org_id)
        .order_by(ScanJob.created_at.desc())
        .limit(20)
    )
    rows = result.all()
    out = []
    for scan, target in rows:
        cfg = scan.config or {}
        created_at = (scan.started_at or scan.completed_at or scan.created_at).isoformat()
        out.append(AgentScanResponse(
            id=str(scan.id),
            status=scan.status,
            target_url=cfg.get("target_url", target.url),
            target_type=cfg.get("target_type", "web"),
            created_at=created_at,
        ))
    return out


@router.get("/{scan_id}", response_model=AgentScanResponse)
async def get_agent_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentScanResponse:
    scan = await _get_scan_or_404(uuid.UUID(scan_id), current_user.org_id, db)
    cfg = scan.config or {}
    created_at = (scan.started_at or scan.completed_at or scan.created_at).isoformat()
    return AgentScanResponse(
        id=str(scan.id),
        status=scan.status,
        target_url=cfg.get("target_url", ""),
        target_type=cfg.get("target_type", "web"),
        created_at=created_at,
        progress_events=cfg.get("progress_events", []),
        error=cfg.get("error"),
    )


@router.get("/{scan_id}/findings")
async def get_agent_scan_findings(
    scan_id: str,
    severity: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _get_scan_or_404(uuid.UUID(scan_id), current_user.org_id, db)

    query = select(Finding).where(Finding.scan_id == uuid.UUID(scan_id))
    if severity:
        query = query.where(Finding.severity == severity)
    query = query.offset(skip).limit(limit)

    findings_result = await db.execute(query)
    findings = findings_result.scalars().all()

    return {
        "scan_id": scan_id,
        "total": len(findings),
        "findings": [
            {
                "id": str(f.id),
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "remediation": f.remediation,
                "status": f.status,
            }
            for f in findings
        ],
    }


@router.websocket("/ws/{scan_id}")
async def agent_scan_ws(
    websocket: WebSocket,
    scan_id: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    if not token or not decode_access_token(token).get("sub"):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    pubsub = get_redis().pubsub()
    await pubsub.subscribe(f"scan:{scan_id}")

    try:
        while True:
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                # No Redis event in 30s — poll DB as fallback
                await db.expire_all()
                result = await db.execute(
                    select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id))
                )
                scan = result.scalar_one_or_none()
                if scan and scan.status in ("completed", "failed"):
                    cfg = scan.config or {}
                    await websocket.send_text(json.dumps({
                        "node": "system",
                        "status": scan.status,
                        "message": f"Scan {scan.status}",
                        "error": cfg.get("error"),
                    }))
                    break
                continue

            if msg is None:
                continue

            await websocket.send_text(msg["data"])
            data = json.loads(msg["data"])
            if data.get("status") in ("completed", "failed"):
                break

    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"scan:{scan_id}")
        await pubsub.aclose()


@router.get("/{scan_id}/chains")
async def get_agent_scan_chains(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_scan_or_404(uuid.UUID(scan_id), current_user.org_id, db)

    result = await db.execute(
        select(AttackChain)
        .where(AttackChain.scan_id == uuid.UUID(scan_id))
        .order_by(AttackChain.created_at)
    )
    chains = result.scalars().all()

    return {
        "scan_id": scan_id,
        "total": len(chains),
        "chains": [
            {
                "id": str(c.id),
                "title": c.title,
                "description": c.description,
                "impact": c.impact,
                "likelihood": c.likelihood,
                "mitre_ids": c.mitre_ids,
                "finding_ids": c.finding_ids,
                "steps": c.steps,
                "created_at": c.created_at.isoformat(),
            }
            for c in chains
        ],
    }
