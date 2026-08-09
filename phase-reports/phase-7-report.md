# Phase 7 Report — Enterprise Features

**Date:** 2026-08-03
**Phase:** 7 — Enterprise Features
**Git HEAD:** a938554
**Status:** ✅ Complete + End-to-End Verified

---

## Overview

Phase 7 adds enterprise-grade capabilities: Active Directory attack path analysis via BloodHound CE, continuous automated monitoring via Celery Beat, and SIEM forwarding to Splunk/Elasticsearch. All 4 scan types verified in a single live demo run.

---

## What Was Built

### P7-1 — BloodHound CE Attack Path Analysis

**Infrastructure:**
- BloodHound CE deployed at `localhost:8080` (Docker; ports remapped to 7475/7688 to avoid Neo4j conflict)
- Synthetic AD: TESTCORP.LOCAL — alice/bob/charlie; attack path: charlie →(WriteDACL)→ bob →(GenericAll)→ alice →(MemberOf)→ Domain Admins

| File | Purpose |
|------|---------|
| `backend/core/bloodhound_client.py` | Rewrote dead REST endpoints → `/api/v2/graphs/cypher` (POST Cypher); `get_attack_paths()`, `get_node_shortest_paths()`, `get_high_value_targets()`, `_to_list()` helper |
| `backend/agents/bloodhound_agent.py` | BH paths → `FindingData(category="ad", severity="critical")`; LLM enriches with attack narrative + pivots |
| `backend/agents/runtime.py` | `bloodhound` node + `"ad"` conditional route |
| `backend/agents/recon_agent.py` + `planner_agent.py` | `"ad"` added to skip list |
| `frontend/app/(dashboard)/agent-scans/page.tsx` | "Active Directory (BloodHound)" scan type added |

**Config (`.env`):**
```
BLOODHOUND_URL=http://localhost:8080
BLOODHOUND_USER=admin
BLOODHOUND_SECRET=<secret>
```

---

### P7-2 — Continuous Monitoring (Celery Beat)

| File | Purpose |
|------|---------|
| `backend/models/models.py` | `ScheduledScan` model (target_id, scan_type, interval_hours, config, is_active, last_run_at, next_run_at) |
| Alembic `d7a6f3c81899` | `scheduled_scans` table — applied ✅ |
| `backend/workers/beat_worker.py` | Beat 60s tick; `check_due_schedules` task: queries due schedules, creates `ScanJob`, calls `send_task("run_agent_task")`, advances `next_run_at` |
| `backend/api/v1/schedules.py` | CRUD: POST/GET/PATCH/DELETE `/schedules` (org-scoped) |
| `frontend/app/(dashboard)/schedules/page.tsx` | Create form, live table, pause/resume/delete |
| `frontend/lib/api.ts` | `Schedule` interface + CRUD helpers |
| `frontend/app/(dashboard)/layout.tsx` | "Schedules" nav link added |

**Start Beat:**
```bash
cd backend && PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) \
  .venv/bin/celery -A workers.beat_worker beat --loglevel=info
```

---

### P7-3 — SIEM Integration (Splunk + Elasticsearch)

| File | Purpose |
|------|---------|
| `backend/core/siem_client.py` | `_send_to_splunk()` (HEC) + `_send_to_elasticsearch()` (bulk ndjson) + `forward_to_siem()` fire-and-forget |
| `backend/workers/siem_worker.py` | Celery task `ship_to_siem(scan_id)` — loads findings from DB, builds events, calls `forward_to_siem` |
| `backend/core/config.py` | `siem_enabled`, `splunk_hec_url/token/index`, `es_url/index/user/password` |
| `backend/workers/agent_worker.py` | After scan completes: calls `ship_to_siem` if `siem_enabled=true` |

**Enable:**
```
SIEM_ENABLED=true
SPLUNK_HEC_URL=https://splunk:8088
SPLUNK_HEC_TOKEN=<token>
SPLUNK_INDEX=sentinelai
ES_URL=http://elasticsearch:9200
ES_INDEX=sentinelai-findings
```

---

## Pipeline State (End of Phase 7)

```
recon → planner → [webapp|network|container|cloud|bloodhound] → validator → chain → graph → END
```

Scan types: `web`, `api`, `network`, `container`, `cloud`, `ad`

---

## Bug Fixes During Phase

### Fix 1 — Neo4j AsyncDriver event-loop binding (commit 16e0804)
**Symptom:** `"Future is attached to a different loop"` warning; Neo4j silently fails on 2nd+ Celery task.  
**Root cause:** Module-level `_driver` singleton binds to first task's event loop. Celery prefork creates new loop per task.  
**Fix:** `_close_neo4j()` called in `run_agent_task` finally block.

### Fix 2 — AWS credentials not in Celery worker env (commit 19a0f1a)
**Symptom:** Prowler exits with "AWS credentials not set" even with valid `.env`.  
**Root cause:** pydantic-settings `env_file` loads into `settings` object but does NOT inject into `os.environ`. Celery worker never sources `.env`.  
**Fix:** `load_dotenv(Path(__file__).parent.parent.parent / ".env")` at top of `agent_worker.py`.

### Fix 3 — BloodHound CE nodes/edges are dicts not lists (commit a938554)
**Symptom:** `"BloodHound agent failed: 0"` — opaque error, 0 findings.  
**Root cause:** BH CE `/api/v2/graphs/cypher` returns `nodes`/`edges` as dicts keyed by string IDs (`{"0": {...}}`). `nodes[0]` raises `KeyError: 0` on a dict; `str(KeyError(0)) == "0"`.  
**Fix:** `_to_list()` helper in `bloodhound_client.py` converts dict values to list.

---

## End-to-End Demo Results (2026-08-03)

| Scan Type | Tool | Findings | Chains | Status |
|-----------|------|----------|--------|--------|
| Network | Nmap + Nuclei | 2 | 1 | ✅ |
| Container | Trivy (python:3.8-slim) | 50 | 5 | ✅ |
| Cloud | Prowler (real AWS account) | 21 | 2 | ✅ |
| Active Directory | BloodHound CE (TESTCORP.LOCAL) | 1 critical | 0 | ✅ |
