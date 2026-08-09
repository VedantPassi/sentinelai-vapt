# SentinelAI — AI-Native VAPT Platform

An autonomous vulnerability assessment and penetration testing platform powered by multi-agent AI. SentinelAI scans web apps, APIs, networks, containers, cloud environments, and Active Directory — then reasons about findings, chains attack paths, and generates compliance reports.

---

## Features

| Capability | Details |
|------------|---------|
| **Multi-surface scanning** | Web app, API, network (Nmap), container (Trivy), cloud (Prowler/AWS), Active Directory (BloodHound CE) |
| **AI agent pipeline** | LangGraph: recon → planner → scanner → validator → chain discovery → Neo4j graph |
| **Attack chain discovery** | Cross-surface kill chains with MITRE ATT&CK stage mapping |
| **Attack path graph** | Neo4j-backed graph with blast radius analysis; Cytoscape.js visualization |
| **Finding validation** | LLM validation + deterministic false-positive classifier; SRS risk scoring (0–100) |
| **Compliance PDFs** | SOC 2 TSC / ISO 27001:2022 / PCI-DSS v4 — one-click export |
| **RBAC** | Admin / Analyst / Viewer roles enforced on every API endpoint |
| **Continuous monitoring** | Celery Beat schedules recurring scans at configurable intervals |
| **SSO / OIDC** | Generic OIDC support (Google tested); auto-provisions users |
| **SIEM integration** | Splunk HEC + Elasticsearch bulk forwarding |
| **Jira + Slack** | One-click finding export to Jira issues and Slack messages |
| **SARIF export** | SARIF 2.1.0 JSON for integration with GitHub Code Scanning and IDE plugins |
| **Production-ready** | Docker Compose + Kubernetes Helm chart; Nginx TLS termination; rate limiting |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| AI / Agents | LangGraph, Anthropic Claude API |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Cytoscape.js |
| Primary DB | PostgreSQL 16 |
| Cache / Queue | Redis 7 + Celery |
| Graph DB | Neo4j 5 (APOC) |
| Scanning | Nmap, Nuclei, Trivy, Prowler, BloodHound CE |
| Infra | Docker Compose (dev) · Helm chart (prod K8s) · Nginx |

---

## Quick Start (Development)

### Prerequisites

- Docker + Docker Compose
- Python 3.12 + Node.js 20
- [Nmap](https://nmap.org/), [Nuclei](https://github.com/projectdiscovery/nuclei), [Trivy](https://github.com/aquasecurity/trivy)
- Anthropic API key **or** local [Ollama](https://ollama.com/) instance

### 1. Clone and configure

```bash
git clone https://github.com/VedantPassi/sentinelai-vapt.git
cd sentinelai-vapt
cp .env.example .env   # edit with your values
```

Minimum `.env` values:

```env
DATABASE_URL=postgresql+asyncpg://sentinel:sentineldev@localhost:5432/sentinelai
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=sentinelneo4j
JWT_SECRET_KEY=change-me-in-production
LLM_PROVIDER=anthropic          # or: ollama
ANTHROPIC_API_KEY=sk-ant-...    # skip if using Ollama
```

### 2. Start infrastructure

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

### 3. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

Start Celery worker (separate terminal):

```bash
cd backend
PATH="/opt/homebrew/bin:$PATH" PYTHONPATH=$(pwd) \
  .venv/bin/celery -A workers.agent_worker.celery_app worker \
  --loglevel=info --concurrency=1
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 5. Seed demo data (optional)

```bash
cd backend
PYTHONPATH=. python3 ../scripts/seed_demo.py
```

Demo credentials after seeding:

| Email | Password | Role |
|-------|----------|------|
| `admin@acmedemo.example.com` | `Demo@Admin1` | Admin |
| `analyst@acmedemo.example.com` | `Demo@Analyst1` | Analyst |
| `viewer@acmedemo.example.com` | `Demo@Viewer1` | Viewer |

---

## Production Deployment

### Docker Compose

```bash
bash scripts/deploy.sh   # interactive: Compose or K8s
```

Or manually:

```bash
cp .env.prod.example .env.prod   # fill in all values
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

### Kubernetes (Helm)

```bash
helm install sentinelai infra/helm/sentinelai \
  --set secrets.postgresPassword=<pw> \
  --set secrets.redisPassword=<pw> \
  --set secrets.neo4jPassword=<pw> \
  --set secrets.jwtSecretKey=<key> \
  --set config.ANTHROPIC_API_KEY=<key> \
  --set ingress.hostname=sentinelai.yourdomain.com
```

Full runbook: [`docs/deployment/on-premise.md`](docs/deployment/on-premise.md)

---

## Agent Pipeline

```
recon → planner → [webapp | network | container | cloud | bloodhound]
      → validator → chain → graph → END
```

Each node is a LangGraph agent node. The planner routes to the appropriate scanner based on `target_type`. All nodes skip gracefully if prerequisites aren't met.

---

## RBAC

| Action | Viewer | Analyst | Admin |
|--------|--------|---------|-------|
| View targets, scans, findings | ✅ | ✅ | ✅ |
| Create targets / launch scans | ✗ | ✅ | ✅ |
| Edit findings / manage schedules | ✗ | ✅ | ✅ |
| Delete targets / schedules | ✗ | ✗ | ✅ |
| Manage users | ✗ | ✗ | ✅ |

---

## Project Structure

```
├── backend/
│   ├── agents/          # LangGraph agent nodes
│   ├── api/v1/          # FastAPI routers
│   ├── core/            # DB, config, security, OIDC, compliance, SIEM
│   ├── models/          # SQLAlchemy models + Alembic migrations
│   ├── scanners/        # Nmap, Nuclei, Trivy, Prowler wrappers
│   ├── scoring/         # SRS formula + FP classifier
│   └── workers/         # Celery agent + beat + SIEM workers
├── frontend/
│   ├── app/(auth)/      # Login, register, OIDC callback
│   ├── app/(dashboard)/ # Targets, scans, findings, chains, schedules, users
│   ├── components/      # ChainGraph, AttackGraphView
│   └── lib/api.ts       # Typed API client
├── infra/
│   ├── docker/          # docker-compose.yml (dev) + docker-compose.prod.yml
│   ├── helm/sentinelai/ # Kubernetes Helm chart (22 templates)
│   └── nginx/           # nginx.conf (TLS, rate limiting, WS proxy)
├── scripts/
│   ├── deploy.sh        # Interactive deployment script
│   └── seed_demo.py     # Demo org seed data
├── docs/deployment/     # On-premise runbook
└── phase-reports/       # Per-phase build reports (P0–P9)
```

---

## Environment Variables

See [`.env.prod.example`](.env.prod.example) for the full list with descriptions.

Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `REDIS_URL` | Redis URL |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j connection |
| `JWT_SECRET_KEY` | HS256 signing key (min 32 chars) |
| `LLM_PROVIDER` | `anthropic` or `ollama` |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `OIDC_ENABLED` | `true` to enable SSO |
| `SIEM_ENABLED` | `true` to forward findings to Splunk/Elasticsearch |

---

## License

Private — all rights reserved.
