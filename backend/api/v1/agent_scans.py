from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user
from core.db import get_db
from models.models import Finding, ScanJob, User
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


@router.post("", response_model=AgentScanResponse, status_code=201)
async def create_agent_scan(
    payload: AgentScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentScanResponse:
    scan_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    scan = ScanJob(
        id=scan_id,
        org_id=current_user.org_id,
        target_id=uuid.UUID(payload.target_id),
        scan_type=f"agent_{payload.target_type}",
        status="queued",
        created_at=now,
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

    return AgentScanResponse(
        id=str(scan.id),
        status=scan.status,
        target_url=payload.target_url,
        target_type=payload.target_type,
        created_at=now.isoformat(),
    )


@router.get("/{scan_id}", response_model=AgentScanResponse)
async def get_agent_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentScanResponse:
    result = await db.execute(
        select(ScanJob).where(
            ScanJob.id == uuid.UUID(scan_id),
            ScanJob.org_id == current_user.org_id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    cfg = scan.config or {}
    return AgentScanResponse(
        id=str(scan.id),
        status=scan.status,
        target_url=cfg.get("target_url", ""),
        target_type=cfg.get("target_type", "web"),
        created_at=scan.created_at.isoformat(),
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
    result = await db.execute(
        select(ScanJob).where(
            ScanJob.id == uuid.UUID(scan_id),
            ScanJob.org_id == current_user.org_id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

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
    db: AsyncSession = Depends(get_db),
) -> None:
    await websocket.accept()
    last_event_count = 0

    try:
        while True:
            result = await db.execute(
                select(ScanJob).where(ScanJob.id == uuid.UUID(scan_id))
            )
            scan = result.scalar_one_or_none()

            if not scan:
                await websocket.send_text(json.dumps({"error": "scan not found"}))
                break

            cfg = scan.config or {}
            events = cfg.get("progress_events", [])

            if len(events) > last_event_count:
                for event in events[last_event_count:]:
                    await websocket.send_text(json.dumps(event))
                last_event_count = len(events)

            if scan.status in ("completed", "failed"):
                await websocket.send_text(json.dumps({
                    "node": "system",
                    "status": scan.status,
                    "message": f"Scan {scan.status}",
                    "error": cfg.get("error"),
                }))
                break

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
