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

**Session #:** 8
**Date:** 2026-07-01
**Phase:** 5 — Reporting & Integrations

**What was done:**
- Fixed WS PENDING bug: `db.expire_all()` in WS polling loop (`api/v1/agent_scans.py`) — stale SQLAlchemy session cache was root cause ✅
- Frontend polling fallback added (`pollUntilDone`) as secondary safety net ✅
- E2e verified: scan completes, UI auto-updates to COMPLETED, findings + badges render ✅
- Phase 5 P5-1 (chain_agent) started:
  - `backend/agents/state.py` — `ChainStep`, `AttackChain` dataclasses + `attack_chains` in `AgentState`
  - `backend/agents/chain_agent.py` — LLM chain discovery, top-20 confirmed findings, 1–5 chains output
  - `backend/agents/runtime.py` — `chain` node wired: validator → chain → END
  - `backend/models/models.py` — `AttackChain` DB model + ScanJob back-ref
  - Alembic migration `cd775e0f3651` — `attack_chains` table live ✅

**Decisions made:**
- Chain agent: reasoning tier LLM, cap 20 findings, 1–5 chains max
- Tenant isolation: ScanJob join (no org_id on attack_chains) — consistent with Finding pattern
- No Cytoscape.js frontend yet — API first, graph after e2e verified

**Blockers:** None

**Next session should (resume here):**
1. CLI proposes `agent_worker.py` diff — write AttackChain rows to DB post-chain node
2. CLI proposes `GET /agent-scans/{scan_id}/chains` endpoint diff — CTO approves + wires
3. E2e test: launch scan, verify chains in DB + API
4. Cytoscape.js frontend chain graph
5. Then P5-2 (Redis streams WS), P5-3 (SARIF), P5-4 (PDF), P5-5 (Jira/Slack)

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
