# ADR-001: Technology Stack Selection

**Status:** Accepted  
**Date:** 2026-06-24

## Context

SentinelAI needs a stack that supports: async API serving, multi-agent AI orchestration, heavy subprocess invocation (scanners), real-time frontend updates, and a clear path to enterprise scale.

## Decisions

### Backend — Python 3.12 + FastAPI

**Rationale:** Python dominates the security tooling ecosystem (all major scanners have Python SDKs or are written in Python). FastAPI provides async-native request handling, auto-generated OpenAPI docs, and Pydantic v2 validation at minimal overhead. SQLAlchemy 2.x async + Alembic gives type-safe ORM with controlled migrations.

### AI / Agents — LangGraph + Anthropic Claude API

**Rationale:** LangGraph's stateful graph model maps directly to multi-agent pipelines with conditional branching (e.g., recon → attack planning → execution → validation). Claude API (`claude-sonnet-4-6` default, `claude-opus-4-8` for reasoning-heavy tasks) provides strong instruction-following for structured security analysis output.

### Frontend — Next.js 15 (App Router) + shadcn/ui

**Rationale:** App Router enables server components for fast initial loads. shadcn/ui gives composable, accessible primitives without a heavyweight component library. Cytoscape.js handles attack path graph visualization (Phase 6).

### Databases — PostgreSQL 16 + Redis 7

**Rationale:** PostgreSQL handles relational data (users, orgs, targets, findings) with full ACID guarantees. Redis serves dual purpose: Celery broker for scan job queuing and application-level caching.

### Queue — Celery (Phase 0–5) → Kafka (Phase 6+)

**Rationale:** Celery over Redis is sufficient for early phases and avoids Kafka operational overhead. Kafka added in Phase 6 when event streaming between microservices justifies the complexity.

### Containers — Docker + docker-compose (dev)

**Rationale:** Reproducible local dev environment. All external dependencies (postgres, redis, scanners) containerized so engineers don't install them natively.

## Rejected Alternatives

| Alternative | Reason rejected |
|-------------|----------------|
| Node.js backend | Weaker security tool ecosystem; async scanner subprocess handling less natural |
| Django | Heavier framework than needed; FastAPI async model fits scan job patterns better |
| OpenAI GPT-4 | Claude's instruction-following and structured output quality preferred for security analysis |
| AutoGen / CrewAI | LangGraph gives finer control over agent state machines needed for VAPT pipelines |
| MongoDB | Relational data model (findings → targets → orgs) fits PostgreSQL; ACID needed |
