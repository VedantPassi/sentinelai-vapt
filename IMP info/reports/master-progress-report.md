# SentinelAI — Master Progress Report

**Date:** 2026-06-30
**Phases Complete:** 0 → 4 (5 of 7)
**Status:** Active development

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

## What's Left (Phases 5–7)

| Phase | Name | Key Deliverables |
|-------|------|-----------------|
| 5 | Reporting & Integrations | Real-time WS streaming, attack chain agent, Jira/Slack integration, SARIF export, WS auth |
| 6 | Advanced Modules | Cloud/K8s scanning, Neo4j attack graph, Weaviate semantic search |
| 7 | Enterprise Features | SSO/SAML, compliance reports (SOC2/OWASP), multi-tenant billing |

---

## Known Deferred Items

| Item | Deferred To |
|------|-------------|
| WebSocket auth | Phase 5 |
| Real-time incremental WS streaming (currently batch at completion) | Phase 5 |
| `chain_agent.py` — attack chain discovery | Phase 5 |
| ANTHROPIC_API_KEY in .env (using Ollama now) | When switching to prod |
| PATCH `/findings/{id}` live curl test | Phase 5 test suite |
