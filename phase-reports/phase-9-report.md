# Phase 9 Report — On-Premise Deployment

**Date:** 2026-08-08
**Phase:** 9 — On-Premise Deployment
**Git HEAD:** 315e87b
**Status:** ✅ Complete

---

## Overview

Phase 9 makes SentinelAI deployable on customer infrastructure. Deliverables: Kubernetes Helm chart, Docker Compose deployment runbook, interactive deploy script, and demo seed data for sales/testing.

---

## What Was Built

### P9-1 — Helm Chart for Kubernetes

**Location:** `infra/helm/sentinelai/` (22 files)

```
infra/helm/sentinelai/
├── Chart.yaml          (apiVersion: v2, version: 0.1.0)
├── values.yaml         (replicas, images, resources, storage, secrets, config)
└── templates/
    ├── _helpers.tpl                    (name, labels, selectorLabels, image helpers)
    ├── configmap.yaml                  (all non-secret env vars)
    ├── secret.yaml                     (passwords + JWT with required guard)
    ├── postgres-{deployment,service,pvc}.yaml
    ├── redis-{deployment,service,pvc}.yaml
    ├── neo4j-{deployment,service,pvc}.yaml
    ├── backend-{deployment,service}.yaml
    ├── worker-deployment.yaml
    ├── beat-deployment.yaml
    ├── frontend-{deployment,service}.yaml
    ├── ingress.yaml                    (nginx, TLS, WS annotation, path routing)
    └── migrations-job.yaml             (post-install/upgrade Helm hook)
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| `required` guard on 4 secrets | `helm install` fails fast with clear message if passwords omitted |
| `sentinelai.image` helper | Optional `global.imageRegistry` prefix for ghcr.io/ECR/GCR |
| `strategy: Recreate` on stateful services | Prevents split-brain on postgres/redis/neo4j PVCs |
| `beat` replicas fixed at 1 | Celery Beat must be singleton |
| migrations-job as post-install/upgrade hook | Runs `alembic upgrade head` before app pods start; `before-hook-creation` delete policy |
| Ingress WS annotation | Passes `Upgrade`/`Connection` headers for `/agent-scans/ws/` |

**Helm lint:** `1 chart(s) linted, 0 chart(s) failed` (icon warning is cosmetic only)

**Install command:**
```bash
helm install sentinelai infra/helm/sentinelai \
  --set secrets.postgresPassword=<pw> \
  --set secrets.redisPassword=<pw> \
  --set secrets.neo4jPassword=<pw> \
  --set secrets.jwtSecretKey=<key> \
  --set config.ANTHROPIC_API_KEY=<key> \
  --set ingress.hostname=sentinelai.example.com
```

---

### P9-2 — Deployment Runbook

**`docs/deployment/on-premise.md`** covers:

| Section | Content |
|---------|---------|
| Prerequisites | Docker, Helm, kubectl, Nmap, Nuclei, Trivy minimum versions |
| Resource requirements | ~7 cores / 8 GB RAM / 35 GB disk (per-service breakdown) |
| Quick-start | `bash scripts/deploy.sh` |
| Docker Compose path | env setup, TLS (certbot + manual), image build, migrations, start, verify |
| Kubernetes path | namespace, Helm install/upgrade, cert-manager ClusterIssuer |
| Upgrade procedures | Compose + K8s paths |
| Backup/restore | `pg_dump`, `neo4j-admin database dump` |
| Troubleshooting | backend not starting, migration failures, Celery issues, WS disconnects |
| Env var reference | Required vs optional table |

---

### P9-3 — Interactive Deploy Script

**`scripts/deploy.sh`** — bash, `set -euo pipefail`

Flow:
1. Validate prerequisites (`docker`, `git`; `kubectl`+`helm` for K8s path)
2. Choose Compose vs K8s
3. Copy `.env.prod.example` → `.env.prod`; auto-generate 4 secrets via `python3 secrets` module; collect domain + Anthropic key; patch with `sed`; `chmod 600`
4. Build `sentinelai/backend:latest` + `sentinelai/frontend:latest`
5. **Compose path:** start infra → wait for postgres healthcheck → run `alembic upgrade head` in isolated container → start all services
6. **K8s path:** create namespace → build values override YAML → `helm install`/`helm upgrade --wait`

`bash -n` syntax check: OK

---

### P9-4 — Demo Seed Data

**`scripts/seed_demo.py`** — Python, psycopg2, idempotent (skips if demo org exists)

| Entity | Details |
|--------|---------|
| Org | AcmeCorp — Demo (plan=enterprise) |
| Users | `admin@acmedemo.example.com` / Demo@Admin1 (admin) |
| | `analyst@acmedemo.example.com` / Demo@Analyst1 (analyst) |
| | `viewer@acmedemo.example.com` / Demo@Viewer1 (viewer) |
| Targets | Acme Web Portal (web, criticality=0.9), Acme Corp Network (network, 0.8), Acme API Gateway (api, 0.95) |
| Scan 1 | Web — completed — 6 findings (SQLi CRIT, XSS HIGH, JWT HIGH, CORS MED, X-Frame LOW, nginx INFO/FP) |
| Scan 2 | Network — completed — 4 findings (runc CVE CRIT, Redis exposure HIGH, SSH MED, ICMP LOW) |
| Scan 3 | API — running (in-progress demo state) |
| Chains | 2: SQLi→Auth bypass→XSS, Redis exposure→runc escape |
| Schedule | 1 weekly web scan |

**Usage:**
```bash
cd backend
PYTHONPATH=. python3 ../scripts/seed_demo.py
```

**Note:** Emails use `.example.com` TLD — Pydantic `EmailStr` rejects `.local` (reserved mDNS TLD).

---

## Platform Status After Phase 9

All phases P0–P9 complete. Full E2E verified 2026-08-09:

| Feature | Verified |
|---------|---------|
| Login / Register | ✅ |
| Targets (RBAC-gated) | ✅ |
| Agent Scans + WebSocket | ✅ |
| Findings (confirm/FP/revalidate) | ✅ |
| Attack Chains + Graph | ✅ |
| Attack Path Graph (Neo4j) | ✅ |
| Compliance PDFs (SOC2/ISO27001/PCI-DSS) | ✅ |
| RBAC (viewer/analyst/admin) | ✅ |
| Schedules (create/pause/delete) | ✅ |
| Users page (admin-only) | ✅ |

**Deferred:** Multi-tenant billing (no timeline).
