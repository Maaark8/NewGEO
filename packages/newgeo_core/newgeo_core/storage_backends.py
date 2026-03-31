from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)

DEFAULT_COLLECTIONS = (
    "projects",
    "pages",
    "snapshots",
    "context_packs",
    "query_clusters",
    "runs",
    "run_artifacts",
    "recommendations",
    "approvals",
    "score_snapshots",
)


@runtime_checkable
class StorageBackend(Protocol):
    def save_model(self, collection: str, model: BaseModel) -> BaseModel:
        ...

    def get_model(self, collection: str, model_cls: type[ModelT], item_id: str) -> ModelT | None:
        ...

    def list_models(self, collection: str, model_cls: type[ModelT], **filters: Any) -> list[ModelT]:
        ...

    def delete_model(self, collection: str, item_id: str) -> None:
        ...


class JsonFileBackend:
    def __init__(self, path: str | Path = ".data/newgeo-store.json") -> None:
        self.path = Path(path)
        self.lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_state(self._empty_state())

    @staticmethod
    def _empty_state() -> dict[str, dict[str, Any]]:
        return {collection: {} for collection in DEFAULT_COLLECTIONS}

    def _read_state(self) -> dict[str, dict[str, Any]]:
        with self.lock:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        for collection in DEFAULT_COLLECTIONS:
            state.setdefault(collection, {})
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        with self.lock:
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False)

    def save_model(self, collection: str, model: BaseModel) -> BaseModel:
        state = self._read_state()
        state.setdefault(collection, {})
        state[collection][model.id] = model.model_dump(mode="json")
        self._write_state(state)
        return model

    def get_model(self, collection: str, model_cls: type[ModelT], item_id: str) -> ModelT | None:
        payload = self._read_state().get(collection, {}).get(item_id)
        if payload is None:
            return None
        return model_cls.model_validate(payload)

    def list_models(self, collection: str, model_cls: type[ModelT], **filters: Any) -> list[ModelT]:
        items = self._read_state().get(collection, {}).values()
        result: list[ModelT] = []
        for payload in items:
            if all(payload.get(key) == value for key, value in filters.items()):
                result.append(model_cls.model_validate(payload))
        return result

    def delete_model(self, collection: str, item_id: str) -> None:
        state = self._read_state()
        state.setdefault(collection, {})
        state[collection].pop(item_id, None)
        self._write_state(state)


class SqliteStore:
    def __init__(self, path: str | Path = ".data/newgeo-store.sqlite3") -> None:
        self.path = Path(path)
        self.lock = RLock()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    collection TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, item_id)
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_records_collection ON records(collection)")
            self._conn.commit()

    def save_model(self, collection: str, model: BaseModel) -> BaseModel:
        payload = json.dumps(model.model_dump(mode="json"), ensure_ascii=False)
        with self.lock:
            self._conn.execute(
                """
                INSERT INTO records (collection, item_id, payload, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(collection, item_id)
                DO UPDATE SET payload = excluded.payload, updated_at = CURRENT_TIMESTAMP
                """,
                (collection, model.id, payload),
            )
            self._conn.commit()
        return model

    def get_model(self, collection: str, model_cls: type[ModelT], item_id: str) -> ModelT | None:
        with self.lock:
            row = self._conn.execute(
                "SELECT payload FROM records WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            ).fetchone()
        if row is None:
            return None
        return model_cls.model_validate(json.loads(row["payload"]))

    def list_models(self, collection: str, model_cls: type[ModelT], **filters: Any) -> list[ModelT]:
        with self.lock:
            rows = self._conn.execute(
                "SELECT payload FROM records WHERE collection = ? ORDER BY item_id ASC",
                (collection,),
            ).fetchall()

        result: list[ModelT] = []
        for row in rows:
            payload = json.loads(row["payload"])
            if all(payload.get(key) == value for key, value in filters.items()):
                result.append(model_cls.model_validate(payload))
        return result

    def delete_model(self, collection: str, item_id: str) -> None:
        with self.lock:
            self._conn.execute(
                "DELETE FROM records WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            )
            self._conn.commit()

    def close(self) -> None:
        with self.lock:
            self._conn.close()


def _normalize_backend_name(value: str | None) -> str:
    if not value:
        return "json"
    return value.strip().lower()


def _sqlite_path_for(source_path: str | Path) -> Path:
    raw_path = Path(source_path)
    if str(raw_path) == ":memory:":
        return raw_path
    if raw_path.suffix in {".sqlite", ".sqlite3", ".db"}:
        return raw_path
    if raw_path.suffix == ".json":
        return raw_path.with_suffix(".sqlite3")
    return raw_path.with_suffix(".sqlite3")


def create_storage_backend(path: str | Path = ".data/newgeo-store.json", backend: str | None = None) -> StorageBackend:
    inferred_backend = None
    path_str = str(path)
    if path_str == ":memory:" or Path(path_str).suffix in {".sqlite", ".sqlite3", ".db"}:
        inferred_backend = "sqlite"

    backend_name = _normalize_backend_name(backend or os.environ.get("NEWGEO_STORAGE_BACKEND") or inferred_backend)
    if backend_name in {"json", "jsonfile", "file"}:
        return JsonFileBackend(path)
    if backend_name in {"sqlite", "sql"}:
        sqlite_override = os.environ.get("NEWGEO_SQLITE_PATH")
        sqlite_path = _sqlite_path_for(sqlite_override or path)
        return SqliteStore(sqlite_path)
    if backend_name in {"postgres", "postgresql"}:
        raise NotImplementedError(
            "Postgres storage is not implemented yet. Use the sqlite backend for now and "
            "swap in a Postgres adapter later behind the same StorageBackend protocol."
        )
    return JsonFileBackend(path)
