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
| 3 | AI Agent Framework | ✅ Complete |
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

**Session #:** 5–6
**Date:** 2026-06-28 to 2026-06-30
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
- Live e2e test: POST /agent-scans → Celery → LangGraph → Nmap → 4 findings stored ✅
- Two full audit rounds run — all findings fixed ✅:
  - `await db.delete()` → `db.delete()` (sync call)
  - dnspython + fpdf2 added to pyproject.toml
  - ScanJob.created_at added + Alembic migration applied
  - CORS hardcoded origins → settings.cors_origins
  - agent_scans.py created_at fallback uses model fields (no datetime.now())
  - reports.py bytes(pdf.output()) → pdf.output()
  - scans.py run_scan moved to top-level import
  - deps.py uuid.UUID parse guarded with try/except → 401
  - auth.py password minimum length (8 chars) enforced
  - zap_scanner.py /tmp/zap hardcoded path → uuid-based per-scan dir

**Decisions made:**
- WebSocket progress: DB polling — Redis stream Phase 5
- Tenant isolation: Target join pattern (no org_id on ScanJob)
- claude-opus-4-8 for planner, claude-sonnet-4-6 for enrichment
- WS endpoint no auth — Phase 5 fix
- ANTHROPIC_API_KEY empty → graceful skip, scanners still run

**Blockers:**
- ANTHROPIC_API_KEY not in .env — Claude enrichment skips (non-blocking)

**Next session should:**
1. Start Phase 4 — Validation & Risk Scoring
2. Add ANTHROPIC_API_KEY to .env before Phase 4 agent work
3. Phase 4 tasks: SRS scoring formula, Validation Agent (PoC confirmation), false-positive classifier

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
