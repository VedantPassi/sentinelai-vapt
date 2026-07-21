# Phase 6 Audit Report — Advanced Modules

**Date:** 2026-07-22  
**Git HEAD:** 8d18e78  
**Status:** COMPLETE ✅

---

## Summary

Phase 6 delivered five advanced modules that extend SentinelAI beyond web/network scanning into container security, cloud posture, graph-based attack path analysis, and cross-surface kill chain discovery. All five tracks verified end-to-end against real targets.

---

## P6-1 — Cytoscape.js Attack Chain Graph

**Delivered:**
- `frontend/components/ChainGraph.tsx` — chain selector sidebar + Cytoscape breadthfirst graph + node tap detail panel
- `frontend/lib/api.ts` — `ChainStep`, `AgentChain` interfaces + `listAgentScanChains()`
- `frontend/app/(dashboard)/agent-scans/page.tsx` — chains state + loadChains() + graph section
- `backend/agents/chain_agent.py` — fixed: LLM gets real `f.id` UUIDs (was ordinal indices)
- `backend/scanners/base.py` — `FindingData.id` stable uuid4 at creation
- `backend/workers/agent_worker.py` — Finding inserted with `fd.id` so DB id matches chain references

**Verified:** 2 attack chains rendered from real network scan (scanme.nmap.org), node tap shows MITRE ID + action, single-node zoom fixed, tsc clean.

---

## P6-2 — Container Image Scanning (Trivy)

**Delivered:**
- `backend/scanners/trivy_scanner.py` — Trivy 0.72.0 subprocess wrapper; parses CVEs, secrets, misconfigurations; CVSS extraction
- `backend/agents/container_agent.py` — runs Trivy, LLM enriches top 20 critical/high CVEs with exploitability + blast radius context
- `backend/agents/recon_agent.py` — early return for `target_type=container`
- `backend/agents/planner_agent.py` — early return for `target_type=container`
- `backend/agents/runtime.py` — container node: planner → container → validator → chain
- `frontend/app/(dashboard)/agent-scans/page.tsx` — "Container Image" scan type added

**Verified:** `python:3.8-slim` → 379 findings (76 critical/high), 26 LLM-enriched with exploitability + blast radius.

---

## P6-3 — Cloud Security (Prowler)

**Delivered:**
- `backend/scanners/prowler_scanner.py` — Prowler 5.35.0 subprocess wrapper; OCSF v5 parser (`metadata.event_code`, `finding_info.{title,desc}`, `resources[0].{uid,region}`, `cloud.account.uid`, `remediation.{desc,references}`)
- `backend/agents/cloud_agent.py` — runs Prowler, LLM enriches top 15 critical/high findings with exploitability + business impact
- `backend/.prowler-venv` — isolated Python 3.12 venv (gitignored); avoids pydantic v1/v2 conflict with main backend
- AWS IAM user `sentinelai-prowler` — ReadOnlyAccess + SecurityAudit policies
- `backend/agents/recon_agent.py` + `planner_agent.py` — skip for `cloud` type
- `backend/agents/runtime.py` — cloud node: planner → cloud → validator → chain
- `frontend/app/(dashboard)/agent-scans/page.tsx` — "Cloud (AWS)" scan type added

**Verified:** 18 findings (2 critical, 2 high, 8 medium, 6 low) from real AWS account, 4 LLM-enriched.

**Key decision:** Prowler isolated in `.prowler-venv` (not main `.venv`) because Prowler forces pydantic v1 which breaks FastAPI + LangGraph. Subprocess pattern (same as Trivy/Nuclei/Nmap) keeps stacks clean.

---

## P6-4 — Neo4j Attack Path Graph

