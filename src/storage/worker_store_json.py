from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.worker_models import WorkerDef
from src.domain.worker_qr import extract_worker_identifier, normalize_worker_id
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class WorkerStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "workers.json"
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

    def get_by_worker_id(self, worker_id: str) -> Optional[WorkerDef]:
        worker_id_norm = normalize_worker_id(worker_id)
        if not worker_id_norm:
            return None
        for worker in self.list_workers():
            if normalize_worker_id(getattr(worker, "worker_id", "")) == worker_id_norm:
                return worker
        return None

    def get_by_pin_code(self, pin_code: str) -> Optional[WorkerDef]:
        pin_code_norm = str(pin_code or "").strip()
        if not pin_code_norm:
            return None
        for worker in self.list_workers():
            worker_pin = str(getattr(worker, "pin_code", "") or "").strip()
            if worker_pin and worker_pin == pin_code_norm:
                return worker
        return None

    def resolve_identifier(self, identifier: str) -> Optional[WorkerDef]:
        """
        Resolve a worker either from a QR payload, worker_id or name.
        """
        worker_id, worker_name = extract_worker_identifier(identifier)
        if worker_id:
            worker = self.get_by_worker_id(worker_id)
            if worker is not None:
                return worker
        if worker_name:
            worker = self.get(worker_name)
            if worker is not None:
                return worker
        raw = str(identifier or "").strip()
        if not raw:
            return None
        return self.get_by_worker_id(raw) or self.get_by_pin_code(raw) or self.get(raw)

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
