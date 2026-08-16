from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
from core.neo4j_client import run_query
from models.models import ScanJob, Target, User

router = APIRouter(prefix="/attack-graph", tags=["attack-graph"])


class NodeOut(BaseModel):
    id: str
    label: str
    type: str
    severity: str | None = None
    surface: str | None = None
    risk_score: float | None = None


class EdgeOut(BaseModel):
    source: str
    target: str
    relation: str


class AttackGraphOut(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]


class ChainPathOut(BaseModel):
    chain_id: str
    title: str
    impact: str
    likelihood: str
    mitre_ids: list[str]
    steps: list[dict]


class BlastRadiusOut(BaseModel):
    finding_id: str
    finding_title: str
    chains_affected: int
    chain_titles: list[str]
    max_impact: str


async def _assert_scan_org(scan_id: str, org_id: uuid.UUID, db: AsyncSession) -> None:
    """Raise 404 if scan_id doesn't belong to the caller's org."""
    result = await db.execute(
        select(ScanJob)
        .join(Target, ScanJob.target_id == Target.id)
        .where(ScanJob.id == uuid.UUID(scan_id), Target.org_id == org_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Scan not found")


@router.get("/scan/{scan_id}", response_model=AttackGraphOut)
async def get_attack_graph(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttackGraphOut:
    await _assert_scan_org(scan_id, current_user.org_id, db)

    rows = await run_query(
        """
        MATCH (s:Scan {id: $scan_id})
        OPTIONAL MATCH (s)-[:HAS_FINDING]->(f:Finding)
        OPTIONAL MATCH (s)-[:HAS_CHAIN]->(c:Chain)
        OPTIONAL MATCH (c)-[:HAS_STEP]->(st:Step)
        OPTIONAL MATCH (st)-[:EXPLOITS]->(ef:Finding)
        OPTIONAL MATCH (st)-[:NEXT_STEP]->(nst:Step)
        RETURN
            collect(DISTINCT {id: f.id, title: f.title, severity: f.severity,
                               category: f.category, risk_score: f.risk_score}) as findings,
            collect(DISTINCT {id: c.id, title: c.title, impact: c.impact}) as chains,
            collect(DISTINCT {id: st.id, action: st.action, surface: st.surface,
                               mitre_id: st.mitre_id}) as steps,
            collect(DISTINCT {from: st.id, to: nst.id}) as step_edges,
            collect(DISTINCT {from: st.id, to: ef.id}) as exploit_edges,
            collect(DISTINCT {from: c.id, to: st.id}) as chain_step_edges
        """,
        {"scan_id": scan_id},
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Scan not found in graph")

    row = rows[0]
    nodes: list[NodeOut] = []
    edges: list[EdgeOut] = []
    seen_ids: set[str] = set()

    for f in row.get("findings") or []:
        if f.get("id") and f["id"] not in seen_ids:
            nodes.append(NodeOut(
                id=f["id"], label=f.get("title", ""), type="finding",
                severity=f.get("severity"), risk_score=f.get("risk_score"),
            ))
            seen_ids.add(f["id"])

    for c in row.get("chains") or []:
        if c.get("id") and c["id"] not in seen_ids:
            nodes.append(NodeOut(id=c["id"], label=c.get("title", ""), type="chain",
                                 severity=c.get("impact")))
            seen_ids.add(c["id"])

    for st in row.get("steps") or []:
        if st.get("id") and st["id"] not in seen_ids:
            nodes.append(NodeOut(
                id=st["id"], label=st.get("action", "")[:60], type="step",
                surface=st.get("surface"),
            ))
            seen_ids.add(st["id"])

    for e in row.get("step_edges") or []:
        if e.get("from") and e.get("to"):
            edges.append(EdgeOut(source=e["from"], target=e["to"], relation="NEXT_STEP"))

    for e in row.get("exploit_edges") or []:
        if e.get("from") and e.get("to"):
            edges.append(EdgeOut(source=e["from"], target=e["to"], relation="EXPLOITS"))

    for e in row.get("chain_step_edges") or []:
        if e.get("from") and e.get("to"):
            edges.append(EdgeOut(source=e["from"], target=e["to"], relation="HAS_STEP"))

    return AttackGraphOut(nodes=nodes, edges=edges)


@router.get("/scan/{scan_id}/paths", response_model=list[ChainPathOut])
async def get_attack_paths(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChainPathOut]:
    await _assert_scan_org(scan_id, current_user.org_id, db)

    rows = await run_query(
        """
        MATCH (s:Scan {id: $scan_id})-[:HAS_CHAIN]->(c:Chain)
        MATCH (c)-[:HAS_STEP]->(st:Step)
        RETURN c.id as chain_id, c.title as title, c.impact as impact,
               c.likelihood as likelihood, c.mitre_ids as mitre_ids,
               collect({step: st.step, action: st.action,
                        mitre_id: st.mitre_id, surface: st.surface}) as steps
        ORDER BY c.impact
        """,
        {"scan_id": scan_id},
    )

    return [
        ChainPathOut(
            chain_id=r["chain_id"],
            title=r["title"],
            impact=r["impact"],
            likelihood=r["likelihood"],
            mitre_ids=r.get("mitre_ids") or [],
            steps=sorted(r.get("steps") or [], key=lambda s: s.get("step", 0)),
        )
        for r in rows
    ]


@router.get("/scan/{scan_id}/blast-radius", response_model=list[BlastRadiusOut])
async def get_blast_radius(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BlastRadiusOut]:
    await _assert_scan_org(scan_id, current_user.org_id, db)

    rows = await run_query(
        """
        MATCH (s:Scan {id: $scan_id})-[:HAS_CHAIN]->(c:Chain)-[:USES_FINDING]->(f:Finding)
        WITH f, collect(c.title) as chain_titles,
             count(c) as chain_count,
             collect(c.impact) as impacts
        ORDER BY chain_count DESC
        RETURN f.id as finding_id, f.title as finding_title,
               chain_count as chains_affected,
               chain_titles,
               CASE
                 WHEN 'critical' IN impacts THEN 'critical'
                 WHEN 'high' IN impacts THEN 'high'
                 WHEN 'medium' IN impacts THEN 'medium'
                 ELSE 'low'
               END as max_impact
        """,
        {"scan_id": scan_id},
    )

    return [
        BlastRadiusOut(
            finding_id=r["finding_id"],
            finding_title=r["finding_title"],
            chains_affected=r["chains_affected"],
            chain_titles=r["chain_titles"],
            max_impact=r["max_impact"],
        )
        for r in rows
    ]
