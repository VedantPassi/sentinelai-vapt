# SentinelAI — Project Memory

> Master context file. Update after every phase. CTO (Claude) reads this at start of every conversation to get full context without re-explaining anything.

---

## Project Identity

**Name:** SentinelAI  
**Type:** AI-native Vulnerability Assessment & Penetration Testing platform  
**GitHub:** https://github.com/VedantPassi/sentinelai-vapt  
**Working Dir:** `/Users/vedantpassi/Desktop/Projects/AI VAPT`  
**Owner:** Vedant Passi (CTO/PM) — passivedant018@gmail.com  

---

## Roles

| Role | Who |
|------|-----|
| CTO / PM / Approver | Vedant (human) |
| CTO Advisor / Auditor | Claude (this chat) |
| Senior Developer | Claude CLI (separate session) |

**Workflow:** CLI proposes commands → Vedant pastes here → Claude (CTO) approves or flags → Vedant runs in CLI.

---

## Reference Sources

| Source | What it gives us |
|--------|-----------------|
| Shannon (KeygraphHQ/shannon) | Multi-agent pipeline architecture, Docker isolation, Claude integration |
| AI-VAPT (vikramrajkumarmajji/AI-VAPT) | Tool integration map (Nmap, Shodan, Metasploit, Amass) |
| `~/Downloads/vapt-platform-blueprint_1.html` | Full SentinelAI platform spec — canonical source of truth |

---

## Tech Stack (locked)

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| AI / Agents | LangGraph + Anthropic Claude API (`claude-sonnet-4-6` default, `claude-opus-4-8` for reasoning) |
| Frontend | Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS v4, Cytoscape.js |
| Primary DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Queue | Apache Kafka + Celery |
| Graph DB | Neo4j — Phase 6+ only |
| Vector DB | Weaviate — Phase 6+ only |
| Containers | Docker + docker-compose (dev) → EKS (Phase 6+) |
| DAST | OWASP ZAP, Nuclei |
| SAST | Semgrep |
| Network | Nmap |
| Secrets | Gitleaks, TruffleHog |
| Testing | pytest (backend), Vitest (frontend) |

---

## Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| AI provider | Claude (Anthropic) primary | Shannon reference uses Claude; best reasoning for security tasks |
| MVP scope | Web + API + Network | Phase 0–5; Cloud/K8s in Phase 6 |
| Build model | Solo (Vedant + Claude CLI) | Vedant = CTO/PM, CLI = senior dev |
| Backend language | Python (FastAPI) | Best AI/ML ecosystem, blueprint spec |
| Frontend | Next.js 15 App Router | Blueprint spec; shadcn/ui for components |
| Package manager | pip + venv (backend), npm (frontend) | uv not available on machine |
| Tailwind version | v4 | Installed by shadcn init — newer than spec'd v3, compatible |

---

## Phase Status

| Phase | Name | Status | Report |
|-------|------|--------|--------|
| 0 | Project Scaffold | ✅ Complete | `IMP info/reports/phase-0-audit.md` |
| 1 | Core Platform Foundation | 🔵 In Progress — DB models done, migration pending | — |
| 2 | Scanning Engine Core | ⬜ Not Started | — |
| 3 | AI Agent Framework | ⬜ Not Started | — |
| 4 | Validation & Risk Scoring | ⬜ Not Started | — |
| 5 | Reporting & Integrations | ⬜ Not Started | — |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started | — |
| 7 | Enterprise Features | ⬜ Not Started | — |

---

## Phase 0 — What Was Built

- Full folder structure (28 dirs) per spec
- FastAPI backend: `main.py`, `core/config.py`, `api/v1/health.py` — `/health` returns 200
- Next.js 15 frontend + shadcn/ui v4.11.0 (Tailwind v4, New York style)
- `infra/docker/docker-compose.yml` — postgres:16 + redis:7 with healthchecks
- `Dockerfile.backend` + `Dockerfile.frontend`
- `.env.example` with all env keys
- `.gitignore` (Python + Node + secrets)
- `docs/architecture.md` — full ASCII system diagram
- `docs/adr/ADR-001-tech-stack.md`
- `tests/targets/README.md` — DVWA + Juice Shop instructions
- Pushed to GitHub: https://github.com/VedantPassi/sentinelai-vapt

