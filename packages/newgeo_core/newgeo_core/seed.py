from __future__ import annotations

from .models import ConstraintType, RunKind
from .service import NewGeoService


def seed_demo_project(service: NewGeoService) -> dict[str, str]:
    project = service.create_project(
        name="Atlas Docs",
        base_url="https://docs.example.com",
        description="Documentation platform for a fictional observability product.",
    )

    page = service.import_page(
        project_id=project.id,
        title="Distributed tracing setup guide",
        url="https://docs.example.com/tracing/setup",
        markdown="""# Distributed tracing setup guide

Atlas tracing captures request flow across services and stores spans for 30 days by default.

## Setup steps

1. Install the tracing SDK in each service.
2. Export spans to the Atlas collector endpoint.
3. Verify traces in the service map.

## Why teams use it

Teams use tracing to diagnose slow requests, understand dependency chains, and confirm release health after deployment.
""",
    )

    context_pack = service.create_context_pack(
        project_id=project.id,
        page_id=page.id,
        brief="Atlas serves platform engineers who need concise, trustworthy setup guides for production systems.",
        voice_rules=["Clear, technical, and direct.", "Prefer steps and definitions over marketing language."],
        constraints=[
            {
                "kind": ConstraintType.locked_fact,
                "value": "stores spans for 30 days by default",
                "description": "Retention period must not change.",
            },
            {
                "kind": ConstraintType.required_term,
                "value": "distributed tracing",
                "description": "Primary query term should be explicit.",
                "strict": False,
            },
            {
                "kind": ConstraintType.forbidden_claim,
                "value": "one-click migration",
                "description": "Do not invent unsupported ease-of-use claims.",
            },
        ],
        supporting_documents=[
            {
                "title": "Tracing concepts",
                "url": "https://docs.example.com/tracing/concepts",
                "body": "Tracing follows a request through services, records spans, and helps explain latency and downstream failures.",
            },
            {
                "title": "Collector reference",
                "url": "https://docs.example.com/reference/collector",
                "body": "The Atlas collector accepts OpenTelemetry spans, batches them, and forwards them for indexing and retention.",
            },
        ],
    )

    query_cluster = service.create_query_cluster(
        project_id=project.id,
        name="Distributed tracing setup",
        description="Queries from engineers looking for setup and implementation guidance.",
        queries=[
            {"text": "how to set up distributed tracing", "intent": "informational"},
            {"text": "distributed tracing configuration guide", "intent": "informational"},
        ],
        target_page_ids=[page.id],
    )

    recommendation = service.create_recommendation(
        project_id=project.id,
        page_id=page.id,
        context_pack_id=context_pack.id,
        query_cluster_id=query_cluster.id,
    )
    run = service.create_run(
        project_id=project.id,
        query_cluster_id=query_cluster.id,
        engine_name="newgeo-benchmark-v1",
        candidate_page_ids=[page.id],
        run_kind=RunKind.benchmark,
    )

    return {
        "project_id": project.id,
        "page_id": page.id,
        "context_pack_id": context_pack.id,
        "query_cluster_id": query_cluster.id,
        "recommendation_id": recommendation.id,
        "run_id": run.id,
    }
