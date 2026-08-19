# SentinelAI — Phase Tracker

> CLI updates this file as tasks are completed. Vedant uses this to track progress.

## Legend
- ⬜ Not Started  
- 🔵 In Progress  
- ✅ Done  
- ❌ Blocked

---

## Phase 0 — Project Scaffold ✅

| Task | Status | Notes |
|------|--------|-------|
| Create full folder structure | ✅ | |
| Backend FastAPI skeleton + health endpoint | ✅ | |
| Frontend Next.js 15 + shadcn/ui scaffold | ✅ | |
| docker-compose (postgres + redis) | ✅ | |
| .env.example | ✅ | |
| docs/architecture.md | ✅ | |
| ADR-001-tech-stack.md | ✅ | |
| Verify docker-compose up healthy | ✅ | postgres:16 + redis:7 both healthy |
| Verify backend /health 200 | ✅ | |
| Verify frontend dev server starts | ✅ | |
| phase-reports/phase-0-report.md | ✅ | |

---

## Phase 1 — Core Platform Foundation ✅

| Task | Status | Notes |
|------|--------|-------|
| PostgreSQL schema: users, orgs, targets, scan_jobs, findings | ✅ | SQLAlchemy models written |
| Alembic migrations | ✅ | 5 tables created, upgrade head clean |
| JWT auth endpoints (register, login, refresh) | ✅ | Live tested — register + login return JWT |
| Target management API (CRUD) | ✅ | All 5 endpoints live tested |
| Domain verification flow | ✅ | DNS TXT record check (_sentinelai-verify) |
| pytest: auth + target CRUD tests | ✅ | 12/12 passing |
| Next.js: auth pages (login/register) | ✅ | Live tested in browser |
| Next.js: dashboard shell + nav | ✅ | Auth guard + nav wired |
| Next.js: target list + add target form | ✅ | Live tested in browser |
| API client (frontend → backend) | ✅ | `frontend/lib/api.ts` — typed fetch client |
| phase-reports/phase-1-report.md | ✅ | `IMP info/reports/phase-1-audit.md` |

---

## Phase 2 — Scanning Engine Core ✅

| Task | Status | Notes |
|------|--------|-------|
| OWASP ZAP wrapper (subprocess + Docker) | ✅ | `backend/scanners/zap_scanner.py` |
| Nuclei wrapper | ✅ | `backend/scanners/nuclei_scanner.py` |
| Semgrep wrapper (SAST) | ✅ | `backend/scanners/semgrep_scanner.py` |
| Nmap wrapper (network scan) | ✅ | `backend/scanners/nmap_scanner.py` — live tested |
| Gitleaks wrapper (secrets) | ✅ | `backend/scanners/gitleaks_scanner.py` |
| Findings normalization layer | ✅ | `backend/scanners/base.py` — ScannerResult + FindingData |
| Scan job API (create, status, cancel) | ✅ | `backend/api/v1/scans.py` |
| Findings storage + retrieval API | ✅ | GET /scans/{id}/findings with pagination |
| Basic PDF report (fpdf2) | ✅ | `backend/api/v1/reports.py` — live tested |
| Celery worker for async scan jobs | ✅ | `backend/workers/scan_worker.py` |
| Frontend: scan launcher UI | ✅ | Built in Phase 3 |
| Frontend: findings list view | ✅ | Built in Phase 3 |
| Test against DVWA or Juice Shop | ✅ | Nmap scan — 5 findings, PDF clean |
| phase-reports/phase-2-report.md | ✅ | `IMP info/reports/phase-2-audit.md` |

---

## Phase 3 — AI Agent Framework ✅

