# Phase 7 Audit Report — Enterprise Features

**Date:** 2026-07-26  
**Git HEAD:** cee2ca1  
**Status:** COMPLETE ✅ (P7-1 ✅ P7-2 ✅ P7-3 ✅)

---

## Summary

Phase 7 adds enterprise-grade capabilities on top of the P6 scanning pipeline: Active Directory attack path analysis via BloodHound CE, continuous monitoring via Celery Beat, and SIEM integration (pending). Synthetic AD dataset (TESTCORP.LOCAL) used for development — no real AD environment required.

---

## P7-1 — BloodHound CE Attack Path Analysis

**Delivered:**
- `backend/core/bloodhound_client.py` — rewrote dead REST endpoints to use `/api/v2/graphs/cypher` (POST):
  - `get_attack_paths(limit)` — Cypher shortestPath from any non-DA User → Group containing "DOMAIN ADMINS"
  - `get_node_shortest_paths(node_id, node_type)` — path from specific node to DA
  - `get_high_value_targets()` — nodes with `admincount=true`
  - `_cypher()` / `_cypher_raw()` — shared Cypher helpers
- `backend/agents/bloodhound_agent.py` (new) — full LangGraph agent node:
  - Queries BH CE for attack paths + high-value targets
  - Converts each path to `FindingData(category="ad", severity="critical", cvss=9.0)`
  - LLM enriches with attack narrative, pivots, priority reasoning
  - Stores pivot chain in `poc_evidence`
- `backend/agents/runtime.py` — `bloodhound` node + `"ad"` conditional route; recon/planner skip for `target_type="ad"`
- `backend/agents/recon_agent.py` + `planner_agent.py` — `"ad"` added to skip list
- `frontend/app/(dashboard)/agent-scans/page.tsx` — "Active Directory (BloodHound)" scan type option

**Infrastructure:**
- BloodHound CE deployed at `localhost:8080` (Docker, ports remapped to avoid Neo4j conflict)
- Synthetic AD: TESTCORP.LOCAL — alice/bob/charlie, Domain Admins group
- Attack path: charlie →(WriteDACL)→ bob →(GenericAll)→ alice →(MemberOf)→ Domain Admins
- Data ingested via SharpHound v2 JSON upload (job Complete, 4 files)
- Cypher endpoint confirmed working against synthetic data

**Config (`.env`):**
```
BLOODHOUND_URL=http://localhost:8080
BLOODHOUND_USER=admin
BLOODHOUND_SECRET=<secret>
```

**Verified:** Imports clean, syntax OK, tsc clean. End-to-end pending real AD or BH CE data query test.

---

## P7-2 — Continuous Monitoring (Celery Beat)

**Delivered:**
- `backend/models/models.py` — `ScheduledScan` model:
  - Fields: `target_id`, `scan_type`, `interval_hours`, `config`, `is_active`, `last_run_at`, `next_run_at`
  - FK → `targets` (CASCADE), relationship on `Target.scheduled_scans`
- `backend/alembic/versions/d7a6f3c81899_add_scheduled_scans.py` — migration applied ✅
- `backend/workers/beat_worker.py` — Celery Beat worker:
  - Imports `celery_app` from `agent_worker` (same broker/backend)
  - `beat_schedule`: `check_due_schedules` every 60s
  - Task: queries `ScheduledScan WHERE is_active=True AND next_run_at <= now`
  - For each due schedule: creates `ScanJob`, calls `celery_app.send_task("workers.agent_worker.run_agent_task", ...)`, advances `next_run_at = now + interval_hours`
- `backend/api/v1/schedules.py` — CRUD router (`/schedules`):
  - `POST /schedules` — create with target_id, scan_type, interval_hours, config
  - `GET /schedules` — list (org-scoped via JWT)
  - `GET /schedules/{id}` — get single
  - `PATCH /schedules/{id}` — toggle is_active, change interval, update config
  - `DELETE /schedules/{id}` — remove
- `backend/main.py` — `schedules_router` registered at `/api/v1`
- `frontend/app/(dashboard)/schedules/page.tsx` (new) — Schedules page:
  - Create form: target selector, scan type, interval hours
  - Table: target name, type badge, interval, last/next run, active status, pause/resume/delete
