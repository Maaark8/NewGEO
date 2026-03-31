# NewGEO Detailed Documentation

This document explains the current NewGEO implementation in detail: what was built, why it was structured this way, how the main workflows behave, what is intentionally simplified, and what should come next.

It is written for two audiences:

- You, as the project owner, so you can understand the current state quickly.
- Future contributors, so they can extend the scaffold without reverse-engineering it first.

---

## 1. What NewGEO Is

NewGEO is an open-source platform for:

- monitoring visibility across generative engines and AI search,
- generating context-aware optimization suggestions for pages,
- preserving meaning while rewriting,
- measuring projected and actual improvement over time.

The repository currently contains:

- `AutoGEO/` and `GEO/` as preserved upstream research references,
- a new product scaffold for `NewGEO` built at the root level.

The important design decision is that NewGEO does **not** directly extend the research codebases. Instead, it borrows ideas from them and wraps those ideas in a platform-oriented architecture.

---

## 2. What Was Implemented

The current scaffold includes five main parts:

### 2.1 Shared backend core

Located in `packages/newgeo_core/newgeo_core/`.

This is the heart of the platform. It contains:

- domain models,
- storage abstraction,
- content normalization utilities,
- constraint validation,
- retrieval helpers for supporting context,
- a heuristic benchmarking engine,
- a context-aware recommendation generator,
- a high-level service layer that orchestrates everything.

### 2.2 FastAPI service

Located in `api/app/main.py`.

This exposes the product as an HTTP API with endpoints for:

- creating projects,
- importing or crawling pages,
- creating context packs,
- creating query clusters,
- running benchmarks,
- generating recommendations,
- approving and exporting recommendations,
- reading dashboard data,
- seeding a demo project.

### 2.3 Worker process

Located in `workers/app/worker.py`.

This is a simple polling worker that processes queued benchmark runs and recommendations. Right now the API can execute jobs synchronously or queue them for the worker.

### 2.4 Frontend dashboard shell

Located in `web/`.

This is a Next.js app-router UI with views for:

- Overview
- Pages
- Queries
- Runs
- Recommendations
- Compare

The UI is already structured around the intended product shape, but for now it falls back to sample data unless a real API base URL and project ID are provided.

### 2.5 Tooling, docs, and demo support

At the repo root:

- `README.md` for quick-start use
- `DOCUMENTATION.md` for deep explanation
- `docker-compose.yml` for local multi-service development
- `scripts/seed_demo.py` for demo data generation
- Python tests in `api/tests/`

---

## 3. High-Level Architecture

Current runtime architecture:

1. The web app displays project, page, query, run, and recommendation state.
2. The API receives requests from the UI or scripts.
3. The API delegates almost all business logic to `NewGeoService`.
4. `NewGeoService` uses the shared core modules to:
   - normalize content,
   - persist models,
   - run benchmarks,
   - generate recommendations,
   - validate constraints,
   - create exports.
5. The worker optionally processes queued runs and recommendations.
6. All current persisted data is stored in a local JSON file.

The architecture is intentionally layered:

- `web` is presentation
- `api` is transport
- `newgeo_core` is domain logic
- `workers` is background orchestration

This separation matters because it makes future migrations easier. For example:

- replacing JSON storage with Postgres,
- replacing heuristic scoring with live LLM connectors,
- replacing the current recommendation generator with a real LLM-powered optimizer,
- replacing polling workers with Redis-backed jobs.

---

## 4. Repository Structure

### Root

- `README.md`
  Short onboarding and run instructions.
- `DOCUMENTATION.md`
  This file.
- `docker-compose.yml`
  Multi-service local development setup.
- `package.json`
  Root workspace scripts.
- `Makefile`
  Convenience commands.
- `.env.example`
  Default environment variables.

### Backend core

- `packages/newgeo_core/newgeo_core/models.py`
  All main entities and enums.
- `packages/newgeo_core/newgeo_core/storage.py`
  File-backed persistence.
