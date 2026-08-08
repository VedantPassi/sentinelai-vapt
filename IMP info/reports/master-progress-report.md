# SentinelAI — Master Progress Report

**Date:** 2026-08-08
**Phases Complete:** 0 → 9 ✅ (PLATFORM FEATURE COMPLETE)
**Status:** All phases shipped — P9 on-premise deployment + demo data complete
**Git HEAD:** 315e87b

---

## What Is SentinelAI?

AI-native Vulnerability Assessment & Penetration Testing (VAPT) platform. Autonomous multi-agent system that runs reconnaissance, plans attacks, executes scanners, validates findings, and scores risk — all without manual intervention.

---

## Phase-by-Phase Summary

---

### Phase 0 — Project Scaffold ✅

**Goal:** Repo structure, Docker, environment setup.

**Delivered:**
- Monorepo layout: `backend/`, `frontend/`, `IMP info/`, `phase-reports/`
- `docker-compose.yml` — PostgreSQL 16, Redis 7, Zookeeper, Kafka
- `.env` template, `.gitignore`, `session.md` (CLI context file)
- `backend/pyproject.toml` — Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic
- `frontend/` — Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui

---

### Phase 1 — Core Platform Foundation ✅

**Goal:** Auth, database models, core API infrastructure.

**Delivered:**

**Database Models (5 tables):**
| Table | Purpose |
|-------|---------|
| `organizations` | Multi-tenant root |
| `users` | Auth, roles (admin/analyst/viewer) |
| `targets` | Scan targets with asset_criticality |
| `scan_jobs` | Scan task records |
| `findings` | Vulnerability findings |

**Auth System:**
- JWT (HS256) — access + refresh tokens
- bcrypt password hashing (direct, no passlib)
- Role-based: admin / analyst / viewer

**API Endpoints:**
- `POST /auth/register` — org + admin user creation
- `POST /auth/login` — JWT token issue
- `GET/POST/PUT/DELETE /targets` — full CRUD
- `GET /health` — liveness check

**Testing:** 12/12 pytest tests passing (auth + targets CRUD)

---

### Phase 2 — Scanning Engine Core ✅

**Goal:** Real scanner integration, async scan jobs, findings storage.

**Delivered:**

**Scanner Integrations:**
| Scanner | Type | Purpose |
|---------|------|---------|
| OWASP ZAP | DAST | Web app active scanning |
| Nuclei | DAST | Template-based vuln detection |
| Nmap | Network | Port/service enumeration |
| Gitleaks | Secrets | Repo secret scanning |
| Semgrep | SAST | Static code analysis |

**Async Task Queue:**
- Celery + Redis broker — scan jobs dispatched async
- `run_scan` task: creates `ScanJob`, dispatches scanner, stores `Finding` records

**API Endpoints:**
- `POST /scans` — create + queue scan job
- `GET /scans/{id}` — status + progress
- `GET /scans/{id}/findings` — paginated findings
- `GET /reports/{scan_id}` — PDF report generation (fpdf2)

**Key decisions:**
- Tenant isolation: `Target.org_id` join pattern (no `org_id` on `ScanJob`)
- Per-scan UUID temp dirs for ZAP (race condition fix)

---

### Phase 3 — AI Agent Framework ✅

**Goal:** LangGraph multi-agent pipeline, autonomous scan orchestration.

**Delivered:**

**LangGraph Pipeline:**
```
POST /agent-scans
  → Celery worker
    → LangGraph graph
      → recon_agent    (DNS, subdomain enum, HTTP fingerprint)
      → planner_agent  (LLM — MITRE ATT&CK attack vectors)
      → webapp_agent   (ZAP + Nuclei + LLM enrichment)   [web/api]
      → network_agent  (Nmap + Gitleaks + LLM CVE map)   [network]
    → findings → DB
```

**Agent Files:**
| File | Purpose |
|------|---------|
| `agents/state.py` | `AgentState` TypedDict — shared state across all nodes |
| `agents/runtime.py` | LangGraph graph builder, lazy compile, `run_agent_scan()` |
| `agents/recon_agent.py` | Async DNS (run_in_executor), subdomain enum, HTTP fingerprint |
| `agents/planner_agent.py` | LLM attack planning, MITRE ATT&CK, 3–8 vectors |
| `agents/webapp_agent.py` | Parallel ZAP + Nuclei via asyncio.gather(), LLM enrichment |
| `agents/network_agent.py` | Nmap + optional Gitleaks, LLM CVE mapping |
| `workers/agent_worker.py` | Celery task wrapping LangGraph |

