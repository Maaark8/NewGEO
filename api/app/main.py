from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "packages" / "newgeo_core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from newgeo_core.ingestion import CrawlRequest, CrawlSeed
from newgeo_core.models import ConstraintType, RecommendationStatus, RunKind
from newgeo_core.seed import seed_demo_project
from newgeo_core.service import NewGeoService


class ProjectCreateRequest(BaseModel):
    name: str
    base_url: str | None = None
    description: str | None = None


class CrawlPageInput(BaseModel):
    title: str | None = None
    markdown: str | None = None
    html: str | None = None
    url: str | None = None
    content_type: str = "docs_article"


class CrawlSeedInput(BaseModel):
    url: str
    label: str | None = None


class ProjectCrawlRequest(BaseModel):
    pages: list[CrawlPageInput] = Field(default_factory=list)
    seeds: list[CrawlSeedInput] = Field(default_factory=list)
    max_pages: int = 25
    max_depth: int = 1
    same_domain_only: bool = True
    include_sitemap_variants: bool = True
    fetch_live_urls: bool = False
    raw_html_by_url: dict[str, str] = Field(default_factory=dict)
    markdown_by_url: dict[str, str] = Field(default_factory=dict)


class PageImportRequest(BaseModel):
    project_id: str
    title: str
    markdown: str
    url: str | None = None
    content_type: str = "docs_article"


class ConstraintInput(BaseModel):
    kind: ConstraintType
    value: str
    description: str | None = None
    strict: bool = True


class SupportingDocumentInput(BaseModel):
    title: str
    body: str
    url: str | None = None


class ContextPackCreateRequest(BaseModel):
    project_id: str
    page_id: str
    brief: str | None = None
    voice_rules: list[str] = Field(default_factory=list)
    constraints: list[ConstraintInput] = Field(default_factory=list)
    supporting_documents: list[SupportingDocumentInput] = Field(default_factory=list)


class QueryInput(BaseModel):
    text: str
    intent: str | None = None


class QueryClusterCreateRequest(BaseModel):
    project_id: str
    name: str
    description: str | None = None
    queries: list[QueryInput] = Field(default_factory=list)
    target_page_ids: list[str] = Field(default_factory=list)


class RunCreateRequest(BaseModel):
    project_id: str
    query_cluster_id: str
    engine_name: str = "newgeo-benchmark-v1"
    candidate_page_ids: list[str] = Field(default_factory=list)
    run_kind: RunKind = RunKind.benchmark
    prompt_version: str = "newgeo-benchmark-v1"
    connector_kind: str = "heuristic"
    connector_config: dict[str, Any] = Field(default_factory=dict)
    queue_only: bool = False


class RecommendationCreateRequest(BaseModel):
    project_id: str
    page_id: str
    context_pack_id: str
    query_cluster_id: str
    engine_name: str = "newgeo-contextual-v1"
    queue_only: bool = False


class RecommendationApprovalRequest(BaseModel):
    approved_by: str
    note: str | None = None


class RecommendationExportRequest(BaseModel):
    force: bool = False


service = NewGeoService()
app = FastAPI(title="NewGEO API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _handle_value_error(exc: ValueError) -> None:
    raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "NewGEO API",
        "status": "ok",
        "endpoints": [
            "/projects",
            "/projects/{id}/crawl",
            "/pages/import",
            "/context-packs",
            "/query-clusters",
            "/runs",
            "/recommendations",
        ],
    }


@app.post("/projects")
def create_project(payload: ProjectCreateRequest) -> Any:
    return service.create_project(payload.name, payload.base_url, payload.description)


@app.get("/projects")
def list_projects() -> Any:
    return service.list_projects()


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> Any:
    try:
        project = service.get_project(project_id)
        return {"project": project, "dashboard": service.get_dashboard(project_id)}
    except ValueError as exc:
        _handle_value_error(exc)


