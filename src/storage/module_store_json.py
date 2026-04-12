from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.stable_record_id import ensure_module_record_id
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
    Persistent store: data/modules.json
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
        if not isinstance(raw, dict):
            return None
        return ModuleDef.from_dict(raw)

    def get_by_id(self, module_id: str) -> Optional[ModuleDef]:
        wanted = str(module_id or "").strip()
        if not wanted:
            return None
        for raw in self._read_all().values():
            if not isinstance(raw, dict):
                continue
            rec_id = str(raw.get("id", "") or raw.get("module_id", "") or "").strip()
            if rec_id == wanted:
                return ModuleDef.from_dict(raw)
        return None

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
        data[module.name] = self._build_record(module, previous=None)
        self._write_all(data)
        return StoreResult(True, f'Zapisano nowy modul: "{module.name}".')

    def overwrite(self, module: ModuleDef) -> StoreResult:
        data = self._read_all()
        previous = data.get(module.name)
        data[module.name] = self._build_record(module, previous=previous if isinstance(previous, dict) else None)
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
            if not isinstance(data, dict):
                return {}

            if "schema_version" in data and "items" in data:
                raw_items = data.get("items", {})
            else:
                raw_items = data

            items = raw_items if isinstance(raw_items, dict) else {}
            normalized, changed = self._normalize_records(items)
            if changed:
                self._write_all(normalized)
            return normalized
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_records(self, raw_items: Dict[str, Any]) -> tuple[Dict[str, dict], bool]:
        normalized: Dict[str, dict] = {}
        changed = False

        for name, raw in (raw_items or {}).items():
            key = str(name or "").strip()
            if not key:
                changed = True
                continue
            if not isinstance(raw, dict):
                changed = True
                continue

            rec = self._normalize_single_record(key, raw)
            if rec != raw:
                changed = True
            normalized[key] = rec

        return normalized, changed

    def _normalize_single_record(self, name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(raw or {})
        payload["name"] = str(payload.get("name") or name)
        payload = ensure_module_record_id(payload)

        now_iso = self._now_iso()
        created_at = str(payload.get("created_at", "") or "").strip()
        updated_at = str(payload.get("updated_at", "") or "").strip()
        if not created_at:
            payload["created_at"] = now_iso
        if not updated_at:
            payload["updated_at"] = now_iso
        return payload

    def _build_record(self, module: ModuleDef, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = dict(module.to_dict() or {})
        payload["name"] = str(getattr(module, "name", payload.get("name", "")) or payload.get("name", ""))

        if previous:
            prev = self._normalize_single_record(payload["name"], previous)
            if not str(payload.get("id", "") or "").strip():
                payload["id"] = str(prev.get("id", "") or "")
            if not str(payload.get("module_id", "") or "").strip():
                payload["module_id"] = str(prev.get("module_id", "") or "")
            if not str(payload.get("created_at", "") or "").strip():
                payload["created_at"] = str(prev.get("created_at", "") or "")

        payload = ensure_module_record_id(payload)
        payload["created_at"] = str(payload.get("created_at", "") or self._now_iso())
        payload["updated_at"] = self._now_iso()

        try:
            module.module_id = str(payload.get("module_id", "") or "")
        except Exception:
            pass

        return payload

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