**API Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent-scans` | Create + queue agent scan |
| GET | `/agent-scans/{id}` | Status + progress events |
| GET | `/agent-scans/{id}/findings` | Paginated findings |
| WS | `/agent-scans/ws/{id}` | Real-time progress stream |

**Frontend:**
- `/agent-scans` page — scan launcher, WebSocket progress terminal, findings list

**Live test:** network scan → Nmap → 4 findings → rendered in browser ✅

**10 bugs fixed** (asyncio, missing deps, ZAP race, CORS hardcode, etc.)

---

### Phase 4 — Validation & Risk Scoring ✅

**Goal:** LLM validates every finding, scores risk, analyst can override.

**Delivered:**

**LLM Abstraction Layer:**
```python
async def llm_complete(prompt, system="", model_tier="standard") -> str
```
- Ollama (local, free) for dev — `qwen2.5:7b` on M5 Mac
- Anthropic (`claude-sonnet-4-6` / `claude-opus-4-8`) for production
- Switch via `LLM_PROVIDER` env var — zero code change
- 1 retry on timeout, `LLMError` on failure, graceful skip in agents

**Updated Pipeline:**
```
recon → planner → webapp|network → validator → END
```

**Validation Agent (`agents/validation_agent.py`):**
- Rules-based pre-filter (classifier) runs first
- Remaining findings sent to LLM in batches of ≤10
- Each finding gets: `status` (confirmed/false_positive), `risk_score` (0–100), `validation_reasoning`

**False-Positive Classifier (`scoring/classifier.py`) — 6 rules:**
1. `severity == "info"` → FP
2. `missing-header` on non-web target → FP
3. Title contains: "test page", "default page", "welcome to", "tech-detect", "technologies" → FP
4. `risk_score == 0` + severity low/info → FP
5. Description < 20 chars → FP
6. Nuclei tech-detect template names → FP

**SRS Risk Formula (`scoring/srs.py`):**
```
SRS = severity(40%) + exploitability(30%) + asset_criticality(20%) + confidence(10%)
Range: 0–100. FP always = 0.
```

**New API Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/findings/{id}` | Full finding + validation_reasoning |
| PATCH | `/findings/{id}` | Manual status/remediation override, recomputes SRS |
| POST | `/findings/{id}/validate` | Re-run LLM on single finding (~2s on Ollama) |

**Frontend Upgrades:**
- SRS score badge (red ≥70, orange ≥40, gray <40)
- Status badge (CONFIRMED green / FALSE POSITIVE red strikethrough / OPEN gray)
- Collapsible validation reasoning
- Confirm / False Positive / Re-validate buttons with optimistic updates

**Live test results:**
- Scan completed: 2 findings
- 1 FP (rules: info severity, `srs_score=0`)
- 1 confirmed (Ollama LLM, `srs_score=68.0`)
- `/findings/{id}/validate` re-ran LLM, updated score ✅

**3 bugs fixed:** asyncio.run() in Celery, asset_criticality float mapping, migration NOT NULL

---

## Current Tech Stack (In Use)

| Layer | Technology | Status |
|-------|-----------|--------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic | ✅ Live |
| AI Agents | LangGraph, Ollama qwen2.5:7b (dev) / Anthropic claude-* (prod) | ✅ Live |
| Frontend | Next.js 15 App Router, TypeScript, Tailwind CSS | ✅ Live |
| Database | PostgreSQL 16 | ✅ Live |
| Cache/Queue | Redis 7 + Celery | ✅ Live |
| Scanners | Nmap, ZAP, Nuclei, Gitleaks, Semgrep | ✅ Integrated |
| Auth | JWT HS256, bcrypt | ✅ Live |
| Graph DB | Neo4j | ⬜ Phase 6 |
| Vector DB | Weaviate | ⬜ Phase 6 |

---

## API Surface (Complete)

| Method | Path | Phase |
|--------|------|-------|
| POST | `/auth/register` | 1 |
| POST | `/auth/login` | 1 |
| GET/POST/PUT/DELETE | `/targets` | 1 |
| GET | `/targets/{id}` | 1 |
| POST | `/scans` | 2 |
| GET | `/scans/{id}` | 2 |
| GET | `/scans/{id}/findings` | 2 |
| GET | `/reports/{scan_id}` | 2 |
| POST | `/agent-scans` | 3 |
| GET | `/agent-scans/{id}` | 3 |
| GET | `/agent-scans/{id}/findings` | 3 |
| WS | `/agent-scans/ws/{id}` | 3 |
| GET | `/findings/{id}` | 4 |
| PATCH | `/findings/{id}` | 4 |
| POST | `/findings/{id}/validate` | 4 |
| GET | `/health` | 1 |

