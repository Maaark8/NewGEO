from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import models
from .storage_backends import DEFAULT_COLLECTIONS, JsonFileBackend, SqliteStore, StorageBackend, create_storage_backend


@dataclass(slots=True)
class MigrationPlan:
    source_path: str | Path
    destination_path: str | Path
    source_backend: str | None = None
    destination_backend: str | None = None
    overwrite: bool = False
    collections: tuple[str, ...] = DEFAULT_COLLECTIONS


@dataclass(slots=True)
class MigrationResult:
    source_path: str
    destination_path: str
    collections: list[str] = field(default_factory=list)
    copied_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_copied(self) -> int:
        return sum(self.copied_counts.values())


MODEL_CLASS_BY_COLLECTION = {
    "projects": models.Project,
    "pages": models.Page,
    "snapshots": models.ContentSnapshot,
    "context_packs": models.ContextPack,
    "query_clusters": models.QueryCluster,
    "runs": models.BenchmarkRun,
    "run_artifacts": models.BenchmarkArtifact,
    "recommendations": models.Recommendation,
    "approvals": models.Approval,
    "score_snapshots": models.ScoreSnapshot,
}


def _resolve_store(path: str | Path, backend: str | None = None) -> StorageBackend:
    return create_storage_backend(path=path, backend=backend)


def _delete_collection(store: StorageBackend, collection: str, item_ids: Iterable[str]) -> None:
    for item_id in item_ids:
        store.delete_model(collection, item_id)


def _close_store(store: StorageBackend) -> None:
    close = getattr(store, "close", None)
    if callable(close):
        close()


def copy_collections(
    source: StorageBackend,
    destination: StorageBackend,
    collections: Iterable[str] = DEFAULT_COLLECTIONS,
    overwrite: bool = False,
) -> MigrationResult:
    copied_counts: dict[str, int] = {}
    copied_collections: list[str] = []

    for collection in collections:
        model_cls = MODEL_CLASS_BY_COLLECTION.get(collection)
        if model_cls is None:
            continue

        items = source.list_models(collection, model_cls)
        if overwrite:
            existing = destination.list_models(collection, model_cls)
            _delete_collection(destination, collection, [item.id for item in existing])

        for item in items:
            destination.save_model(collection, item)

        copied_counts[collection] = len(items)
        copied_collections.append(collection)

    source_path = str(getattr(source, "path", "source"))
    destination_path = str(getattr(destination, "path", "destination"))
    return MigrationResult(
        source_path=source_path,
        destination_path=destination_path,
        collections=copied_collections,
        copied_counts=copied_counts,
    )


def migrate_store(plan: MigrationPlan) -> MigrationResult:
    source = _resolve_store(plan.source_path, plan.source_backend)
    destination = _resolve_store(plan.destination_path, plan.destination_backend)
    try:
        return copy_collections(source, destination, collections=plan.collections, overwrite=plan.overwrite)
    finally:
        _close_store(source)
        _close_store(destination)


def export_json_to_sqlite(
    source_json_path: str | Path,
    destination_sqlite_path: str | Path,
    overwrite: bool = False,
) -> MigrationResult:
    source = JsonFileBackend(source_json_path)
    destination = SqliteStore(destination_sqlite_path)
    try:
        return copy_collections(source, destination, overwrite=overwrite)
    finally:
        _close_store(source)
        _close_store(destination)