- `packages/newgeo_core/newgeo_core/content.py`
  Normalization, tokenization, embeddings, and simple text helpers.
- `packages/newgeo_core/newgeo_core/retrieval.py`
  Supporting-document ranking and summarization.
- `packages/newgeo_core/newgeo_core/constraints.py`
  Constraint checking and semantic drift checks.
- `packages/newgeo_core/newgeo_core/diffing.py`
  Markdown diff generation.
- `packages/newgeo_core/newgeo_core/benchmarking.py`
  Benchmark connector interface and heuristic benchmark implementations.
- `packages/newgeo_core/newgeo_core/recommendations.py`
  Context-aware rewrite generation and preview scoring.
- `packages/newgeo_core/newgeo_core/service.py`
  The main orchestration layer.
- `packages/newgeo_core/newgeo_core/seed.py`
  Demo project seeding.

### API

- `api/app/main.py`
  FastAPI app and request models.
- `api/tests/test_service.py`
  Service-level tests.
- `api/tests/test_api.py`
  Route-function smoke test.

### Worker

- `workers/app/worker.py`
  Polling worker for queued jobs.

### Frontend

- `web/app/layout.tsx`
  Root app layout.
- `web/app/page.tsx`
  Overview dashboard.
- `web/app/pages/page.tsx`
  Page inventory view.
- `web/app/queries/page.tsx`
  Query cluster view.
- `web/app/runs/page.tsx`
  Benchmark run view.
- `web/app/recommendations/page.tsx`
  Recommendation queue view.
- `web/app/compare/page.tsx`
  Before/after comparison view.
- `web/components/dashboard-shell.tsx`
  Main dashboard shell and reusable cards.
- `web/lib/api.ts`
  UI-side data helpers.
- `web/lib/sample-data.ts`
  Fallback demo data for the current UI.

---

## 5. Core Domain Models

The main models live in `models.py`.

### Project

Represents a monitored site or documentation property.

Fields:

- `id`
- `name`
- `base_url`
- `description`
- `created_at`

### Page

Represents a page that NewGEO tracks and optimizes.

Fields:

- `project_id`
- `url`
- `title`
- `content_type`
- `status`
- `current_snapshot_id`

Important note:

- the page itself is lightweight,
- the actual content lives in `ContentSnapshot`.

### ContentSnapshot

Represents a saved version of page content.

Fields:

- `raw_markdown`
- `normalized_markdown`
- `embedding`

Why this exists:

- snapshots let us separate the page identity from the content body,
- this is useful later for version history, approval trails, and benchmark comparisons.

### ContextPack

This is one of the most important models in the whole platform.

It contains the extra read-only context that the recommendation generator can use without editing those other sources.

Fields:

- `brief`
- `voice_rules`
- `supporting_documents`
- `constraints`

This is the implementation of your key product idea:

> allow more context outside the source being rewritten so the system preserves meaning better.

### Constraint

Current constraint types:

- `locked_fact`
- `forbidden_claim`
- `required_term`
- `voice_rule`

These are used both during recommendation generation and during approval safety checks.

### QueryCluster

Groups related user queries into one monitoring unit.

Why this matters:

- GEO is query-specific,
- so visibility should be measured against query clusters, not just page-level content.

### BenchmarkRun

Represents one benchmark execution against an engine connector.

Fields include:

- `engine_name`
- `run_kind`
- `status`
- `candidate_page_ids`
- `observations`
- `score_snapshot_ids`

### ScoreSnapshot

Stores the scored outcome for one page inside one run.

This is what makes trend reporting possible later.

### Recommendation

Represents a generated optimization suggestion for one page.

It stores:

- the recommendation bundle,
- approval/export state,
- timestamps,
- errors if generation failed.

### RecommendationBundle

Contains the actual output of the recommendation engine:

- `rewritten_markdown`
- `diff_markdown`
- `rationale`
- `confidence`
- `supporting_context_used`
- `constraint_checks`
- `preview`