- `frontend/lib/api.ts` — `Schedule` interface + `listSchedules`, `createSchedule`, `toggleSchedule`, `deleteSchedule`
- `frontend/app/(dashboard)/layout.tsx` — "Schedules" nav link added

**Start Beat in dev:**
```bash
cd backend && PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) \
  .venv/bin/celery -A workers.beat_worker beat --loglevel=info
```

**Verified:** All 4 Python files syntax OK, migration auto-generated + applied clean, tsc zero errors.

---

## Pipeline State (End of P7-2)

```
recon → planner → [webapp|network|container|cloud|bloodhound] → validator → chain → graph → END
```

Scan types: `web`, `api`, `network`, `container`, `cloud`, `ad`

Continuous monitoring: Celery Beat → `check_due_schedules` (60s) → `run_agent_task` on worker

---

## P7-3 — SIEM Integration ✅

**Delivered:**
- `backend/core/siem_client.py` (new):
  - `_send_to_splunk()` — POSTs newline-delimited JSON to Splunk HEC `/services/collector/event`; auth via `Splunk <token>` header
  - `_send_to_elasticsearch()` — POSTs ndjson bulk payload to `/_bulk`; optional basic auth
  - `forward_to_siem()` — calls both if configured; swallows `HTTPError` (fire-and-forget)
- `backend/workers/siem_worker.py` (new):
  - Celery task `ship_to_siem(scan_id)` registered on `agent_worker.celery_app`
  - Loads `ScanJob` + `Target` + all `Finding` rows from DB
  - Builds structured event per finding: scan_id, target_url, scan_type, finding_id, title, category, severity, status, srs_score, remediation, timestamp
  - Calls `forward_to_siem(events)`
- `backend/core/config.py` — new SIEM settings block:
  ```
  siem_enabled: bool = False
  splunk_hec_url: str = ""
  splunk_hec_token: str = ""
  splunk_index: str = "sentinelai"
  es_url: str = ""
  es_index: str = "sentinelai-findings"
  es_user: str = ""
  es_password: str = ""
  ```
- `backend/workers/agent_worker.py` — after scan completes + DB writes done:
  ```python
  if settings.siem_enabled and scan.status == "completed":
      celery_app.send_task("workers.siem_worker.ship_to_siem", args=[scan_id])
  ```

**Enable in `.env`:**
```
SIEM_ENABLED=true
SPLUNK_HEC_URL=https://splunk:8088
SPLUNK_HEC_TOKEN=<token>
SPLUNK_INDEX=sentinelai
ES_URL=http://elasticsearch:9200
ES_INDEX=sentinelai-findings
```

**Verified:** syntax OK all 4 files, `workers.siem_worker.ship_to_siem` in `celery_app.tasks`. Pushed cee2ca1.

---

## Known Gaps / Deferred

| Item | Reason deferred |
|------|-----------------|
| Real AD environment test | No Windows AD in dev; synthetic data used |
| BH CE Cypher edge traversal | `_cypher_raw` returns nodes+edges but BH graph format may vary by version |
| Beat HA / Redis lock | Multiple Beat instances would double-trigger; single Beat process assumed |
| Schedule last-run history | No per-run history stored; only `last_run_at` timestamp kept |

---

## Files Changed (Phase 7 so far)

**Backend:**
- `core/bloodhound_client.py` (rewritten)
- `agents/bloodhound_agent.py` (new)
- `agents/runtime.py` (bloodhound node + ad route)
- `agents/recon_agent.py` (ad skip)
- `agents/planner_agent.py` (ad skip)
- `models/models.py` (ScheduledScan model)
- `alembic/versions/d7a6f3c81899_add_scheduled_scans.py` (new)
- `workers/beat_worker.py` (new)
- `api/v1/schedules.py` (new)
- `main.py` (schedules router)

**Frontend:**
- `app/(dashboard)/agent-scans/page.tsx` (ad scan type)
- `app/(dashboard)/schedules/page.tsx` (new)
- `app/(dashboard)/layout.tsx` (Schedules nav link)
- `lib/api.ts` (Schedule interface + helpers)
