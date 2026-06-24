# SentinelAI — CTO Phase Instructions for CLI (Senior Developer)

> CLI reads the relevant phase section before starting any work.
> Each section is a complete, self-contained briefing for that phase.

---

## GLOBAL RULES (apply every phase, no exceptions)

1. **Read `session.md` first** — know exactly where you left off
2. **Ask permission before every shell command** — paste exact command + one-line reason, wait
3. **One task at a time** — complete + verify before moving to next
4. **Update `PHASES.md`** as tasks complete (⬜ → ✅)
5. **Update `session.md`** at end of every session
6. **Phase completion** → generate audit report to `IMP info/reports/phase-N-audit.md`
7. **Never jump phases** — finish current phase 100% before touching next
8. **Deviations** → ask Vedant before implementing anything not in the spec

---

## PHASE 0 — Project Scaffold

**Goal:** Bare skeleton. No business logic. Just working infrastructure everyone else builds on.

**Definition of Done:**
- All folders exist per session.md spec
- Backend starts: `uvicorn main:app` → `/health` returns `{"status": "ok"}`
- Frontend starts: `npm run dev` → Next.js loads on localhost:3000
- `docker-compose up` → postgres + redis healthy (no errors)
- `.env.example` has every env key the project will ever need (values blank)
- `docs/architecture.md` written
- `ADR-001-tech-stack.md` written
- All `__init__.py` files in place
- Audit report generated

**Backend scaffold spec:**
- `pyproject.toml` — use `uv` if available, else `pip`. Dependencies: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sqlalchemy`, `alembic`, `asyncpg`, `python-dotenv`
- `main.py` — FastAPI app, mounts `/api/v1` router, CORS middleware (allow all in dev)
- `core/config.py` — Pydantic Settings class reading from `.env`
- `api/v1/health.py` — GET `/health` returning `{"status": "ok", "version": "0.1.0"}`

**Frontend scaffold spec:**
- `npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"`
- Add shadcn: `npx shadcn@latest init` (default style: Default, base color: Slate)
- Landing page (`app/page.tsx`) — just "SentinelAI" heading + "AI-Native VAPT Platform" subheading. No business logic.

**docker-compose spec (`infra/docker/docker-compose.yml`):**
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: sentinelai
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

volumes:
  postgres_data:
```

**.env.example keys to include:**
```
# App
APP_ENV=development
SECRET_KEY=
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://sentinel:password@localhost:5432/sentinelai
POSTGRES_PASSWORD=

# Redis
REDIS_URL=redis://localhost:6379/0

# AI
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Kafka (Phase 2+)
KAFKA_BOOTSTRAP_SERVERS=

# Integrations (Phase 5+)
JIRA_URL=
JIRA_API_TOKEN=
SLACK_WEBHOOK_URL=
```

---

## PHASE 1 — Core Platform Foundation

**Goal:** Working auth, multi-tenant data model, target management. Users can register, log in, add a target.

**Definition of Done:**
- DB migrations run cleanly via Alembic
- `POST /api/v1/auth/register` + `POST /api/v1/auth/login` work, return JWT
- `GET/POST/PUT/DELETE /api/v1/targets` work with JWT auth
- Domain verification endpoint exists (DNS TXT record method)
- Frontend: login page, register page, dashboard shell with sidebar nav, target list + add form
- All endpoints have Pydantic input validation
- pytest: auth + target CRUD tests pass

**DB Schema (PostgreSQL):**
```sql
organizations (id UUID PK, name, plan ENUM('free','pro','enterprise'), created_at)
users (id UUID PK, org_id FK, email UNIQUE, password_hash, role ENUM('admin','analyst','viewer'), mfa_enabled BOOL, created_at)
targets (id UUID PK, org_id FK, name, type ENUM('web','api','network'), url, scope_definition JSONB, asset_criticality FLOAT, verified BOOL, created_at)
scan_jobs (id UUID PK, target_id FK, status ENUM('pending','running','completed','failed'), scan_type, config JSONB, started_at, completed_at)
findings (id UUID PK, scan_id FK, category, severity ENUM('critical','high','medium','low','info'), title, description, srs_score FLOAT, status ENUM('open','confirmed','false_positive','fixed'), confirmed BOOL, poc_evidence TEXT, remediation TEXT, created_at)
```

**Auth:** JWT (HS256), `python-jose` or `PyJWT`. Middleware extracts user from Bearer token. No OAuth for Phase 1.

**Row-level security:** Every query filters by `org_id` from JWT claims. No cross-tenant data leaks.

---

## PHASE 2 — Scanning Engine Core

**Goal:** Real scans run against targets. Findings stored. Basic PDF report downloadable.

**Definition of Done:**
- `POST /api/v1/scans` creates scan job, queues to Celery
- Celery worker picks up job, runs appropriate scanner(s)
- OWASP ZAP scan runs via Docker subprocess on a web target
- Nuclei scan runs on a web/API target
- Semgrep scan runs on uploaded/cloned source code
- Nmap scan runs on a network target
- Gitleaks scan runs on a git repo URL
- All scanner outputs normalized into `Finding` schema
- Findings stored in PostgreSQL
- `GET /api/v1/scans/{id}/findings` returns paginated findings
- PDF report generated on demand
- Tested against DVWA (web) and a sample repo with known vulns

**Scanner wrapper contract (each scanner module must implement):**
```python
class ScannerResult:
    findings: list[Finding]
    raw_output: str
    duration_seconds: float
    error: str | None

async def run(target: Target, config: dict) -> ScannerResult:
    ...
