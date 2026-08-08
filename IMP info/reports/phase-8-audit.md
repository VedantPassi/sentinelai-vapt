# Phase 8 Audit Report — Polish & Hardening

**Date:** 2026-08-08
**Git HEAD:** (session 25 — pending final push)
**Status:** COMPLETE ✅ (P8-1 ✅ P8-2 ✅ P8-3 ✅ P8-4 ✅)

---

## Summary

Phase 8 adds enterprise polish: role-based access control across all API surfaces, compliance PDF exports (SOC2 / ISO27001 / PCI-DSS), and (upcoming) production-grade deployment and SSO.

---

## P8-1 — RBAC Enforcement ✅ (aeade70)

### Deliverables

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
| `POST /agent-scans/{id}/integrations/slack` | `require_analyst` |
| `POST /agent-scans/{id}/integrations/jira` | `require_analyst` |
| `POST /schedules` | `require_analyst` |
| `PATCH /schedules/{id}` | `require_analyst` |
| `DELETE /schedules/{id}` | `require_admin` |
| All `GET /users/*` | `require_admin` |
| `POST /users` (invite) | `require_admin` |
| `PATCH /users/{id}/role` | `require_admin` |
| `DELETE /users/{id}` | `require_admin` |

**`api/v1/users.py` (new):**
- `GET /users` — list org members
- `POST /users` — invite: email + temp password + role; validated against (`admin/analyst/viewer`)
- `PATCH /users/{id}/role` — change role; blocked if `user.id == current_user.id`
- `DELETE /users/{id}` — remove; blocked if self

**`api/v1/auth.py`:**
- Added `GET /auth/me` → `{id, email, role, org_id}`

**Frontend:**
- `contexts/UserContext.tsx` — `UserProvider` wraps layout; `useUser()` hook
- `layout.tsx` — fetches `/auth/me` on mount; renders `email · Role` in nav; Users link admin-only
- `agent-scans/page.tsx` — Launch button: `{user?.role !== "viewer" && <button>}`
- `schedules/page.tsx` — create form + pause/delete: `{user?.role !== "viewer" && ...}`
- `users/page.tsx` (new) — member table with role dropdown + remove; invite form; redirects non-admins to `/dashboard`

**Verified:** syntax OK all files, tsc zero errors, pushed aeade70.

---

## P8-2 — Compliance Reports ✅ (1d7e5d2)

### Deliverables

**`core/compliance.py` (new):**

Control mapping for 3 frameworks:

| Framework | Controls |
|-----------|---------|
| SOC2 TSC | CC6.1, CC6.2, CC6.6, CC6.7, CC7.1, CC7.2, CC8.1, CC9.2 |
| ISO 27001:2022 Annex A | A.5.23, A.8.8, A.9.1, A.9.4, A.10.1, A.12.1, A.14.2, A.16.1 |
| PCI-DSS v4 | Req 1, 2, 3, 4, 6, 7, 8, 10, 11 |

Matching logic: `finding.category` + `finding.severity` + title/description keyword search → control IDs.

Status per control:
- `NON-COMPLIANT` — any confirmed finding matches
- `REVIEW` — any open finding matches
- `COMPLIANT` — no actionable findings match

**`api/v1/compliance.py` (new):**
- `GET /agent-scans/{scan_id}/compliance/{framework}` → PDF download
- Auth: Bearer header OR `?token=` query param (same pattern as WebSocket auth) — enables browser `<a download>` without JS fetch
- `_resolve_user` dependency handles both paths; `HTTPBearer(auto_error=False)`
- PDF sections: header, scan info, compliance summary (overall status), controls table (all controls), control detail (issues only with findings + remediation), compliant controls list

**Frontend (`agent-scans/page.tsx`):**
```tsx
{activeScan.status === "completed" && (
  <div className="flex gap-2 flex-wrap items-center">
    <span className="text-xs text-gray-400">Compliance:</span>
    {(["soc2", "iso27001", "pci-dss"] as const).map((fw) => (
      <a key={fw} href={`.../${fw}?token=${localStorage.getItem("access_token")}`} download>
        {fw}
      </a>
    ))}
  </div>
)}
```

**Verified:** syntax OK all files, tsc zero errors, pushed 1d7e5d2.

---

## P8-3 — Production Docker Stack ✅ (session 25)

### Deliverables

**`infra/docker/docker-compose.prod.yml`:**
- Services: postgres, redis, neo4j, backend, worker (Celery), beat (Celery Beat), frontend, nginx
- `internal` network (bridge, no external access) for all services; `external` network only for nginx
- No ports exposed except 80/443 on nginx
- Redis password-protected in prod (`--requirepass`)
- Health checks on postgres, redis, neo4j, backend
- All secrets from `.env.prod` (never baked into image)

**`infra/nginx/nginx.conf`:**
- HTTP → HTTPS permanent redirect (301)
- TLS 1.2/1.3 only; modern cipher suite; `ssl_session_cache`
- Security headers: HSTS (63072000s + preload), X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy
- Rate limiting: `30r/m` on `/api/`, `10r/m` on auth endpoints
- WS proxy: `/agent-scans/ws/` with `Upgrade` header passthrough; 3600s timeout
- `/health` unrated (liveness probe)
- `client_max_body_size 50M`

**`backend/Dockerfile`:** python:3.12-slim, `uvicorn main:app --workers 2`

**`frontend/Dockerfile`:** Multi-stage — `deps` (npm ci) → `builder` (next build, standalone) → `runner` (node server.js)

