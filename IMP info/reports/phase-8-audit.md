# Phase 8 Audit Report — Polish & Hardening

**Date:** 2026-08-07
**Git HEAD:** 1d7e5d2
**Status:** IN PROGRESS 🔵 (P8-1 ✅ P8-2 ✅ P8-3 ⬜ P8-4 ⬜)

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

## P8-3 — Production Docker Stack ⬜ (next)

Planned:
- `infra/docker/docker-compose.prod.yml` — Nginx, TLS termination, all services
- `infra/nginx/nginx.conf` — reverse proxy backend + frontend, SSL config
- `.env.prod.example` — documented production env vars
- Health checks on all services
- Secrets via Docker secrets or env file (not baked into image)

---

## P8-4 — SSO / OIDC ⬜ (planned)

Planned:
- `python-jose` + `httpx` OIDC flow (Google / Azure AD)
- `POST /auth/oidc/callback` — exchange code for user, create/link org account
- `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` in `.env`
- Frontend: "Sign in with Google" button on login page

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
