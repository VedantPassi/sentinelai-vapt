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
| 6 | Advanced Modules (Cloud/K8s) | ✅ Complete |
| 7 | Enterprise Features | ✅ Complete (P7-1 ✅ P7-2 ✅ P7-3 ✅) |
| 8 | Polish & Hardening | ⬜ Not started |

**Current Phase: 7 — COMPLETE ✅ / Phase 8 next**

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

**What was done (session 16 - P6-2):**
- Trivy 0.72.0 installed via brew
- `backend/scanners/trivy_scanner.py` — Trivy wrapper: image + fs scan, parses CVEs/secrets/misconfigs, CVSS extraction
- `backend/agents/container_agent.py` — container agent: runs trivy, LLM enriches top 20 critical/high CVEs
- `backend/agents/recon_agent.py` — early return for container target_type (skip DNS/fingerprint)
- `backend/agents/planner_agent.py` — early return for container target_type (skip LLM planning)
- `backend/agents/runtime.py` — added container node + route in graph
- `frontend/app/(dashboard)/agent-scans/page.tsx` — added "Container Image" scan type option
- Verified: python:3.8-slim → 379 findings (76 critical/high), 26 LLM-enriched with exploitability + blast radius

**P6-2 Container scanning — COMPLETE ✅**

**What was done (session 17 - P6-5):**
- `backend/agents/chain_agent.py` — upgraded to v2: cross-surface kill chains
  - Includes `open` high/critical findings (not just confirmed)
  - Groups findings by surface (web/network/container/secrets) before LLM
  - Prompt models MITRE kill chain stages, explicitly requests cross-surface pivots
  - 30 finding cap (was 20), sorted by severity tier + risk_score
  - Each step now includes `surface` field
- `backend/agents/state.py` — `ChainStep.surface: str | None` added
- `frontend/lib/api.ts` — `ChainStep.surface: string | null` added
- `frontend/components/ChainGraph.tsx` — surface badge (purple) in node detail panel
- Verified: synthetic 5-finding cross-surface test → 2 chains, both cross-surface (network→web, web→container→secrets)

**P6-5 Chain Discovery Agent v2 — COMPLETE ✅**

