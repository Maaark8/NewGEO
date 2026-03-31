# NewGEO

NewGEO is an open-source platform for monitoring visibility, optimizing presence, and measuring growth across LLMs and AI search. This repository keeps the upstream `AutoGEO/` and `GEO/` research repos intact while adding a new product-oriented monorepo scaffold beside them.

For a full architecture walkthrough, implementation notes, and the recommended next roadmap, read [`DOCUMENTATION.md`](./DOCUMENTATION.md).

## What is implemented

- A shared Python domain package for projects, pages, context packs, query clusters, benchmark runs, score snapshots, recommendations, approvals, and exports.
- A FastAPI service with the planned core endpoints plus a dashboard endpoint and a recommendation creation endpoint.
- A worker entry point that can process queued runs and recommendations.
- A heuristic benchmarking engine and a context-aware recommendation generator that preserve locked facts and source claims.
- A Next.js dashboard shell with Overview, Pages, Queries, Runs, Recommendations, and Compare views.
- Docker-based local development, seed data, and Python tests for the core workflow.

## Current implementation notes

- The core service is fully runnable with a local file-backed store so the platform works without extra infrastructure.
- Connector, storage, and retrieval boundaries are separated so Postgres/pgvector and richer engine integrations can be added without rewriting the product surface.
- The benchmark and recommendation engines are intentionally deterministic and transparent. They are designed as the first platform layer, not as a replacement for future LLM-powered connectors.

## Repo layout

- `api/`: FastAPI application and API smoke tests.
- `workers/`: background worker loop for queued jobs.
- `packages/newgeo_core/`: shared Python models and services used by the API and workers.
- `web/`: Next.js dashboard UI.
- `examples/`: seed content for demo projects.
- `AutoGEO/` and `GEO/`: preserved upstream research references.

## Quick start

### API

```bash
PYTHONPATH=packages/newgeo_core uvicorn api.app.main:app --reload
```

### Worker

```bash
PYTHONPATH=packages/newgeo_core python3 -m workers.app.worker
```

### Web

```bash
cd web
npm install
npm run dev
```

### Tests

```bash
PYTHONPATH=packages/newgeo_core python3 -m unittest discover -s api/tests -v
```

### Seed demo data

```bash
PYTHONPATH=packages/newgeo_core python3 scripts/seed_demo.py
```

## Docker

```bash
docker compose up --build
```

## Planned extension points

- Replace the file-backed store with a Postgres/pgvector adapter.
- Add real LLM engine connectors and live product spot-check connectors.
- Add crawler integrations, CMS export adapters, and analytics imports.
