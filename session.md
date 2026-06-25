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
5. At phase completion, generate `phase-reports/phase-N-report.md`
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
| 1 | Core Platform Foundation | ⬜ Not Started |
| 2 | Scanning Engine Core | ⬜ Not Started |
| 3 | AI Agent Framework | ⬜ Not Started |
| 4 | Validation & Risk Scoring | ⬜ Not Started |
| 5 | Reporting & Integrations | ⬜ Not Started |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started |
| 7 | Enterprise Features | ⬜ Not Started |

**Current Phase: 1**

---

## Phase 0 — Project Scaffold (Tasks)

> Goal: Create the entire folder structure, base configs, Docker dev stack, and all scaffolding so Phase 1 can start building immediately.

### Tasks
- [ ] Create full folder structure per spec below
- [ ] Initialize Python backend with `pyproject.toml` (uv or pip), FastAPI skeleton, health check endpoint
- [ ] Initialize Next.js 15 frontend with TypeScript, Tailwind, shadcn/ui
- [ ] Create `docker-compose.yml` with: postgres, redis, (kafka optional for phase 0)
- [ ] Create `.env.example` with all required env var keys (no values)
- [ ] Create `PHASES.md` task board
- [ ] Create `docs/architecture.md` with high-level system design
- [ ] Create `docs/adr/` folder for Architecture Decision Records
- [ ] Write `ADR-001-tech-stack.md` documenting stack decisions and rationale
- [ ] Verify: `docker-compose up` brings postgres + redis healthy
- [ ] Verify: backend `uvicorn` starts, `/health` returns 200
- [ ] Verify: frontend `npm run dev` starts without errors
- [ ] Generate `phase-reports/phase-0-report.md`

### Folder Structure to Create
```
AI VAPT/
├── session.md                    ← this file
├── PHASES.md                     ← phase task board
├── .env.example                  ← env var template
├── .gitignore
├── docs/
│   ├── architecture.md
│   └── adr/
│       └── ADR-001-tech-stack.md
├── backend/
│   ├── pyproject.toml
│   ├── README.md
│   ├── main.py                   ← FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── agents/
│   │   └── __init__.py
│   ├── scanners/
│   │   └── __init__.py
│   ├── scoring/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   └── core/
│       ├── __init__.py
│       └── config.py
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   └── ui/
│   └── lib/
│       └── utils.ts
├── workers/
│   └── __init__.py
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.backend
│   │   └── Dockerfile.frontend
│   ├── terraform/
│   │   └── .gitkeep
│   └── k8s/
│       └── .gitkeep
├── tools/
│   ├── nuclei-templates/
│   │   └── .gitkeep
│   ├── semgrep-rules/
│   │   └── .gitkeep
│   └── zap-config/
│       └── .gitkeep
├── tests/
│   ├── unit/
│   │   └── .gitkeep
│   ├── integration/
│   │   └── .gitkeep
│   └── targets/
│       └── README.md             ← instructions to spin up DVWA/Juice Shop
└── phase-reports/
    └── .gitkeep
```

---

## Coding Standards

- **No unnecessary comments.** Self-documenting names only.
- **No features beyond current phase scope.**
- **Every API endpoint:** Pydantic input validation, typed responses.
- **Security:** No hardcoded secrets. All config via `.env`. No raw SQL string concat.
- **No backwards-compat shims.** Delete dead code.
- **Error handling:** Only at system boundaries (HTTP, subprocess, external API calls).

---

## Reference Materials

- Blueprint: `~/Downloads/vapt-platform-blueprint_1.html` — full platform spec
- Shannon (agent architecture reference): https://github.com/KeygraphHQ/shannon
- AI-VAPT (tool integration reference): https://github.com/vikramrajkumarmajji/AI-VAPT

---

## Current Session Log

**Session #:** 1  
**Date:** 2026-06-24  
**Phase:** 0  
**What was done:**
- Created full folder structure per spec
- Backend: FastAPI skeleton, `/api/v1/health` endpoint, Pydantic settings, `pyproject.toml`
- Frontend: Next.js 15 (create-next-app@16.2.9) + TypeScript + Tailwind v4 + shadcn/ui v4.11.0
- docker-compose.yml (postgres:16 + redis:7) + Dockerfiles
- `.env.example`, `.gitignore`, `docs/architecture.md`, `ADR-001-tech-stack.md`
- Verified: backend `/health` → 200 ✅, frontend dev server → 200 ✅
- Generated `phase-reports/phase-0-report.md`

**Decisions made:**
- Docker compose verification deferred — `compose` plugin not installed on this machine

**Blockers:** None

**Next session should:** Start Phase 1 — PostgreSQL schema (users, orgs, targets, scan_jobs, findings) + Alembic migrations. Containers are already running.

---

## End of Session Template

> Replace "Current Session Log" section with:

```
**Session #:** N  
**Date:** YYYY-MM-DD  
**Phase:** X  
**What was done:** [bullet list]  
**Decisions made:** [any deviations or choices]  
**Blockers:** [anything blocking]  
**Next session should:** [first task to pick up]
```
