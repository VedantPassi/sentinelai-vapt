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
| 3 | AI Agent Framework | ✅ Complete |
| 4 | Validation & Risk Scoring | ✅ Complete |
| 5 | Reporting & Integrations | ⬜ Not Started |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started |
| 7 | Enterprise Features | ⬜ Not Started |

**Current Phase: 4**

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

**Session #:** 9
**Date:** 2026-07-01
**Phase:** 5 — Reporting & Integrations

**What was done:**
- P5-1 chain_agent — fully wired + e2e verified ✅
  - `chain_agent.py` enumerate bug fixed (`for i, f in enumerate(top)`)
  - `agent_worker.py` writes AttackChain rows to DB post-scan
  - `GET /agent-scans/{scan_id}/chains` endpoint live
  - Chain API tested: 3 chains returned from Ollama on synthetic confirmed findings
- P5-2 Redis pub/sub WS + JWT auth — complete ✅
  - `core/redis_client.py` — async Redis singleton (db=3)
  - `core/events.py` — `publish_scan_event()` with error swallow
  - `agents/runtime.py` — switched to `astream`, publishes events per node
  - `api/v1/agent_scans.py` — JWT auth via `?token=` query param, Redis subscribe, 30s fallback to DB poll
  - `workers/agent_worker.py` — terminal system event published after all DB commits
  - `frontend/lib/api.ts` — `?token=` appended to WS URL
  - E2e verified: scan completed, 13 progress events, 0 chains (correct — no scanner tools = no findings)

**Decisions made:**
- Redis pub/sub (not streams) — simpler, WS is sole consumer
- `?token=` query param for WS auth — only way from browser JS
- CLI truncation bug confirmed: CTO writes scripts >20 lines to /tmp/*.py directly
- Celery restart pattern: `pkill -f "celery.*agent_worker"` + `PYTHONPATH=$(pwd)` required

**Blockers:** None

**What was done (continued):**
- P5-3: SARIF 2.1.0 export — `GET /agent-scans/{scan_id}/sarif` ✅
- P5-4: PDF improvements — exec summary, SRS per finding, attack chains section, fpdf2 multi_cell cursor fix ✅
- P5-5: Jira + Slack integrations ✅
  - `backend/api/v1/integrations.py` — `POST /{scan_id}/integrations/slack` + `POST /{scan_id}/integrations/jira`
  - `core/config.py` — 5 new integration settings fields
  - Wired into `main.py`

**Phase 5 — COMPLETE ✅**

**Next session should (resume here):**
- Phase 6: Advanced Modules (Cloud/K8s scanning)
- OR: Frontend Cytoscape.js chain graph visualization (deferred from P5-1)
- Ask CTO which to prioritize

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
