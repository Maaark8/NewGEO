from __future__ import annotations

import json
import os

from newgeo_core.seed import seed_demo_project
from newgeo_core.service import NewGeoService


def main() -> None:
    service = NewGeoService()
    identifiers = seed_demo_project(service)
    print(json.dumps({"store": os.environ.get("NEWGEO_STORE_PATH", ".data/newgeo-store.json"), **identifiers}, indent=2))


if __name__ == "__main__":
    main()