@app.get("/projects/{project_id}/dashboard")
def get_dashboard(project_id: str) -> Any:
    try:
        return service.get_dashboard(project_id)
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/projects/{project_id}/crawl")
def crawl_project(project_id: str, payload: ProjectCrawlRequest) -> Any:
    try:
        pages = [item.model_dump(mode="json", exclude_none=True) for item in payload.pages]
        crawl_request = None
        if payload.seeds or payload.raw_html_by_url or payload.markdown_by_url:
            crawl_request = CrawlRequest(
                project_id=project_id,
                seeds=[CrawlSeed(**item.model_dump(mode="json")) for item in payload.seeds],
                max_pages=payload.max_pages,
                max_depth=payload.max_depth,
                same_domain_only=payload.same_domain_only,
                include_sitemap_variants=payload.include_sitemap_variants,
                fetch_live_urls=payload.fetch_live_urls,
                raw_html_by_url=payload.raw_html_by_url,
                markdown_by_url=payload.markdown_by_url,
            )
        return {"project_id": project_id, "imported_pages": service.crawl_project(project_id, pages, crawl_request)}
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/pages/import")
def import_page(payload: PageImportRequest) -> Any:
    try:
        return service.import_page(
            project_id=payload.project_id,
            title=payload.title,
            markdown=payload.markdown,
            url=payload.url,
            content_type=payload.content_type,
        )
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/context-packs")
def create_context_pack(payload: ContextPackCreateRequest) -> Any:
    try:
        return service.create_context_pack(
            project_id=payload.project_id,
            page_id=payload.page_id,
            brief=payload.brief,
            voice_rules=payload.voice_rules,
            constraints=[item.model_dump(mode="json") for item in payload.constraints],
            supporting_documents=[item.model_dump(mode="json") for item in payload.supporting_documents],
        )
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/query-clusters")
def create_query_cluster(payload: QueryClusterCreateRequest) -> Any:
    try:
        return service.create_query_cluster(
            project_id=payload.project_id,
            name=payload.name,
            description=payload.description,
            queries=[item.model_dump(mode="json") for item in payload.queries],
            target_page_ids=payload.target_page_ids,
        )
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/runs")
def create_run(payload: RunCreateRequest) -> Any:
    try:
        return service.create_run(
            project_id=payload.project_id,
            query_cluster_id=payload.query_cluster_id,
            engine_name=payload.engine_name,
            candidate_page_ids=payload.candidate_page_ids,
            run_kind=payload.run_kind,
            prompt_version=payload.prompt_version,
            connector_kind=payload.connector_kind,
            connector_config=payload.connector_config,
            queue_only=payload.queue_only,
        )
    except ValueError as exc:
        _handle_value_error(exc)


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> Any:
    try:
        return service.get_run(run_id)
    except ValueError as exc:
        _handle_value_error(exc)


@app.get("/runs/{run_id}/artifacts")
def get_run_artifacts(run_id: str) -> Any:
    try:
        return service.list_run_artifacts(run_id)
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/recommendations")
def create_recommendation(payload: RecommendationCreateRequest) -> Any:
    try:
        return service.create_recommendation(
            project_id=payload.project_id,
            page_id=payload.page_id,
            context_pack_id=payload.context_pack_id,
            query_cluster_id=payload.query_cluster_id,
            engine_name=payload.engine_name,
            queue_only=payload.queue_only,
        )
    except ValueError as exc:
        _handle_value_error(exc)


@app.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str) -> Any:
    try:
        return service.get_recommendation(recommendation_id)
    except ValueError as exc:
        _handle_value_error(exc)


@app.post("/recommendations/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: str, payload: RecommendationApprovalRequest) -> Any:
    try:
        return service.approve_recommendation(
            recommendation_id=recommendation_id,
            approved_by=payload.approved_by,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/recommendations/{recommendation_id}/export")
def export_recommendation(recommendation_id: str, payload: RecommendationExportRequest) -> Any:
    try:
        recommendation = service.get_recommendation(recommendation_id)
        if payload.force and recommendation.status == RecommendationStatus.generated:
            recommendation = service.approve_recommendation(recommendation_id, approved_by="system", note="Forced export.")
        return service.export_recommendation(recommendation.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/seed/demo")
def seed_demo() -> Any:
    identifiers = seed_demo_project(service)
    return {"seeded": True, **identifiers}
