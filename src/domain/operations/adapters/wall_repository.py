from __future__ import annotations

from typing import Protocol

from src.domain.wall_models import WallLayoutDef
from src.storage.wall_store_json import WallStoreJson


class WallRepository(Protocol):
    def get_by_name(self, name: str) -> WallLayoutDef | None:
        ...

    def save(self, wall: WallLayoutDef) -> None:
        ...


class JsonWallRepository:
    def __init__(self, store: WallStoreJson | None = None) -> None:
        self._store = store if store is not None else WallStoreJson()

    def get_by_name(self, name: str) -> WallLayoutDef | None:
        return self._store.get(str(name or "").strip())

    def save(self, wall: WallLayoutDef) -> None:
        existing = self._store.get(str(getattr(wall, "name", "") or ""))
        if existing is None:
            self._store.save_new(wall)
            return
        self._store.overwrite(wall)

