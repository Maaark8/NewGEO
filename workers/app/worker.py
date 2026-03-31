from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "packages" / "newgeo_core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from newgeo_core.service import NewGeoService


def run_forever() -> None:
    service = NewGeoService()
    interval = int(os.environ.get("NEWGEO_POLL_INTERVAL_SECONDS", "5"))
    print("NewGEO worker started. Polling for queued jobs...")
    while True:
        processed = service.process_pending_jobs()
        if processed["runs"] or processed["recommendations"]:
            print(f"Processed jobs: {processed}")
        time.sleep(interval)


if __name__ == "__main__":
    run_forever()

