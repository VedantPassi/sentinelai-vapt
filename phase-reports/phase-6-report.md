# Phase 6 Report — Advanced Modules

**Date:** 2026-07-22
**Phase:** 6 — Advanced Modules (Cloud/K8s)
**Git HEAD:** 8d18e78
**Status:** ✅ Complete

---

## Overview

Phase 6 extended SentinelAI beyond web/network scanning into container security, cloud posture assessment, Neo4j-backed attack path graphs, and cross-surface kill chain discovery. All five tracks verified end-to-end.

---

## What Was Built

### P6-1 — Cytoscape.js Attack Chain Graph

| File | Purpose |
|------|---------|
| `frontend/components/ChainGraph.tsx` | Chain selector sidebar + Cytoscape breadthfirst graph + node tap detail panel |
| `frontend/lib/api.ts` | `ChainStep`, `AgentChain` interfaces + `listAgentScanChains()` |
| `frontend/app/(dashboard)/agent-scans/page.tsx` | `chains` state + `loadChains()` + graph section |
| `backend/agents/chain_agent.py` | Fixed: LLM now receives real `f.id` UUIDs (was ordinal indices) |
| `backend/scanners/base.py` | `FindingData.id` is stable uuid4 at creation |
| `backend/workers/agent_worker.py` | `Finding` inserted with `fd.id` so DB id matches chain references |

**Verified:** 2 chains rendered from real network scan (scanme.nmap.org). Node tap shows MITRE ID + action. tsc clean.

---

### P6-2 — Container Image Scanning (Trivy)

| File | Purpose |
|------|---------|
| `backend/scanners/trivy_scanner.py` | Trivy 0.72.0 wrapper; parses CVEs, secrets, misconfigs; CVSS extraction |
| `backend/agents/container_agent.py` | Runs Trivy; LLM enriches top 20 critical/high CVEs with exploitability + blast radius |
| `backend/agents/recon_agent.py` | Early return for `target_type=container` |
| `backend/agents/planner_agent.py` | Early return for `target_type=container` |
| `backend/agents/runtime.py` | container node: planner → container → validator → chain |
| `frontend/app/(dashboard)/agent-scans/page.tsx` | "Container Image" scan type added |

**Verified:** `python:3.8-slim` → 379 findings (76 critical/high), 26 LLM-enriched.

---

### P6-3 — Cloud Security (Prowler)

| File | Purpose |
|------|---------|
| `backend/scanners/prowler_scanner.py` | Prowler 5.35.0 wrapper; OCSF v5 parser |
| `backend/agents/cloud_agent.py` | Runs Prowler; LLM enriches top 15 critical/high findings |
| `backend/.prowler-venv` | Isolated Python 3.12 venv (gitignored) — avoids pydantic v1/v2 conflict |
| `backend/agents/runtime.py` | cloud node: planner → cloud → validator → chain |

**AWS setup:** IAM user `sentinelai-prowler` (ReadOnlyAccess + SecurityAudit), creds in `.env`.

**Key decision:** Prowler isolated in `.prowler-venv` — Prowler forces pydantic v1 which breaks FastAPI + LangGraph in the main venv. Same subprocess pattern as Trivy/Nuclei/Nmap.

**Verified:** 18 findings (2 critical, 2 high, 8 medium, 6 low) from real AWS account, 4 LLM-enriched.

---

### P6-4 — Neo4j Attack Path Graph

| File | Purpose |
|------|---------|
| `infra/docker/docker-compose.yml` | Neo4j 5 Community (ports 7474/7687, APOC plugin) |
| `backend/core/neo4j_client.py` | Async driver wrapper (bolt://localhost:7687) |
| `backend/agents/graph_agent.py` | Ingests Scan/Target/Finding/Chain/Step as nodes + edges into Neo4j |
| `backend/api/v1/attack_graph.py` | 3 endpoints: full graph, attack paths, blast radius |
| `frontend/components/AttackGraphView.tsx` | Cytoscape graph (finding=ellipse, chain=diamond, step=rect) + blast radius tab |
| `backend/requirements.txt` | `neo4j>=6.2.0` added |

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/attack-graph/scan/{id}` | Full node/edge graph |
| GET | `/attack-graph/scan/{id}/paths` | Ordered chain steps |
| GET | `/attack-graph/scan/{id}/blast-radius` | Findings appearing in most chains |

**Runtime:** chain → graph → END

**Verified:** 2 findings + 1 chain + 2 steps stored in Neo4j; API returns correct graph; blast radius working.

---

### P6-5 — Chain Discovery Agent v2 (Cross-Surface Kill Chains)

| Change | Detail |
|--------|--------|
| Includes `open` findings | v1 only used `confirmed`; v2 includes open high/critical |
| Surface grouping | Findings grouped by surface (web/network/container/secrets/cloud) before LLM |
| Cross-surface prompt | Models MITRE ATT&CK kill chain stages; explicitly requests pivot chains |
| Finding cap | 30 findings (was 20); sorted by severity tier + risk_score |
| `surface` field | Each step now records its surface |

**Verified:** Synthetic 5-finding cross-surface test → 2 chains, both cross-surface (network→web→container→secrets).

---

## Pipeline State (End of Phase 6)

```
recon → planner → [webapp|network|container|cloud] → validator → chain → graph → END
```

Scan types: `web`, `api`, `network`, `container`, `cloud`

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Prowler in isolated venv | Prowler forces pydantic v1 which conflicts with FastAPI + LangGraph |
| BH CE ports remapped (7475/7688) | Avoids conflict with SentinelAI's own Neo4j (7474/7687) |
| chain → graph ordering | graph_agent has all chain data to build complete edges |

---

## Known Gaps / Deferred

| Item | Status |
|------|--------|
| kube-bench (K8s hardening) | No local K8s cluster in dev |
| Prowler ec2/guardduty/cloudtrail coverage | Only iam+s3 tested |
| AWS credential rotation | Long-lived keys; use IAM roles in prod |
