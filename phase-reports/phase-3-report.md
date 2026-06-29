# Phase 3 Report — AI Agent Framework

**Date:** 2026-06-30
**Phase:** 3 — AI Agent Framework
**Status:** ✅ Complete

---

## Overview

Phase 3 built the autonomous AI agent layer on top of the Phase 2 scanning engine. A LangGraph-based multi-agent pipeline orchestrates reconnaissance, attack planning (via Claude API), and scanner execution, with results stored in PostgreSQL and streamed to the frontend via WebSocket.

---

## What Was Built

### Agent Pipeline (LangGraph)

```
POST /agent-scans
  → Celery worker
    → LangGraph graph
      → recon_agent    (DNS, subdomain enum, HTTP fingerprint)
      → planner_agent  (Claude Opus 4.8 — MITRE ATT&CK vectors)
      → webapp_agent   (ZAP + Nuclei + Claude enrichment)  [web/api targets]
      → network_agent  (Nmap + Gitleaks + Claude CVE mapping) [network targets]
    → findings stored in DB
    → progress_events stored in scan.config JSONB
```

### Files Created

| File | Purpose |
|------|---------|
| `backend/agents/state.py` | AgentState TypedDict + dataclasses |
| `backend/agents/runtime.py` | LangGraph graph + `run_agent_scan()` |
| `backend/agents/recon_agent.py` | DNS, subdomain, HTTP fingerprint |
| `backend/agents/planner_agent.py` | Claude Opus 4.8 attack planning |
| `backend/agents/webapp_agent.py` | ZAP + Nuclei + Claude enrichment |
| `backend/agents/network_agent.py` | Nmap + Gitleaks + Claude CVE mapping |
| `backend/workers/agent_worker.py` | Celery task wrapping LangGraph |
| `backend/api/v1/agent_scans.py` | REST + WebSocket endpoints |
| `frontend/app/(dashboard)/agent-scans/page.tsx` | Scan launcher + progress + findings UI |
| `frontend/lib/api.ts` | Agent scan API client + WebSocket helper |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agent-scans` | Create + queue agent scan |
| GET | `/api/v1/agent-scans/{id}` | Status + progress events |
| GET | `/api/v1/agent-scans/{id}/findings` | Paginated findings |
| WS | `/api/v1/agent-scans/ws/{id}` | Real-time progress stream |

---

## Live Test

**Target:** https://example.com (Cloudflare)
**Type:** Network scan

- Recon: 1 subdomain found, Cloudflare fingerprinted ✅
- Planner: skipped (no ANTHROPIC_API_KEY) — graceful fallback ✅
- Nmap: 4 open ports (80, 443, 8080, 8443) ✅
- CVE mapping: skipped (no API key) — raw findings stored ✅
- DB: 4 findings stored, 11 progress events ✅
- Frontend: launcher → progress terminal → findings list ✅

---

## Key Decisions

- **WebSocket progress:** DB polling every 2s — events batch-written at scan completion. Redis streaming deferred to Phase 5.
- **Model split:** `claude-opus-4-8` for attack planning (reasoning), `claude-sonnet-4-6` for finding enrichment (speed/cost).
- **Graceful fallback:** All Claude calls skip cleanly if `ANTHROPIC_API_KEY` is absent — scanners still run.
- **Tenant isolation:** Target join pattern (no `org_id` on `ScanJob`) — consistent with Phase 2.

---

## Bugs Fixed During Phase

10 bugs found across 2 audit rounds — all fixed:

1. `await db.delete()` → `db.delete()` (sync call)
2. Missing `dnspython` + `fpdf2` in `pyproject.toml`
3. `ScanJob` missing `created_at` + Alembic migration
4. CORS hardcoded → `settings.cors_origins`
5. `agent_scans.py` `created_at` used `datetime.now()` at read time
6. `bytes(pdf.output())` double-wrap in `reports.py`
7. Inline `run_scan` import inside request handler
8. Unguarded `uuid.UUID()` in `deps.py` → 500 on invalid token
9. No password minimum length in `auth.py`
10. ZAP hardcoded `/tmp/zap/` path → parallel scan race condition

---

## Deferred to Phase 5

- WebSocket auth (currently unauthenticated)
- Real-time incremental event streaming (Redis streams)
- Full Claude enrichment test (needs `ANTHROPIC_API_KEY`)
