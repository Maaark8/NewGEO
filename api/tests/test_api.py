from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class ApiRouteFunctionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["NEWGEO_STORE_PATH"] = str(Path(self.temp_dir.name) / "store.json")
        os.environ["NEWGEO_EXPORT_DIR"] = str(Path(self.temp_dir.name) / "exports")

        import importlib
        import api.app.main as api_main

        self.api_main = importlib.reload(api_main)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seed_and_dashboard_flow(self) -> None:
        seeded = self.api_main.seed_demo()
        projects = self.api_main.list_projects()
        dashboard = self.api_main.get_dashboard(seeded["project_id"])
        run_id = dashboard["runs"][0]["id"]
        artifacts = self.api_main.get_run_artifacts(run_id)

        self.assertTrue(seeded["seeded"])
        self.assertGreaterEqual(len(projects), 1)
        self.assertGreaterEqual(dashboard["summary"]["page_count"], 1)
        self.assertGreaterEqual(len(dashboard["runs"]), 1)
        self.assertGreaterEqual(len(dashboard["recommendations"]), 1)
        self.assertGreaterEqual(len(artifacts), 1)
