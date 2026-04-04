from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class RecepturaStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else data_dir() / "receptura.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, {"rows": []}, ensure_ascii=False, indent=2)

    def list_rows(self) -> list[dict[str, Any]]:
        payload = self._read_payload()
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            return []
        cleaned = [dict(row) for row in rows if isinstance(row, dict)]
        cleaned.sort(key=lambda row: str(row.get("id", "")))
        return cleaned

    def get(self, row_id: str) -> dict[str, Any] | None:
        wanted = str(row_id or "").strip().upper()
        if not wanted:
            return None
        for row in self.list_rows():
            if str(row.get("id", "") or "").strip().upper() == wanted:
                return row
        return None

    def list_for_quote(self) -> list[dict[str, Any]]:
        return [row for row in self.list_rows() if bool(row.get("for_quote", True))]

    def list_for_module(self) -> list[dict[str, Any]]:
        return [row for row in self.list_rows() if bool(row.get("for_module", True))]

    def next_id(self) -> str:
        max_num = 0
        for row in self.list_rows():
            raw = str(row.get("id", "") or "").strip().upper()
            if not raw.startswith("R"):
                continue
            digits = "".join(ch for ch in raw if ch.isdigit())
            if not digits:
                continue
            try:
                max_num = max(max_num, int(digits))
            except Exception:
                continue
        return f"R{max_num + 1:04d}"

    def upsert(self, row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        payload = self._read_payload()
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        item = dict(row or {})
        row_id = str(item.get("id", "") or "").strip().upper()
        if not row_id:
            row_id = self.next_id()
        item["id"] = row_id
        item["name"] = str(item.get("name", "") or "").strip()
        item["material_type"] = str(item.get("material_type", "") or "").strip()
        item["unit"] = str(item.get("unit", "") or "").strip().lower()
        item["notes"] = str(item.get("notes", "") or "").strip()
        item["for_quote"] = bool(item.get("for_quote", True))
        item["for_module"] = bool(item.get("for_module", True))

        try:
            item["quantity"] = float(item.get("quantity", 0.0) or 0.0)
        except Exception:
            item["quantity"] = 0.0
        try:
            item["price_net"] = float(item.get("price_net", 0.0) or 0.0)
        except Exception:
            item["price_net"] = 0.0
        try:
            item["vat_percent"] = float(item.get("vat_percent", 23.0) or 23.0)
        except Exception:
            item["vat_percent"] = 23.0
        if item["vat_percent"] < 0:
            item["vat_percent"] = 0.0
        if item["quantity"] < 0:
            item["quantity"] = 0.0
        if item["price_net"] < 0:
            item["price_net"] = 0.0

        computed_gross = item["price_net"] * (1.0 + (item["vat_percent"] / 100.0))
        item["price_gross"] = round(float(computed_gross), 2)

        item.setdefault("created_at", _now_text())
        item["updated_at"] = _now_text()

        for idx, existing in enumerate(rows):
            if not isinstance(existing, dict):
                continue
            existing_id = str(existing.get("id", "") or "").strip().upper()
            if existing_id != row_id:
                continue
            # Keep original creation timestamp on overwrite.
            created = str(existing.get("created_at", "") or "").strip()
            if created:
                item["created_at"] = created
            rows[idx] = item
            payload["rows"] = rows
            self._write_payload(payload)
            return False, item

        rows.append(item)
        payload["rows"] = rows
        self._write_payload(payload)
        return True, item

    def delete(self, row_id: str) -> bool:
        wanted = str(row_id or "").strip().upper()
        if not wanted:
            return False
        payload = self._read_payload()
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            return False

        keep: list[dict[str, Any]] = []
        removed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            existing_id = str(row.get("id", "") or "").strip().upper()
            if existing_id == wanted:
                removed = True
                continue
            keep.append(row)

        if removed:
            payload["rows"] = keep
            self._write_payload(payload)
        return removed

    def _read_payload(self) -> dict[str, Any]:
        payload = read_json_file(self._path, default={"rows": []}, expected_type=dict)
        if not isinstance(payload, dict):
            return {"rows": []}
        if not isinstance(payload.get("rows", []), list):
            payload["rows"] = []
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        write_json_atomic(self._path, payload, ensure_ascii=False, indent=2)
