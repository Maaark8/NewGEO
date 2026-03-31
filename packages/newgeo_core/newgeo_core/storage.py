from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .storage_backends import StorageBackend, create_storage_backend


ModelT = TypeVar("ModelT", bound=BaseModel)


class JsonStore:
    """Compatibility facade for the service layer.

    Keep the current JSON file behavior by default. Set
    `NEWGEO_STORAGE_BACKEND=sqlite` to route the same interface to the
    SQL-backed implementation.
    """

    def __init__(self, path: str | Path = ".data/newgeo-store.json") -> None:
        self._backend: StorageBackend = create_storage_backend(path)
        self.path = Path(getattr(self._backend, "path", path))

    def save_model(self, collection: str, model: BaseModel) -> BaseModel:
        return self._backend.save_model(collection, model)

    def get_model(self, collection: str, model_cls: type[ModelT], item_id: str) -> ModelT | None:
        return self._backend.get_model(collection, model_cls, item_id)

    def list_models(self, collection: str, model_cls: type[ModelT], **filters: Any) -> list[ModelT]:
        return self._backend.list_models(collection, model_cls, **filters)

    def delete_model(self, collection: str, item_id: str) -> None:
        self._backend.delete_model(collection, item_id)


__all__ = [
    "JsonStore",
    "StorageBackend",
]