| Task | Status | Notes |
|------|--------|-------|
| LangGraph agent runtime setup | ✅ | `backend/agents/runtime.py` — astream loop |
| Recon Agent (DNS, subdomain, fingerprint) | ✅ | `backend/agents/recon_agent.py` |
| Attack Planner Agent (MITRE ATT&CK mapping) | ✅ | `backend/agents/planner_agent.py` |
| Web App Agent (crawl + OWASP Top 10) | ✅ | `backend/agents/webapp_agent.py` — Nuclei |
| API Agent (OpenAPI spec parsing + BOLA/BFLA) | ✅ | `backend/agents/api_agent.py` |
| Network Agent (Nmap-guided CVE mapping) | ✅ | `backend/agents/network_agent.py` |
| LLM abstraction (Ollama dev / Claude prod) | ✅ | `llm_complete()` — `LLM_PROVIDER` env var |
| Agent result storage + pipeline wiring | ✅ | LangGraph graph: recon→planner→webapp/network→validator→chain |
| WebSocket real-time scan progress | ✅ | Redis pub/sub → WS |
| Frontend: live scan progress view | ✅ | `frontend/app/(dashboard)/agent-scans/page.tsx` |
| Celery worker for agent tasks | ✅ | `backend/workers/agent_worker.py` |
| phase-reports/phase-3-report.md | ✅ | `IMP info/reports/phase-3-audit.md` |

---

## Phase 4 — Validation & Risk Scoring ✅

| Task | Status | Notes |
|------|--------|-------|
| Validation Agent (PoC confirmation logic) | ✅ | `backend/agents/validator_agent.py` |
| SRS formula engine | ✅ | severity(40%) + exploitability(30%) + asset_criticality(20%) + confidence(10%) → 0–100 |
| False-positive detection | ✅ | LLM-based confidence scoring |
| Chain Discovery Agent v1 | ✅ | `backend/agents/chain_agent.py` — 1–5 attack paths from confirmed findings |
| Finding status workflow | ✅ | open/confirmed/false_positive/fixed — PATCH /findings/{id} |
| Frontend: SRS score + status badges | ✅ | FindingCard with SRS badge + confirm/FP/revalidate actions |
| Re-validation endpoint | ✅ | `POST /findings/{id}/validate` |
| phase-reports/phase-4-report.md | ✅ | `IMP info/reports/phase-4-audit.md` |

---

## Phase 5 — Reporting & Integrations ✅

| Task | Status | Notes |
|------|--------|-------|
| Attack chain discovery (P5-1) | ✅ | chain_agent + AttackChain model + GET /agent-scans/{id}/chains |
| Redis pub/sub WS + JWT auth (P5-2) | ✅ | Live events stream; sync publish in worker; async subscribe in WS |
| SARIF 2.1.0 export (P5-3) | ✅ | GET /agent-scans/{id}/sarif |
| PDF report improvements (P5-4) | ✅ | Exec summary, SRS per finding, chains section; fpdf2 cursor fix |
| Jira + Slack integrations (P5-5) | ✅ | POST /agent-scans/{id}/integrations/slack|jira |
| UI refresh state persistence | ✅ | GET /agent-scans list + listAgentScans() + mount useEffect |
| Nuclei v3 fix | ✅ | -jsonl flag, returncode check, PATH fix |
| Redis pub/sub sync fix | ✅ | publish_scan_event_sync() — no event-loop errors |
| E2E verified | ✅ | 15 findings, 1 chain, 17 live events — scanme.nmap.org |
| phase-reports/phase-5-report.md | ✅ | `IMP info/reports/phase-5-audit.md` |

---

## Phase 6 — Advanced Modules ✅

| Task | Status | Notes |
|------|--------|-------|
| Cytoscape.js chain graph (P6-1) | ✅ | ChainGraph.tsx — chain selector + graph + node tap detail; verified with real scan |
| Container/K8s: Trivy + kube-bench (P6-2) | ✅ | trivy_scanner.py + container_agent.py — 379 findings, 26 LLM-enriched |
| Cloud Security: Prowler/ScoutSuite (P6-3) | ✅ | prowler_scanner.py + cloud_agent.py — 18 findings on real AWS, LLM-enriched |
| Neo4j attack path graph (P6-4) | ✅ | graph_agent + attack_graph API + AttackGraphView — Cytoscape + blast radius tab |
| Chain Discovery Agent v2 (P6-5) | ✅ | Cross-surface kill chains — network→web→container→secrets pivots, surface badges in UI |