---

## Codebase Stats

| Metric | Count |
|--------|-------|
| Backend Python files | 42 |
| Frontend TS/TSX files | 12 |
| DB tables | 5 |
| API endpoints | 16 |
| Scanners integrated | 5 |
| Agent nodes | 5 (recon, planner, webapp, network, validator) |
| Bugs fixed total | ~25 across all phases |

---

## Phase 5 — Reporting & Integrations ✅
P5-1 chain_agent, P5-2 Redis WS streaming, P5-3 SARIF export, P5-4 PDF improvements, P5-5 Jira+Slack. See phase-5-audit.md.

## Phase 6 — Advanced Modules ✅
P6-1 Cytoscape chain graph, P6-2 Trivy container scanning, P6-3 Prowler cloud (AWS), P6-4 Neo4j attack graph, P6-5 chain agent v2 cross-surface kill chains. See phase-6-audit.md.

## Phase 7 — Enterprise Features ✅ COMPLETE

### P7-1 BloodHound CE — Active Directory Attack Paths ✅
- BloodHound CE deployed (Docker, localhost:8080)
- Synthetic AD: TESTCORP.LOCAL, charlie→bob→alice→Domain Admins via WriteDACL+GenericAll
- `bloodhound_client.py` uses `/api/v2/graphs/cypher` (Cypher queries, not dead REST endpoints)
- `bloodhound_agent.py` — paths → FindingData(category=ad, severity=critical) + LLM enrichment
- Pipeline route: `target_type="ad"` → bloodhound node; recon/planner skip for `ad`
- Frontend: "Active Directory (BloodHound)" scan type option

### P7-2 Continuous Monitoring — Celery Beat ✅
- `ScheduledScan` model: target, scan_type, interval_hours, next_run_at, is_active
- `workers/beat_worker.py`: 60s tick → `check_due_schedules` → creates ScanJob → enqueues run_agent_task
- Full CRUD API: `POST/GET/PATCH/DELETE /schedules`
- Frontend `/schedules` page: create form, pause/resume/delete table

### P7-3 SIEM Integration ✅
- `siem_client.py` — async httpx: Splunk HEC + Elasticsearch bulk API, fire-and-forget
- `siem_worker.py` — Celery task `ship_to_siem(scan_id)`: loads findings from DB, builds events, calls `forward_to_siem`
- Triggered post-scan in `agent_worker.py` if `SIEM_ENABLED=true`
- Enable: `SIEM_ENABLED=true`, `SPLUNK_HEC_URL`, `SPLUNK_HEC_TOKEN`, `ES_URL` in `.env`

### End-to-End Demo ✅ (verified 2026-08-03)
| Scan Type | Tool | Findings | Chains |
|-----------|------|----------|--------|
| Network | Nmap + Nuclei | 2 | 1 |
| Container | Trivy (python:3.8-slim) | 50 | 5 |
| Cloud | Prowler (real AWS) | 21 | 2 |
| Active Directory | BloodHound CE (TESTCORP.LOCAL) | 1 critical | 0 |

### Bug Fixes (session 22)
| Bug | Fix | Commit |
|-----|-----|--------|
| Neo4j `AsyncDriver` binds to first task's event loop; subsequent tasks fail | `_close_neo4j()` in `run_agent_task` finally block | 16e0804 |
| Prowler reads `os.environ` directly; Celery worker never sources `.env` | `load_dotenv(Path(...) / ".env")` at top of `agent_worker.py` | 19a0f1a |
| BH CE `/api/v2/graphs/cypher` returns nodes/edges as string-keyed dicts; `nodes[0]` → `KeyError: 0` | `_to_list()` helper normalizes dict→list in `bloodhound_client.py` | a938554 |

---

## Phase 8 — Polish & Hardening ✅ COMPLETE