**`frontend/next.config.ts`:** `output: "standalone"` when `NODE_ENV=production`

**`.env.prod.example`:** All vars documented with `CHANGE_ME` placeholders — postgres, redis (password), neo4j, JWT, LLM, domain, TLS cert path, BH, AWS, SIEM, Slack/Jira, OIDC

**`.gitignore`:** `.env.prod` added

---

## P8-4 — SSO / OIDC ✅ (session 25)

### Deliverables

**`backend/core/oidc.py` (new):**
```python
async def _discovery() -> dict  # fetches {issuer}/.well-known/openid-configuration
def build_authorization_url(state: str) -> str  # constructs redirect URL
async def exchange_code(code: str) -> dict  # POST to token_endpoint
async def fetch_userinfo(access_token: str) -> dict  # GET userinfo_endpoint
```

**`backend/core/config.py`:**
```python
oidc_enabled: bool = False
oidc_issuer: str = "https://accounts.google.com"
oidc_client_id: str = ""
oidc_client_secret: str = ""
oidc_redirect_uri: str = "http://localhost:8000/auth/oidc/callback"
```

**`backend/api/v1/auth.py` — 2 new endpoints:**

`GET /auth/oidc/login`:
- Returns 404 if `oidc_enabled=false`
- Generates `state = secrets.token_urlsafe(16)`, stores in httpOnly cookie (5 min TTL)
- Redirects to Google authorization URL

`GET /auth/oidc/callback?code=...&state=...`:
- Validates state cookie (CSRF protection)
- Exchanges code → access token → userinfo
- Finds existing user by email OR provisions new user (new org named after email domain; role=admin; empty password_hash — local login blocked)
- Issues JWT → `RedirectResponse` to `{FRONTEND_URL}/auth/callback?token={jwt}`

**`frontend/app/(auth)/callback/page.tsx` (new):**
- Reads `?token=` from URL → `localStorage.setItem("access_token", token)` → `router.replace("/dashboard")`
- On missing token → `router.replace("/login?error=sso_failed")`

**`frontend/app/(auth)/login/page.tsx`:**
- "Sign in with Google" button rendered only when `NEXT_PUBLIC_OIDC_ENABLED === "true"`
- Inline Google SVG logo, links directly to `GET /auth/oidc/login`
- Divider between email/password form and SSO button

**`.env.prod.example`:** OIDC section added

**Verified:** syntax OK all backend files, tsc zero errors

---

## Files Changed (Full Phase 8)

**Backend:**
- `core/deps.py` (P8-1: require_roles factory)
- `api/v1/targets.py` (P8-1: RBAC guards)
- `api/v1/agent_scans.py` (P8-1: RBAC guards)
- `api/v1/findings.py` (P8-1: RBAC guards)
- `api/v1/integrations.py` (P8-1: RBAC guards)
- `api/v1/schedules.py` (P8-1: RBAC guards)
- `api/v1/users.py` (P8-1: new — admin user management)
- `api/v1/auth.py` (P8-1: GET /auth/me; P8-4: OIDC login + callback)
- `api/v1/compliance.py` (P8-2: new — compliance PDF)
- `core/compliance.py` (P8-2: new — framework mapping)
- `core/config.py` (P8-4: OIDC fields)
- `core/oidc.py` (P8-4: new — OIDC client)
- `main.py` (P8-1/P8-2: routers registered)
- `Dockerfile` (P8-3: new)

**Frontend:**
- `contexts/UserContext.tsx` (P8-1: new)
- `app/(dashboard)/layout.tsx` (P8-1: UserProvider, role-aware nav)
- `app/(dashboard)/users/page.tsx` (P8-1: new)
- `app/(dashboard)/agent-scans/page.tsx` (P8-1: viewer gating; P8-2: compliance buttons)
- `app/(dashboard)/schedules/page.tsx` (P8-1: viewer gating)
- `lib/api.ts` (P8-1: user management functions)
- `app/(auth)/login/page.tsx` (P8-4: Google SSO button)
- `app/(auth)/callback/page.tsx` (P8-4: new — OIDC token handler)
- `Dockerfile` (P8-3: new)
- `next.config.ts` (P8-3: standalone output)

**Infra:**
- `infra/docker/docker-compose.prod.yml` (P8-3: new)
- `infra/nginx/nginx.conf` (P8-3: new)
- `.env.prod.example` (P8-3/P8-4: new)
- `.gitignore` (P8-3: .env.prod added)

---

## Files Changed (Phase 8 so far)

**Backend:**
- `core/deps.py` (require_roles factory)
- `api/v1/targets.py` (RBAC guards)
- `api/v1/agent_scans.py` (RBAC guards)
- `api/v1/findings.py` (RBAC guards)
- `api/v1/integrations.py` (RBAC guards)
- `api/v1/schedules.py` (RBAC guards)
- `api/v1/users.py` (new — user management)
- `api/v1/auth.py` (GET /auth/me)
- `api/v1/compliance.py` (new — compliance PDF)
- `core/compliance.py` (new — framework mapping)
- `main.py` (users + compliance routers registered)

**Frontend:**
- `contexts/UserContext.tsx` (new)
- `app/(dashboard)/layout.tsx` (UserProvider, role-aware nav)
- `app/(dashboard)/users/page.tsx` (new)
- `app/(dashboard)/agent-scans/page.tsx` (viewer gating + compliance buttons)
- `app/(dashboard)/schedules/page.tsx` (viewer gating)
- `lib/api.ts` (user management + getCurrentUser functions)
