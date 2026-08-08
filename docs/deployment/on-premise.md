# SentinelAI — On-Premise Deployment Guide

**Version:** 1.0 | **Updated:** 2026-08-08

---

## Overview

Two deployment paths:

| Path | When to use |
|------|-------------|
| **Docker Compose** | Single VM / small team / < 10 concurrent scans |
| **Kubernetes (Helm)** | HA / multi-node / production scale |

Both paths require the same prerequisites and produce the same running application.

---

## Prerequisites

### All deployments

| Tool | Min version | Install |
|------|-------------|---------|
| Docker | 24+ | https://docs.docker.com/engine/install/ |
| Docker Compose | 2.20+ | bundled with Docker Desktop |
| Git | any | system package |
| Nmap | 7.9+ | `apt install nmap` / `brew install nmap` |
| Nuclei | 3.x | https://github.com/projectdiscovery/nuclei/releases |
| Trivy | 0.50+ | https://aquasecurity.github.io/trivy/latest/getting-started/installation/ |

### Kubernetes path (additional)

| Tool | Min version |
|------|-------------|
| kubectl | 1.28+ |
| Helm | 3.14+ |
| Kubernetes cluster | 1.28+ (EKS / GKE / AKS / k3s / RKE2) |
| nginx-ingress-controller | any |
| cert-manager | 1.14+ (optional, for auto TLS) |

### Resource requirements

| Component | CPU | RAM | Disk |
|-----------|-----|-----|------|
| Postgres | 0.5 core | 512 MB | 20 GB |
| Redis | 0.2 core | 256 MB | 5 GB |
| Neo4j | 0.5 core | 1 GB | 10 GB |
| Backend (×2) | 1 core | 1 GB | — |
| Worker (×2) | 2 cores | 2 GB | — |
| Frontend (×2) | 0.5 core | 512 MB | — |
| **Total** | **~7 cores** | **~8 GB** | **35 GB** |

---

## Quick Start

```bash
git clone https://github.com/YourOrg/sentinelai-vapt.git
cd sentinelai-vapt
bash scripts/deploy.sh
```

The script asks which path (Compose or K8s), walks through secret generation, and starts all services.

---

## Path A — Docker Compose

### 1. Prepare environment file

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` — replace every `CHANGE_ME` value:

```bash
# Generate a strong JWT secret
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Required values:

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Strong password, 20+ chars |
| `REDIS_PASSWORD` | Strong password |
| `NEO4J_PASSWORD` | Strong password |
| `JWT_SECRET_KEY` | 64-char hex (use generator above) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` from console.anthropic.com |
| `DOMAIN` | Your domain, e.g. `vapt.example.com` |
| `TLS_CERT_DIR` | Path to dir containing `fullchain.pem` + `privkey.pem` |
| `NEXT_PUBLIC_API_URL` | `https://your-domain.com` |

### 2. Obtain TLS certificate

**Option A — Let's Encrypt (certbot):**
```bash
apt install certbot
certbot certonly --standalone -d vapt.example.com
# certs land at /etc/letsencrypt/live/vapt.example.com/
# set TLS_CERT_DIR=/etc/letsencrypt/live/vapt.example.com in .env.prod
```

**Option B — Existing certificate:**
```bash
mkdir -p /etc/sentinelai/certs
cp fullchain.pem /etc/sentinelai/certs/
cp privkey.pem  /etc/sentinelai/certs/
# set TLS_CERT_DIR=/etc/sentinelai/certs in .env.prod
```

### 3. Build images

```bash
docker build -t sentinelai/backend:latest ./backend
docker build -t sentinelai/frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://your-domain.com \
  ./frontend
```

### 4. Run database migrations

```bash
docker run --rm --env-file .env.prod \
  -e DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}" \
  --network host \
  sentinelai/backend:latest \
  alembic upgrade head
```

> Run migrations **after** postgres is healthy (step 5 first if postgres not running yet).

### 5. Start the stack

```bash
docker compose -f infra/docker/docker-compose.prod.yml --env-file .env.prod up -d
```

### 6. Verify

```bash
# All containers running
docker compose -f infra/docker/docker-compose.prod.yml ps

# Backend health
curl https://your-domain.com/health

# First login — register an admin account
curl -X POST https://your-domain.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"YourPassword123","org_name":"My Org"}'
```

---

## Path B — Kubernetes (Helm)

### 1. Add chart to local Helm

```bash
cd infra/helm
```

### 2. Create namespace

```bash
kubectl create namespace sentinelai
```

### 3. Create secrets file (never commit this)

```bash
cat > values.prod.yaml <<'EOF'
ingress:
  host: vapt.example.com

secrets:
  postgresPassword: "CHANGE_ME"
  redisPassword: "CHANGE_ME"
  neo4jPassword: "CHANGE_ME"
  jwtSecretKey: "CHANGE_ME_64_char_hex"
  anthropicApiKey: "sk-ant-CHANGE_ME"
  bloodhoundSecret: "CHANGE_ME"

config:
  oidcEnabled: "false"

backend:
  image:
    repository: sentinelai/backend
    tag: "1.0.0"

frontend:
  image:
    repository: sentinelai/frontend
    tag: "1.0.0"
EOF
```

