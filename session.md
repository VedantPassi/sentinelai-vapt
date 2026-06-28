# SentinelAI — Session Context File

> **CLI: Read this entire file before doing anything.**
> Update the "Current Session" section at the start of every session and the "End of Session" section when done.

---

## Project Identity

**Name:** SentinelAI  
**Type:** AI-native Vulnerability Assessment & Penetration Testing platform  
**Goal:** Autonomous multi-agent security testing — web app, API, and network surfaces  
**Working Dir:** `/Users/vedantpassi/Desktop/Projects/AI VAPT`

---

## Your Role

You are a **senior full-stack + security engineer**.  
Vedant is the **CTO / PM** — he reviews and approves everything.

**Non-negotiable rules:**
1. Ask permission before executing ANY shell command — list exact command + reason, wait for approval
2. Work only on tasks in the current phase — do not jump ahead
3. Read this file first, every single session
4. Update this file at the end of every session
5. At phase completion, generate `IMP info/reports/phase-N-audit.md`
6. Keep `PHASES.md` updated as your task board

---

## Tech Stack (locked — do not deviate without asking)

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| AI / Agents | LangGraph, Anthropic Claude API (`claude-sonnet-4-6` default, `claude-opus-4-8` for reasoning-heavy tasks) |
| Frontend | Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS, Cytoscape.js |
| Primary DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Queue | Apache Kafka + Celery |
| Graph DB | Neo4j — Phase 6+ only |
| Vector DB | Weaviate — Phase 6+ only |
| Containers | Docker + docker-compose (dev) |
| DAST Tools | OWASP ZAP, Nuclei |
| SAST Tools | Semgrep |
| Network | Nmap |
| Secrets | Gitleaks, TruffleHog |
| Testing | pytest (backend), Vitest (frontend) |

---

## Phase Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Project Scaffold | ✅ Complete |
| 1 | Core Platform Foundation | ✅ Complete |
| 2 | Scanning Engine Core | ✅ Complete |
| 2 | Scanning Engine Core | ✅ Complete |
| 3 | AI Agent Framework | 🔄 In Progress |
| 4 | Validation & Risk Scoring | ⬜ Not Started |
| 5 | Reporting & Integrations | ⬜ Not Started |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started |
| 7 | Enterprise Features | ⬜ Not Started |

**Current Phase: 3**

---

## Coding Standards

- **No unnecessary comments.** Self-documenting names only.
- **No features beyond current phase scope.**
- **Every API endpoint:** Pydantic input validation, typed responses.
- **Security:** No hardcoded secrets. All config via `.env`. No raw SQL string concat.
- **No backwards-compat shims.** Delete dead code.
- **Error handling:** Only at system boundaries (HTTP, subprocess, external API calls).

---

## Known Issues / Constraints

- **CLI Write tool corrupts files >50 lines** (line-wrap truncation). CTO writes all long Python files directly. CLI must run `python3 -c "import ast; ast.parse(open('f').read())"` after any file write.
- **passlib incompatible with bcrypt 5.x** — `__about__` removed. Fixed: replaced passlib with direct `bcrypt` calls in `core/security.py`.
- **asyncpg connections tied to event loop** — each pytest-anyio test gets its own loop. Fix: `dispose_engine` autouse fixture in `tests/unit/conftest.py`.
- **postgres dev password:** `sentineldev`
- **config.py `env_file="../.env"`** — tech debt, switch to `Path(__file__)` in Phase 2.

---

## Reference Materials

- Blueprint: `~/Downloads/vapt-platform-blueprint_1.html` — full platform spec
- Shannon (agent architecture reference): https://github.com/KeygraphHQ/shannon
- AI-VAPT (tool integration reference): https://github.com/vikramrajkumarmajji/AI-VAPT

---

## Current Session Log

**Session #:** 5
**Date:** 2026-06-28
**Phase:** 3 — AI Agent Framework

**What was done:**
- All Phase 3 agent files written + syntax verified ✅:
  - `backend/agents/state.py` — AgentState TypedDict, ReconData, AttackPlan, AttackVector, ProgressEvent
  - `backend/agents/runtime.py` — LangGraph graph (recon→planner→webapp|network), lazy compile, `run_agent_scan()` entry point
  - `backend/agents/recon_agent.py` — async DNS lookup (run_in_executor), subdomain enum, HTTP fingerprint
  - `backend/agents/planner_agent.py` — Claude Opus 4.8 attack planning, MITRE ATT&CK vectors, graceful no-key fallback
  - `backend/agents/webapp_agent.py` — parallel ZAP + Nuclei, Claude sonnet-4-6 enrichment
  - `backend/agents/network_agent.py` — Nmap + optional Gitleaks, Claude CVE mapping
  - `backend/workers/agent_worker.py` — Celery task wrapping run_agent_scan, stores findings in DB
  - `backend/api/v1/agent_scans.py` — POST /agent-scans, GET /{id}, GET /{id}/findings, WS /ws/{id}
- `main.py` updated — agent_scans_router wired ✅
- Live API test: POST /agent-scans → 201, scan_id returned, status=pending ✅
- Celery agent worker started + confirmed working ✅
- Full end-to-end test: POST /agent-scans → Celery → LangGraph → Nmap → 4 findings stored in DB ✅
- progress_events persisted to scan.config JSONB, WebSocket polling confirmed functional ✅

**Decisions made:**
- WebSocket progress: DB polling (scan.config["progress_events"]) — Redis stream deferred to Phase 5
- Tenant isolation: Target join pattern (no org_id on ScanJob) — matches existing scans.py
- Model split: claude-opus-4-8 for planner (reasoning), claude-sonnet-4-6 for webapp/network enrichment
- WS endpoint has no auth (acceptable Phase 3 dev risk — Phase 5 fix)
- ANTHROPIC_API_KEY empty in .env — planner + enrichment skip gracefully, scanners still run

**Blockers:**
- ANTHROPIC_API_KEY not set in .env — Claude enrichment will skip until filled
- Celery agent worker not tested end-to-end yet (Nmap scan + findings storage)

**Next session should:**
1. Start Celery agent worker:
   `PYTHONPATH=. .venv/bin/celery -A workers.agent_worker worker --loglevel=info`
2. Add ANTHROPIC_API_KEY to .env
3. POST /agent-scans → wait → GET status → verify progress_events populated
4. GET /agent-scans/{id}/findings → verify findings stored
5. Generate `IMP info/reports/phase-3-audit.md`
6. Start Phase 3 frontend: scan launcher UI + real-time progress WebSocket view

---

## End of Session Template

```
**Session #:** N  
**Date:** YYYY-MM-DD  
**Phase:** X  
**What was done:** [bullet list]  
**Decisions made:** [any deviations or choices]  
**Blockers:** [anything blocking]  
**Next session should:** [first task to pick up]
```
