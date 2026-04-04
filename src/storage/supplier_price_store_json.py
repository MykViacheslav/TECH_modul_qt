from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


def _new_offer_id() -> str:
    return uuid.uuid4().hex[:12].upper()


class SupplierPriceStoreJson:
    """Manualna baza ofert cenowych dostawcow/konkurencji."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "supplier_prices.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, [], ensure_ascii=False, indent=2)

    def list_rows(self) -> list[dict[str, Any]]:
        data = read_json_file(self._path, default=[], expected_type=list)
        return [dict(row) for row in data if isinstance(row, dict)]

    def list_for_material(self, material_id: str = "", material_name: str = "") -> list[dict[str, Any]]:
        id_norm = str(material_id or "").strip().lower()
        name_norm = str(material_name or "").strip().lower()
        out: list[dict[str, Any]] = []
        for row in self.list_rows():
            row_id = str(row.get("material_id", "") or "").strip().lower()
            row_name = str(row.get("material_name", "") or "").strip().lower()
            if id_norm and row_id == id_norm:
                out.append(row)
                continue
            if name_norm and row_name and row_name == name_norm:
                out.append(row)
        return out

    def upsert_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row or {})
        offer_id = str(payload.get("offer_id", "") or "").strip() or _new_offer_id()
        payload["offer_id"] = offer_id
        payload["material_id"] = str(payload.get("material_id", "") or "").strip()
        payload["material_name"] = str(payload.get("material_name", "") or "").strip()
        payload["supplier"] = str(payload.get("supplier", "") or "").strip()
        payload["unit"] = str(payload.get("unit", "") or "").strip()
        payload["price_basis"] = str(payload.get("price_basis", "unknown") or "unknown").strip().lower()
        payload["source"] = str(payload.get("source", "manual") or "manual").strip().lower()
        payload["note"] = str(payload.get("note", "") or "").strip()
        payload["updated_at"] = str(payload.get("updated_at", "") or "").strip() or datetime.now().strftime("%Y-%m-%d")
        try:
            payload["unit_price"] = float(payload.get("unit_price", 0.0) or 0.0)
        except Exception:
            payload["unit_price"] = 0.0

        rows = self.list_rows()
        replaced = False
        for i, existing in enumerate(rows):
            if str(existing.get("offer_id", "") or "").strip() == offer_id:
                rows[i] = payload
                replaced = True
                break
        if not replaced:
            rows.append(payload)
        write_json_atomic(self._path, rows, ensure_ascii=False, indent=2)
        return payload

    def delete_row(self, offer_id: str) -> bool:
        target = str(offer_id or "").strip()
        if not target:
            return False
        rows = self.list_rows()
        filtered = [row for row in rows if str(row.get("offer_id", "") or "").strip() != target]
        if len(filtered) == len(rows):
            return False
        write_json_atomic(self._path, filtered, ensure_ascii=False, indent=2)
        return True

