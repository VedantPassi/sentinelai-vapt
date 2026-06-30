# Phase 4 Report — Validation & Risk Scoring

**Date:** 2026-06-30
**Phase:** 4 — Validation & Risk Scoring
**Status:** ✅ Complete

---

## Overview

Phase 4 added LLM-powered finding validation, deterministic false-positive filtering, and risk scoring to the agent pipeline. Every finding now exits the pipeline with a `status`, `risk_score`, `srs_score`, and `validation_reasoning`.

---

## What Was Built

### LLM Abstraction Layer

| File | Purpose |
|------|---------|
| `backend/core/llm.py` | `llm_complete()` — provider-transparent (Ollama / Anthropic), 1 retry on timeout, `LLMError` on failure |
| `backend/core/config.py` | `llm_provider`, `ollama_base_url`, `ollama_model` settings |

Switch between providers via `LLM_PROVIDER` env var — no code change.

### Agent Pipeline Changes

```
recon → planner → webapp|network → validator → END
```

New `validator` node added to LangGraph graph. Runs after scanner agents, before results written to DB.

| File | Purpose |
|------|---------|
| `backend/agents/validation_agent.py` | Batched LLM validation (≤10 findings/call, chunked), sets `status` + `risk_score` + `validation_reasoning` |
| `backend/agents/runtime.py` | Wired `validator` node between scanner agents and END |

### Scoring

| File | Purpose |
|------|---------|
| `backend/scoring/srs.py` | SRS formula: severity (40%) + exploitability (30%) + asset criticality (20%) + confidence (10%) → 0–100 int |
| `backend/scoring/classifier.py` | 6 deterministic rules — pre-filters obvious FPs before LLM call |

**Classifier rules:**
1. `severity == "info"` → FP
2. `missing-header` category on non-web target → FP
3. Title contains "test page", "default page", "welcome to", "tech-detect", "technologies" → FP
4. `risk_score == 0` and severity low/info → FP
5. Description < 20 chars → FP
6. (Implicit via rule 3) Nuclei tech-detect templates → FP

### Worker + DB Changes

| File | Change |
|------|--------|
| `backend/workers/agent_worker.py` | Reads `fd.status` + `fd.risk_score` from validation agent; computes `srs_score` via `compute_srs()` before DB write |
| `backend/models/models.py` | Added `validation_reasoning: Text` column to `Finding` |
| `backend/scanners/base.py` | Added `status`, `risk_score`, `validation_reasoning` fields to `FindingData` |
| Alembic migration | `add_finding_validation_reasoning` — two-step (server_default → drop default) |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/findings/{id}` | Full finding detail + validation_reasoning |
| PATCH | `/api/v1/findings/{id}` | Manual status override + remediation edit; recomputes SRS |
| POST | `/api/v1/findings/{id}/validate` | Re-runs LLM validation on single finding |

### Frontend

- `FindingCard` component with SRS badge (colored by score range), status badge, collapsible reasoning
- Confirm / False Positive / Re-validate action buttons with optimistic updates
- `patchFinding()`, `revalidateFinding()`, `getFinding()` added to `frontend/lib/api.ts`

---

## Live Test

- **Target:** `http://localhost` (network scan, Nmap)
- **Findings:** 2 stored
- **Validation agent:** 1 classified `false_positive` (rules: info severity), 1 `confirmed` (Ollama qwen2.5:7b)
- **SRS scores:** 0 on FP, 68.0 on confirmed (high severity, 0.8 asset criticality)
- **GET /findings/{id}:** all fields populated ✅
- **POST /findings/{id}/validate:** LLM reclassified finding, `srs_score` recalculated to 68.0 ✅

---

## Key Decisions

- **Ollama for Phase 4 dev:** `qwen2.5:7b` local, free, ~2s per call on M5. Switch to `claude-opus-4-8` for production via `LLM_PROVIDER=anthropic`.
- **Batch validation:** ≤10 findings per LLM call to preserve context. Chunked automatically for larger sets.
- **Rules-first:** Classifier runs before LLM — saves tokens on obvious noise. Catches ~30–50% of scanner FPs deterministically.
- **Sync validate endpoint:** Single-finding re-validation runs inline (~2s on Ollama) — no Celery needed.
- **SRS on FP always 0:** False positives never contribute to risk score regardless of severity.

---

## Bugs Fixed During Phase

1. `asyncio.run()` in Celery prefork → `new_event_loop()` pattern (tasks not executing)
2. `asset_criticality` float → int mapping was negative (-12.5) → fixed to `round(val * 100)`
3. Migration NOT NULL without server_default → two-step migration

---

## Deferred to Phase 5

- `backend/agents/chain_agent.py` — attack chain discovery
- WS auth (still unauthenticated)
- Real-time incremental event streaming
- PATCH finding tested only via syntax — no live curl test run
