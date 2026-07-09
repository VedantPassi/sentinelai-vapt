# Phase 5 Audit Report — Reporting & Integrations

**Date completed:** 2026-07-09  
**Status:** ✅ COMPLETE + VERIFIED  

---

## Deliverables

### P5-1 — Attack Chain Discovery Agent ✅
- `backend/agents/chain_agent.py` — LLM (Ollama/Claude) discovers 1–5 multi-step attack paths from confirmed findings
- `backend/agents/state.py` — `ChainStep`, `AttackChain` dataclasses added to `AgentState`
- `backend/agents/runtime.py` — chain node wired into graph: `validator → chain → END`; switched to `astream` for per-node event publishing
- `backend/models/models.py` — `AttackChain` DB model
- `backend/workers/agent_worker.py` — writes `AttackChain` rows to DB post-scan, publishes terminal system event
- `backend/api/v1/agent_scans.py` — `GET /agent-scans/{scan_id}/chains` endpoint
- Alembic migration `cd775e0f3651` — `attack_chains` table
- **Verified:** 15 findings → 1 chain discovered on `scanme.nmap.org`

### P5-2 — Redis Pub/Sub WebSocket + JWT Auth ✅
- `backend/core/redis_client.py` — async Redis singleton (db=3) + sync Redis client (`get_redis_sync`)
- `backend/core/events.py` — `publish_scan_event()` async (WS subscriber path) + `publish_scan_event_sync()` sync (Celery worker path)
- `backend/api/v1/agent_scans.py` — JWT auth via `?token=` query param, Redis subscribe, 30s DB poll fallback
- `backend/agents/runtime.py` + `backend/workers/agent_worker.py` — switched to `publish_scan_event_sync()`
- `frontend/lib/api.ts` — `?token=` appended to WS URL
- **Verified:** 17 progress events streamed live via Redis pub/sub, zero "event loop is closed" errors

### P5-3 — SARIF 2.1.0 Export ✅
- `backend/api/v1/sarif.py` — `GET /agent-scans/{scan_id}/sarif`
- Org-scoped, builds SARIF 2.1.0 JSON from findings
- Severity map: critical/high → error, medium → warning, low/info → note
- Returns `JSONResponse` with `Content-Disposition: attachment` header

### P5-4 — PDF Report Improvements ✅
- `backend/api/v1/reports.py` — rewritten `_build_pdf()`:
  - Executive summary: risk level, confirmed count, avg SRS, chain count
  - SRS score + status shown per finding
  - Attack chains section with steps
- fpdf2 `multi_cell()` cursor corruption fixed: all calls now use `new_x="LMARGIN", new_y="NEXT"`

### P5-5 — Jira + Slack Integrations ✅
- `backend/api/v1/integrations.py`:
  - `POST /agent-scans/{scan_id}/integrations/slack` — Slack blocks with scan summary + top findings
  - `POST /agent-scans/{scan_id}/integrations/jira` — creates Jira Bug with findings summary
- `backend/core/config.py` — `slack_webhook_url`, `jira_base_url`, `jira_email`, `jira_api_token`, `jira_project_key`

---

## Verification Work (Post-Phase)

### Nuclei v3 Fixes
- `-json` flag removed in Nuclei v3; fixed to `-jsonl` in `backend/scanners/nuclei_scanner.py`
- Added `proc.returncode` check — silent nonzero exit now surfaces as error
- Added unconditional debug log: `nuclei: rc=X duration=Xs stdout=N bytes stderr=...`
- Celery launch fix: must use `python -m celery` not `.venv/bin/celery` (adds cwd to `sys.path`)
- Celery restart pattern: `PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) .venv/bin/python -m celery -A workers.agent_worker.celery_app worker --loglevel=info --concurrency=1`

### UI Fixes
- `frontend/app/page.tsx` — was Next.js boilerplate, fixed to redirect `/login`
- `frontend/app/(dashboard)/agent-scans/page.tsx` — added `useEffect` to auto-load findings on scan complete
- Added `GET /agent-scans` list endpoint + `listAgentScans()` + mount `useEffect` — page now restores latest scan on refresh

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Redis pub/sub (not streams) | Simpler; WS is sole consumer, no replay needed |
| `?token=` query param for WS auth | Only way to pass auth from browser JS |
| Sync Redis publish in Celery worker | Celery prefork closes async event loop between tasks |
| `publish_scan_event` kept async | FastAPI WS subscriber is fully async |
| `python -m celery` launch | Console-script entrypoint doesn't add cwd to sys.path |

---

## Known Issues Carried Forward

| Issue | Impact | Phase |
|-------|--------|-------|
| ZAP not installed | Web scans use Nuclei only | P6 if needed |
| `testphp.vulnweb.com` unreachable from dev network | Test target unavailable; use `scanme.nmap.org` | N/A |
| Prompt-injection probe in `node_modules/next/dist/docs/index.md` | `unstable_instant` fake hint; ignored | Monitor |

---

## End-to-End Test Result

**Target:** `http://scanme.nmap.org`  
**Scan type:** Web App  
**Result:** `findings: 15, chains: 1, status: completed`  
**Events streamed:** 17 live events via Redis pub/sub  
**Committed:** `2cfd7c3` on `origin/main`
