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

**Session #:** 7
**Date:** 2026-06-30
**Phase:** 4 — Validation & Risk Scoring

**What was done:**
- Phase 4 COMPLETE ✅ — all features built, tested e2e
- `backend/core/llm.py` — `llm_complete()`, Ollama + Anthropic, 1 retry, `LLMError`
- All 3 Phase 3 agents migrated to `llm_complete()` (no inline Anthropic calls)
- `backend/agents/validation_agent.py` — batched LLM validation, rules pre-filter, status/risk_score/reasoning set
- `backend/agents/runtime.py` — `validator` node wired: webapp|network → validator → END
- `backend/scoring/srs.py` — SRS formula (severity 40% + exploitability 30% + asset 20% + confidence 10%)
- `backend/scoring/classifier.py` — 6 deterministic FP rules (info severity, missing-header on non-web, noise titles, Nuclei tech-detect, zero risk + low, short description)
- `backend/workers/agent_worker.py` — reads fd.status/risk_score, computes SRS, writes to DB; fixed asyncio.run() → new_event_loop(); fixed asset_criticality float mapping
- `backend/api/v1/findings.py` — GET/PATCH/POST validate endpoints; tenant isolation via Finding→ScanJob→Target join
- `backend/models/models.py` — `validation_reasoning` column added to Finding
- Alembic migration `3155935e555c` — two-step NOT NULL migration
- `frontend/lib/api.ts` — `getFinding`, `patchFinding`, `revalidateFinding` + extended `AgentFinding` type
- `frontend/app/(dashboard)/agent-scans/page.tsx` — `FindingCard` with SRS badge, status badge, reasoning, Confirm/FP/Re-validate buttons
- Phase 4 audit report + phase report generated ✅
- 3 bugs fixed: asyncio.run() in Celery, asset_criticality float mapping, migration NOT NULL

**Decisions made:**
- Ollama `qwen2.5:7b` for dev; switch to Anthropic via `LLM_PROVIDER=anthropic` for prod
- Validation: rules-first (classifier), then LLM batch (≤10/call)
- `POST /validate` runs LLM sync in request (~2s on Ollama) — no Celery for single finding
- FP `srs_score` always 0 regardless of severity

**Blockers:** None

**Next session — Phase 5:**
- `backend/agents/chain_agent.py` — attack chain discovery (deferred from Phase 4)
- Real-time WebSocket streaming (Redis streams, not DB poll)
- WebSocket auth
- Reporting improvements (PDF + SARIF export)
- Integrations (Jira, Slack)

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