## Phase 0 — Known Tech Debt

1. `Dockerfile.backend` uses `pip install -e .` (editable) — switch to non-editable for Phase 6 prod
2. Kafka not in docker-compose yet — add in Phase 2
3. `frontend/.git` (nested repo) — removed before first commit ✅

---

## Phase 1 — In Progress

**Goal:** Working auth, multi-tenant data model, target management.

**Plan (CLI execution order):**
1. Alembic init + SQLAlchemy models (organizations, users, targets, scan_jobs, findings)
2. DB migration (alembic revision --autogenerate + upgrade head)
3. Auth endpoints (POST /auth/register, POST /auth/login — JWT HS256)
4. JWT middleware + get_current_user dependency
5. Targets CRUD (org_id row-level filtering)
6. Domain verification endpoint (DNS TXT record method)
7. pytest — auth + target CRUD tests
8. Frontend — login, register, dashboard shell, target list + add form
9. PHASES.md + session.md update
10. Phase audit → `IMP info/reports/phase-1-audit.md`

**Status:** 🔵 In Progress — DB models written, Alembic initialized, migration autogenerate next.

**Completed so far:**
- All backend deps installed (including pydantic[email], dnspython, greenlet)
- `pyproject.toml` build backend fixed
- Alembic initialized + `alembic/env.py` (async) written by CTO
- `models/base.py` + `models/models.py` (5 tables) written by CTO
- Migration autogenerated + `alembic upgrade head` — 5 tables in postgres ✅
- postgres password set to `sentineldev`, `.env` DATABASE_URL updated
- `core/db.py` — async engine + session
- `core/security.py` — bcrypt + JWT
- `core/deps.py` — get_current_user dependency
- `api/v1/auth.py` — register + login (CTO wrote)
- `api/v1/targets.py` — full CRUD + DNS verify (CTO wrote)
- auth router wired into main.py ✅
- targets router wiring pending (next session task 1)

**Remaining Phase 1 tasks:**
1. Wire targets router into main.py + install dnspython
2. Live test (uvicorn + curl register/login/targets)
3. pytest tests (auth + targets CRUD)
4. Frontend (login, register, dashboard, target list)
5. Commit all + phase-1-audit.md

**Known issue:** CLI's Write tool corrupts files >50 lines (line-wrap truncation). CTO writes all long Python files directly. CLI must run `python3 -c "import ast; ast.parse(open('f').read())"` after every file write.

---

## Environment Notes

- **Machine:** macOS (Darwin 25.5.0), Apple Silicon (aarch64)
- **Python:** 3.14 (detected from `.pyc` filenames — newer than spec's 3.12, compatible)
- **Node:** 20+
- **Docker Desktop:** Installed, running, Compose v5
- **postgres + redis:** Running via docker-compose on ports 5432 / 6379
- **.env:** Must be created from `.env.example` and filled before Phase 1 migrations

---

## IMP info Folder Index

| File | Purpose |
|------|---------|
| `memory.md` | This file — master project memory |
| `instructions.md` | Full CTO phase-by-phase instructions for CLI |
| `reports/phase-0-audit.md` | Phase 0 CTO audit |
| `reports/phase-0-summary.md` | Phase 0 full file verification |
| `resources/reference-links.md` | All tool docs, repo links, API references |

---

## How to Resume Any Conversation

Paste this to Claude (CTO chat):
> "Read IMP info/memory.md in the SentinelAI project. Continue from where we left off."

Paste this to CLI (developer session):
> "Read session.md and IMP info/instructions.md Phase N section. Begin Phase N. Ask permission before every command."
