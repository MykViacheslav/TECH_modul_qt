from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.stable_record_id import ensure_record_id
from src.domain.order_models import OrderDef
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class OrderStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "orders.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_codes(self) -> List[str]:
        return sorted(list(self._read_all().keys()))

    def list_orders(self) -> List[OrderDef]:
        raw_all = self._read_all()
        return [
            OrderDef.from_dict(raw_all[code])
            for code in sorted(raw_all.keys())
            if isinstance(raw_all.get(code), dict)
        ]

    def get(self, code: str) -> Optional[OrderDef]:
        raw = self._read_all().get(code)
        return OrderDef.from_dict(raw) if isinstance(raw, dict) else None

    def get_by_id(self, order_id: str) -> Optional[OrderDef]:
        wanted = str(order_id or "").strip()
        if not wanted:
            return None
        for raw in self._read_all().values():
            if not isinstance(raw, dict):
                continue
            rec_id = str(raw.get("id", "") or raw.get("order_id", "") or "").strip()
            if rec_id == wanted:
                return OrderDef.from_dict(raw)
        return None

    def save_new(self, order: OrderDef) -> StoreResult:
        data = self._read_all()
        if order.code in data:
            return StoreResult(False, f'Zamowienie "{order.code}" juz istnieje. Uzyj "Nadpisz".')
        data[order.code] = self._build_record(order, previous=None)
        self._write_all(data)
        return StoreResult(True, f'Zapisano zamowienie: "{order.code}".')

    def overwrite(self, order: OrderDef) -> StoreResult:
        data = self._read_all()
        previous = data.get(order.code)
        data[order.code] = self._build_record(order, previous=previous if isinstance(previous, dict) else None)
        self._write_all(data)
        return StoreResult(True, f'Nadpisano zamowienie: "{order.code}".')

    def delete(self, code: str) -> StoreResult:
        data = self._read_all()
        if code not in data:
            return StoreResult(False, f'Nie ma zamowienia "{code}" w bazie.')
        data.pop(code, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto zamowienie: "{code}".')

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
        for code, raw in (raw_items or {}).items():
            key = str(code or "").strip()
            if not key or not isinstance(raw, dict):
                changed = True
                continue
            rec = self._normalize_single_record(key, raw)
            if rec != raw:
                changed = True
            normalized[key] = rec
        return normalized, changed

    def _normalize_single_record(self, code: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(raw or {})
        payload["code"] = str(payload.get("code") or code)
        payload = ensure_record_id(payload, "ord", field_name="id")

        domain_id = str(payload.get("order_id", "") or "").strip()
        if not domain_id:
            payload["order_id"] = str(payload.get("id", "") or "")

        now_iso = self._now_iso()
        if not str(payload.get("created_at", "") or "").strip():
            payload["created_at"] = now_iso
        if not str(payload.get("updated_at", "") or "").strip():
            payload["updated_at"] = now_iso
        return payload

    def _build_record(self, order: OrderDef, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = dict(order.to_dict() or {})
        payload["code"] = str(getattr(order, "code", payload.get("code", "")) or payload.get("code", ""))

        if previous:
            prev = self._normalize_single_record(payload["code"], previous)
            if not str(payload.get("id", "") or "").strip():
                payload["id"] = str(prev.get("id", "") or "")
            if not str(payload.get("order_id", "") or "").strip():
                payload["order_id"] = str(prev.get("order_id", "") or "")
            if not str(payload.get("created_at", "") or "").strip():
                payload["created_at"] = str(prev.get("created_at", "") or "")

        payload = self._normalize_single_record(payload["code"], payload)
        payload["updated_at"] = self._now_iso()

        try:
            order.id = str(payload.get("id", "") or "")
            order.order_id = str(payload.get("order_id", "") or "")
            order.created_at = str(payload.get("created_at", "") or "")
            order.updated_at = str(payload.get("updated_at", "") or "")
        except Exception:
            pass

        return payload

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
