from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "packages" / "newgeo_core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from newgeo_core.migration import MigrationPlan, export_json_to_sqlite, migrate_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copy NewGEO collections between storage backends.")
    parser.add_argument("source", help="Source store path, e.g. .data/newgeo-store.json")
    parser.add_argument("destination", help="Destination store path, e.g. .data/newgeo-store.sqlite3")
    parser.add_argument("--source-backend", default=None, help="Override source backend: json, sqlite")
    parser.add_argument("--destination-backend", default=None, help="Override destination backend: json, sqlite")
    parser.add_argument("--overwrite", action="store_true", help="Replace destination records before copying")
    parser.add_argument(
        "--export-json-to-sqlite",
        action="store_true",
        help="Shortcut for copying a JSON file into a SQLite database.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.export_json_to_sqlite:
        result = export_json_to_sqlite(args.source, args.destination, overwrite=args.overwrite)
    else:
        plan = MigrationPlan(
            source_path=args.source,
            destination_path=args.destination,
            source_backend=args.source_backend,
            destination_backend=args.destination_backend,
            overwrite=args.overwrite,
        )
        result = migrate_store(plan)

    print(
        json.dumps(
            {
                "source": result.source_path,
                "destination": result.destination_path,
                "collections": result.collections,
                "copied_counts": result.copied_counts,
                "total_copied": result.total_copied,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

