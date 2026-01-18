from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class ModuleRecord:
    name: str
    state: Dict[str, Any]


class ModuleLibrary:
    """
    Prosta baza modułów (JSON).
    - Tworzy plik automatycznie jeśli nie istnieje
    - Zabezpiecza przed zepsutym JSON
    """
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"modules": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self) -> Dict[str, Any]:
        self._ensure_file()
        try:
            raw = self.path.read_text(encoding="utf-8", errors="ignore").strip()
            if not raw:
                return {"modules": {}}
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"modules": {}}
            if "modules" not in data or not isinstance(data.get("modules"), dict):
                data["modules"] = {}
            return data
        except Exception:
            # jeśli JSON zepsuty — zrób backup i start od nowa
            try:
                bak = self.path.with_suffix(self.path.suffix + ".corrupt.bak")
                bak.write_text(self.path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
            except Exception:
                pass
            return {"modules": {}}

    def _write(self, data: Dict[str, Any]) -> None:
        self._ensure_file()
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, name: str) -> ModuleRecord:
        name = (name or "").strip()
        if not name:
            raise KeyError("Pusta nazwa modułu.")
        data = self._read()
        mods = data.get("modules", {})
        if name not in mods:
            raise KeyError(f"Nie znaleziono modułu: {name}")
        st = mods.get(name) or {}
        if not isinstance(st, dict):
            st = {}
        return ModuleRecord(name=name, state=st)

    def upsert(self, record: ModuleRecord) -> None:
        name = (record.name or "").strip()
        if not name:
            raise ValueError("Pusta nazwa modułu.")
        data = self._read()
        data["modules"][name] = record.state or {}
        self._write(data)