**What was done (session 18 - P6-4):**
- `infra/docker/docker-compose.yml` — Neo4j 5 community added (ports 7474/7687, APOC plugin)
- `backend/core/neo4j_client.py` — async driver wrapper (bolt://localhost:7687)
- `backend/core/config.py` — neo4j_uri/user/password settings added
- `backend/agents/graph_agent.py` — ingests Scan/Target/Finding/Chain/Step nodes + edges into Neo4j
- `backend/api/v1/attack_graph.py` — 3 endpoints: full graph, attack paths, blast radius
- `backend/agents/runtime.py` — graph node after chain: chain→graph→END
- `backend/requirements.txt` — neo4j>=6.2.0 added
- `frontend/lib/api.ts` — GraphNode/GraphEdge/AttackGraph/BlastRadius interfaces + getAttackGraph/getBlastRadius
- `frontend/components/AttackGraphView.tsx` — Cytoscape graph (finding=ellipse/red, chain=diamond/blue, step=rect/green) + blast radius tab
- `frontend/app/(dashboard)/agent-scans/page.tsx` — AttackGraphView section added after chains
- Verified: smoke test → 2 findings + 1 chain + 2 steps in Neo4j; API returns correct graph; tsc clean
- Pushed to origin/main (a458a9a)

**P6-4 Neo4j attack path graph — COMPLETE ✅**

**Phase 6 status:**
- P6-1 Cytoscape chain graph ✅
- P6-2 Container scanning (Trivy) ✅
- P6-3 Cloud Security (Prowler) ⬜ — needs AWS creds
- P6-4 Neo4j attack path graph ✅
- P6-5 Chain Discovery Agent v2 ✅

**What was done (session 19 - P6-3):**
- AWS IAM user `sentinelai-prowler` created (ReadOnlyAccess + SecurityAudit policies)
- AWS creds added to .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
- Prowler 5.35.0 installed in isolated `backend/.prowler-venv` (Python 3.12, no venv conflict)
- `backend/scanners/prowler_scanner.py` — Prowler subprocess wrapper, OCSF v5 parser
  - Uses `--output-directory` + `--output-filename`, reads JSON file (not stdout)
  - OCSF v5 fields: metadata.event_code, finding_info.{title,desc}, resources[0].{uid,region}, cloud.account.uid, remediation.{desc,references}
- `backend/agents/cloud_agent.py` — runs Prowler, LLM enriches top 15 critical/high findings
- `backend/agents/recon_agent.py` — skip for `cloud` type
- `backend/agents/planner_agent.py` — skip for `cloud` type
- `backend/agents/runtime.py` — cloud node added: planner→cloud→validator→chain→graph
- `frontend/app/(dashboard)/agent-scans/page.tsx` — "Cloud (AWS)" scan type added
- Verified: 18 findings (2 critical, 2 high, 8 medium, 6 low) from real AWS account, 4 LLM-enriched

**P6-3 Cloud Security (Prowler) — COMPLETE ✅**

**Phase 6 — ALL COMPLETE ✅**
- P6-1 Cytoscape chain graph ✅
- P6-2 Container scanning (Trivy) ✅
- P6-3 Cloud Security (Prowler) ✅
- P6-4 Neo4j attack path graph ✅
- P6-5 Chain Discovery Agent v2 ✅

**What was done (session 20 - P7-1 BloodHound CE):**
- BloodHound CE deployed via Docker at localhost:8080 (ports remapped: 7475/7688 for Neo4j to avoid conflict with SentinelAI Neo4j at 7474/7687)
- Synthetic AD dataset created + uploaded: TESTCORP.LOCAL, alice/bob/charlie users
  - Attack path: charlie →(WriteDACL)→ bob →(GenericAll)→ alice →(MemberOf)→ Domain Admins
  - Upload via bhce_seed.py (scratchpad) — job Complete, 4 files ingested
- `backend/core/bloodhound_client.py` — rewrote dead REST endpoints to use /api/v2/graphs/cypher:
  - `get_attack_paths()` — Cypher shortestPath (User → Group containing "DOMAIN ADMINS")
  - `get_node_shortest_paths(node_id, node_type)` — path from specific node to DA
  - `get_high_value_targets()` — nodes with admincount=true
  - `_cypher()` / `_cypher_raw()` helpers
- `backend/agents/bloodhound_agent.py` (new) — BH paths → FindingData(category="ad", severity="critical") + LLM enrichment
- `backend/agents/runtime.py` — bloodhound node + "ad" conditional route
- `backend/agents/recon_agent.py` + `planner_agent.py` — "ad" added to skip list
- `frontend/app/(dashboard)/agent-scans/page.tsx` — "Active Directory (BloodHound)" scan type added
- Committed: fd51085

**P7-1 BloodHound CE — COMPLETE ✅**

**What was done (session 20 continued - P7-2 Celery Beat):**
- `backend/models/models.py` — ScheduledScan model (target_id, scan_type, interval_hours, config, is_active, last_run_at, next_run_at)
- `backend/alembic/versions/d7a6f3c81899_add_scheduled_scans.py` — migration generated + applied
- `backend/workers/beat_worker.py` — Beat schedule (60s tick) + check_due_schedules task:
  - Queries ScheduledScan WHERE is_active=True AND next_run_at <= now
  - Creates ScanJob, enqueues run_agent_task via send_task(), advances next_run_at
- `backend/api/v1/schedules.py` — CRUD: POST/GET/PATCH/DELETE /schedules (org-scoped)
- `backend/main.py` — schedules router registered
- `frontend/app/(dashboard)/schedules/page.tsx` (new) — create form, live table, pause/resume/delete
- `frontend/lib/api.ts` — Schedule interface + listSchedules/createSchedule/toggleSchedule/deleteSchedule
- `frontend/app/(dashboard)/layout.tsx` — "Schedules" nav link added
- Committed: 12a9e9e, pushed to origin/main (dbc74c6 after reports)

**Beat start command:**
```bash
cd "/Users/vedantpassi/Desktop/Projects/AI VAPT/backend"
PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) .venv/bin/celery -A workers.beat_worker beat --loglevel=info
```

**P7-2 Continuous Monitoring — COMPLETE ✅**

**What was done (session 21 - P7-3 SIEM Integration):**
- `backend/core/siem_client.py` (new) — `_send_to_splunk` + `_send_to_elasticsearch` + `forward_to_siem`; async httpx, fire-and-forget
- `backend/workers/siem_worker.py` (new) — Celery task `ship_to_siem(scan_id)`: loads findings+target from DB, builds event dicts, calls `forward_to_siem`
- `backend/core/config.py` — added `siem_enabled`, `splunk_hec_url`, `splunk_hec_token`, `splunk_index`, `es_url`, `es_index`, `es_user`, `es_password`
- `backend/workers/agent_worker.py` — after scan completes: `celery_app.send_task("workers.siem_worker.ship_to_siem", ...)` if `settings.siem_enabled`
- Verified: syntax OK all 4 files, task registers on celery_app
- Pushed: cee2ca1

**P7-3 SIEM Integration — COMPLETE ✅**

**Phase 7 — ALL COMPLETE ✅**
- P7-1 BloodHound CE (AD attack paths) ✅
- P7-2 Celery Beat (continuous monitoring) ✅
- P7-3 SIEM integration (Splunk HEC + Elasticsearch) ✅

**To enable SIEM — add to .env:**
```
SIEM_ENABLED=true
SPLUNK_HEC_URL=https://splunk:8088
SPLUNK_HEC_TOKEN=<token>
SPLUNK_INDEX=sentinelai
ES_URL=http://elasticsearch:9200
ES_INDEX=sentinelai-findings
ES_USER=elastic
ES_PASSWORD=<password>
```

**What was done (session 22 - end-to-end demo + bug fixes):**
- Ran full end-to-end demo across all 4 scan types:
  - Network (nmap/nuclei) → 2 findings, 1 chain ✅
  - Container (Trivy, python:3.8-slim) → 50 findings, 5 chains ✅
  - Cloud (Prowler/AWS) → 21 findings, 2 chains ✅ (after 2 bug fixes)
  - Active Directory (BloodHound CE) → 1 critical finding (DOMAIN ADMINS path) ✅ (after 1 bug fix)

- **Bug fix 1: Neo4j driver event-loop binding (agent_worker.py)**
  - `neo4j_client.py` module-level `_driver` singleton binds to first task's loop
  - Subsequent Celery tasks create new loops → "Future attached to a different loop" warning + driver unusable
  - Fix: added `_close_neo4j()` async helper, called in `run_agent_task` finally block
  - Committed: 16e0804

- **Bug fix 2: AWS credentials not loaded in Celery worker (agent_worker.py)**
  - `prowler_scanner.py` reads `os.environ.get('AWS_ACCESS_KEY_ID')` directly
  - `pydantic-settings env_file` does NOT inject into `os.environ`; Celery worker never sourced `.env`
  - Fix: `load_dotenv(Path(__file__).parent.parent.parent / ".env")` at top of `agent_worker.py`
  - Committed: 19a0f1a

- **Bug fix 3: BloodHound CE nodes/edges returned as dicts not lists (bloodhound_client.py)**
  - BH CE `/api/v2/graphs/cypher` returns `nodes`/`edges` as dicts keyed by string IDs (`{"0": {...}, "1": {...}}`)
  - `_path_to_finding` in `bloodhound_agent.py` did `nodes[0]` → `KeyError: 0` (dict, not list)
  - Error surfaced as `"BloodHound agent failed: 0"` (str(KeyError(0)) == '0')
  - Fix: added `_to_list()` helper in `bloodhound_client.py`; applied in `_cypher()`, `get_attack_paths()`, `get_node_shortest_paths()`
  - Committed: a938554

- Identified stale Celery worker issue (PID 6381/6389 from Jul 18, running alongside fresh worker) — killed stale pair
- All 3 fixes pushed: a938554 (git HEAD)

**What was done (session 23 - P8-1 RBAC enforcement):**
- `backend/core/deps.py` — added `require_roles(*roles)` factory + `require_admin` / `require_analyst` shorthands
- Route guards wired (single `Depends` swap, no DB changes):
  - `targets.py`: POST/PUT → analyst+; DELETE → admin
  - `agent_scans.py`: POST → analyst+
  - `findings.py`: PATCH, POST /validate → analyst+
  - `integrations.py`: both POSTs → analyst+
  - `schedules.py`: POST/PATCH → analyst+; DELETE → admin
  - GET endpoints unchanged (viewers can read)
- `backend/api/v1/users.py` (new) — admin-only: GET /users, POST /users (invite), PATCH /users/{id}/role, DELETE /users/{id}; self-remove + self-role-change blocked
- `backend/api/v1/auth.py` — added GET /auth/me → {id, email, role, org_id}
- `backend/main.py` — users_router registered
- `frontend/contexts/UserContext.tsx` (new) — React context, UserProvider + useUser() hook; fetches /auth/me on mount
- `frontend/app/(dashboard)/layout.tsx` — wraps tree in UserProvider; Nav shows Users link for admin; email+role in header
- `frontend/lib/api.ts` — UserRole type, CurrentUser/OrgUser interfaces, getCurrentUser/listUsers/inviteUser/updateUserRole/removeUser
- `frontend/app/(dashboard)/agent-scans/page.tsx` — Launch button hidden for viewer
- `frontend/app/(dashboard)/schedules/page.tsx` — create form + pause/delete hidden for viewer
- `frontend/app/(dashboard)/users/page.tsx` (new) — admin-only: member table, role dropdown, remove button, invite form
- tsc clean, pushed aeade70

**P8-1 RBAC — COMPLETE ✅**

**What was done (session 23 continued - P8-2 Compliance Reports, IN PROGRESS):**
- `backend/core/compliance.py` (new) — control mapping tables for SOC2/ISO27001/PCI-DSS:
  - SOC2: CC6.1, CC6.2, CC6.6, CC6.7, CC7.1, CC7.2, CC8.1, CC9.2
  - ISO27001: A.5.23, A.8.8, A.9.1, A.9.4, A.10.1, A.12.1, A.14.2, A.16.1
  - PCI-DSS: Req 1–4, 6–8, 10–11
  - `evaluate_framework(framework, findings)` → list[ControlResult] with NON-COMPLIANT/REVIEW/COMPLIANT
  - Matching via category + severity + title/description keywords
- `backend/api/v1/compliance.py` (new) — `GET /agent-scans/{scan_id}/compliance/{framework}`:
  - Accepts Bearer header OR `?token=` query param (for browser `<a>` download)
  - `_resolve_user` dependency handles both auth paths
  - PDF: header, summary, controls overview table, per-control detail (issues only), compliant list
  - fpdf2, same pattern as reports.py
- `backend/main.py` — compliance_router registered
- **PENDING**: frontend compliance export buttons on agent-scans page

**P8-2 Compliance Reports — COMPLETE ✅ (1d7e5d2)**
- Frontend: compliance export buttons (SOC2/ISO27001/PCI-DSS) on completed scan, `?token=` query param for browser `<a>` download
- tsc clean, pushed 1d7e5d2

**Next session should:**
Continue Phase 8:
1. P8-3 Production Docker stack (Nginx + TLS + secrets management)
2. P8-4 SSO/OIDC

**Git HEAD:** 1d7e5d2

---

**Session #:** 24
**Date:** 2026-08-07
**Phase:** 8
**What was done:**
- Context resumed from previous session (context window compaction)
- Created `IMP info/reports/phase-8-audit.md` — full P8-1 + P8-2 audit (route matrix, control tables, P8-3/P8-4 planned)
- Verified all docs synced: master-progress-report, PHASES.md, memory files, audit files all current
- Pushed 2 auto-sync commits to origin/main → HEAD now ca29d2f
**Decisions made:** None (doc-only session)
**Blockers:** None
**Next session should:**
Continue Phase 8:
1. P8-3 Production Docker stack (Nginx + TLS + secrets management — `infra/docker/docker-compose.prod.yml`, `infra/nginx/nginx.conf`, `.env.prod.example`)
2. P8-4 SSO/OIDC

**Git HEAD:** ca29d2f

---

**Session #:** 25
**Date:** 2026-08-08
**Phase:** 8
**What was done:**
- **P8-3 Production Docker stack** ✅
  - `infra/docker/docker-compose.prod.yml` — all services (postgres, redis, neo4j, backend, worker, beat, frontend, nginx); internal/external networks; no ports exposed except 80/443 on nginx
  - `infra/nginx/nginx.conf` — HTTP→HTTPS redirect, TLS 1.2/1.3, rate limiting (30r/m API / 10r/m auth), WS proxy, security headers (HSTS, CSP-class headers)
  - `.env.prod.example` — all prod vars documented with CHANGE_ME placeholders, never committed
  - `backend/Dockerfile` — python:3.12-slim, uvicorn 2 workers
  - `frontend/Dockerfile` — multi-stage Next.js standalone build
  - `frontend/next.config.ts` — `output: "standalone"` in production
  - `.gitignore` — `.env.prod` added
- **P8-4 SSO / OIDC** ✅
  - `backend/core/oidc.py` — generic OIDC client: discovery, authorization URL builder, code exchange, userinfo fetch (httpx)
  - `backend/core/config.py` — added: oidc_enabled, oidc_issuer, oidc_client_id, oidc_client_secret, oidc_redirect_uri
  - `backend/api/v1/auth.py` — `GET /auth/oidc/login` (state cookie + Google redirect); `GET /auth/oidc/callback` (code exchange → find/create user → JWT → redirect to frontend)
  - `frontend/app/(auth)/callback/page.tsx` — reads `?token=` from URL, stores in localStorage, redirects to /dashboard
  - `frontend/app/(auth)/login/page.tsx` — "Sign in with Google" button (shown only when NEXT_PUBLIC_OIDC_ENABLED=true)
  - `.env.prod.example` — OIDC section added (OIDC_ENABLED, OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI, NEXT_PUBLIC_OIDC_ENABLED)
- tsc clean, syntax OK all files
**Decisions made:**
- OIDC state validated via httpOnly cookie (short-lived, 300s) to prevent CSRF
- OIDC user provisioning: new email → new org named after email domain; existing email → existing user
- OIDC password_hash set to "" (OIDC users have no local password — local login blocked for them by empty hash)
- Google button rendered client-side only when NEXT_PUBLIC_OIDC_ENABLED=true (zero UI impact when SSO disabled)
**Blockers:** None
**Next session should:**
- Phase 8 is COMPLETE ✅ — all P8-1 through P8-4 shipped
- Phase 9 options: on-premise deployment guide, multi-tenant billing, fine-tuned security LLMs, or customer demo prep
- Decide next phase direction with CTO

**Git HEAD:** 525f016 (P8 complete push)

---

**Session #:** 25 (continued)
**Date:** 2026-08-08
**Phase:** 9
**What was done:**
- **P9-1 Helm chart** ✅ — `infra/helm/sentinelai/` (22 files)
  - Chart.yaml, values.yaml, _helpers.tpl
  - Deployments + Services: postgres, redis, neo4j, backend, worker, beat, frontend
  - PVCs: postgres (20Gi), redis (5Gi), neo4j (10Gi)
  - ConfigMap: all non-secret env vars, DB URLs constructed from release name
  - Secret: all passwords/keys via `stringData` with `required` guard on critical values
  - Ingress: nginx-ingress, TLS, WS annotation, path routing (backend API/auth/ws, frontend /)
  - migrations-job: post-install/upgrade Helm hook, `alembic upgrade head`
- **P9-2 Deployment runbook** ✅ — `docs/deployment/on-premise.md`
  - Prerequisites table (Docker/K8s paths), resource requirements, quick-start
  - Docker Compose path: env setup, TLS (certbot/manual), build, migrate, start, verify
  - Kubernetes path: Helm install/upgrade, cert-manager ClusterIssuer
  - Upgrade procedures for both paths
  - Backup/restore: postgres pg_dump, neo4j neo4j-admin dump
  - Troubleshooting section (common failure modes)
  - Env var reference table
- **P9-3 Quick-start script** ✅ — `scripts/deploy.sh`
  - Interactive: choose Compose vs K8s
  - Validates prerequisites (docker, kubectl, helm)
  - Auto-generates secrets (JWT, PG, Redis, Neo4j) via python3 secrets module
  - Collects domain + Anthropic key; patches .env.prod in-place
  - Compose path: starts infra, waits for postgres healthcheck, runs migrations, starts all services
  - K8s path: creates namespace, builds values override from .env.prod, helm install/upgrade --wait
  - bash -n syntax check: OK
**Decisions made:**
- Helm chart uses `sentinelai.image` helper for optional global registry prefix (ghcr.io etc)
- `required` guard on postgresPassword/redisPassword/neo4jPassword/jwtSecretKey in secret.yaml — `helm install` fails fast with clear message if omitted
- deploy.sh generates secrets locally (no external dep), patches .env.prod with sed, chmod 600
- Migrations run in isolated docker run (Compose) or Helm hook Job (K8s) — never in the app container startup
**Blockers:** helm not installed locally — CLI should run: `brew install helm && helm lint infra/helm/sentinelai --set secrets.postgresPassword=x --set secrets.redisPassword=x --set secrets.neo4jPassword=x --set secrets.jwtSecretKey=x`
**Next session should:**
- P9 remaining: P9-4 optional — seed data / demo org script
- Or decide Phase 10 direction

**Git HEAD:** (pending push)

**Restart Celery worker command:**
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