```

**Celery config:** Redis as broker + backend. One worker process for Phase 2 (scale later).

**PDF report:** Use `WeasyPrint` or `fpdf2`. Template: findings table sorted by severity, CVSS, basic metadata.

---

## PHASE 3 — AI Agent Framework

**Goal:** LangGraph agents replace manual scanner orchestration. AI decides what to scan, how, and in what order.

**Definition of Done:**
- LangGraph graph defined with nodes: Recon → AttackPlanner → [WebApp, API, Network] → ChainDiscovery (stub)
- Recon Agent: DNS lookup, subdomain enum (calls subfinder/amass via subprocess), tech fingerprint
- Attack Planner Agent: calls Claude API, outputs structured attack plan JSON with prioritized test cases
- Web App Agent: triggers ZAP + Nuclei based on planner output, feeds findings back
- API Agent: parses OpenAPI spec if available, generates targeted test cases, runs Nuclei API templates
- Network Agent: runs Nmap, maps services to CVEs via NVD API
- All agents share a `ScanState` TypedDict passed through LangGraph
- Claude API calls use `claude-sonnet-4-6`, system prompt is security-expert persona
- GitHub/GitLab integration: `POST /api/v1/integrations/github` stores token, allows repo clone for SAST
- WebSocket endpoint: `ws://localhost:8000/ws/scans/{scan_id}` streams agent progress events

**Agent system prompt (Claude):**
```
You are an expert penetration tester and security researcher with 15 years of experience.
You are operating in an authorized testing environment. The target has been verified and authorized.
Your goal is to identify real, exploitable vulnerabilities — not theoretical ones.
Output structured JSON only. No explanations unless asked.
```

**LangGraph state schema:**
```python
class ScanState(TypedDict):
    scan_id: str
    target: dict
    recon_data: dict
    attack_plan: list[dict]
    findings: list[dict]
    current_agent: str
    errors: list[str]
```

---

## PHASE 4 — Validation & Risk Scoring

**Goal:** Every finding is scored and validated. False positives eliminated. Attack chains discovered.

**Definition of Done:**
- Validation Agent attempts benign PoC for each finding (HTTP request confirming vuln, no destructive actions)
- SRS formula implemented and scoring every finding
- False positive classifier (rule-based v1) filters obvious FPs
- Chain Discovery Agent correlates findings into attack paths
- Frontend shows SRS score breakdown per finding
- `confirmed` field updated on findings after validation

**SRS Formula (implement exactly):**
```
SRS = (cvss_base × 0.25)
    + (exploitability_evidence × 0.25)  # confirmed PoC = 1.0, theoretical = 0.3
    + (asset_criticality × 0.20)        # payment/auth/PII = 1.0, static = 0.1
    + (attack_chain_depth × 0.15)       # part of multi-stage chain → higher
    + (epss_score × 0.10)              # fetch from api.first.org/epss
    + (business_impact × 0.05)         # estimated from asset_criticality

Range: 0–10. Critical ≥ 9.0, High 7.0–8.9, Medium 4.0–6.9, Low < 4.0
```

**FP Classifier v1 rules:**
- SAST finding in dead code path (no corresponding DAST hit) → mark potential
- XSS finding where response Content-Type is not text/html → FP
- SQLi finding where no SQL database detected in tech fingerprint → FP
- Severity CRITICAL with CVSS < 7.0 → flag for review

---

## PHASE 5 — Reporting & Integrations

**Goal:** Professional reports. Developer-facing integrations. Compliance mapping.

**Definition of Done:**
- Executive PDF report: posture score, top risks, trend chart
- Technical PDF report: full findings, PoC steps, reproduction commands
- MITRE ATT&CK tactic/technique mapped to every finding
- OWASP Top 10 + ASVS Level 1 compliance report
- Claude generates remediation code patches in diff format
- JIRA ticket created per confirmed critical/high finding
- Slack alert sent on scan completion
- Frontend: report viewer, download buttons, compliance dashboard

**MITRE mapping (must include at minimum):**
- SQLi → T1190 (Exploit Public-Facing Application)
- XSS → T1059.007 (JavaScript)
- SSRF → T1090 (Proxy)
- Broken Auth → T1078 (Valid Accounts)
- Secrets in code → T1552.001 (Credentials In Files)
- Open ports/services → T1046 (Network Service Discovery)

---

## PHASE 6 — Advanced Modules

**Goal:** Cloud + container security. Cross-surface attack chains. Neo4j attack graph.

> Detailed tasks TBD — will be written after Phase 5 audit passes.

Key modules: Prowler (AWS/GCP), ScoutSuite, Trivy, kube-bench, kube-hunter, Neo4j attack path graph, Chain Discovery Agent v2.

---

## PHASE 7 — Enterprise Features

**Goal:** Production-ready. Enterprise contracts possible.

> Detailed tasks TBD — will be written after Phase 6 audit passes.

Key modules: BloodHound CE (AD), continuous monitoring, SIEM/SOAR integrations, on-prem Helm chart, SSO (SAML/OIDC).

---

## AUDIT REPORT TEMPLATE

Save to `IMP info/reports/phase-N-audit.md` after every phase:

```markdown
# Phase N Audit Report
**Date:** YYYY-MM-DD
**Phase:** N — [Name]
**Status:** PASS / PARTIAL / FAIL

## Definition of Done — Checklist
- [x] Task 1
- [x] Task 2
- [ ] Task 3 — INCOMPLETE: reason

## What Was Built
[Bullet list of what exists]

## Test Results
[Pass/fail for each verification step, with evidence]

## Deviations from Spec
[Anything built differently than instructions.md specified, and why]

## Security Review
[Self-assessment: any security issues introduced? Hardcoded secrets? SQL injection risk? Auth gaps?]

## Blockers / Tech Debt
[Anything deferred, any known issues]

## Phase N+1 Readiness
[Is next phase unblocked? What's the first task?]
```