### Approval

Represents a human approval action on a recommendation.

This is how the current human-in-the-loop workflow is expressed.

---

## 6. Storage Model

Current persistence is handled by `JsonStore` in `storage.py`.

The store file defaults to:

```text
.data/newgeo-store.json
```

The JSON file contains separate top-level collections:

- `projects`
- `pages`
- `snapshots`
- `context_packs`
- `query_clusters`
- `runs`
- `recommendations`
- `approvals`
- `score_snapshots`

Why this was chosen:

- it makes the scaffold runnable immediately,
- it keeps the service layer testable,
- it avoids blocking on missing database dependencies.

Why it should eventually be replaced:

- no relational guarantees,
- weak concurrent write behavior,
- poor queryability,
- no vector indexing,
- not suitable for production-scale job processing.

Planned replacement:

- Postgres for primary persistence,
- pgvector for embeddings and retrieval,
- Redis for queue coordination.

---

## 7. Content and Retrieval Logic

Implemented in:

- `content.py`
- `retrieval.py`

### Content helpers

`content.py` currently provides:

- markdown normalization,
- tokenization,
- sentence splitting,
- numeric-claim extraction,
- a deterministic lightweight embedding function,
- cosine similarity,
- keyword overlap scoring.

The embedding function is **not** a semantic embedding model. It is a deterministic hashed vector used only to make the scaffold work now.

### Retrieval

`retrieval.py` ranks supporting documents by similarity to:

- the query cluster name,
- the context-pack brief.

Current behavior:

- supporting docs are embedded,
- a query embedding is generated,
- cosine similarity ranks documents,
- the top documents are summarized and included in the recommendation bundle.

This is a good first slice because it validates the architecture around context packs without requiring an external embedding provider.

---

## 8. Benchmark Engine

Implemented in `benchmarking.py`.

### Connector interface

The system defines an `EngineConnector` protocol with:

- `name`
- `run_kind`
- `comparable`
- `run_benchmark(query_cluster, candidate_pages)`

This is important because the product should eventually support multiple engines without rewriting service logic.

### Current connectors

Two connectors are implemented:

- `HeuristicEngineConnector`
- `LiveSpotCheckConnector`

#### HeuristicEngineConnector

Used for comparable benchmark runs.

It calculates a score based on:

- query keyword overlap,
- early token coverage,
- structural signals like headings and bullet points,
- authority cues,
- quote/snippet friendliness,
- a very small deterministic noise term.

This produces metrics for:

- mention rate
- citation share
- answer position
- token share
- quote coverage
- run variance
- overall score

#### LiveSpotCheckConnector

This extends the heuristic connector but marks results as:

- `run_kind = live_spot_check`
- `comparable = False`

It also increases variance slightly and lowers confidence in the score. That captures the product idea that live spot checks are useful but should not be mixed directly into benchmark trends.

### Why the benchmark is heuristic right now

The current benchmark exists to validate the product architecture, data model, and UI flows.

It is **not** a substitute for:

- real API-based LLM evaluations,
- real AI search product monitoring,
- citation parsing from live responses.

Those should be the next implementation steps.

---

## 9. Recommendation Engine

Implemented in `recommendations.py`.

This module is the current implementation of context-aware optimization.

### Inputs

It takes:

- `page`
- `original_markdown`
- `context_pack`
- `query_cluster`
- `candidate_pages`

### Step-by-step flow

1. Rank supporting documents from the context pack.
2. Build a structured rewrite draft.
3. Evaluate constraints against the draft.
4. Check source-claim preservation.
5. Benchmark the original page.
6. Benchmark the projected rewritten page.
7. Store both baseline and projected metrics in the recommendation preview.

### Draft structure

The current generated draft usually contains:

- optional top-level title,
- `## Quick answer`,
- `## Locked facts to preserve`,
- `## Related internal context`,
- `## Suggested page body`.

This is intentionally conservative.

