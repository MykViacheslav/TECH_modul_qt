from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.assembly_models import FurnitureAssemblyDef


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


def _default_data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)

    root = Path(__file__).resolve().parents[2]
    proj = root.parent
    return proj / "data"


class AssemblyStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _default_data_dir() / "assemblies.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_names(self) -> List[str]:
        return sorted(list(self._read_all().keys()))

    def list_assemblies(self) -> List[FurnitureAssemblyDef]:
        raw_all = self._read_all()
        assemblies: List[FurnitureAssemblyDef] = []
        for name in sorted(raw_all.keys()):
            raw = raw_all.get(name)
            if isinstance(raw, dict):
                assemblies.append(FurnitureAssemblyDef.from_dict(raw))
        return sorted(
            assemblies,
            key=lambda item: (
                str(getattr(item, "client_name", "") or "").lower(),
                str(getattr(item, "order_name", "") or "").lower(),
                str(getattr(item, "name", "") or "").lower(),
            ),
        )

    def get(self, name: str) -> Optional[FurnitureAssemblyDef]:
        raw = self._read_all().get(name)
        return FurnitureAssemblyDef.from_dict(raw) if isinstance(raw, dict) else None

    def save_new(self, assembly: FurnitureAssemblyDef) -> StoreResult:
        data = self._read_all()
        if assembly.name in data:
            return StoreResult(False, f'Nazwa "{assembly.name}" juz istnieje. Uzyj "Nadpisz".')
        data[assembly.name] = assembly.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano nowy komplet: "{assembly.name}".')

    def overwrite(self, assembly: FurnitureAssemblyDef) -> StoreResult:
        data = self._read_all()
        data[assembly.name] = assembly.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Nadpisano komplet: "{assembly.name}".')

    def delete(self, name: str) -> StoreResult:
        data = self._read_all()
        if name not in data:
            return StoreResult(False, f'Nie ma kompletu "{name}" w bazie.')
        data.pop(name, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto komplet: "{name}".')

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
