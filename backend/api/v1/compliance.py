from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.compliance import FRAMEWORK_NAMES, ControlResult, evaluate_framework
from core.db import get_db
from core.security import decode_access_token
from models.models import Finding, ScanJob, Target, User

_optional_bearer = HTTPBearer(auto_error=False)


async def _resolve_user(
    token: str | None = Query(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    payload = decode_access_token(raw_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

router = APIRouter(prefix="/agent-scans", tags=["compliance"])

_STATUS_COLORS = {
    "NON-COMPLIANT": (220, 50, 50),
    "REVIEW": (220, 150, 30),
    "COMPLIANT": (50, 150, 80),
}
_SEVERITY_COLORS = {
    "critical": (220, 50, 50),
    "high": (230, 100, 30),
    "medium": (220, 170, 30),
    "low": (50, 150, 80),
    "info": (80, 120, 200),
}


def _s(text: str) -> str:
    return (text or "").replace("—", "-").replace("–", "-").replace("•", "*")


@router.get("/{scan_id}/compliance/{framework}")
async def download_compliance_report(
    scan_id: uuid.UUID,
    framework: str,
    current_user: User = Depends(_resolve_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if framework not in FRAMEWORK_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown framework '{framework}'. Valid: soc2, iso27001, pci-dss",
        )

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
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = list(findings_result.scalars().all())

    results = evaluate_framework(framework, findings)
    pdf_bytes = _build_compliance_pdf(framework, scan, target, results)

    fname = f"compliance-{framework}-{scan_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


def _build_compliance_pdf(
    framework: str,
    scan: ScanJob,
    target: Target | None,
    results: list[ControlResult],
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    fw_name = FRAMEWORK_NAMES[framework]
    non_compliant = [r for r in results if r.status == "NON-COMPLIANT"]
    review = [r for r in results if r.status == "REVIEW"]
    compliant = [r for r in results if r.status == "COMPLIANT"]

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, "SentinelAI - Compliance Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(40, 40, 140)
    pdf.cell(0, 8, _s(fw_name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Scan Info ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, f"Scan ID: {scan.id}   |   Target: {target.url if target else 'unknown'}   |   Type: {scan.scan_type}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Compliance Summary ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, "Compliance Summary", new_x="LMARGIN", new_y="NEXT")

    overall = "NON-COMPLIANT" if non_compliant else ("REVIEW" if review else "COMPLIANT")
    r, g, b = _STATUS_COLORS[overall]
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 7, f"Overall Status: {overall}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Controls checked: {len(results)}   |   Non-compliant: {len(non_compliant)}   |   Requires review: {len(review)}   |   Compliant: {len(compliant)}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Controls Summary Table ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, "Controls Overview", new_x="LMARGIN", new_y="NEXT")

    col_id = 28
    col_name = 90
    col_status = 40
    col_findings = 32

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 245)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(col_id, 6, "Control ID", border=1, fill=True, new_x="RIGHT", new_y="LAST")
    pdf.cell(col_name, 6, "Control Name", border=1, fill=True, new_x="RIGHT", new_y="LAST")
    pdf.cell(col_status, 6, "Status", border=1, fill=True, new_x="RIGHT", new_y="LAST")
    pdf.cell(col_findings, 6, "Findings", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    for res in results:
        r, g, b = _STATUS_COLORS[res.status]
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_id, 6, res.control.id, border=1, new_x="RIGHT", new_y="LAST")
        pdf.cell(col_name, 6, _s(res.control.name), border=1, new_x="RIGHT", new_y="LAST")
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_status, 6, res.status, border=1, new_x="RIGHT", new_y="LAST")
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(col_findings, 6, str(len(res.findings)), border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # ── Per-Control Detail (only non-compliant + review) ─────────────────────
    actionable = [r for r in results if r.status in ("NON-COMPLIANT", "REVIEW")]
    if actionable:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 8, "Control Detail — Issues Found", new_x="LMARGIN", new_y="NEXT")

        for res in actionable:
            r, g, b = _STATUS_COLORS[res.status]
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 7, f"{res.control.id} — {_s(res.control.name)}  [{res.status}]",
                     new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, _s(res.control.description), new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 5, f"Affected findings ({len(res.findings)}):", new_x="LMARGIN", new_y="NEXT")

            for f in res.findings:
                fr, fg, fb = _SEVERITY_COLORS.get(f.severity, (80, 80, 80))
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(fr, fg, fb)
                pdf.cell(0, 5, f"  [{f.severity.upper()}] {_s(f.title)} — {f.status}",
                         new_x="LMARGIN", new_y="NEXT")
                if f.remediation:
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(80, 100, 80)
                    pdf.multi_cell(0, 4, _s(f"  Fix: {f.remediation}"), new_x="LMARGIN", new_y="NEXT")

            pdf.set_text_color(20, 20, 20)
            pdf.ln(3)

    # ── Compliant Controls ───────────────────────────────────────────────────
    if compliant:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 8, "Compliant Controls", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 150, 80)
        for res in compliant:
            pdf.cell(0, 5, f"  {res.control.id} — {_s(res.control.name)}",
                     new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
