from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import get_db
from core.deps import get_current_user, require_analyst
from models.models import AttackChain, Finding, ScanJob, Target, User

router = APIRouter(prefix="/agent-scans", tags=["integrations"])


class SlackPayload(BaseModel):
    webhook_url: str = ""


class JiraPayload(BaseModel):
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""


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


async def _load_scan_data(
    scan_id: uuid.UUID, db: AsyncSession
) -> tuple[Target | None, list[Finding], list[AttackChain]]:
    target = (await db.execute(
        select(Target).join(ScanJob, ScanJob.target_id == Target.id).where(ScanJob.id == scan_id)
    )).scalar_one_or_none()

    findings = list((await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )).scalars().all())

    chains = list((await db.execute(
        select(AttackChain).where(AttackChain.scan_id == scan_id)
    )).scalars().all())

    return target, findings, chains


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


@router.post("/{scan_id}/integrations/slack")
async def post_to_slack(
    scan_id: uuid.UUID,
    payload: SlackPayload,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    scan = await _get_scan_or_404(scan_id, current_user.org_id, db)
    target, findings, chains = await _load_scan_data(scan_id, db)

    webhook = payload.webhook_url or settings.slack_webhook_url
    if not webhook:
        raise HTTPException(status_code=400, detail="No Slack webhook URL configured")

    counts = _severity_counts(findings)
    confirmed = sum(1 for f in findings if f.status == "confirmed")
    target_url = target.url if target else "unknown"

    severity_lines = "  ".join(
        f"*{sev.upper()}*: {counts[sev]}"
        for sev in ["critical", "high", "medium", "low", "info"]
        if sev in counts
    )

    top_findings = sorted(
        [f for f in findings if f.status == "confirmed"],
        key=lambda f: (f.srs_score or 0),
        reverse=True,
    )[:5]

    finding_lines = "\n".join(
        f"  • [{f.severity.upper()}] {f.title} (SRS: {int(f.srs_score or 0)})"
        for f in top_findings
    )

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "SentinelAI Scan Complete"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Target:*\n{target_url}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{scan.status.upper()}"},
                {"type": "mrkdwn", "text": f"*Findings:*\n{len(findings)} total, {confirmed} confirmed"},
                {"type": "mrkdwn", "text": f"*Attack Chains:*\n{len(chains)}"},
            ],
        },
    ]

    if severity_lines:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Severity Breakdown:*\n{severity_lines}"},
        })

    if finding_lines:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Top Confirmed Findings:*\n{finding_lines}"},
        })

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook, json={"blocks": blocks})

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Slack webhook returned {resp.status_code}: {resp.text}",
        )

    return {"sent": True, "findings": len(findings), "chains": len(chains)}


@router.post("/{scan_id}/integrations/jira")
async def create_jira_issue(
    scan_id: uuid.UUID,
    payload: JiraPayload,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    scan = await _get_scan_or_404(scan_id, current_user.org_id, db)
    target, findings, chains = await _load_scan_data(scan_id, db)

    base_url = (payload.jira_base_url or settings.jira_base_url).rstrip("/")
    email = payload.jira_email or settings.jira_email
    token = payload.jira_api_token or settings.jira_api_token
    project = payload.jira_project_key or settings.jira_project_key

    if not all([base_url, email, token, project]):
        raise HTTPException(status_code=400, detail="Jira credentials not fully configured")

    counts = _severity_counts(findings)
    confirmed = [f for f in findings if f.status == "confirmed"]
    target_url = target.url if target else "unknown"

    severity_summary = ", ".join(
        f"{sev.upper()}: {counts[sev]}"
        for sev in ["critical", "high", "medium", "low", "info"]
        if sev in counts
    )

    top_findings_text = "\n".join(
        f"* [{f.severity.upper()}] {f.title} (SRS: {int(f.srs_score or 0)}) - {f.description[:200]}"
        for f in sorted(confirmed, key=lambda f: (f.srs_score or 0), reverse=True)[:10]
    )

    chains_text = "\n".join(
        f"* [{c.impact.upper()}] {c.title} (likelihood: {c.likelihood})"
        for c in chains
    )

    description = (
        f"h2. Scan Summary\n"
        f"* Target: {target_url}\n"
        f"* Scan ID: {scan_id}\n"
        f"* Status: {scan.status}\n"
        f"* Total findings: {len(findings)} ({len(confirmed)} confirmed)\n"
        f"* Severity: {severity_summary or 'none'}\n"
        f"* Attack chains: {len(chains)}\n\n"
        f"h2. Top Confirmed Findings\n{top_findings_text or 'None'}\n\n"
        f"h2. Attack Chains\n{chains_text or 'None'}\n"
    )

    priority_map = {"critical": "Highest", "high": "High", "medium": "Medium"}
    top_sev = next(
        (s for s in ["critical", "high", "medium"] if counts.get(s, 0) > 0), "low"
    )

    issue_body = {
        "fields": {
            "project": {"key": project},
            "summary": f"[SentinelAI] Scan findings for {target_url} — {len(confirmed)} confirmed",
            "description": description,
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority_map.get(top_sev, "Low")},
        }
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url}/rest/api/2/issue",
            json=issue_body,
            auth=(email, token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Jira API returned {resp.status_code}: {resp.text[:300]}",
        )

    data = resp.json()
    return {
        "created": True,
        "issue_key": data.get("key"),
        "issue_url": f"{base_url}/browse/{data.get('key')}",
    }
