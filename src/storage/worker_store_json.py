from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.stable_record_id import ensure_record_id
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

    def get_by_id(self, employee_id: str) -> Optional[WorkerDef]:
        wanted = str(employee_id or "").strip()
        if not wanted:
            return None
        for raw in self._read_all().values():
            if not isinstance(raw, dict):
                continue
            rec_id = str(raw.get("id", "") or raw.get("worker_id", "") or "").strip()
            if rec_id == wanted:
                return WorkerDef.from_dict(raw)
        return None

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
        data[worker.name] = self._build_record(worker, previous=None)
        self._write_all(data)
        return StoreResult(True, f'Zapisano pracownika: "{worker.name}".')

    def overwrite(self, worker: WorkerDef) -> StoreResult:
        data = self._read_all()
        previous = data.get(worker.name)
        data[worker.name] = self._build_record(worker, previous=previous if isinstance(previous, dict) else None)
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
            if not isinstance(data, dict):
                return {}
            normalized, changed = self._normalize_records(data)
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
            if not key or not isinstance(raw, dict):
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
        payload = ensure_record_id(payload, "emp", field_name="id")

        domain_id = str(payload.get("worker_id", "") or "").strip()
        if not domain_id:
            payload["worker_id"] = str(payload.get("id", "") or "")

        now_iso = self._now_iso()
        if not str(payload.get("created_at", "") or "").strip():
            payload["created_at"] = now_iso
        if not str(payload.get("updated_at", "") or "").strip():
            payload["updated_at"] = now_iso
        return payload

    def _build_record(self, worker: WorkerDef, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = dict(worker.to_dict() or {})
        payload["name"] = str(getattr(worker, "name", payload.get("name", "")) or payload.get("name", ""))

        if previous:
            prev = self._normalize_single_record(payload["name"], previous)
            if not str(payload.get("id", "") or "").strip():
                payload["id"] = str(prev.get("id", "") or "")
            if not str(payload.get("worker_id", "") or "").strip():
                payload["worker_id"] = str(prev.get("worker_id", "") or "")
            if not str(payload.get("created_at", "") or "").strip():
                payload["created_at"] = str(prev.get("created_at", "") or "")

        payload = self._normalize_single_record(payload["name"], payload)
        payload["updated_at"] = self._now_iso()

        try:
            worker.id = str(payload.get("id", "") or "")
            worker.worker_id = str(payload.get("worker_id", "") or "")
            worker.created_at = str(payload.get("created_at", "") or "")
            worker.updated_at = str(payload.get("updated_at", "") or "")
        except Exception:
            pass

        return payload

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
