from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.assembly_models import FurnitureAssemblyDef
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


def _default_data_dir() -> Path:
    return data_dir()


class AssemblyStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _default_data_dir() / "assemblies.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_names(self) -> List[str]:
        # Keep name listing for UI if needed, but ordered by name
        assemblies = self.list_assemblies()
        return [a.name for a in assemblies]

    def list_assemblies(self) -> List[FurnitureAssemblyDef]:
        raw_all = self._read_all()
        assemblies: List[FurnitureAssemblyDef] = []
        for aid in raw_all.keys():
            raw = raw_all.get(aid)
            if isinstance(raw, dict):
                assemblies.append(FurnitureAssemblyDef.from_dict(raw))
        # Ensure every assembly has an ID (migration)
        for a in assemblies:
            if not a.assembly_id:
                from src.domain.assembly_models import new_assembly_id
                a.assembly_id = new_assembly_id()
        
        return sorted(
            assemblies,
            key=lambda item: (
                str(getattr(item, "client_name", "") or "").lower(),
                str(getattr(item, "order_name", "") or "").lower(),
                str(getattr(item, "name", "") or "").lower(),
            ),
        )

    def get(self, assembly_id: str) -> Optional[FurnitureAssemblyDef]:
        aid_norm = str(assembly_id or "").strip()
        if not aid_norm:
            return None
        data = self._read_all()
        # Lookup by ID
        raw = data.get(aid_norm)
        if isinstance(raw, dict):
            return FurnitureAssemblyDef.from_dict(raw)
        # Fallback to name for legacy data during transition
        for val in data.values():
            if isinstance(val, dict) and str(val.get("name", "")).strip() == aid_norm:
                return FurnitureAssemblyDef.from_dict(val)
        return None

    def save_new(self, assembly: FurnitureAssemblyDef) -> StoreResult:
        from src.domain.assembly_models import new_assembly_id
        if not assembly.assembly_id:
            assembly.assembly_id = new_assembly_id()
        
        data = self._read_all()
        if assembly.assembly_id in data:
            return StoreResult(False, f'ID "{assembly.assembly_id}" juz istnieje.')
        
        # Check for duplicate names (optional UX safety)
        for val in data.values():
            if isinstance(val, dict) and val.get("name") == assembly.name:
                return StoreResult(False, f'Nazwa "{assembly.name}" juz istnieje.')

        data[assembly.assembly_id] = assembly.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano новий комплект: "{assembly.name}".')

    def overwrite(self, assembly: FurnitureAssemblyDef) -> StoreResult:
        if not assembly.assembly_id:
            from src.domain.assembly_models import new_assembly_id
            assembly.assembly_id = new_assembly_id()
        
        data = self._read_all()
        data[assembly.assembly_id] = assembly.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Nadpisano komplet: "{assembly.name}".')

    def delete(self, assembly_id: str) -> StoreResult:
        aid_norm = str(assembly_id or "").strip()
        data = self._read_all()
        if aid_norm not in data:
            # Fallback search by name for legacy
            found_id = None
            for gid, val in data.items():
                if isinstance(val, dict) and val.get("name") == aid_norm:
                    found_id = gid
                    break
            if not found_id:
                return StoreResult(False, f'Nie ma kompletu "{aid_norm}" w bazie.')
            aid_norm = found_id
            
        data.pop(aid_norm, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto komplet ID: "{aid_norm}".')

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
