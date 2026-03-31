from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .benchmarking import CandidatePage, connector_for_run
from .content import generate_embedding, normalize_markdown
from .ingestion import CrawlRequest, CrawlSeed, create_ingested_page, expand_crawl_request, fetch_html, normalize_url
from .models import (
    Approval,
    BenchmarkArtifact,
    BenchmarkRun,
    Constraint,
    ContextPack,
    ContentSnapshot,
    JobStatus,
    Page,
    Project,
    QueryCluster,
    QueryTerm,
    Recommendation,
    RecommendationStatus,
    RunKind,
    ScoreSnapshot,
    SupportingDocument,
    now_iso,
)
from .recommendations import generate_recommendation_bundle
from .storage import JsonStore
from .storage_backends import StorageBackend


class NewGeoService:
    def __init__(self, store: StorageBackend | None = None) -> None:
        store_path = os.environ.get("NEWGEO_STORE_PATH", ".data/newgeo-store.json")
        self.store = store or JsonStore(store_path)

    def create_project(self, name: str, base_url: str | None = None, description: str | None = None) -> Project:
        project = Project(name=name, base_url=base_url, description=description)
        return self.store.save_model("projects", project)

    def list_projects(self) -> list[Project]:
        return self.store.list_models("projects", Project)

    def get_project(self, project_id: str) -> Project:
        project = self.store.get_model("projects", Project, project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")
        return project

    def list_project_pages(self, project_id: str) -> list[Page]:
        return self.store.list_models("pages", Page, project_id=project_id)

    def list_project_context_packs(self, project_id: str) -> list[ContextPack]:
        return self.store.list_models("context_packs", ContextPack, project_id=project_id)

    def list_project_query_clusters(self, project_id: str) -> list[QueryCluster]:
        return self.store.list_models("query_clusters", QueryCluster, project_id=project_id)

    def list_project_runs(self, project_id: str) -> list[BenchmarkRun]:
        return self.store.list_models("runs", BenchmarkRun, project_id=project_id)

    def list_run_artifacts(self, run_id: str) -> list[BenchmarkArtifact]:
        return self.store.list_models("run_artifacts", BenchmarkArtifact, run_id=run_id)

    def list_project_recommendations(self, project_id: str) -> list[Recommendation]:
        return self.store.list_models("recommendations", Recommendation, project_id=project_id)

    def list_project_score_snapshots(self, project_id: str) -> list[ScoreSnapshot]:
        return self.store.list_models("score_snapshots", ScoreSnapshot, project_id=project_id)

    def import_page(
        self,
        project_id: str,
        title: str,
        markdown: str,
        url: str | None = None,
        content_type: str = "docs_article",
    ) -> Page:
        normalized = normalize_markdown(markdown)
        page = Page(
            project_id=project_id,
            url=url,
            title=title,
            content_type=content_type,
            current_snapshot_id="pending",
        )
        snapshot = ContentSnapshot(
            page_id=page.id,
            title=title,
            source_url=url,
            raw_markdown=markdown,
            normalized_markdown=normalized,
            embedding=generate_embedding(normalized),
        )
        page = page.model_copy(update={"current_snapshot_id": snapshot.id})
        self.store.save_model("snapshots", snapshot)
        return self.store.save_model("pages", page)

    def import_ingested_page(self, project_id: str, page_payload: Any) -> Page:
        title = getattr(page_payload, "title", None) or page_payload["title"]
        markdown = getattr(page_payload, "markdown", None) or page_payload["markdown"]
        url = getattr(page_payload, "url", None) if hasattr(page_payload, "url") else page_payload.get("url")
        content_type = (
            getattr(page_payload, "content_type", None)
            if hasattr(page_payload, "content_type")
            else page_payload.get("content_type", "docs_article")
        )
        return self.import_page(
            project_id=project_id,
            title=title,
            markdown=markdown,
            url=url,
            content_type=content_type or "docs_article",
        )

    def crawl_project(self, project_id: str, pages: list[dict[str, Any]] | None = None, crawl_request: CrawlRequest | None = None) -> list[Page]:
        project = self.get_project(project_id)
        imported: list[Page] = []

        if pages:
            for payload in pages:
                if payload.get("html") or not payload.get("markdown") or not payload.get("title"):
                    ingested = create_ingested_page(
                        url=payload.get("url") or project.base_url or "https://example.invalid",
                        html=payload.get("html"),
                        markdown=payload.get("markdown"),
                        title=payload.get("title"),
                        source="crawl_payload",
                        base_url=project.base_url,
                    )
                    imported.append(self.import_ingested_page(project_id, ingested))
                    continue
                imported.append(
                    self.import_page(
                        project_id=project_id,
                        title=payload["title"],
                        markdown=payload["markdown"],
                        url=payload.get("url"),
                        content_type=payload.get("content_type", "docs_article"),
                    )
                )
            return imported

        request = crawl_request or CrawlRequest(
            project_id=project_id,
            base_url=project.base_url,
            seeds=[CrawlSeed(url=project.base_url)] if project.base_url else [],
        )
        if request.base_url is None:
            request.base_url = project.base_url

        expanded_seeds = expand_crawl_request(request)
        if not expanded_seeds:
            fallback_markdown = (
                f"# {project.name}\n\n"
                f"{project.description or 'Imported page from the project crawl.'}\n\n"
                "## Why it matters\n\n"
                "This page is the first imported content snapshot for NewGEO."
            )
            imported.append(
                self.import_page(
                    project_id=project_id,
                    title=f"{project.name} Overview",
                    markdown=fallback_markdown,
                    url=project.base_url,
                    content_type="docs_article",
                )
            )
            return imported

        raw_html_by_url = request.raw_html_by_url
        markdown_by_url = request.markdown_by_url

        for seed in expanded_seeds:
            normalized_seed_url = normalize_url(seed.url, base_url=request.base_url)
            if normalized_seed_url in markdown_by_url:
                ingested = create_ingested_page(
                    url=normalized_seed_url,
                    markdown=markdown_by_url[normalized_seed_url],
                    title=seed.label,
                    source="crawl_request",
                    base_url=request.base_url,
                )
                imported.append(self.import_ingested_page(project_id, ingested))
                continue
            if normalized_seed_url in raw_html_by_url:
                ingested = create_ingested_page(
                    url=normalized_seed_url,
                    html=raw_html_by_url[normalized_seed_url],
                    title=seed.label,
                    source="crawl_request",
                    base_url=request.base_url,
                )
                imported.append(self.import_ingested_page(project_id, ingested))
                continue
            if request.fetch_live_urls:
                fetched_html = fetch_html(normalized_seed_url)
                if fetched_html:
                    ingested = create_ingested_page(
                        url=normalized_seed_url,
                        html=fetched_html,
                        title=seed.label,
                        source="live_crawl",
                        base_url=request.base_url,
                    )
                    imported.append(self.import_ingested_page(project_id, ingested))
        if imported:
            return imported

        for seed in expanded_seeds[: request.max_pages]:
            imported.append(
                self.import_page(
                    project_id=project_id,
                    title=seed.label or normalize_url(seed.url, base_url=request.base_url).rsplit("/", 1)[-1] or project.name,
                    markdown=(
                        f"# {seed.label or project.name}\n\n"
                        f"Imported crawl seed for `{normalize_url(seed.url, base_url=request.base_url)}`.\n\n"
                        "## Status\n\n"
                        "Content fetch is not available in the current environment, so this seed was recorded as a placeholder."
                    ),
                    url=normalize_url(seed.url, base_url=request.base_url),
                    content_type="web_page",
                )
            )
        return imported

    def create_context_pack(
        self,
        project_id: str,
        page_id: str,
        brief: str | None = None,
        voice_rules: list[str] | None = None,
        constraints: list[dict[str, Any]] | None = None,
        supporting_documents: list[dict[str, Any]] | None = None,
    ) -> ContextPack:
        normalized_constraints = [
            Constraint.model_validate(payload) if isinstance(payload, dict) else payload
            for payload in (constraints or [])
        ]
        normalized_documents = []
        for payload in supporting_documents or []:
            document = SupportingDocument.model_validate(payload)
            normalized_documents.append(document.model_copy(update={"embedding": generate_embedding(document.body)}))
        context_pack = ContextPack(
            project_id=project_id,
            page_id=page_id,
            brief=brief,
            voice_rules=voice_rules or [],
            constraints=normalized_constraints,
            supporting_documents=normalized_documents,
        )
        return self.store.save_model("context_packs", context_pack)

    def create_query_cluster(
        self,
        project_id: str,
        name: str,
        description: str | None = None,
        queries: list[dict[str, Any]] | None = None,
        target_page_ids: list[str] | None = None,
    ) -> QueryCluster:
        query_cluster = QueryCluster(
            project_id=project_id,
            name=name,
            description=description,
            queries=[QueryTerm.model_validate(query) for query in (queries or [])],
            target_page_ids=target_page_ids or [],
        )
        return self.store.save_model("query_clusters", query_cluster)

    def _page_snapshot(self, page_id: str) -> tuple[Page, ContentSnapshot]:
        page = self.store.get_model("pages", Page, page_id)
        if page is None:
            raise ValueError(f"Page not found: {page_id}")
        snapshot = self.store.get_model("snapshots", ContentSnapshot, page.current_snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot not found for page: {page_id}")
        return page, snapshot

    def _candidate_pages(self, project_id: str, candidate_page_ids: list[str] | None = None) -> list[CandidatePage]:
        selected_pages = []
        if candidate_page_ids:
            for page_id in candidate_page_ids:
                page, snapshot = self._page_snapshot(page_id)
                selected_pages.append(
                    CandidatePage(page_id=page.id, title=page.title, content=snapshot.normalized_markdown, url=page.url)
                )
            return selected_pages

        for page in self.list_project_pages(project_id):
            snapshot = self.store.get_model("snapshots", ContentSnapshot, page.current_snapshot_id)
            if snapshot is None:
                continue
            selected_pages.append(
                CandidatePage(page_id=page.id, title=page.title, content=snapshot.normalized_markdown, url=page.url)
            )
        return selected_pages

    def _execute_run(self, run: BenchmarkRun) -> BenchmarkRun:
        query_cluster = self.store.get_model("query_clusters", QueryCluster, run.query_cluster_id)
        if query_cluster is None:
            raise ValueError(f"Query cluster not found: {run.query_cluster_id}")

        candidate_pages = self._candidate_pages(run.project_id, run.candidate_page_ids or query_cluster.target_page_ids)
        connector = connector_for_run(
            run.engine_name,
            run.run_kind,
            connector_kind=run.connector_kind,
            connector_config=run.connector_config,
        )
        execution = connector.run_benchmark(query_cluster, candidate_pages, prompt_version=run.prompt_version)
        observations = execution.observations

        score_snapshot_ids: list[str] = []
        for observation in observations:
            snapshot = ScoreSnapshot(
                project_id=run.project_id,
                page_id=observation.page_id,
                query_cluster_id=run.query_cluster_id,
                run_id=run.id,
                engine_name=connector.name,
                run_kind=connector.run_kind,
                comparable=connector.comparable,
                metrics=observation.metrics,
            )
            self.store.save_model("score_snapshots", snapshot)
            score_snapshot_ids.append(snapshot.id)

        artifact_ids: list[str] = []
        for artifact in execution.artifacts:
            stored_artifact = BenchmarkArtifact(
                project_id=run.project_id,
                run_id=run.id,
                query_cluster_id=run.query_cluster_id,
                engine_name=run.engine_name,
                run_kind=run.run_kind,
                prompt_version=execution.prompt_version,
                connector_kind=execution.connector_kind,
                query_text=artifact.query_text,
                prompt_text=artifact.prompt_text,
                raw_response=artifact.raw_response,
                metadata=artifact.metadata,
            )
            self.store.save_model("run_artifacts", stored_artifact)
            artifact_ids.append(stored_artifact.id)

        completed = run.model_copy(
            update={
                "status": JobStatus.completed,
                "comparable": execution.comparable,
                "observations": observations,
                "score_snapshot_ids": score_snapshot_ids,
                "artifact_ids": artifact_ids,
                "completed_at": now_iso(),
            }
        )
        return self.store.save_model("runs", completed)

    def create_run(
        self,
        project_id: str,
        query_cluster_id: str,
        engine_name: str,
        candidate_page_ids: list[str] | None = None,
        run_kind: RunKind = RunKind.benchmark,
        prompt_version: str = "newgeo-benchmark-v1",
        connector_kind: str = "heuristic",
        connector_config: dict[str, Any] | None = None,
        queue_only: bool = False,
    ) -> BenchmarkRun:
        run = BenchmarkRun(
            project_id=project_id,
            query_cluster_id=query_cluster_id,
            engine_name=engine_name,
            run_kind=run_kind,
            prompt_version=prompt_version,
            connector_kind=connector_kind,
            connector_config=connector_config or {},
            candidate_page_ids=candidate_page_ids or [],
            status=JobStatus.queued if queue_only else JobStatus.running,
        )
        self.store.save_model("runs", run)
        if queue_only:
            return run
        try:
            return self._execute_run(run)
        except Exception as exc:
            failed = run.model_copy(update={"status": JobStatus.failed, "error": str(exc), "completed_at": now_iso()})
            self.store.save_model("runs", failed)
            raise

    def get_run(self, run_id: str) -> BenchmarkRun:
        run = self.store.get_model("runs", BenchmarkRun, run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        return run

    def create_recommendation(
        self,
        project_id: str,
        page_id: str,
        context_pack_id: str,
        query_cluster_id: str,
        engine_name: str = "newgeo-contextual-v1",
        queue_only: bool = False,
    ) -> Recommendation:
        recommendation = Recommendation(
            project_id=project_id,
            page_id=page_id,
            context_pack_id=context_pack_id,
            query_cluster_id=query_cluster_id,
            engine_name=engine_name,
            status=RecommendationStatus.queued if queue_only else RecommendationStatus.generated,
        )
        self.store.save_model("recommendations", recommendation)
        if queue_only:
            return recommendation
        try:
            return self._execute_recommendation(recommendation)
        except Exception as exc:
            failed = recommendation.model_copy(update={"status": RecommendationStatus.failed, "error": str(exc)})
            self.store.save_model("recommendations", failed)
            raise

    def _execute_recommendation(self, recommendation: Recommendation) -> Recommendation:
        page, snapshot = self._page_snapshot(recommendation.page_id)
        context_pack = self.store.get_model("context_packs", ContextPack, recommendation.context_pack_id)
        if context_pack is None:
            raise ValueError(f"Context pack not found: {recommendation.context_pack_id}")
        query_cluster = self.store.get_model("query_clusters", QueryCluster, recommendation.query_cluster_id)
        if query_cluster is None:
            raise ValueError(f"Query cluster not found: {recommendation.query_cluster_id}")

        candidate_ids = query_cluster.target_page_ids or [page.id]
        candidate_pages = self._candidate_pages(recommendation.project_id, candidate_ids)
        bundle = generate_recommendation_bundle(
            page=page,
            original_markdown=snapshot.normalized_markdown,
            context_pack=context_pack,
            query_cluster=query_cluster,
            candidate_pages=candidate_pages,
        )
        generated = recommendation.model_copy(update={"bundle": bundle, "status": RecommendationStatus.generated})
        return self.store.save_model("recommendations", generated)

    def get_recommendation(self, recommendation_id: str) -> Recommendation:
        recommendation = self.store.get_model("recommendations", Recommendation, recommendation_id)
        if recommendation is None:
            raise ValueError(f"Recommendation not found: {recommendation_id}")
        return recommendation

    def approve_recommendation(self, recommendation_id: str, approved_by: str, note: str | None = None) -> Recommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation.bundle is None:
            raise ValueError("Recommendation has not been generated yet.")

        failures = [check for check in recommendation.bundle.constraint_checks if check.status == "fail"]
        if failures:
            raise ValueError("Recommendation cannot be approved while constraint failures remain.")

        approval = Approval(recommendation_id=recommendation_id, approved_by=approved_by, note=note)
        self.store.save_model("approvals", approval)
        approved = recommendation.model_copy(
            update={"status": RecommendationStatus.approved, "approved_at": approval.approved_at}
        )
        return self.store.save_model("recommendations", approved)

    def export_recommendation(self, recommendation_id: str) -> Recommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation.status not in {RecommendationStatus.approved, RecommendationStatus.exported}:
            raise ValueError("Recommendation must be approved before export.")
        if recommendation.bundle is None:
            raise ValueError("Recommendation has no generated bundle to export.")

        export_dir = Path(os.environ.get("NEWGEO_EXPORT_DIR", "exports"))
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{recommendation.page_id}-{recommendation.id}.md"
        export_path.write_text(recommendation.bundle.rewritten_markdown, encoding="utf-8")

        exported = recommendation.model_copy(
            update={"status": RecommendationStatus.exported, "export_path": str(export_path)}
        )
        return self.store.save_model("recommendations", exported)

    def get_dashboard(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        pages = self.list_project_pages(project_id)
        context_packs = self.list_project_context_packs(project_id)
        query_clusters = self.list_project_query_clusters(project_id)
        runs = sorted(self.list_project_runs(project_id), key=lambda item: item.created_at, reverse=True)
        recommendations = sorted(
            self.list_project_recommendations(project_id), key=lambda item: item.created_at, reverse=True
        )
        score_snapshots = sorted(
            self.list_project_score_snapshots(project_id), key=lambda item: item.created_at, reverse=True
        )

        page_scores: dict[str, float] = {}
        for snapshot in score_snapshots:
            page_scores.setdefault(snapshot.page_id, snapshot.metrics.overall_score)

        return {
            "project": project,
            "summary": {
                "page_count": len(pages),
                "context_pack_count": len(context_packs),
                "query_cluster_count": len(query_clusters),
                "run_count": len(runs),
                "recommendation_count": len(recommendations),
            },
            "pages": [
                {
                    **page.model_dump(mode="json"),
                    "latest_score": page_scores.get(page.id, 0.0),
                }
                for page in pages
            ],
            "context_packs": [pack.model_dump(mode="json") for pack in context_packs],
            "query_clusters": [cluster.model_dump(mode="json") for cluster in query_clusters],
            "runs": [run.model_dump(mode="json") for run in runs[:10]],
            "recommendations": [rec.model_dump(mode="json") for rec in recommendations[:10]],
            "score_snapshots": [snapshot.model_dump(mode="json") for snapshot in score_snapshots[:20]],
        }

    def process_pending_jobs(self) -> dict[str, int]:
        processed_runs = 0
        processed_recommendations = 0

        for run in self.store.list_models("runs", BenchmarkRun):
            if run.status != JobStatus.queued:
                continue
            running = run.model_copy(update={"status": JobStatus.running})
            self.store.save_model("runs", running)
            try:
                self._execute_run(running)
            except Exception as exc:
                failed = running.model_copy(
                    update={"status": JobStatus.failed, "error": str(exc), "completed_at": now_iso()}
                )
                self.store.save_model("runs", failed)
            processed_runs += 1

        for recommendation in self.store.list_models("recommendations", Recommendation):
            if recommendation.status != RecommendationStatus.queued:
                continue
            try:
                self._execute_recommendation(recommendation)
            except Exception as exc:
                failed = recommendation.model_copy(update={"status": RecommendationStatus.failed, "error": str(exc)})
                self.store.save_model("recommendations", failed)
            processed_recommendations += 1

        return {"runs": processed_runs, "recommendations": processed_recommendations}