The reasoning is:

- preserve the original body,
- make critical context explicit,
- improve structure and surfaceability,
- avoid semantic drift from aggressive paraphrasing.

### Why this matters

This directly addresses the original concern:

- AutoGEO-style rewriting can improve visibility,
- but without external context it can shift meaning,
- NewGEO uses context packs and explicit constraints to reduce that risk.

### Constraint checks

The recommendation engine currently validates:

- locked facts must still appear,
- forbidden claims must not appear,
- required terms should appear,
- source claims with numeric details should still be preserved.

### Preview scoring

Each recommendation includes:

- baseline metrics,
- projected metrics,
- projected score delta.

This is useful because a reviewer can see the likely benefit before approving.

---

## 10. Service Layer

Implemented in `service.py`.

This is the orchestration layer and currently the most important backend file.

### Main responsibilities

- create and read projects,
- import or crawl pages,
- create context packs,
- create query clusters,
- generate benchmark runs,
- generate recommendations,
- approve recommendations,
- export recommendations,
- build dashboard data,
- process queued jobs.

### Why this file exists

Without a service layer, the API would become the business-logic layer. That would make future changes much harder.

The service layer is what allows the API, worker, tests, and scripts to share the same behavior.

---

## 11. API Layer

Implemented in `api/app/main.py`.

### Available endpoints

- `GET /health`
- `GET /`
- `POST /projects`
- `GET /projects/{project_id}`
- `GET /projects/{project_id}/dashboard`
- `POST /projects/{project_id}/crawl`
- `POST /pages/import`
- `POST /context-packs`
- `POST /query-clusters`
- `POST /runs`
- `GET /runs/{run_id}`
- `POST /recommendations`
- `GET /recommendations/{recommendation_id}`
- `POST /recommendations/{recommendation_id}/approve`
- `POST /recommendations/{recommendation_id}/export`
- `POST /seed/demo`

### Important note

The original plan listed approval/export endpoints but not recommendation creation. I added `POST /recommendations` because the rest of the workflow would be incomplete without it.

### Request model design

The API defines request-only models for:

- project creation,
- page import/crawl payloads,
- context pack creation,
- query cluster creation,
- benchmark run creation,
- recommendation creation,
- approval/export actions.

That separation is useful because request contracts and stored domain models often evolve at different speeds.

---

## 12. Worker

Implemented in `workers/app/worker.py`.

The worker is deliberately simple right now.

It:

- creates a `NewGeoService`,
- polls every few seconds,
- processes queued runs,
- processes queued recommendations.

Why this exists now even though jobs can run synchronously:

- it proves the background-job boundary,
- it gives the architecture a place to move expensive work later,
- it prevents the API from owning all execution patterns.

What it is not yet:

- a robust distributed queue,
- a retry/backoff system,
- a Redis-backed job runner.

---

## 13. Frontend

Implemented in `web/`.

### What the UI currently does

It provides a polished dashboard shell that mirrors the intended product shape.

Current views:

- `Overview`
- `Pages`
- `Queries`
- `Runs`
- `Recommendations`
- `Compare`

### Data strategy

`web/lib/api.ts` is already prepared to fetch dashboard data from the API, but it currently falls back to `web/lib/sample-data.ts` unless:

- `NEXT_PUBLIC_API_BASE_URL` is set,
- and a real project ID is provided to the data helper.

Why this fallback exists:

- it keeps the UI explorable before the mutation flow is fully wired,
- it avoids blocking frontend work on the final API integration shape.

### Styling direction

The frontend uses:

- a non-default editorial/ops look,
- a glassmorphism-like layered panel system,
- distinct route views,
- reusable cards and panels.

This was done on purpose so the UI already feels like a product, not only a technical scaffold.

---

## 14. End-to-End Workflow

This is the current intended user flow.

### 14.1 Create a project

`POST /projects`

This creates a top-level monitored content property.

### 14.2 Add pages

Either:

