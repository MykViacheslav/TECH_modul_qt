from __future__ import annotations

from typing import Protocol

from src.domain.module_models import ModuleDef
from src.storage.module_store_json import ModuleStoreJson


class ModuleRepository(Protocol):
    def get_by_id(self, module_id: str) -> ModuleDef | None:
        ...

    def get_by_name(self, name: str) -> ModuleDef | None:
        ...

    def save(self, module: ModuleDef) -> None:
        ...


class JsonModuleRepository:
    def __init__(self, store: ModuleStoreJson | None = None) -> None:
        self._store = store if store is not None else ModuleStoreJson()

    def get_by_id(self, module_id: str) -> ModuleDef | None:
        return self._store.get_by_id(str(module_id or "").strip())

    def get_by_name(self, name: str) -> ModuleDef | None:
        return self._store.get(str(name or "").strip())

    def save(self, module: ModuleDef) -> None:
        self._store.overwrite(module)