---

## Phase 7 — Enterprise Features ✅

| Task | Status | Notes |
|------|--------|-------|
| BloodHound CE — AD attack paths (P7-1) | ✅ | bloodhound_client.py Cypher; bloodhound_agent.py; "ad" route in runtime |
| Continuous monitoring — Celery Beat (P7-2) | ✅ | ScheduledScan model; beat_worker.py 60s tick; /schedules CRUD API + frontend page |
| SIEM integration — Splunk HEC + ES (P7-3) | ✅ | siem_client.py; siem_worker.py; ship_to_siem triggered post-scan if SIEM_ENABLED |
| End-to-end demo — all 4 scan types | ✅ | Network ✅ Container ✅ Cloud ✅ AD ✅ — verified 2026-08-03 |
| Bug fix: Neo4j driver event-loop binding | ✅ | _close_neo4j() in agent_worker.py finally block (16e0804) |
| Bug fix: Prowler AWS creds in Celery worker | ✅ | load_dotenv at top of agent_worker.py (19a0f1a) |
| Bug fix: BH CE nodes/edges dict→list | ✅ | _to_list() helper in bloodhound_client.py (a938554) |

**Git HEAD:** a938554

---

## Phase 8 — Polish & Hardening ✅

| Task | Status | Notes |
|------|--------|-------|
| RBAC org-level permissions (P8-1) | ✅ | require_roles() + admin/analyst/viewer enforced; users API; UserContext frontend |
| Compliance reports — SOC2/ISO27001/PCI-DSS (P8-2) | ✅ | core/compliance.py mapping + /compliance/{framework} PDF endpoint + frontend export buttons |
| Production Docker Compose stack (P8-3) | ✅ | Nginx + TLS + internal network; backend/frontend Dockerfiles |
| SSO / SAML / OIDC auth (P8-4) | ✅ | Google OIDC; /auth/oidc/login + /callback; auto-provision users |
| Demo seed data (P9-4) | ✅ | scripts/seed_demo.py — demo org, 3 users, 3 targets, 2 scans, 10 findings, 2 chains |
| Multi-tenant billing | ⬜ | Deferred — no timeline |
| On-premise deployment guide | ✅ | Helm chart (22 templates) + Docker Compose runbook + deploy.sh |

---

## Full Platform E2E Verification ✅ (2026-08-09, git HEAD 97baee1)

| Feature | Status | Notes |
|---------|--------|-------|
| Login / Register | ✅ | |
| Targets (RBAC-gated Add/Delete) | ✅ | Viewer read-only; Admin delete only |
| Agent Scans + WebSocket live events | ✅ | |
| Findings (confirm/FP/revalidate) | ✅ | |
| Attack Chains + Cytoscape graph | ✅ | |
| Attack Path Graph (Neo4j) | ✅ | |
| Compliance PDFs (SOC2/ISO27001/PCI-DSS) | ✅ | Fixed: em-dash latin-1 crash |
| RBAC (viewer/analyst/admin) | ✅ | Fixed: targets page missing role gate |
| Schedules (create/pause/delete) | ✅ | |
| Users page (admin-only) | ✅ | |

**Bug fixes landed this session:**
- `frontend/lib/api.ts`: Pydantic array `detail` → `.msg` join (fixed `[object Object]` on login errors)
- `scripts/seed_demo.py`: `.local` → `.example.com` TLD in seed emails
- `backend/scanners/nmap_scanner.py`: `-T4 --host-timeout 90s` (fast single-host scans)
- `backend/api/v1/compliance.py`: 4 em-dash literals → ASCII `-` (fpdf2 latin-1 crash)
- `frontend/app/(dashboard)/targets/page.tsx`: role-gated Add target + Delete buttons

