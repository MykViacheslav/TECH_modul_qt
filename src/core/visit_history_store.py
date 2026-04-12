from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any
import uuid

from src.storage.data_paths import data_dir


@dataclass
class VisitHistoryRecord:
    id: str = ""
    point_id: str = ""
    order_id: str = ""
    project_id: str = ""
    project_name: str = ""
    client_id: str = ""
    client_name: str = ""
    visit_date: str = ""
    crew: str = ""
    workers: list[str] = field(default_factory=list)
    visit_type: str = ""
    status_before: str = ""
    status_after: str = ""
    work_done: str = ""
    work_remaining: str = ""
    items_taken: str = ""
    issues_found: str = ""
    client_contact_name: str = ""
    client_contact_phone: str = ""
    address: str = ""
    city: str = ""
    duration_minutes: int = 0
    is_closed: bool = False
    finance_result: str = "brak"
    payment_unlocked_amount: float = 0.0
    ready_to_invoice: bool = False
    requires_settlement: bool = False
    requires_confirmation: bool = False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "VisitHistoryRecord":
        data = data if isinstance(data, dict) else {}
        workers = data.get("workers", [])
        if not isinstance(workers, list):
            workers = []
        return cls(
            id=str(data.get("id", "") or "").strip(),
            point_id=str(data.get("point_id", "") or "").strip(),
            order_id=str(data.get("order_id", "") or "").strip(),
            project_id=str(data.get("project_id", "") or "").strip(),
            project_name=str(data.get("project_name", "") or "").strip(),
            client_id=str(data.get("client_id", "") or "").strip(),
            client_name=str(data.get("client_name", "") or "").strip(),
            visit_date=str(data.get("visit_date", "") or "").strip(),
            crew=str(data.get("crew", "") or "").strip(),
            workers=[str(x or "").strip() for x in workers if str(x or "").strip()],
            visit_type=str(data.get("visit_type", "") or "").strip(),
            status_before=str(data.get("status_before", "") or "").strip(),
            status_after=str(data.get("status_after", "") or "").strip(),
            work_done=str(data.get("work_done", "") or "").strip(),
            work_remaining=str(data.get("work_remaining", "") or "").strip(),
            items_taken=str(data.get("items_taken", "") or "").strip(),
            issues_found=str(data.get("issues_found", "") or "").strip(),
            client_contact_name=str(data.get("client_contact_name", "") or "").strip(),
            client_contact_phone=str(data.get("client_contact_phone", "") or "").strip(),
            address=str(data.get("address", "") or "").strip(),
            city=str(data.get("city", "") or "").strip(),
            duration_minutes=int(data.get("duration_minutes", 0) or 0),
            is_closed=bool(data.get("is_closed", False)),
            finance_result=str(data.get("finance_result", "brak") or "brak").strip().lower(),
            payment_unlocked_amount=float(data.get("payment_unlocked_amount", 0.0) or 0.0),
            ready_to_invoice=bool(data.get("ready_to_invoice", False)),
            requires_settlement=bool(data.get("requires_settlement", False)),
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            notes=str(data.get("notes", "") or "").strip(),
            created_at=str(data.get("created_at", "") or "").strip(),
            updated_at=str(data.get("updated_at", "") or "").strip(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "point_id": self.point_id,
            "order_id": self.order_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "visit_date": self.visit_date,
            "crew": self.crew,
            "workers": [str(x or "").strip() for x in self.workers if str(x or "").strip()],
            "visit_type": self.visit_type,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "work_done": self.work_done,
            "work_remaining": self.work_remaining,
            "items_taken": self.items_taken,
            "issues_found": self.issues_found,
            "client_contact_name": self.client_contact_name,
            "client_contact_phone": self.client_contact_phone,
            "address": self.address,
            "city": self.city,
            "duration_minutes": int(self.duration_minutes or 0),
            "is_closed": bool(self.is_closed),
            "finance_result": str(self.finance_result or "brak").strip().lower(),
            "payment_unlocked_amount": float(self.payment_unlocked_amount or 0.0),
            "ready_to_invoice": bool(self.ready_to_invoice),
            "requires_settlement": bool(self.requires_settlement),
            "requires_confirmation": bool(self.requires_confirmation),
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class VisitHistoryStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        base = Path(data_dir) if data_dir is not None else data_dir_fn()
        self._path = base / "visit_history.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_json(self._path, {"records": []})

    def _read_json(self, path: Path) -> dict:
        try:
            raw = path.read_text(encoding="utf-8-sig")
            data = json.loads(raw) if raw.strip() else {}
            return data if isinstance(data, dict) else {"records": []}
        except Exception:
            return {"records": []}

    def _write_json(self, path: Path, data: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        txt = json.dumps(data, ensure_ascii=False, indent=2)
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
            fh.write("\n")
        os.replace(tmp, path)

    def _now_iso(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _new_history_id(self) -> str:
        return f"VIS-{uuid.uuid4().hex[:10].upper()}"

    def list_records(self) -> list[VisitHistoryRecord]:
        data = self._read_json(self._path)
        rows = data.get("records", [])
        if not isinstance(rows, list):
            rows = []
        out = [VisitHistoryRecord.from_dict(x) for x in rows if isinstance(x, dict)]
        out.sort(key=lambda x: (str(x.visit_date or ""), str(x.updated_at or "")), reverse=True)
        return out

    def get_record(self, record_id: str) -> VisitHistoryRecord | None:
        rid = str(record_id or "").strip()
        if not rid:
            return None
        for rec in self.list_records():
            if rec.id == rid:
                return rec
        return None

    def list_for_point(self, point_id: str) -> list[VisitHistoryRecord]:
        pid = str(point_id or "").strip()
        rows = [x for x in self.list_records() if x.point_id == pid]
        rows.sort(key=lambda x: (str(x.visit_date or ""), str(x.updated_at or "")), reverse=True)
        return rows

    def list_for_order(self, order_id: str) -> list[VisitHistoryRecord]:
        oid = str(order_id or "").strip()
        rows = [x for x in self.list_records() if x.order_id == oid]
        rows.sort(key=lambda x: (str(x.visit_date or ""), str(x.updated_at or "")), reverse=True)
        return rows

    def add_record(self, record: VisitHistoryRecord) -> VisitHistoryRecord:
        data = self._read_json(self._path)
        rows = data.get("records", [])
        if not isinstance(rows, list):
            rows = []
        now = self._now_iso()
        rec = record
        if not rec.id:
            rec.id = self._new_history_id()
        if not rec.created_at:
            rec.created_at = now
        rec.updated_at = now
        rows.append(rec.to_dict())
        data["records"] = rows
        data["updated_at"] = now
        self._write_json(self._path, data)
        return rec

    def update_record(self, record: VisitHistoryRecord) -> None:
        data = self._read_json(self._path)
        rows = data.get("records", [])
        if not isinstance(rows, list):
            rows = []
        rid = str(record.id or "").strip()
        if not rid:
            self.add_record(record)
            return
        now = self._now_iso()
        replaced = False
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            if str(row.get("id", "") or "").strip() == rid:
                created_at = str(row.get("created_at", "") or "").strip()
                rec = record
                rec.created_at = created_at or rec.created_at or now
                rec.updated_at = now
                rows[i] = rec.to_dict()
                replaced = True
                break
        if not replaced:
            self.add_record(record)
            return
        data["records"] = rows
        data["updated_at"] = now
        self._write_json(self._path, data)

    def delete_record(self, record_id: str) -> None:
        rid = str(record_id or "").strip()
        if not rid:
            return
        data = self._read_json(self._path)
        rows = data.get("records", [])
        if not isinstance(rows, list):
            rows = []
        rows = [x for x in rows if not (isinstance(x, dict) and str(x.get("id", "") or "").strip() == rid)]
        data["records"] = rows
        data["updated_at"] = self._now_iso()
        self._write_json(self._path, data)

    def append_finance_result(
        self,
        *,
        point_id: str,
        finance_result: str,
        payment_unlocked_amount: float,
        ready_to_invoice: bool,
        requires_settlement: bool,
        requires_confirmation: bool,
        notes: str = "",
    ) -> VisitHistoryRecord:
        existing = self.list_for_point(point_id)
        if existing:
            rec = existing[0]
        else:
            rec = VisitHistoryRecord(
                point_id=str(point_id or "").strip(),
                visit_date=self._now_iso()[:10],
            )
        rec.finance_result = str(finance_result or "brak").strip().lower()
        rec.payment_unlocked_amount = float(payment_unlocked_amount or 0.0)
        rec.ready_to_invoice = bool(ready_to_invoice)
        rec.requires_settlement = bool(requires_settlement)
        rec.requires_confirmation = bool(requires_confirmation)
        if notes:
            rec.notes = (rec.notes + "\n" + str(notes).strip()).strip()
        if rec.id:
            self.update_record(rec)
            return rec
        return self.add_record(rec)


def data_dir_fn() -> Path:
    return data_dir()
