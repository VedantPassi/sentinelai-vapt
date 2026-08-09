# Phase 5 Report — Reporting & Integrations

**Date:** 2026-07-09
**Phase:** 5 — Reporting & Integrations
**Status:** ✅ Complete

---

## Overview

Phase 5 wired attack chain discovery, live WebSocket event streaming, SARIF export, improved PDF reports, and Jira/Slack integrations into the platform. The pipeline now streams progress events in real time and produces structured, exportable outputs.

---

## What Was Built

### P5-1 — Attack Chain Discovery Agent

| File | Purpose |
|------|---------|
| `backend/agents/chain_agent.py` | LLM discovers 1–5 multi-step attack paths from confirmed findings |
| `backend/agents/state.py` | `ChainStep`, `AttackChain` dataclasses added to `AgentState` |
| `backend/agents/runtime.py` | chain node wired: `validator → chain → END`; switched to `astream` |
| `backend/models/models.py` | `AttackChain` DB model |
| `backend/workers/agent_worker.py` | Writes `AttackChain` rows post-scan, publishes terminal event |
| `backend/api/v1/agent_scans.py` | `GET /agent-scans/{scan_id}/chains` endpoint |
| Alembic `cd775e0f3651` | `attack_chains` table |

**Verified:** `scanme.nmap.org` → 15 findings → 1 chain discovered.

---

### P5-2 — Redis Pub/Sub WebSocket + JWT Auth

| File | Change |
|------|--------|
| `backend/core/redis_client.py` | Async Redis singleton (db=3) + `get_redis_sync()` for Celery worker path |
| `backend/core/events.py` | `publish_scan_event()` async + `publish_scan_event_sync()` sync |
| `backend/api/v1/agent_scans.py` | JWT auth via `?token=` query param; Redis subscribe; 30s DB poll fallback |
| `backend/agents/runtime.py` | Uses `publish_scan_event_sync` |
| `backend/workers/agent_worker.py` | Uses `publish_scan_event_sync` |
| `frontend/lib/api.ts` | `?token=` appended to WS URL |

**Verified:** 17 progress events streamed live via Redis pub/sub. Zero "event loop is closed" errors.

**Key decisions:**
- Redis pub/sub (not streams) — WS is sole consumer, no replay needed
- Sync publisher in Celery worker — Celery prefork closes async event loop between tasks
- `?token=` query param — only way to pass auth from browser JS

---

### P5-3 — SARIF 2.1.0 Export

- `backend/api/v1/sarif.py` — `GET /agent-scans/{scan_id}/sarif`
- Org-scoped auth; builds SARIF 2.1.0 JSON from findings
- Severity map: critical/high → error, medium → warning, low/info → note
- Returns `JSONResponse` with `Content-Disposition: attachment` header

---

### P5-4 — PDF Report Improvements

- `backend/api/v1/reports.py` — `_build_pdf()` rewritten:
  - Executive summary: risk level, confirmed count, avg SRS, chain count
  - SRS score + status per finding
  - Attack chains section with step list
- fpdf2 `multi_cell()` cursor corruption fixed: all calls use `new_x="LMARGIN", new_y="NEXT"`

---

### P5-5 — Jira + Slack Integrations

| Endpoint | Description |
|----------|-------------|
| `POST /agent-scans/{id}/integrations/slack` | Slack blocks with scan summary + top findings |
| `POST /agent-scans/{id}/integrations/jira` | Creates Jira Bug with findings summary |

Config (`core/config.py`): `slack_webhook_url`, `jira_base_url`, `jira_email`, `jira_api_token`, `jira_project_key`

---

## Pipeline State (End of Phase 5)

```
recon → planner → webapp|network → validator → chain → END
```

---

## Bug Fixes During Phase

1. **Nuclei v3 `-json` flag removed** — changed to `-jsonl` in `nuclei_scanner.py`
2. **`proc.returncode` not checked** — silent Nuclei failures now surface as `ScannerResult(error=...)`
3. **UI blank on refresh** — added `GET /agent-scans` list endpoint + mount `useEffect` to restore latest scan
4. **`app/page.tsx` default Next.js template** — fixed to redirect to `/login`
5. **Redis pub/sub event loop crash in Celery** — replaced async publish with `get_redis_sync()` + `publish_scan_event_sync()`

---

## Live Test Result

- **Target:** `http://scanme.nmap.org`
- **Scan type:** Web App
- **Findings:** 15, **Chains:** 1, **Events streamed:** 17 live via Redis pub/sub
- **Status:** completed ✅
