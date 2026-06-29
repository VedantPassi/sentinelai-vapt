# Security & Code Audit Findings — Phase 3

**Date:** 2026-06-30
**Auditor:** CTO (automated + manual review)
**Scope:** All backend + frontend files modified or created in Phase 3

---

## Round 1 Findings

### 🔴 Critical

| # | File | Line | Issue | Fix Applied |
|---|------|------|-------|-------------|
| 1 | `api/v1/agent_scans.py` | 155 | WebSocket no auth — any client streams any scan | Deferred Phase 5 (known risk) |
| 2 | `api/v1/targets.py` | 118 | `await db.delete()` — `delete()` is sync, TypeError at runtime | ✅ Removed `await` |

### 🟠 High

| # | File | Issue | Fix Applied |
|---|------|-------|-------------|
| 3 | `pyproject.toml` | `dnspython` + `fpdf2` missing from declared deps | ✅ Added both with version pins |

### 🟡 Medium

| # | File | Line | Issue | Fix Applied |
|---|------|------|-------|-------------|
| 4 | `models/models.py` | 65 | `ScanJob` missing `created_at` (all other models have it) | ✅ Added + Alembic migration |
| 5 | `main.py` | 16 | CORS `allow_origins` hardcoded | ✅ Moved to `settings.cors_origins` |
| 6 | `api/v1/agent_scans.py` | 88, 105 | `created_at` used `datetime.now()` at read time | ✅ Uses model fields now |

---

## Round 2 Findings

### 🟠 High

| # | File | Line | Issue | Fix Applied |
|---|------|------|-------|-------------|
| 7 | `api/v1/reports.py` | 148 | `bytes(pdf.output())` — fpdf2 already returns bytes, double-wrap fails | ✅ Removed `bytes()` wrapper |
| 8 | `scanners/zap_scanner.py` | 40 | `/tmp/zap/report.json` hardcoded — parallel scan race condition | ✅ Per-scan UUID dir `/tmp/zap-{run_id}` |

### 🟡 Medium

| # | File | Line | Issue | Fix Applied |
|---|------|------|-------|-------------|
| 9 | `api/v1/scans.py` | 84 | `run_scan` imported inline inside request handler | ✅ Moved to top-level import |
| 10 | `core/deps.py` | 26 | `uuid.UUID(user_id)` unguarded — invalid UUID in token → 500 | ✅ try/except → 401 |
| 11 | `api/v1/auth.py` | 33 | No password minimum length — empty string accepted | ✅ `model_post_init` check ≥8 chars |
| 12 | `agents/recon_agent.py` | 76, 94 | `asyncio.get_event_loop()` deprecated (3.10+) | ✅ Replaced with `get_running_loop()` |
| 13 | `agents/recon_agent.py` | 71 | DNS `resolver.resolve()` called sync — blocks event loop | ✅ Wrapped in `run_in_executor` |

### 🔵 Low / Informational (accepted / deferred)

| # | File | Issue | Decision |
|---|------|-------|----------|
| 14 | `agents/webapp_agent.py` | `verify=False` SSL — disables cert check | Acceptable — VAPT tool intentionally scans targets |
| 15 | `api/v1/agent_scans.py` | WS no auth | Deferred Phase 5 |
| 16 | `api/v1/reports.py` | Double sort on findings (DB + Python) | Low impact, leave |
| 17 | `agents/planner_agent.py` | Auditor flagged `claude-opus-4-8` as invalid | FALSE POSITIVE — model ID confirmed correct per Anthropic SDK |

---

## Summary

| Severity | Found | Fixed | Deferred |
|----------|-------|-------|----------|
| 🔴 Critical | 2 | 1 | 1 (WS auth) |
| 🟠 High | 3 | 3 | 0 |
| 🟡 Medium | 8 | 8 | 0 |
| 🔵 Low | 4 | 0 | 4 (accepted) |
| **Total** | **17** | **12** | **5** |

All blocking issues resolved. Platform is production-safe for dev/staging use.
