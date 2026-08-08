# Phase 9 Audit Report — On-Premise Deployment

**Date:** 2026-08-08
**Git HEAD:** 315e87b
**Status:** COMPLETE ✅ (P9-1 ✅ P9-2 ✅ P9-3 ✅ P9-4 ✅)

---

## Summary

Phase 9 makes SentinelAI deployable by customers on their own infrastructure. Deliverables: Helm chart for Kubernetes, Docker Compose runbook, interactive deploy script, and demo seed data.

---

## P9-1 — Helm Chart ✅ (7093c32)

### Structure

```
infra/helm/sentinelai/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── _helpers.tpl
    ├── configmap.yaml
    ├── secret.yaml
    ├── postgres-{deployment,service,pvc}.yaml
    ├── redis-{deployment,service,pvc}.yaml
    ├── neo4j-{deployment,service,pvc}.yaml
    ├── backend-{deployment,service}.yaml
    ├── worker-deployment.yaml
    ├── beat-deployment.yaml
    ├── frontend-{deployment,service}.yaml
    ├── ingress.yaml
    └── migrations-job.yaml
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| `required` guard on 4 secrets | `helm install` fails fast with clear message if passwords omitted |
| `sentinelai.image` helper | Optional `global.imageRegistry` prefix for ghcr.io/ECR/GCR |
| `strategy: Recreate` on stateful services | Prevents split-brain on postgres/redis/neo4j PVCs |
| `beat` replicas fixed at 1 | Celery Beat must be singleton — Recreate strategy |
| migrations-job as post-install/upgrade hook | Runs `alembic upgrade head` before app pods start; `before-hook-creation` delete policy for clean upgrades |
| Ingress WS annotation | `nginx.ingress.kubernetes.io/configuration-snippet` passes Upgrade/Connection headers for `/agent-scans/ws/` |

### Helm lint result
```
==> Linting infra/helm/sentinelai
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
```
Pass (icon cosmetic only).

---

## P9-2 — Deployment Runbook ✅ (9837645)

**`docs/deployment/on-premise.md`** covers:

- Prerequisites table — Docker, Helm, kubectl, Nmap, Nuclei, Trivy with min versions
- Resource requirements table (CPU/RAM/disk per service, total ~7 cores / 8 GB / 35 GB)
- Quick-start (`bash scripts/deploy.sh`)
- **Docker Compose path:** env setup, TLS (certbot + manual), image build, migrations, start, verify
- **Kubernetes path:** namespace, Helm install, cert-manager ClusterIssuer for auto TLS
- Upgrade procedures for both paths
- Backup/restore: `pg_dump` (Compose + K8s), `neo4j-admin database dump`
- Troubleshooting: backend not starting, migration failures, Celery not consuming, WS disconnects, port conflicts
- Environment variable reference table (required vs optional)

---

## P9-3 — Deploy Script ✅ (9837645)

**`scripts/deploy.sh`** — bash, `set -euo pipefail`

Flow:
1. Check prerequisites (`docker`, `git`; `kubectl` + `helm` for K8s path)
2. Choose Compose vs K8s
3. Generate `.env.prod` from `.env.prod.example`; auto-generate secrets via `python3 secrets` module; collect domain + Anthropic key; patch with sed; `chmod 600`
4. Build `sentinelai/backend:latest` and `sentinelai/frontend:latest`
5. **Compose path:** start infra → wait for postgres healthcheck → run migrations in isolated container → start all services → print URL + register command
6. **K8s path:** create namespace → build values override YAML from `.env.prod` → `helm install` or `helm upgrade --wait`

`bash -n` syntax check: **OK**

---

## P9-4 — Demo Seed Data ✅ (8eff21b)

**`scripts/seed_demo.py`** — Python, psycopg2, idempotent

| Entity | Details |
|--------|---------|
| Org | AcmeCorp — Demo (plan=enterprise) |
| Users | admin@acme-demo.local / Demo@Admin1 (admin) |
| | analyst@acme-demo.local / Demo@Analyst1 (analyst) |
| | viewer@acme-demo.local / Demo@Viewer1 (viewer) |
| Targets | Acme Web Portal (web, criticality=0.9), Acme Corp Network (network, 0.8), Acme API Gateway (api, 0.95) |
| Scan 1 | Web scan — completed — 6 findings |
| Scan 2 | Network scan — completed — 4 findings |
| Scan 3 | API scan — running (in-progress state) |
| Chains | 2 (SQLi→XSS chain, Redis→runc escape chain) |
| Schedule | Weekly web scan |

Finding distribution:
| Severity | Count | Status |
|----------|-------|--------|
| critical | 2 | confirmed |
| high | 3 | confirmed |
| medium | 2 | open |
| low | 2 | open |
| info | 1 | false_positive |

Usage:
```bash
cd backend
PYTHONPATH=. python3 ../scripts/seed_demo.py
```

---

## Files Changed

| File | Type |
|------|------|
| `infra/helm/sentinelai/Chart.yaml` | new |
| `infra/helm/sentinelai/values.yaml` | new |
| `infra/helm/sentinelai/templates/_helpers.tpl` | new |
| `infra/helm/sentinelai/templates/configmap.yaml` | new |
| `infra/helm/sentinelai/templates/secret.yaml` | new |
| `infra/helm/sentinelai/templates/postgres-*.yaml` (×3) | new |
| `infra/helm/sentinelai/templates/redis-*.yaml` (×3) | new |
| `infra/helm/sentinelai/templates/neo4j-*.yaml` (×3) | new |
| `infra/helm/sentinelai/templates/backend-*.yaml` (×2) | new |
| `infra/helm/sentinelai/templates/worker-deployment.yaml` | new |
| `infra/helm/sentinelai/templates/beat-deployment.yaml` | new |
| `infra/helm/sentinelai/templates/frontend-*.yaml` (×2) | new |
| `infra/helm/sentinelai/templates/ingress.yaml` | new |
| `infra/helm/sentinelai/templates/migrations-job.yaml` | new |
| `docs/deployment/on-premise.md` | new |
| `scripts/deploy.sh` | new |
| `scripts/seed_demo.py` | new |
| `PHASES.md` | updated (P9 items ✅, stale P2 markers fixed) |
