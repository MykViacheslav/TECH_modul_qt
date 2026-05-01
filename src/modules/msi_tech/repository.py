"""
TechModuleRepository — dostęp do danych dla MSI Tech Module.

Aktualnie odczyt/zapis przez JSON (data/modules.json).
TODO: migracja do SQLite wzorowana na order_store_sqlite.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .models import TechModule


def _data_dir() -> Path:
    """Zwraca katalog danych — respektuje TECH_MODUL_DATA_DIR."""
    import os
    env = os.environ.get("TECH_MODUL_DATA_DIR", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[4] / "data"


class TechModuleRepository:
    """Repozytorium modułów technicznych (format JSON)."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._path = (data_dir or _data_dir()) / "modules.json"

    # --- odczyt ---

    def list_all(self) -> list[TechModule]:
        raw = self._load_raw()
        result: list[TechModule] = []
        for entry in raw:
            try:
                result.append(self._deserialize(entry))
            except (KeyError, TypeError):
                pass  # pomiń uszkodzone rekordy
        return result

    def load(self, module_id: str) -> TechModule | None:
        for entry in self._load_raw():
            if entry.get("id") == module_id:
                try:
                    return self._deserialize(entry)
                except (KeyError, TypeError):
                    return None
        return None

    # --- zapis ---

    def save(self, module: TechModule) -> None:
        if not module.id:
            module.id = str(uuid.uuid4())
        raw = self._load_raw()
        updated = False
        for i, entry in enumerate(raw):
            if entry.get("id") == module.id:
                raw[i] = self._serialize(module)
                updated = True
                break
        if not updated:
            raw.append(self._serialize(module))
        self._save_raw(raw)

    def delete(self, module_id: str) -> bool:
        raw = self._load_raw()
        new_raw = [e for e in raw if e.get("id") != module_id]
        if len(new_raw) == len(raw):
            return False
        self._save_raw(new_raw)
        return True

    # --- prywatne ---

    def _load_raw(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with self._path.open(encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_raw(self, raw: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)

    def _serialize(self, m: TechModule) -> dict[str, Any]:
        return {
            "id": m.id,
            "name": m.name,
            "width_mm": m.width_mm,
            "height_mm": m.height_mm,
            "depth_mm": m.depth_mm,
            "material_thickness_mm": m.material_thickness_mm,
            "back_thickness_mm": m.back_thickness_mm,
            "num_drawers": m.num_drawers,
            "drawer_system": m.drawer_system,
            "drawer_height_key": m.drawer_height_key,
            "num_shelves": m.num_shelves,
            "has_door": m.has_door,
            "door_type": m.door_type,
            "num_doors": m.num_doors,
            "has_lift": m.has_lift,
            "edge_banding_front": m.edge_banding_front,
            "edge_banding_visible": m.edge_banding_visible,
            "notes": m.notes,
            "tags": m.tags,
        }

    def _deserialize(self, d: dict[str, Any]) -> TechModule:
        # TODO: dodać walidację schemy przy migracji do SQLite
        return TechModule(
            id=d["id"],
            name=d["name"],
            width_mm=float(d["width_mm"]),
            height_mm=float(d["height_mm"]),
            depth_mm=float(d["depth_mm"]),
            material_thickness_mm=float(d.get("material_thickness_mm", 18.0)),
            back_thickness_mm=float(d.get("back_thickness_mm", 3.0)),
            num_drawers=int(d.get("num_drawers", 0)),
            drawer_system=d.get("drawer_system", "blum_antaro"),
            drawer_height_key=d.get("drawer_height_key", "M"),
            num_shelves=int(d.get("num_shelves", 1)),
            has_door=bool(d.get("has_door", False)),
            door_type=d.get("door_type", "overlay"),
            num_doors=int(d.get("num_doors", 1)),
            has_lift=bool(d.get("has_lift", False)),
            edge_banding_front=d.get("edge_banding_front", "abs_2mm"),
            edge_banding_visible=d.get("edge_banding_visible", "abs_2mm"),
            notes=d.get("notes", ""),
            tags=list(d.get("tags", [])),
        )
