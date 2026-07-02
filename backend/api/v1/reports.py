import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
from models.models import AttackChain, Finding, ScanJob, Target, User

router = APIRouter(prefix="/reports", tags=["reports"])

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEVERITY_COLORS = {
    "critical": (220, 50, 50),
    "high": (230, 100, 30),
    "medium": (220, 170, 30),
    "low": (50, 150, 80),
    "info": (80, 120, 200),
}
_IMPACT_COLORS = {
    "critical": (220, 50, 50),
    "high": (230, 100, 30),
    "medium": (220, 170, 30),
    "low": (50, 150, 80),
}


@router.get("/scans/{scan_id}")
async def download_report(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    scan_result = await db.execute(
        select(ScanJob)
        .join(Target, ScanJob.target_id == Target.id)
        .where(ScanJob.id == scan_id, Target.org_id == current_user.org_id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    target_result = await db.execute(select(Target).where(Target.id == scan.target_id))
    target = target_result.scalar_one_or_none()

    findings_result = await db.execute(
        select(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.severity)
    )
    findings = list(findings_result.scalars().all())
    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))

    chains_result = await db.execute(
        select(AttackChain)
        .where(AttackChain.scan_id == scan_id)
        .order_by(AttackChain.created_at)
    )
    chains = list(chains_result.scalars().all())

    pdf_bytes = _build_pdf(scan, target, findings, chains)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.pdf"},
    )


def _s(text: str) -> str:
    return (text or "").replace("—", "-").replace("–", "-").replace("•", "*")


def _risk_level(findings: list[Finding]) -> str:
    counts = {f.severity: 0 for f in findings}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    if counts.get("critical", 0) > 0:
        return "CRITICAL"
    if counts.get("high", 0) > 0:
        return "HIGH"
    if counts.get("medium", 0) > 0:
        return "MEDIUM"
    if counts.get("low", 0) > 0:
        return "LOW"
    return "INFORMATIONAL"


def _section(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")


def _build_pdf(
    scan: ScanJob,
    target: Target | None,
    findings: list[Finding],
    chains: list[AttackChain],
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, "SentinelAI - Scan Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Executive Summary ────────────────────────────────────────────────────
    _section(pdf, "Executive Summary")
    risk = _risk_level(findings)
    confirmed = [f for f in findings if f.status == "confirmed"]
    fps = [f for f in findings if f.status == "false_positive"]
    avg_srs = (
        round(sum(f.srs_score or 0 for f in confirmed) / len(confirmed))
        if confirmed else 0
    )
    r, g, b = _SEVERITY_COLORS.get(risk.lower(), (80, 80, 80))

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 7, f"Overall Risk: {risk}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 10)

    summary_lines = [
        f"Target: {target.url if target else 'unknown'}",
        f"Total findings: {len(findings)}  |  Confirmed: {len(confirmed)}  |  False positives: {len(fps)}",
        f"Average SRS score (confirmed): {avg_srs}/100",
        f"Attack chains discovered: {len(chains)}",
        f"Scan status: {scan.status}",
    ]
    for line in summary_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Scan Details ─────────────────────────────────────────────────────────
    _section(pdf, "Scan Details")
    pdf.set_font("Helvetica", "", 10)
    meta = [
        ("Scan ID", str(scan.id)),
        ("Target", target.url if target else "unknown"),
        ("Type", scan.scan_type),
        ("Status", scan.status),
        ("Started", str(scan.started_at or "-")),
        ("Completed", str(scan.completed_at or "-")),
    ]
    for label, value in meta:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(40, 6, f"{label}:", new_x="RIGHT", new_y="LAST")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Findings Summary ─────────────────────────────────────────────────────
    _section(pdf, f"Findings Summary ({len(findings)} total)")
    pdf.set_font("Helvetica", "", 10)
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    for sev in ["critical", "high", "medium", "low", "info"]:
        n = counts.get(sev, 0)
        if n:
            r, g, b = _SEVERITY_COLORS[sev]
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 6, f"  {sev.upper()}: {n}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(20, 20, 20)
    pdf.ln(4)

    # ── Findings Detail ───────────────────────────────────────────────────────
    if findings:
        _section(pdf, "Findings")
        for i, f in enumerate(findings, 1):
            r, g, b = _SEVERITY_COLORS.get(f.severity, (80, 80, 80))
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 7, _s(f"{i}. [{f.severity.upper()}] {f.title}"),
                     new_x="LMARGIN", new_y="NEXT")

            # SRS score + status
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(80, 80, 80)
            srs_label = f"SRS Score: {int(f.srs_score or 0)}/100  |  Status: {f.status.upper()}"
            pdf.cell(0, 5, srs_label, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _s(f.description or ""))

            if f.remediation:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(80, 100, 80)
                pdf.multi_cell(0, 5, _s(f"Remediation: {f.remediation}"))

            if f.validation_reasoning:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 130)
                pdf.multi_cell(0, 5, _s(f"AI Reasoning: {f.validation_reasoning}"))

            pdf.set_text_color(20, 20, 20)
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "No findings for this scan.", new_x="LMARGIN", new_y="NEXT")

    # ── Attack Chains ─────────────────────────────────────────────────────────
    if chains:
        pdf.ln(2)
        _section(pdf, f"Attack Chains ({len(chains)} discovered)")
        for i, chain in enumerate(chains, 1):
            r, g, b = _IMPACT_COLORS.get(chain.impact, (80, 80, 80))
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 7, _s(f"{i}. {chain.title}  [{chain.impact.upper()}]"),
                     new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, f"Likelihood: {chain.likelihood}  |  MITRE: {', '.join(chain.mitre_ids or [])}",
                     new_x="LMARGIN", new_y="NEXT")

            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _s(chain.description or ""))

            if chain.steps:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 5, "Attack Steps:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                for step in chain.steps:
                    step_num = step.get("step", "?")
                    action = _s(step.get("action", ""))
                    mitre = step.get("mitre_id") or ""
                    suffix = f" [{mitre}]" if mitre else ""
                    pdf.multi_cell(0, 5, f"  {step_num}. {action}{suffix}")

            pdf.set_text_color(20, 20, 20)
            pdf.ln(3)

    return pdf.output()
