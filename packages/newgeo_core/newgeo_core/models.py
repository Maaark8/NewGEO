from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ConstraintType(str, Enum):
    locked_fact = "locked_fact"
    forbidden_claim = "forbidden_claim"
    required_term = "required_term"
    voice_rule = "voice_rule"


class RunKind(str, Enum):
    benchmark = "benchmark"
    live_spot_check = "live_spot_check"


class RecommendationStatus(str, Enum):
    queued = "queued"
    generated = "generated"
    approved = "approved"
    exported = "exported"
    failed = "failed"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prj"))
    name: str
    base_url: str | None = None
    description: str | None = None
    created_at: str = Field(default_factory=now_iso)


class ContentSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("snp"))
    page_id: str
    title: str
    source_url: str | None = None
    raw_markdown: str
    normalized_markdown: str
    embedding: list[float] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class Page(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pag"))
    project_id: str
    url: str | None = None
    title: str
    content_type: str = "docs_article"
    status: str = "active"
    current_snapshot_id: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Constraint(BaseModel):
    id: str = Field(default_factory=lambda: new_id("con"))
    kind: ConstraintType
    value: str
    description: str | None = None
    strict: bool = True


class SupportingDocument(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ctx"))
    title: str
    url: str | None = None
    body: str
    embedding: list[float] = Field(default_factory=list)


class ContextPack(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cpk"))
    project_id: str
    page_id: str
    brief: str | None = None
    voice_rules: list[str] = Field(default_factory=list)
    supporting_documents: list[SupportingDocument] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class QueryTerm(BaseModel):
    id: str = Field(default_factory=lambda: new_id("qry"))
    text: str
    intent: str | None = None


class QueryCluster(BaseModel):
    id: str = Field(default_factory=lambda: new_id("qcl"))
    project_id: str
    name: str
    description: str | None = None
    queries: list[QueryTerm] = Field(default_factory=list)
    target_page_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class VisibilityMetrics(BaseModel):
    mention_rate: float = 0.0
    citation_share: float = 0.0
    answer_position: float = 0.0
    token_share: float = 0.0
    quote_coverage: float = 0.0
    run_variance: float = 0.0
    overall_score: float = 0.0


class EngineObservation(BaseModel):
    page_id: str
    engine_name: str
    query_text: str
    metrics: VisibilityMetrics
    notes: list[str] = Field(default_factory=list)


class ScoreSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("scr"))
    project_id: str
    page_id: str
    query_cluster_id: str
    run_id: str
    engine_name: str
    run_kind: RunKind
    comparable: bool
    metrics: VisibilityMetrics
    created_at: str = Field(default_factory=now_iso)


class BenchmarkArtifact(BaseModel):
    id: str = Field(default_factory=lambda: new_id("art"))
    project_id: str
    run_id: str
    query_cluster_id: str
    engine_name: str
    run_kind: RunKind
    prompt_version: str
    connector_kind: str = "heuristic"
    query_text: str
    prompt_text: str
    raw_response: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)


class BenchmarkRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    query_cluster_id: str
    engine_name: str
    run_kind: RunKind = RunKind.benchmark
    prompt_version: str = "newgeo-benchmark-v1"
    connector_kind: str = "heuristic"
    connector_config: dict[str, Any] = Field(default_factory=dict)
    comparable: bool = True
    candidate_page_ids: list[str] = Field(default_factory=list)
    observations: list[EngineObservation] = Field(default_factory=list)
    score_snapshot_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.queued
    created_at: str = Field(default_factory=now_iso)
    completed_at: str | None = None
    error: str | None = None


class ConstraintCheck(BaseModel):
    constraint_id: str
    constraint_kind: str
    status: Literal["pass", "warn", "fail"]
    message: str


class RecommendationPreview(BaseModel):
    baseline: VisibilityMetrics = Field(default_factory=VisibilityMetrics)
    projected: VisibilityMetrics = Field(default_factory=VisibilityMetrics)
    score_delta: float = 0.0


class RecommendationBundle(BaseModel):
    rewritten_markdown: str
    diff_markdown: str
    rationale: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    supporting_context_used: list[str] = Field(default_factory=list)
    constraint_checks: list[ConstraintCheck] = Field(default_factory=list)
    preview: RecommendationPreview = Field(default_factory=RecommendationPreview)


class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rec"))
    project_id: str
    page_id: str
    context_pack_id: str
    query_cluster_id: str
    engine_name: str = "newgeo-contextual-v1"
    status: RecommendationStatus = RecommendationStatus.queued
    bundle: RecommendationBundle | None = None
    created_at: str = Field(default_factory=now_iso)
    approved_at: str | None = None
    export_path: str | None = None
    error: str | None = None


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: new_id("apr"))
    recommendation_id: str
    approved_by: str
    note: str | None = None
    approved_at: str = Field(default_factory=now_iso)
