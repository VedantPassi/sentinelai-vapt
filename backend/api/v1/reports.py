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
from models.models import Finding, ScanJob, Target, User

router = APIRouter(prefix="/reports", tags=["reports"])

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEVERITY_COLORS = {
    "critical": (220, 50, 50),
    "high": (230, 100, 30),
    "medium": (220, 170, 30),
    "low": (50, 150, 80),
    "info": (80, 120, 200),
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

    pdf_bytes = _build_pdf(scan, target, findings)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.pdf"},
    )


def _s(text: str) -> str:
    return text.replace("—", "-").replace("–", "-").replace("•", "*")


def _build_pdf(scan: ScanJob, target: Target | None, findings: list[Finding]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, "SentinelAI - Scan Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Scan metadata
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, "Scan Details", new_x="LMARGIN", new_y="NEXT")
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
        pdf.cell(40, 6, f"{label}:", new_x="RIGHT", new_y="LAST")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Summary counts
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Findings Summary ({len(findings)} total)", new_x="LMARGIN", new_y="NEXT")
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

    # Findings detail
    if findings:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Findings", new_x="LMARGIN", new_y="NEXT")

        for i, f in enumerate(findings, 1):
            r, g, b = _SEVERITY_COLORS.get(f.severity, (80, 80, 80))
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 7, _s(f"{i}. [{f.severity.upper()}] {f.title}"), new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _s(f.description or ""))

            if f.remediation:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(80, 100, 80)
                pdf.multi_cell(0, 5, _s(f"Remediation: {f.remediation}"))

            pdf.set_text_color(20, 20, 20)
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "No findings for this scan.", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
