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
| Frontend: scan launcher UI | ⬜ | Phase 3 |
| Frontend: findings list view | ⬜ | Phase 3 |
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

## Phase 8 — Polish & Hardening 🔵

| Task | Status | Notes |
|------|--------|-------|
| RBAC org-level permissions (P8-1) | ✅ | require_roles() + admin/analyst/viewer enforced; users API; UserContext frontend |
| Compliance reports — SOC2/ISO27001/PCI-DSS (P8-2) | ✅ | core/compliance.py mapping + /compliance/{framework} PDF endpoint + frontend export buttons |
| Production Docker Compose stack (P8-3) | ⬜ | Nginx, TLS, secrets management |
| SSO / SAML / OIDC auth (P8-4) | ⬜ | |
| Multi-tenant billing | ⬜ | |
| On-premise deployment guide | ⬜ | |
