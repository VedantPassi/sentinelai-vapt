# Phase 8 Report — Polish & Hardening

**Date:** 2026-08-08
**Phase:** 8 — Polish & Hardening
**Git HEAD:** 525f016
**Status:** ✅ Complete

---

## Overview

Phase 8 adds enterprise polish: role-based access control across all API surfaces, compliance PDF exports (SOC2 / ISO27001 / PCI-DSS), a production-ready Docker/Nginx stack, and generic OIDC SSO.

---

## What Was Built

### P8-1 — RBAC Enforcement

**Backend `core/deps.py`:**
```python
def require_roles(*roles: str) -> Callable:
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"Role '{user.role}' cannot perform this action")
        return user
    return _check

require_admin   = require_roles("admin")
require_analyst = require_roles("admin", "analyst")
```

**Route enforcement matrix:**

| Endpoint | Guard |
|----------|-------|
| `POST /targets` | `require_analyst` |
| `PUT /targets/{id}` | `require_analyst` |
| `DELETE /targets/{id}` | `require_admin` |
| `POST /agent-scans` | `require_analyst` |
| `PATCH /findings/{id}` | `require_analyst` |
| `POST /findings/{id}/validate` | `require_analyst` |
| `POST /agent-scans/{id}/integrations/*` | `require_analyst` |
| `POST /schedules` | `require_analyst` |
| `PATCH /schedules/{id}` | `require_analyst` |
| `DELETE /schedules/{id}` | `require_admin` |
| All `/users/*` | `require_admin` |

**New: `api/v1/users.py`** — admin-only user management:
- `GET /users` — list org members
- `POST /users` — invite (email + password + role)
- `PATCH /users/{id}/role` — change role; self-change blocked
- `DELETE /users/{id}` — remove; self-remove blocked

**New: `GET /auth/me`** → `{id, email, role, org_id}`

**Frontend:**
- `contexts/UserContext.tsx` — `UserProvider` wraps layout; `useUser()` hook fetches `/auth/me`
- `layout.tsx` — renders `email · Role` in nav; Users link admin-only
- `agent-scans/page.tsx` — Launch button hidden for viewer
- `schedules/page.tsx` — create form + pause/delete hidden for viewer
- `users/page.tsx` (new) — member table, role dropdown, remove, invite form; redirects non-admins to `/dashboard`
- `targets/page.tsx` — Add target hidden for viewer; Delete hidden for non-admin *(fixed in session 27)*

---

### P8-2 — Compliance Reports (SOC2 / ISO27001 / PCI-DSS)

**`core/compliance.py`** — control mapping tables:

| Framework | Controls |
|-----------|---------|
| SOC2 TSC | CC6.1, CC6.2, CC6.6, CC6.7, CC7.1, CC7.2, CC8.1, CC9.2 |
| ISO 27001:2022 Annex A | A.5.23, A.8.8, A.9.1, A.9.4, A.10.1, A.12.1, A.14.2, A.16.1 |
| PCI-DSS v4 | Req 1, 2, 3, 4, 6, 7, 8, 10, 11 |

Matching logic: category + severity + title/description keywords → control IDs.  
Status per control: `NON-COMPLIANT` (confirmed finding) / `REVIEW` (open finding) / `COMPLIANT` (no match).

**`api/v1/compliance.py`** — `GET /agent-scans/{scan_id}/compliance/{framework}`:
- Auth: Bearer header OR `?token=` query param (enables browser `<a download>` without JS fetch)
- PDF: header → scan info → summary → controls overview table → per-control detail (issues + remediation) → compliant controls list

**Frontend:** SOC2/ISO27001/PCI-DSS buttons on completed scan card, each is `<a download href="...?token=...">`.

---

### P8-3 — Production Docker Stack

| File | Purpose |
|------|---------|
| `infra/docker/docker-compose.prod.yml` | All 8 services; internal/external networks; no ports except 80/443 on nginx; health checks |
| `infra/nginx/nginx.conf` | HTTP→HTTPS, TLS 1.2/1.3, rate limiting (30r/m API / 10r/m auth), WS proxy, security headers (HSTS 63072000s) |
| `backend/Dockerfile` | python:3.12-slim; uvicorn 2 workers |
| `frontend/Dockerfile` | Multi-stage: deps → builder (next build standalone) → runner |
| `frontend/next.config.ts` | `output: "standalone"` in production |
| `.env.prod.example` | All vars with `CHANGE_ME` placeholders |
| `.gitignore` | `.env.prod` added |

---

### P8-4 — SSO / OIDC

**`backend/core/oidc.py`:**
```python
async def _discovery() -> dict           # {issuer}/.well-known/openid-configuration
def build_authorization_url(state) -> str
async def exchange_code(code) -> dict
async def fetch_userinfo(access_token) -> dict
```

**`GET /auth/oidc/login`:**
- Generates `state` via `secrets.token_urlsafe(16)`, stores in httpOnly cookie (300s TTL)
- Redirects to provider authorization URL

**`GET /auth/oidc/callback`:**
- Validates state cookie (CSRF protection)
- Exchanges code → access_token → userinfo
- Finds or provisions user (new email → new org named after email domain; role=admin; `password_hash=""`)
- Issues JWT → `RedirectResponse` to `{FRONTEND_URL}/auth/callback?token={jwt}`

**Frontend:**
- `app/(auth)/callback/page.tsx` — reads `?token=`, stores in localStorage, redirects to `/dashboard`
- `app/(auth)/login/page.tsx` — Google SSO button rendered only when `NEXT_PUBLIC_OIDC_ENABLED=true`

---

## Bug Fix (session 27)

**Compliance PDF 500 error** — em-dash `—` (U+2014) in 4 hardcoded f-strings in `api/v1/compliance.py` bypassed the `_s()` sanitizer and crashed fpdf2's latin-1 encoder (`FPDFUnicodeEncodingException`). Fixed by replacing all 4 with ASCII `-`. (commit 91700a1)

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `?token=` for compliance PDF download | Consistent with WS auth; browser `<a download>` can't set Authorization header |
| OIDC state in httpOnly cookie | CSRF protection; cookie not accessible to JS |
| OIDC users get empty password_hash | Prevents local login for SSO-provisioned accounts |
| SSO button rendered client-side only | `NEXT_PUBLIC_OIDC_ENABLED` gate — zero UI impact when SSO disabled |
| `require_roles` factory | Single call generates typed dependency; no boilerplate per route |
