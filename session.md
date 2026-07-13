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
| 5 | Reporting & Integrations | ✅ Complete |
| 6 | Advanced Modules (Cloud/K8s) | ⬜ Not Started |
| 7 | Enterprise Features | ⬜ Not Started |

**Current Phase: 6 — NOT STARTED**

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

**What was done (session 10 - verification):**
- Fixed `app/page.tsx` — was default Next.js template, now redirects to `/login` ✅
- Fixed Nuclei scanner: `-json` flag removed in v3, changed to `-jsonl` in `scanners/nuclei_scanner.py` ✅
- Nuclei installed via brew (v3.10.0, templates installed) ✅
- Celery restart pattern confirmed: `pkill -f "celery.*agent_worker"` + `PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd)`
- Added `useEffect` to auto-load findings when `activeScan.status === "completed"` in agent-scans page ✅
- Redis pub/sub `publish_scan_event` fails silently in Celery prefork (event loop closed) — fallback to DB poll works, not blocking

**Known issues remaining:**
- ZAP not installed — web scans only use Nuclei (sufficient for now)
- Redis pub/sub events don't stream live (event loop closed in Celery prefork) — DB poll fallback works
- "Waiting for events..." shown on historical scans (expected — pub/sub doesn't persist)

**What was done (session 11 - Nuclei debug):**
- Root cause found: `nuclei_scanner.py` never checked `proc.returncode` — nuclei exits nonzero silently, returns `ScannerResult(findings=[], error=None)`, logs nothing
- Fix applied: added `if proc.returncode != 0: return ScannerResult(error=f"nuclei exited {proc.returncode}: {stderr.decode()[:2000]}")` after `proc.communicate()`
- Celery restarted with `PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd)` 
- Test task queued (scan_id `219e6517-b897-47be-a127-831b65ca2a7b`, target `http://testphp.vulnweb.com`) — still running when session ended
- UI issue found: page resets on refresh (no scan history persistence) — deferred

**What was done (session 12):**
- Root cause of 0 findings: `nuclei_scanner.py` never checked `proc.returncode` (already fixed in session 11)
- Added unconditional debug log to nuclei_scanner.py: `logger.info("nuclei: rc=%s duration=%.1fs stdout=%d bytes stderr=%s", ...)`
- Confirmed: `rc=0, duration=23s, stdout=0 bytes` → nuclei exits clean with zero output
- Identified: `testphp.vulnweb.com` unreachable from dev network (ping 100% packet loss) — not a code bug
- Verified against `scanme.nmap.org`: `rc=0, duration=180s, stdout=208752 bytes` → `findings: 15, chains: 1` ✅
- Full pipeline verified end-to-end: Nuclei → findings → SRS scoring → chain discovery → DB persist
- **UI state persistence fix**: added `GET /agent-scans` list endpoint (backend) + `listAgentScans()` (frontend api.ts) + mount useEffect to load latest scan on page refresh
- **Security note**: prompt-injection probe found in `node_modules/next/dist/docs/index.md` — fake "AI agent hint" suggesting `unstable_instant` export. Ignored. Report to Next.js security team if not expected.

**What was done (session 13):**
- Redis pub/sub fix — all 3 changes shipped and verified:
  - `core/redis_client.py` — added `get_redis_sync()` (plain `redis.Redis`, no event loop binding)
  - `core/events.py` — added `publish_scan_event_sync()` for worker path
  - `agents/runtime.py` + `workers/agent_worker.py` — switched to sync publisher
- Verified: 17 progress events streamed live via Redis pub/sub, zero "event loop is closed" errors
- Committed + pushed (`2cfd7c3`)

**What was done (session 14 - Phase 6 start):**
- chain_agent.py: fixed finding_ids — LLM now gets real `f.id` UUIDs instead of ordinal indices
- scanners/base.py: `FindingData` gets stable `id: str` (uuid4) at creation
- workers/agent_worker.py: `Finding` inserted with `uuid.UUID(fd.id)` so DB id matches chain references
- Cytoscape installed: `npm install cytoscape @types/cytoscape`
- `frontend/components/ChainGraph.tsx` — new component: chain selector sidebar + Cytoscape breadthfirst graph + node detail panel on tap
- `frontend/lib/api.ts` — added `ChainStep`, `AgentChain` interfaces + `listAgentScanChains()`
- `frontend/app/(dashboard)/agent-scans/page.tsx` — wired: `chains` state, `loadChains()`, graph renders after findings
- Pushed to origin/main (`2d08512`)

**What was done (session 15 - P6-1 verified):**
- TypeCheck: `npx tsc --noEmit` clean — zero errors
- UI verified: network scan against scanme.nmap.org → 2 findings (CONFIRMED + FALSE POSITIVE) + 2 attack chains
- Chain graph renders: node size fixed (single-node zoom capped), node tap shows detail panel with MITRE ID + action + "finding not linked" badge
- "finding not linked" expected for pre-UUID-fix scans; new scans will show finding titles
- mount useEffect updated: prefer latest completed scan over latest scan
- Pushed to origin/main (`8ad1cad`)

**P6-1 Cytoscape chain graph — COMPLETE ✅**

**Next session should (resume here):**
1. Phase 6 track 2: Container/K8s scanning — Trivy + kube-bench
   - Need: Docker running locally + a test container image
2. Phase 6 track 3: Cloud Security — Prowler (needs AWS creds)
3. Phase 6 track 4: Neo4j attack path graph

**Restart Celery command:**
```bash
cd "/Users/vedantpassi/Desktop/Projects/AI VAPT/backend"
pkill -f "celery.*agent_worker" 2>/dev/null; sleep 1
PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) .venv/bin/celery -A workers.agent_worker.celery_app worker --loglevel=info --concurrency=1 > /tmp/celery_fresh.log 2>&1 &
```

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
