from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.state import AgentState, ProgressEvent
from core.neo4j_client import run_write, run_query

logger = logging.getLogger(__name__)

_CONSTRAINTS = [
    "CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (f:Finding) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT chain_id IF NOT EXISTS FOR (c:Chain) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT scan_id IF NOT EXISTS FOR (s:Scan) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT target_url IF NOT EXISTS FOR (t:Target) REQUIRE t.url IS UNIQUE",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node="graph", status=status, message=message, timestamp=_ts())


async def ensure_constraints() -> None:
    for cypher in _CONSTRAINTS:
        try:
            await run_write(cypher)
        except Exception as exc:
            logger.warning("Constraint setup: %s", exc)


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "graph"
    state["progress_events"].append(_event("started", "Graph agent — ingesting into Neo4j"))

    scan_id = state["scan_id"]
    target_url = state["target_url"]
    findings = state.get("findings", [])
    chains = state.get("attack_chains", [])

    try:
        await ensure_constraints()
        await _ingest_scan(scan_id, target_url, state.get("target_type", "unknown"))
        await _ingest_findings(scan_id, findings)
        await _ingest_chains(scan_id, chains)
    except Exception as exc:
        logger.error("Graph ingestion failed: %s", exc)
        state["progress_events"].append(_event("failed", f"Graph ingestion error: {exc}"))
        return state

    state["progress_events"].append(
        _event(
            "completed",
            f"Graph agent done — {len(findings)} findings, {len(chains)} chains ingested",
        )
    )
    return state


async def _ingest_scan(scan_id: str, target_url: str, target_type: str) -> None:
    await run_write(
        """
        MERGE (t:Target {url: $url})
        SET t.updated_at = $ts
        MERGE (s:Scan {id: $scan_id})
        SET s.target_type = $target_type, s.created_at = $ts
        MERGE (s)-[:SCANNED]->(t)
        """,
        {"url": target_url, "scan_id": scan_id, "target_type": target_type, "ts": _ts()},
    )


async def _ingest_findings(scan_id: str, findings) -> None:
    for f in findings:
        await run_write(
            """
            MERGE (f:Finding {id: $id})
            SET f.title = $title,
                f.severity = $severity,
                f.category = $category,
                f.status = $status,
                f.risk_score = $risk_score,
                f.description = $description
            WITH f
            MATCH (s:Scan {id: $scan_id})
            MERGE (s)-[:HAS_FINDING]->(f)
            """,
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "status": f.status,
                "risk_score": f.risk_score,
                "description": f.description[:500],
                "scan_id": scan_id,
            },
        )


async def _ingest_chains(scan_id: str, chains) -> None:
    for i, chain in enumerate(chains):
        chain_node_id = f"{scan_id}:chain:{i}"
        await run_write(
            """
            MERGE (c:Chain {id: $chain_id})
            SET c.title = $title,
                c.description = $description,
                c.impact = $impact,
                c.likelihood = $likelihood,
                c.mitre_ids = $mitre_ids
            WITH c
            MATCH (s:Scan {id: $scan_id})
            MERGE (s)-[:HAS_CHAIN]->(c)
            """,
            {
                "chain_id": chain_node_id,
                "title": chain.title,
                "description": chain.description,
                "impact": chain.impact,
                "likelihood": chain.likelihood,
                "mitre_ids": chain.mitre_ids,
                "scan_id": scan_id,
            },
        )

        # Link chain to its findings
        for fid in chain.finding_ids:
            await run_write(
                """
                MATCH (c:Chain {id: $chain_id})
                MATCH (f:Finding {id: $finding_id})
                MERGE (c)-[:USES_FINDING]->(f)
                """,
                {"chain_id": chain_node_id, "finding_id": fid},
            )

        # Create step nodes + NEXT_STEP edges
        prev_step_id = None
        for step in sorted(chain.steps, key=lambda s: s.step):
            step_id = f"{chain_node_id}:step:{step.step}"
            await run_write(
                """
                MERGE (st:Step {id: $step_id})
                SET st.step = $step,
                    st.action = $action,
                    st.mitre_id = $mitre_id,
                    st.surface = $surface
                WITH st
                MATCH (c:Chain {id: $chain_id})
                MERGE (c)-[:HAS_STEP]->(st)
                """,
                {
                    "step_id": step_id,
                    "step": step.step,
                    "action": step.action,
                    "mitre_id": step.mitre_id or "",
                    "surface": step.surface or "unknown",
                    "chain_id": chain_node_id,
                },
            )

            if step.finding_id:
                await run_write(
                    """
                    MATCH (st:Step {id: $step_id})
                    MATCH (f:Finding {id: $finding_id})
                    MERGE (st)-[:EXPLOITS]->(f)
                    """,
                    {"step_id": step_id, "finding_id": step.finding_id},
                )

            if prev_step_id:
                await run_write(
                    """
                    MATCH (a:Step {id: $from_id})
                    MATCH (b:Step {id: $to_id})
                    MERGE (a)-[:NEXT_STEP]->(b)
                    """,
                    {"from_id": prev_step_id, "to_id": step_id},
                )
            prev_step_id = step_id
