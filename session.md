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
| 2 | Scanning Engine Core | ⬜ Not Started |
| 3 | AI Agent Framework | ⬜ Not Started |
| 4 | Validation & Risk Scoring | ⬜ Not Started |
| 5 | Reporting & Integrations | ⬜ Not Started |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started |
| 7 | Enterprise Features | ⬜ Not Started |

**Current Phase: 2**

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

**Session #:** 4  
**Date:** 2026-06-26  
**Phase:** 2 — Scanning Engine Core  
**What was done:**
- Phase 1 fully closed: frontend built + live tested, audit report generated, all pushed ✅
- Phase 2 started:
  - Added Kafka + Zookeeper to `infra/docker/docker-compose.yml` ✅
  - Installed `celery[redis]`, `fpdf2`, `httpx` into `.venv` ✅
  - CTO wrote all 6 scanner wrappers — syntax verified: ✅
    - `backend/scanners/base.py` — ScannerResult + FindingData dataclasses
    - `backend/scanners/nmap_scanner.py` — Nmap XML parser
    - `backend/scanners/nuclei_scanner.py` — Nuclei JSONL parser
    - `backend/scanners/zap_scanner.py` — ZAP Docker subprocess + JSON report parser
    - `backend/scanners/semgrep_scanner.py` — Semgrep JSON parser
    - `backend/scanners/gitleaks_scanner.py` — Gitleaks JSON parser
  - Created `backend/workers/` package ✅

**Decisions made:**
- ZAP runs via Docker subprocess (no local ZAP install required)
- Celery uses Redis as broker (same Redis instance, different DB index)
- Kafka ephemeral in dev (no volume) — stateless queue fine for Phase 2

**Blockers:** None

**Next session should:**
1. CTO reads `main.py` to confirm wiring pattern
2. CTO writes `backend/api/v1/scans.py` — POST /scans, GET /scans/{id}, GET /scans/{id}/findings
3. Wire scans router into `main.py`
4. CTO writes `backend/workers/scan_worker.py` — Celery task dispatching to correct scanner
5. CTO writes `backend/api/v1/reports.py` — GET /scans/{id}/report → PDF via fpdf2
6. Test against DVWA
7. Commit + push + `IMP info/reports/phase-2-audit.md`

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
