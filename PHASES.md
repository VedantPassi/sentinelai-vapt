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

## Phase 3 — AI Agent Framework ⬜

| Task | Status | Notes |
|------|--------|-------|
| LangGraph agent runtime setup | ⬜ | |
| Recon Agent (DNS, subdomain, fingerprint) | ⬜ | |
| Attack Planner Agent (MITRE ATT&CK mapping) | ⬜ | |
| Web App Agent (crawl + OWASP Top 10) | ⬜ | |
| API Agent (OpenAPI spec parsing + BOLA/BFLA) | ⬜ | |
| Network Agent (Nmap-guided CVE mapping) | ⬜ | |
| Claude API integration (claude-sonnet-4-6) | ⬜ | |
| GitHub/GitLab source code integration | ⬜ | |
| Agent result storage + pipeline wiring | ⬜ | |
| WebSocket real-time scan progress | ⬜ | |
| Frontend: live scan progress view | ⬜ | |
| phase-reports/phase-3-report.md | ⬜ | |

---

## Phase 4 — Validation & Risk Scoring ⬜

| Task | Status | Notes |
|------|--------|-------|
| Validation Agent (PoC confirmation logic) | ⬜ | |
| SRS formula engine (CVSS + exploitability + asset criticality + EPSS) | ⬜ | |
| False-positive ML classifier v1 | ⬜ | |
| Chain Discovery Agent v1 (finding correlation) | ⬜ | |
| Confidence scoring per finding | ⬜ | |
| Finding status workflow (confirmed/unconfirmed/FP) | ⬜ | |
| Frontend: SRS score display + risk breakdown | ⬜ | |
| phase-reports/phase-4-report.md | ⬜ | |

---

## Phase 5 — Reporting & Integrations ⬜

| Task | Status | Notes |
|------|--------|-------|
| Executive dashboard (posture score, trends) | ⬜ | |
| PDF/HTML report templates | ⬜ | |
| MITRE ATT&CK mapping in reports | ⬜ | |
| OWASP ASVS compliance report | ⬜ | |
| Code patch generation (Claude API) | ⬜ | |
| JIRA integration (ticket creation) | ⬜ | |
| Slack integration (finding alerts) | ⬜ | |
| Frontend: report viewer + download | ⬜ | |
| phase-reports/phase-5-report.md | ⬜ | |

---

## Phase 6 — Advanced Modules ⬜
_(Months 4–6 — detailed tasks TBD at Phase 5 completion)_

- Cloud Security: Prowler/ScoutSuite (AWS/GCP)
- Container/K8s: Trivy, kube-bench, kube-hunter
- Neo4j attack path graph
- Chain Discovery Agent v2 (cross-surface kill chains)

---

## Phase 7 — Enterprise Features ⬜
_(Months 7–12 — detailed tasks TBD at Phase 6 completion)_

- Active Directory / IAM (BloodHound CE)
- Continuous monitoring mode
- Fine-tuned security LLMs
- SIEM/SOAR integrations
- On-premise deployment