### 4. Install

```bash
helm install sentinelai ./sentinelai \
  -n sentinelai \
  -f values.prod.yaml \
  --wait
```

The `migrations-job` runs automatically as a Helm post-install hook.

### 5. Verify

```bash
kubectl get pods -n sentinelai
kubectl logs -n sentinelai -l app.kubernetes.io/component=backend --tail=50
curl https://vapt.example.com/health
```

### 6. TLS — cert-manager (auto)

```bash
# Install cert-manager if not present
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF
```

The Ingress annotation `cert-manager.io/cluster-issuer: letsencrypt-prod` in `values.yaml` handles the rest.

---

## Upgrading

### Docker Compose

```bash
git pull
docker build -t sentinelai/backend:latest ./backend
docker build -t sentinelai/frontend:latest --build-arg NEXT_PUBLIC_API_URL=https://your-domain.com ./frontend

# Run migrations before restarting
docker run --rm --env-file .env.prod sentinelai/backend:latest alembic upgrade head

docker compose -f infra/docker/docker-compose.prod.yml --env-file .env.prod up -d
```

### Kubernetes

```bash
git pull
# Build + push new images to your registry
docker build -t ghcr.io/yourorg/sentinelai-backend:1.0.1 ./backend && docker push ...
docker build -t ghcr.io/yourorg/sentinelai-frontend:1.0.1 ./frontend && docker push ...

helm upgrade sentinelai ./infra/helm/sentinelai \
  -n sentinelai \
  -f values.prod.yaml \
  --set backend.image.tag=1.0.1 \
  --set frontend.image.tag=1.0.1 \
  --wait
```

Migrations run automatically via the post-upgrade hook.

---

## Backup & Restore

### PostgreSQL backup

```bash
# Docker Compose
docker exec $(docker compose -f infra/docker/docker-compose.prod.yml ps -q postgres) \
  pg_dump -U sentinel sentinelai | gzip > backup_$(date +%Y%m%d).sql.gz

# Kubernetes
kubectl exec -n sentinelai deploy/sentinelai-postgres -- \
  pg_dump -U sentinel sentinelai | gzip > backup_$(date +%Y%m%d).sql.gz
```

### PostgreSQL restore

```bash
# Docker Compose
gunzip -c backup_20260808.sql.gz | \
  docker exec -i $(docker compose -f infra/docker/docker-compose.prod.yml ps -q postgres) \
  psql -U sentinel sentinelai

# Kubernetes
gunzip -c backup_20260808.sql.gz | \
  kubectl exec -i -n sentinelai deploy/sentinelai-postgres -- psql -U sentinel sentinelai
```

### Neo4j backup

```bash
# Docker Compose
docker exec $(docker compose -f infra/docker/docker-compose.prod.yml ps -q neo4j) \
  neo4j-admin database dump neo4j --to-stdout > neo4j_$(date +%Y%m%d).dump
```

---

## Troubleshooting

### Backend not starting

```bash
# Docker
docker compose -f infra/docker/docker-compose.prod.yml logs backend

# K8s
kubectl logs -n sentinelai -l app.kubernetes.io/component=backend --tail=100
```

Common causes:
- `DATABASE_URL` wrong — verify postgres container is healthy first
- `JWT_SECRET_KEY` empty — required, no default

### Migrations failed

```bash
# Check migration history
docker run --rm --env-file .env.prod sentinelai/backend:latest alembic history
docker run --rm --env-file .env.prod sentinelai/backend:latest alembic current
```

### Celery worker not picking up tasks

```bash
docker compose -f infra/docker/docker-compose.prod.yml logs worker
# Common: REDIS_URL or CELERY_BROKER_URL has wrong password
```

### WebSocket disconnects immediately

Nginx/Ingress must pass `Upgrade` + `Connection` headers. Verify:
- Docker Compose: `nginx.conf` has `proxy_set_header Upgrade $http_upgrade;`
- K8s: Ingress annotation `nginx.ingress.kubernetes.io/configuration-snippet` is present

### Port 80/443 already in use

```bash
# Find what's using port 80
lsof -i :80
# Stop conflicting service (e.g. apache2)
systemctl stop apache2
```

---

## Environment Variable Reference

See `.env.prod.example` for the full annotated list. Required variables:

| Variable | Required | Default |
|----------|----------|---------|
| `POSTGRES_PASSWORD` | ✅ | — |
| `REDIS_PASSWORD` | ✅ | — |
| `NEO4J_PASSWORD` | ✅ | — |
| `JWT_SECRET_KEY` | ✅ | — |
| `ANTHROPIC_API_KEY` | If `LLM_PROVIDER=anthropic` | — |
| `DOMAIN` | ✅ (Compose) | — |
| `TLS_CERT_DIR` | ✅ (Compose) | — |
| `NEXT_PUBLIC_API_URL` | ✅ | — |
| `AWS_ACCESS_KEY_ID` | Cloud scans only | — |
| `OIDC_CLIENT_SECRET` | SSO only | — |
| `BLOODHOUND_SECRET` | AD scans only | — |
