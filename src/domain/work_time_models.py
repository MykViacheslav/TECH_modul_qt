from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WorkTimeEntryDef:
    day: int = 1
    date_iso: str = ""
    work_type: str = ""
    start_time: str = ""
    end_time: str = ""
    hours: float = 0.0
    overtime_hours: float = 0.0
    extra_pay: float = 0.0
    project_code: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": int(self.day or 1),
            "date_iso": self.date_iso,
            "work_type": self.work_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "hours": float(self.hours or 0.0),
            "overtime_hours": float(self.overtime_hours or 0.0),
            "extra_pay": float(self.extra_pay or 0.0),
            "project_code": self.project_code,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkTimeEntryDef":
        data = data or {}
        return cls(
            day=int(data.get("day", 1) or 1),
            date_iso=str(data.get("date_iso", "") or ""),
            work_type=str(data.get("work_type", "") or ""),
            start_time=str(data.get("start_time", "") or ""),
            end_time=str(data.get("end_time", "") or ""),
            hours=float(data.get("hours", 0.0) or 0.0),
            overtime_hours=float(data.get("overtime_hours", 0.0) or 0.0),
            extra_pay=float(data.get("extra_pay", 0.0) or 0.0),
            project_code=str(data.get("project_code", "") or ""),
            note=str(data.get("note", "") or ""),
        )


@dataclass
class WorkerMonthSheetDef:
    worker_name: str = ""
    year: int = 0
    month: int = 0
    entries: List[WorkTimeEntryDef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_name": self.worker_name,
            "year": int(self.year or 0),
            "month": int(self.month or 0),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerMonthSheetDef":
        data = data or {}
        entries_raw = data.get("entries", []) or []
        return cls(
            worker_name=str(data.get("worker_name", "") or ""),
            year=int(data.get("year", 0) or 0),
            month=int(data.get("month", 0) or 0),
            entries=[
                WorkTimeEntryDef.from_dict(item)
                for item in entries_raw
                if isinstance(item, dict)
            ],
        )
