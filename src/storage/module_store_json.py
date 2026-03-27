from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.module_base_group import (
    BASE_GROUP_ORDER,
    normalize_module_base_group,
    sort_module_base_groups,
)
from src.domain.module_models import ModuleDef
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


def _default_data_dir() -> Path:
    return data_dir()


class ModuleStoreJson:
    """
    Pamiec stala: data/modules.json
    (na razie JSON, potem latwo podmienimy na SQLite).
    """
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _default_data_dir() / "modules.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_names(self) -> List[str]:
        return sorted(list(self._read_all().keys()))

    def get(self, name: str) -> Optional[ModuleDef]:
        raw = self._read_all().get(name)
        return ModuleDef.from_dict(raw) if raw else None

    def list_grouped_names(self) -> Dict[str, List[str]]:
        raw_all = self._read_all()
        grouped: Dict[str, List[str]] = {}

        for name in sorted(raw_all.keys()):
            raw = raw_all.get(name) or {}
            module = ModuleDef.from_dict(raw) if isinstance(raw, dict) else ModuleDef(name=str(name or ""))
            base_group = normalize_module_base_group(getattr(module, "base_group", ""))
            grouped.setdefault(base_group, []).append(name)

        ordered_groups = sort_module_base_groups(list(grouped.keys()))
        return {key: grouped.get(key, []) for key in ordered_groups if grouped.get(key)}

    def list_base_groups(self) -> List[str]:
        raw_all = self._read_all()
        groups = set(BASE_GROUP_ORDER)

        for raw in raw_all.values():
            module = ModuleDef.from_dict(raw) if isinstance(raw, dict) else ModuleDef()
            groups.add(normalize_module_base_group(getattr(module, "base_group", "")))

        return sort_module_base_groups(groups)

    def save_new(self, module: ModuleDef) -> StoreResult:
        data = self._read_all()
        if module.name in data:
            return StoreResult(False, f'Nazwa "{module.name}" juz istnieje. Uzyj "Nadpisz".')
        data[module.name] = module.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano nowy modul: "{module.name}".')

    def overwrite(self, module: ModuleDef) -> StoreResult:
        data = self._read_all()
        data[module.name] = module.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Nadpisano modul: "{module.name}".')

    def delete(self, name: str) -> StoreResult:
        data = self._read_all()
        if name not in data:
            return StoreResult(False, f'Nie ma modulu "{name}" w bazie.')
        data.pop(name, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto modul: "{name}".')

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
