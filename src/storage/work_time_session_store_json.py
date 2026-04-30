from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from src.storage.data_paths import data_dir


@dataclass
class WorkTimeSessionDef:
    worker_id: str = ""
    worker_name: str = ""
    work_type: str = ""
    project_code: str = ""
    order_id: str = ""
    workstation: str = ""
    note: str = ""
    started_at_iso: str = ""
    break_started_at_iso: str = ""
    break_total_minutes: float = 0.0
    last_action_iso: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "work_type": self.work_type,
            "project_code": self.project_code,
            "order_id": self.order_id,
            "workstation": self.workstation,
            "note": self.note,
            "started_at_iso": self.started_at_iso,
            "break_started_at_iso": self.break_started_at_iso,
            "break_total_minutes": float(self.break_total_minutes or 0.0),
            "last_action_iso": self.last_action_iso,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "WorkTimeSessionDef":
        data = data or {}
        return cls(
            worker_id=str(data.get("worker_id", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            work_type=str(data.get("work_type", "") or ""),
            project_code=str(data.get("project_code", "") or ""),
            order_id=str(data.get("order_id", "") or ""),
            workstation=str(data.get("workstation", "") or ""),
            note=str(data.get("note", "") or ""),
            started_at_iso=str(data.get("started_at_iso", "") or ""),
            break_started_at_iso=str(data.get("break_started_at_iso", "") or ""),
            break_total_minutes=float(data.get("break_total_minutes", 0.0) or 0.0),
            last_action_iso=str(data.get("last_action_iso", "") or ""),
        )


class WorkTimeSessionStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "work_time_sessions.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def get(self, worker_id: str) -> Optional[WorkTimeSessionDef]:
        worker_id = str(worker_id or "").strip()
        if not worker_id:
            return None
        raw = self._read_all().get(worker_id)
        return WorkTimeSessionDef.from_dict(raw) if isinstance(raw, dict) else None

    def set(self, session: WorkTimeSessionDef) -> None:
        data = self._read_all()
        data[str(session.worker_id or "").strip()] = session.to_dict()
        self._write_all(data)

    def delete(self, worker_id: str) -> None:
        data = self._read_all()
        data.pop(str(worker_id or "").strip(), None)
        self._write_all(data)

    def list_sessions(self) -> list[WorkTimeSessionDef]:
        return [
            WorkTimeSessionDef.from_dict(raw)
            for raw in self._read_all().values()
            if isinstance(raw, dict)
        ]

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