### P8-1 RBAC Enforcement ✅ (aeade70)
- `core/deps.py` — `require_roles(*roles)` factory; `require_admin` / `require_analyst` shorthands
- Route guards: targets (POST/PUT=analyst, DELETE=admin), agent_scans (POST=analyst), findings (PATCH/validate=analyst), integrations (POST=analyst), schedules (POST/PATCH=analyst, DELETE=admin)
- `api/v1/users.py` — admin-only: GET/POST/PATCH role/DELETE org members; self-remove + self-role-change blocked
- `api/v1/auth.py` — `GET /auth/me` → `{id, email, role, org_id}`
- Frontend: `UserContext` + `useUser()` hook; layout shows email+role+Users nav (admin only); Launch/create/delete hidden for viewer

### P8-2 Compliance Reports ✅ (1d7e5d2)
- `core/compliance.py` — control mapping for 3 frameworks:
  - SOC2 TSC: CC6.1, CC6.2, CC6.6, CC6.7, CC7.1, CC7.2, CC8.1, CC9.2
  - ISO27001 Annex A: A.5.23, A.8.8, A.9.1, A.9.4, A.10.1, A.12.1, A.14.2, A.16.1
  - PCI-DSS v4: Req 1–4, 6–8, 10–11
  - Matching: category + severity + title/description keywords → `evaluate_framework()` → `ControlResult(status=NON-COMPLIANT|REVIEW|COMPLIANT)`
- `api/v1/compliance.py` — `GET /agent-scans/{id}/compliance/{framework}` → PDF download
  - `?token=` query param fallback (same as WS auth) for browser `<a>` download
  - PDF: header, summary, controls table, per-control detail with findings + remediation, compliant list
- Frontend: 3 compliance export buttons (SOC2 / ISO27001 / PCI-DSS) on completed scan card

### P8-3 Production Docker Stack ✅ (session 25)
- `infra/docker/docker-compose.prod.yml` — all services, internal/external networks, no exposed ports except 80/443
- `infra/nginx/nginx.conf` — TLS 1.2/1.3, HTTP→HTTPS, rate limiting, WS proxy, security headers
- `backend/Dockerfile` + `frontend/Dockerfile` (multi-stage standalone)
- `.env.prod.example` — full prod var template, `.env.prod` gitignored

### P8-4 SSO / OIDC ✅ (session 25)
- `backend/core/oidc.py` — generic OIDC discovery + code exchange + userinfo (httpx)
- `GET /auth/oidc/login` — state cookie + redirect to provider
- `GET /auth/oidc/callback` — CSRF check + code exchange + find/create user + JWT + redirect
- `frontend/app/(auth)/callback/page.tsx` — token handler, localStorage, redirect to /dashboard
- Login page: "Sign in with Google" button (gated by `NEXT_PUBLIC_OIDC_ENABLED`)

## Phase 9 — On-Premise Deployment ✅ COMPLETE (315e87b)

### P9-1 Helm Chart ✅
- `infra/helm/sentinelai/` — 22 templates
- All 8 services: postgres, redis, neo4j, backend, worker, beat, frontend, ingress
- PVCs (postgres 20Gi, redis 5Gi, neo4j 10Gi), ConfigMap, Secret with required guards
- migrations Job (post-install/upgrade hook), Ingress (nginx, TLS, WS)
- Helm lint: PASS

### P9-2 Runbook ✅
- `docs/deployment/on-premise.md` — Docker Compose + K8s paths, TLS (certbot/manual), upgrade, backup/restore, troubleshooting, env var reference

### P9-3 Deploy Script ✅
- `scripts/deploy.sh` — interactive; auto-generates secrets; builds images; waits for healthchecks; runs migrations; helm install/upgrade

### P9-4 Demo Seed ✅
- `scripts/seed_demo.py` — idempotent; AcmeCorp demo org; admin/analyst/viewer users; 3 targets; 2 completed scans; 10 realistic findings (SQLi, XSS, JWT, Redis exposure, runc CVE); 2 attack chains; 1 running scan; 1 weekly schedule

---

## Platform Status: FEATURE COMPLETE

All phases P0–P9 shipped. Deferred items:

| Item | Status |
|------|--------|
| Multi-tenant billing (Stripe) | Deferred — no timeline |
| Fine-tuned security LLM | Deferred |

---

## Known Deferred Items

| Item | Deferred To |
|------|-------------|
| Real Windows AD environment test | Phase 8 or customer env |
| BH CE Cypher edge traversal edge cases | Covered by `_to_list()` fix |
| Beat HA / Redis lock (multiple Beat instances) | Phase 8 |
| Schedule per-run history | Phase 8 |
| Fine-tuned security LLMs | Phase 8 |