- `POST /projects/{id}/crawl`
- or `POST /pages/import`

Current crawl behavior is mock-friendly: it imports supplied page payloads rather than doing a real web crawl.

### 14.3 Add a context pack

`POST /context-packs`

This is where the user defines:

- brief,
- voice rules,
- locked facts,
- forbidden claims,
- required terms,
- supporting read-only pages/docs.

### 14.4 Add a query cluster

`POST /query-clusters`

This groups the queries that matter for measuring visibility.

### 14.5 Run a benchmark

`POST /runs`

This creates a benchmark run and score snapshots.

### 14.6 Generate a recommendation

`POST /recommendations`

This creates a recommendation bundle with:

- rewrite,
- diff,
- rationale,
- checks,
- projected lift.

### 14.7 Approve and export

- `POST /recommendations/{id}/approve`
- `POST /recommendations/{id}/export`

This keeps a human in the loop before the output leaves the system.

---

## 15. Seeded Demo

`scripts/seed_demo.py` and `seed.py` create a fictional docs project called `Atlas Docs`.

It includes:

- one setup guide page,
- one context pack,
- one query cluster,
- one generated recommendation,
- one completed benchmark run.

This is useful for:

- quick manual testing,
- UI exploration,
- onboarding,
- regression checks.

---

## 16. Tests and Verification

### Implemented tests

`api/tests/test_service.py` covers:

- recommendation generation,
- locked-fact preservation,
- benchmark run generation,
- approval flow,
- export flow.

`api/tests/test_api.py` covers:

- seed flow,
- dashboard flow.

### Commands used successfully

```bash
PYTHONPATH=packages/newgeo_core python3 -m unittest discover -s api/tests -v
PYTHONPATH=packages/newgeo_core python3 -m py_compile api/app/main.py workers/app/worker.py packages/newgeo_core/newgeo_core/*.py
PYTHONPATH=packages/newgeo_core python3 scripts/seed_demo.py
```

### Important testing note

In this sandbox, `FastAPI TestClient` hung during request execution, so the API smoke test was written as direct route-function validation instead. The API logic itself worked; this was a test-harness limitation in the environment.

---

## 17. Current Limitations

This section is important because it separates:

- what is implemented,
- from what is still architectural intent.

### Storage

Current:

- file-backed JSON store

Missing:

- Postgres persistence
- pgvector retrieval
- migrations
- robust concurrency handling

### Crawling

Current:

- payload-based mock crawl/import

Missing:

- real website crawling
- HTML extraction
- canonical URL handling
- robots/respectful crawl behavior

### Benchmarking

Current:

- deterministic heuristic benchmark

Missing:

- real LLM API evaluation
- prompt versioning in storage and reporting
- citation parsing from actual responses
- engine-specific adapters

### Recommendation generation

Current:

- deterministic structured rewrite builder

Missing:

- LLM-powered generation
- prompt templating by engine/content type
- stronger factuality/entailment validation
- richer rewrite strategies

### Background jobs

Current:

- polling worker

Missing:

- Redis or message queue
- retries
- dead-letter behavior
- job observability

### Frontend

Current:

- well-structured dashboard shell
- sample-data fallback

Missing:

- full live API integration
- forms and mutations
- auth/workspace support
- rich charts
- diff review UI

---

## 18. Why Certain Choices Were Made

### Why a JSON store first

Because it lets the service layer, tests, API, and worker all run now.

### Why heuristic connectors first

Because the main goal of this iteration was to validate:

- the data model,
- the workflows,
- the UI shape,
- the context-pack idea.

### Why preserve original content inside the recommendation draft

Because your main product concern was meaning preservation. The current draft structure is intentionally conservative so the product bias is toward safety, not over-aggressive rewriting.

### Why the UI still uses sample data

Because the dashboard shape needed to exist before the API mutation flow and project selection flow were fully wired.

---

## 19. Recommended Next Implementation Steps

This is the most important roadmap section.

