# SentinelAI — System Architecture

## Overview

SentinelAI is an AI-native VAPT platform. Multi-agent orchestration drives autonomous security testing across web app, API, and network attack surfaces.

## High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 15)                     │
│  Auth · Dashboard · Target Mgmt · Scan Launcher · Report Viewer  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  REST API · JWT Auth · Scan Job API · Findings API · WS Gateway  │
└───┬─────────────────┬───────────────────┬────────────────────────┘
    │                 │                   │
    ▼                 ▼                   ▼
PostgreSQL 16      Redis 7           Celery Workers
(primary store)   (cache/queue)     (async scan jobs)
                                         │
                    ┌────────────────────┘
                    ▼
         ┌─────────────────────┐
         │   AI Agent Runtime  │
         │   (LangGraph)        │
         ├─────────────────────┤
         │  Recon Agent        │
         │  Attack Planner     │
         │  Web App Agent      │
         │  API Agent          │
         │  Network Agent      │
         │  Validation Agent   │
         │  Chain Discovery    │
         └──────┬──────────────┘
                │
     ┌──────────▼──────────┐
     │   Scanner Wrappers   │
     │  ZAP · Nuclei        │
     │  Semgrep · Nmap      │
     │  Gitleaks            │
     └─────────────────────┘
```

## Data Flow

1. User adds target → verified via domain ownership check
2. Scan job created → queued to Celery via Redis broker
3. Worker picks job → spawns LangGraph agent pipeline
4. Agents invoke scanner wrappers → results normalized
5. Findings stored in PostgreSQL → scored via SRS formula
6. Validation agent confirms PoCs → FP classifier filters noise
7. Results streamed to frontend via WebSocket
8. Report generated on demand (PDF/HTML)

## Phase 6+ Extensions

- Neo4j: attack path graph for kill chain visualization
- Weaviate: vector search over historical findings
- Cloud scanners: Prowler (AWS), ScoutSuite (GCP)
- Container: Trivy, kube-bench, kube-hunter

## Security Boundaries

- All secrets via environment variables — never in code or git
- No raw SQL string concatenation — SQLAlchemy ORM only
- JWT tokens short-lived (30 min access, 7 day refresh)
- Scanner subprocesses run in isolated Docker containers
- Target scoping enforced server-side — agents cannot scan out-of-scope IPs
