from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from newgeo_core.ingestion import CrawlRequest, CrawlSeed
from newgeo_core.migration import export_json_to_sqlite
from newgeo_core.models import ConstraintType, ContentSnapshot, RunKind
from newgeo_core.service import NewGeoService
from newgeo_core.storage import JsonStore
from newgeo_core.storage_backends import SqliteStore


class NewGeoServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        store_path = Path(self.temp_dir.name) / "store.json"
        self.service = NewGeoService(JsonStore(store_path))
        self.project = self.service.create_project(
            name="Acme Docs",
            base_url="https://docs.acme.test",
            description="Technical docs for Acme's observability platform.",
        )
        self.page = self.service.import_page(
            project_id=self.project.id,
            title="Latency monitoring guide",
            url="https://docs.acme.test/latency",
            markdown="""# Latency monitoring guide

Acme measures p95 latency for API requests and stores data for 14 days by default.

## Steps

1. Enable the HTTP instrumentation package.
2. Create an alert on p95 latency.
3. Review trace waterfalls when the alert fires.
""",
        )
        self.context_pack = self.service.create_context_pack(
            project_id=self.project.id,
            page_id=self.page.id,
            brief="This page should help SRE teams understand setup fast without losing factual accuracy.",
            constraints=[
                {
                    "kind": ConstraintType.locked_fact,
                    "value": "stores data for 14 days by default",
                },
                {
                    "kind": ConstraintType.required_term,
                    "value": "latency monitoring",
                    "strict": False,
                },
                {
                    "kind": ConstraintType.forbidden_claim,
                    "value": "fully autonomous remediation",
                },
            ],
            supporting_documents=[
                {
                    "title": "Alerting reference",
                    "body": "Alerting policies can watch p95 latency, error rate, and saturation in the same dashboard.",
                }
            ],
        )
        self.query_cluster = self.service.create_query_cluster(
            project_id=self.project.id,
            name="Latency monitoring",
            queries=[
                {"text": "latency monitoring guide", "intent": "informational"},
                {"text": "how to monitor api latency", "intent": "informational"},
            ],
            target_page_ids=[self.page.id],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_recommendation_preserves_locked_facts_and_context(self) -> None:
        recommendation = self.service.create_recommendation(
            project_id=self.project.id,
            page_id=self.page.id,
            context_pack_id=self.context_pack.id,
            query_cluster_id=self.query_cluster.id,
        )

        self.assertIsNotNone(recommendation.bundle)
        self.assertIn("stores data for 14 days by default", recommendation.bundle.rewritten_markdown)
        self.assertIn("Related internal context", recommendation.bundle.rewritten_markdown)
        self.assertGreaterEqual(recommendation.bundle.preview.score_delta, 0.0)
        failures = [check for check in recommendation.bundle.constraint_checks if check.status == "fail"]
        self.assertEqual(failures, [])

    def test_benchmark_run_generates_observations(self) -> None:
        run = self.service.create_run(
            project_id=self.project.id,
            query_cluster_id=self.query_cluster.id,
            engine_name="newgeo-benchmark-v1",
            candidate_page_ids=[self.page.id],
            run_kind=RunKind.benchmark,
        )

        self.assertEqual(run.status.value, "completed")
        self.assertEqual(len(run.observations), 1)
        self.assertGreaterEqual(len(run.artifact_ids), 1)
        self.assertGreater(run.observations[0].metrics.overall_score, 0.0)
        artifacts = self.service.list_run_artifacts(run.id)
        self.assertGreaterEqual(len(artifacts), 1)
        self.assertIn("Prompt version", artifacts[0].prompt_text)
        self.assertIn("rankings", artifacts[0].raw_response)

    def test_approval_and_export_flow(self) -> None:
        recommendation = self.service.create_recommendation(
            project_id=self.project.id,
            page_id=self.page.id,
            context_pack_id=self.context_pack.id,
            query_cluster_id=self.query_cluster.id,
        )
        approved = self.service.approve_recommendation(recommendation.id, approved_by="reviewer@example.com")
        exported = self.service.export_recommendation(approved.id)

        self.assertEqual(approved.status.value, "approved")
        self.assertEqual(exported.status.value, "exported")
        self.assertTrue(Path(exported.export_path).exists())

    def test_crawl_request_imports_html_seed_content(self) -> None:
        seed_url = "https://docs.acme.test/guides/tracing"
        crawled = self.service.crawl_project(
            self.project.id,
            crawl_request=CrawlRequest(
                project_id=self.project.id,
                base_url=self.project.base_url,
                seeds=[CrawlSeed(url=seed_url, label="Tracing guide")],
                include_sitemap_variants=False,
                raw_html_by_url={
                    seed_url: "<html><head><title>Tracing setup</title></head><body><h1>Tracing setup</h1><p>Install the SDK and export spans.</p></body></html>"
                },
            ),
        )

        self.assertEqual(len(crawled), 1)
        snapshot = self.service.store.get_model("snapshots", ContentSnapshot, crawled[0].current_snapshot_id)
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertIn("Install the SDK and export spans.", snapshot.normalized_markdown)


class StorageBackendParityTestCase(unittest.TestCase):
    def test_sqlite_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "store.sqlite3"
            service = NewGeoService(SqliteStore(sqlite_path))
            project = service.create_project(name="SQLite Project", base_url="https://sqlite.test")
            listed = service.list_projects()
            loaded = service.get_project(project.id)

            self.assertEqual(len(listed), 1)
            self.assertEqual(loaded.name, "SQLite Project")

    def test_export_json_to_sqlite_preserves_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "source.json"
            sqlite_path = Path(temp_dir) / "target.sqlite3"
            source_service = NewGeoService(JsonStore(json_path))
            created = source_service.create_project(name="Migrated Project", base_url="https://migrate.test")

            result = export_json_to_sqlite(json_path, sqlite_path, overwrite=True)
            migrated_service = NewGeoService(SqliteStore(sqlite_path))
            loaded = migrated_service.get_project(created.id)

            self.assertGreaterEqual(result.total_copied, 1)
            self.assertEqual(loaded.name, "Migrated Project")
