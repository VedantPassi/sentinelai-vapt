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
| bcrypt | Direct `bcrypt` calls (no passlib) | passlib incompatible with bcrypt 5.x (`__about__` removed) |
| Auth HTTP status | 401 for missing/invalid token | RFC 7235 correct; HTTPBearer returns 401 not 403 |
| Test DB | Real dev postgres (no mocks) | Project rule — mocks masked prod migration failures before |

---

## Phase Status

| Phase | Name | Status | Report |
|-------|------|--------|--------|
| 0 | Project Scaffold | ✅ Complete | `IMP info/reports/phase-0-audit.md` |
| 1 | Core Platform Foundation | ✅ Complete | `IMP info/reports/phase-1-audit.md` |
| 2 | Scanning Engine Core | ✅ Complete | `IMP info/reports/phase-2-audit.md` |
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

**Completed:**
- All backend deps installed (fastapi, sqlalchemy, alembic, asyncpg, jose, bcrypt, celery, anthropic, pytest, ruff, mypy, pydantic[email], dnspython, greenlet, httpx, anyio, pytest-anyio)
- `pyproject.toml` build backend fixed + pytest config (`asyncio_mode = "auto"`)
- Alembic initialized + `alembic/env.py` (async) — migration `254ed6990d72` — 5 tables in postgres ✅
- `models/base.py` + `models/models.py` — Organization, User, Target, ScanJob, Finding
- `core/db.py` — async SQLAlchemy engine + session
- `core/security.py` — direct bcrypt (no passlib), JWT create/decode
- `core/deps.py` — `get_current_user` FastAPI dependency
- `api/v1/auth.py` — POST /auth/register + POST /auth/login (live tested ✅)
- `api/v1/targets.py` — full CRUD + DNS TXT domain verification (live tested ✅)
- `main.py` — all 3 routers wired (health, auth, targets)
- `tests/unit/test_auth.py` + `tests/unit/test_targets.py` — **12/12 passing** ✅
- `tests/unit/conftest.py` — `unique_email()` + `dispose_engine` autouse fixture
- Commits pushed: `fca74fa`, latest test commit on `main`

**Phase 1 is COMPLETE.** All tasks done, pushed to main, audit report generated.

## Phase 2 — In Progress

**Completed so far:**
- Kafka + Zookeeper added to `infra/docker/docker-compose.yml`
- Deps installed: `celery[redis]`, `fpdf2`, `httpx`
- All 6 scanner wrappers written + syntax verified:
  - `backend/scanners/base.py` — ScannerResult + FindingData dataclasses
  - `backend/scanners/nmap_scanner.py`
  - `backend/scanners/nuclei_scanner.py`
  - `backend/scanners/zap_scanner.py` (Docker subprocess)
  - `backend/scanners/semgrep_scanner.py`
  - `backend/scanners/gitleaks_scanner.py`
- `backend/workers/` package created

**Remaining:**
1. `backend/api/v1/scans.py` — POST /scans, GET /scans/{id}, GET /scans/{id}/findings
2. Wire scans router into `main.py`
3. `backend/workers/scan_worker.py` — Celery task
4. `backend/api/v1/reports.py` — PDF generation (fpdf2)
5. Test against DVWA
6. `IMP info/reports/phase-2-audit.md`

**Known issues:**
- CLI Write tool corrupts files >50 lines — CTO writes all long Python/TSX files directly
- `config.py` uses `env_file="../.env"` — tech debt (Phase 2 fix)
- postgres dev password: `sentineldev`

---

## Environment Notes

- **Machine:** macOS (Darwin 25.5.0), Apple Silicon (aarch64)
- **Python:** 3.14 (detected from `.pyc` filenames — newer than spec's 3.12, compatible)
- **Node:** 20+
- **Docker Desktop:** Installed, running, Compose v5
- **postgres + redis:** Running via docker-compose on ports 5432 / 6379
- **.env:** Present at project root with DATABASE_URL + JWT_SECRET_KEY

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
