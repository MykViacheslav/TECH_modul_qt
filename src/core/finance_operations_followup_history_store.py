from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {"records": []}
    except Exception:
        return {"records": []}
    if not raw.strip():
        return {"records": []}
    try:
        payload = json.loads(raw)
    except Exception:
        return {"records": []}
    if not isinstance(payload, dict):
        return {"records": []}
    records = payload.get("records", [])
    if not isinstance(records, list):
        payload["records"] = []
    return payload


def _save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


class FinanceOperationsFollowupHistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        base = data_dir()
        self._path = path if path is not None else base / "finance_operations_followup_history.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            _save_json_atomic(self._path, {"records": []})

    def _read_payload(self) -> dict[str, Any]:
        return _load_json(self._path)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _now_iso()
        _save_json_atomic(self._path, payload)

    def list_records(self) -> list[dict]:
        payload = self._read_payload()
        records = payload.get("records", [])
        out = [dict(x) for x in records if isinstance(x, dict)]
        out.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return out

    def list_for_point(self, point_id: str) -> list[dict]:
        pid = str(point_id or "").strip()
        if not pid:
            return []
        return [row for row in self.list_records() if str(row.get("point_id", "") or "").strip() == pid]

    def append_record(
        self,
        point_id: str,
        action_type: str,
        created_by: str = "",
        old_office_status: str = "",
        new_office_status: str = "",
        old_invoice_status: str = "",
        new_invoice_status: str = "",
        old_payment_status: str = "",
        new_payment_status: str = "",
        invoice_number: str = "",
        invoice_date: str = "",
        paid_amount: float = 0.0,
        payment_date: str = "",
        payment_method: str = "",
        note: str = "",
    ) -> dict:
        pid = str(point_id or "").strip()
        if not pid:
            return {}
        rec = {
            "id": f"foh_{uuid.uuid4().hex[:12]}",
            "point_id": pid,
            "created_at": _now_iso(),
            "created_by": str(created_by or "").strip(),
            "action_type": str(action_type or "").strip(),
            "old_office_status": str(old_office_status or "").strip(),
            "new_office_status": str(new_office_status or "").strip(),
            "old_invoice_status": str(old_invoice_status or "").strip(),
            "new_invoice_status": str(new_invoice_status or "").strip(),
            "old_payment_status": str(old_payment_status or "").strip(),
            "new_payment_status": str(new_payment_status or "").strip(),
            "invoice_number": str(invoice_number or "").strip(),
            "invoice_date": str(invoice_date or "").strip(),
            "paid_amount": float(paid_amount or 0.0),
            "payment_date": str(payment_date or "").strip(),
            "payment_method": str(payment_method or "").strip(),
            "note": str(note or "").strip(),
        }
        payload = self._read_payload()
        rows = payload.get("records", [])
        if not isinstance(rows, list):
            rows = []
        rows.append(rec)
        payload["records"] = rows
        self._write_payload(payload)
        return dict(rec)

    def clear_for_point(self, point_id: str) -> None:
        pid = str(point_id or "").strip()
        if not pid:
            return
        payload = self._read_payload()
        rows = payload.get("records", [])
        if not isinstance(rows, list):
            rows = []
        payload["records"] = [
            row
            for row in rows
            if not isinstance(row, dict) or str(row.get("point_id", "") or "").strip() != pid
        ]
        self._write_payload(payload)