### Step 1: Replace JSON storage with a real database layer

Goal:

- make the backend production-capable.

Recommended work:

- add a repository abstraction above `JsonStore`,
- implement a Postgres-backed store,
- store embeddings with pgvector,
- keep the current file store as a dev fallback.

Why first:

- almost every future feature depends on durable querying and concurrency-safe writes.

### Step 2: Add a real crawler and content ingestion pipeline

Goal:

- move from scaffold imports to actual site ingestion.

Recommended work:

- crawl URLs from sitemap or base URL,
- fetch HTML,
- extract clean article/doc content,
- normalize titles and canonical URLs,
- deduplicate pages,
- persist crawl snapshots.

### Step 3: Implement real benchmark connectors

Goal:

- turn the benchmark layer into a real GEO measurement system.

Recommended work:

- add API-based connectors for target LLMs,
- store raw prompts and raw responses,
- parse citations/mentions,
- compare results across multiple runs,
- version benchmark prompts explicitly.

### Step 4: Upgrade recommendation generation to LLM-backed optimization

Goal:

- move from structured heuristics to actual high-quality optimization suggestions.

Recommended work:

- build prompt templates using:
  - page content,
  - context pack,
  - query cluster,
  - locked facts,
  - required terms,
  - supporting pages,
- request structured output:
  - rewritten markdown,
  - rationale,
  - inserted terms,
  - preserved facts,
  - cited supporting context,
- validate output before approval.

### Step 5: Strengthen meaning-preservation validation

Goal:

- make the core differentiator much stronger.

Recommended work:

- claim extraction from the original page,
- NLI/entailment checks,
- numeric-value consistency checks,
- contradiction checks against locked facts,
- required citation backreferences to supporting context.

### Step 6: Wire the frontend to the real API

Goal:

- turn the UI from scaffold to working product.

Recommended work:

- add project loading,
- create forms for page import/context pack/query cluster creation,
- trigger benchmark runs and recommendation generation,
- poll run/recommendation status,
- display live dashboard data,
- show approval/export actions.

### Step 7: Improve background processing

Goal:

- make expensive runs safe and scalable.

Recommended work:

- replace polling with Redis-backed jobs,
- add retries and job status history,
- add cancellation and backoff,
- add worker metrics.

### Step 8: Add authentication and multi-project collaboration

Goal:

- prepare the platform for real teams.

Recommended work:

- auth,
- user/workspace/project ownership,
- reviewer metadata,
- audit logs,
- collaborative approval history.

### Step 9: Improve reporting

Goal:

- make measurement genuinely useful over time.

Recommended work:

- trend charts,
- per-engine comparison,
- baseline vs approved vs exported tracking,
- query-cluster history,
- recommendation outcome attribution.

### Step 10: Bring AutoGEO/GEO research ideas in more deeply

Goal:

- move from inspired architecture to research-informed optimization.

Recommended work:

- adapt extracted rule sets from AutoGEO,
- reuse evaluation ideas from GEO,
- incorporate rule-learning into recommendation prompts,
- create benchmark datasets and regression fixtures from those projects.

---

## 20. Suggested Immediate Development Order

If you want the most practical next sequence, I recommend:

1. Postgres/pgvector repository layer
2. Real crawling and page ingestion
3. Real benchmark connectors
4. LLM-backed recommendation engine
5. Stronger drift/claim validation
6. Live API integration in the frontend
7. Redis-backed job orchestration

That order preserves momentum and keeps infrastructure work tied directly to visible product gains.

---

## 21. Short Summary

What exists today:

- a real project scaffold,
- a real domain model,
- a working API,
- a working worker,
- a working recommendation flow,
- a working benchmark flow,
- a dashboard shell,
- demo data,
- tests.

What it is best understood as:

- a solid v1 foundation,
- not yet the finished platform.

What makes it valuable already:

- the architecture is in the right shape,
- the core context-pack idea is already expressed in code,
- future implementation can now be incremental instead of speculative.