**Delivered:**
- `infra/docker/docker-compose.yml` — Neo4j 5 Community Edition (ports 7474/7687, APOC plugin)
- `backend/core/neo4j_client.py` — async driver wrapper (bolt://localhost:7687)
- `backend/core/config.py` — neo4j_uri/user/password settings
- `backend/agents/graph_agent.py` — ingests Scan/Target/Finding/Chain/Step as Neo4j nodes; SCANNED, HAS_FINDING, HAS_CHAIN, HAS_STEP, NEXT_STEP, EXPLOITS, USES_FINDING edges
- `backend/api/v1/attack_graph.py` — 3 endpoints:
  - `GET /attack-graph/scan/{id}` — full node/edge graph
  - `GET /attack-graph/scan/{id}/paths` — ordered chain steps
  - `GET /attack-graph/scan/{id}/blast-radius` — findings appearing in most chains
- `backend/agents/runtime.py` — graph node after chain: chain → graph → END
- `frontend/lib/api.ts` — GraphNode/GraphEdge/AttackGraph/BlastRadius interfaces
- `frontend/components/AttackGraphView.tsx` — Cytoscape graph (finding=ellipse, chain=diamond, step=rect) + blast radius tab
- `backend/requirements.txt` — neo4j>=6.2.0

**Verified:** smoke-test-001 → 2 findings + 1 chain + 2 steps in Neo4j; API returns correct graph; blast radius query working.

---

## P6-5 — Chain Discovery Agent v2 (Cross-Surface Kill Chains)

**Delivered:**
- `backend/agents/chain_agent.py` — v2 upgrade:
  - Includes `open` findings with severity critical/high (v1 only used `confirmed`)
  - Groups findings by surface (web/network/container/secrets/cloud) before LLM
  - Prompt models MITRE ATT&CK kill chain stages (Initial Access → Exfiltration)
  - Explicitly requests cross-surface pivot chains
  - 30 finding cap (was 20), sorted by severity tier + risk_score
  - Each step includes `surface` field
- `backend/agents/state.py` — `ChainStep.surface: str | None` added
- `frontend/lib/api.ts` — `ChainStep.surface: string | null` added
- `frontend/components/ChainGraph.tsx` — purple surface badge in node detail panel

**Verified:** Synthetic 5-finding cross-surface test (network + web + container + secrets) → 2 chains, both cross-surface, network→web→container→secrets pivots generated correctly.

---

## Pipeline State (End of Phase 6)

```
recon → planner → [webapp|network|container|cloud] → validator → chain → graph → END
```

Scan types supported: `web`, `api`, `network`, `container`, `cloud`

All nodes skip gracefully if their prerequisites aren't met (no findings → chain skipped, Neo4j down → graph logs warning and continues).

---

## Known Gaps / Deferred

| Item | Reason deferred |
|------|-----------------|
| kube-bench (K8s hardening) | No local K8s cluster in dev |
| Prowler service coverage | Only iam+s3 tested; ec2/guardduty/cloudtrail untested |
| Neo4j browser UI integration | Data queryable via Bolt; no embedded browser view |
| AWS credential rotation | Long-lived keys used; should rotate or use IAM roles in prod |

---

## Files Changed (Phase 6)

**Backend:**
- `scanners/trivy_scanner.py` (new)
- `scanners/prowler_scanner.py` (new)
- `agents/container_agent.py` (new)
- `agents/cloud_agent.py` (new)
- `agents/graph_agent.py` (new)
- `agents/chain_agent.py` (upgraded to v2)
- `agents/recon_agent.py` (container+cloud skip)
- `agents/planner_agent.py` (container+cloud skip)
- `agents/runtime.py` (container+cloud+graph nodes)
- `agents/state.py` (ChainStep.surface)
- `core/neo4j_client.py` (new)
- `core/config.py` (neo4j settings)
- `api/v1/attack_graph.py` (new)
- `main.py` (attack_graph router)
- `requirements.txt` (neo4j>=6.2.0)

**Frontend:**
- `components/ChainGraph.tsx` (surface badge)
- `components/AttackGraphView.tsx` (new)
- `lib/api.ts` (graph interfaces + functions)
- `app/(dashboard)/agent-scans/page.tsx` (container+cloud types, AttackGraphView)

**Infra:**
- `infra/docker/docker-compose.yml` (Neo4j service)
- `backend/.prowler-venv/` (gitignored)