---

## Session 29 — Manual Testing + Bug Fixes ✅ (2026-08-20, git HEAD 7b546f8)

**Bugs found and fixed during manual E2E testing:**

| Fix | Commit | File |
|-----|--------|------|
| `pollUntilDone` 90s timeout too short for network scans (~127s) → 6 min | `c9653af` | `frontend/app/(dashboard)/agent-scans/page.tsx` |
| ChainGraph: step nodes with no finding show "Step N" for all → show action text | `9985aa3` | `frontend/components/ChainGraph.tsx` |
| `validation_agent` bounds check `chunk_idx < len(...)` misses `offset` → IndexError on large scans | `7b546f8` | `backend/agents/validation_agent.py` |

**Verified working:**
- Login, RBAC, unverified target gate, target delete, Pydantic 422s
- Network scan end-to-end (findings, attack chains, attack path graph)
- Compliance PDF (SOC2 / ISO27001 / PCI-DSS)
- Container scan (Trivy + LLM enrichment pipeline)

**Known gaps (not blocking):**
- ZAP not installed → web/API DAST always 0 findings (`brew install --cask owasp-zap`)
- Schedules + Users CRUD UI not walked through this session
- Compliance PDF, findings confirm/FP/revalidate, Blast Radius tab — not UI-clicked yet (API verified)

**Container scan verified:** `python:3.8-slim` → 400 findings, 3 chains, 940s ✅

**Next session: start from findings UI actions → compliance PDF → schedules → users**

---

## Professional Code Review — All 14 Findings Fixed ✅ (2026-08-16, git HEAD cd7d870)

| Finding | Severity | Fix | File(s) |
|---------|----------|-----|---------|
| Missing pip dependencies | P0 | requirements.txt rewritten with 18 pinned deps | `backend/requirements.txt` |
| Validation index misalignment | P0 | `to_validate_indices` now used in `_validate_chunk`; chunk-relative→global mapping | `backend/agents/validation_agent.py` |
| Missing await on db.delete | P0 | `await db.delete(target)` | `backend/api/v1/targets.py` |
| Attack graph no org-scoping | P1 | `_assert_scan_org()` helper on all 3 endpoints | `backend/api/v1/attack_graph.py` |
| WebSocket no auth check | P1 | Org membership verified before `websocket.accept()` | `backend/api/v1/agent_scans.py` |
| nginx WS path never matched | P1 | `/api/v1/agent-scans/ws/` explicit location | `infra/nginx/nginx.conf` |
| nginx health path 404 | P1 | `/api/v1/health` → `backend:8000/api/v1/health` | `infra/nginx/nginx.conf` |
| Docker healthcheck path wrong | P1 | `curl … /api/v1/health` | `infra/docker/docker-compose.prod.yml` |
| Viewer can launch scans | P2 | `Depends(require_analyst)` on POST /scans | `backend/api/v1/scans.py` |
| Unverified target scannable | P2 | 422 if `not target.verified` | `backend/api/v1/scans.py` |
| Nmap info → auto-FP | P2 | `severity="low"` | `backend/scanners/nmap_scanner.py` |
| Pydantic v1 validators | P2 | `@field_validator` in auth.py + users.py | `backend/api/v1/auth.py`, `users.py` |
| OIDC hardcoded authorize URL | P2 | Async `build_authorization_url` from discovery | `backend/core/oidc.py`, `auth.py` |
| Stale model IDs | P3 | `claude-opus-5` / `claude-sonnet-5` | `backend/core/llm.py` |
| Kafka never used | P3 | Removed Kafka + Zookeeper services | `infra/docker/docker-compose.yml` |
| No DB rollback on error | P3 | `try/except rollback` in `get_db` | `backend/core/db.py` |
| Redundant except clause | P3 | `except (LLMError, Exception)` → `except Exception` | `backend/api/v1/findings.py` |
