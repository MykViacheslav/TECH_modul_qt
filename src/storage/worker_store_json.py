from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.worker_models import WorkerDef


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class WorkerStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            root = Path(__file__).resolve().parents[2]
            proj = root.parent
            path = proj / "data" / "workers.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_names(self) -> List[str]:
        return sorted(list(self._read_all().keys()))

    def list_workers(self) -> List[WorkerDef]:
        raw_all = self._read_all()
        return [
            WorkerDef.from_dict(raw_all[name])
            for name in sorted(raw_all.keys())
            if isinstance(raw_all.get(name), dict)
        ]

    def get(self, name: str) -> Optional[WorkerDef]:
        raw = self._read_all().get(name)
        return WorkerDef.from_dict(raw) if isinstance(raw, dict) else None

    def save_new(self, worker: WorkerDef) -> StoreResult:
        data = self._read_all()
        if worker.name in data:
            return StoreResult(False, f'Pracownik "{worker.name}" juz istnieje. Uzyj "Nadpisz".')
        data[worker.name] = worker.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano pracownika: "{worker.name}".')

    def overwrite(self, worker: WorkerDef) -> StoreResult:
        data = self._read_all()
        data[worker.name] = worker.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Nadpisano pracownika: "{worker.name}".')

    def delete(self, name: str) -> StoreResult:
        data = self._read_all()
        if name not in data:
            return StoreResult(False, f'Nie ma pracownika "{name}" w bazie.')
        data.pop(name, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto pracownika: "{name}".')

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
