from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.order_models import OrderDef


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class OrderStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            root = Path(__file__).resolve().parents[2]
            proj = root.parent
            path = proj / "data" / "orders.json"
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

    def save_new(self, order: OrderDef) -> StoreResult:
        data = self._read_all()
        if order.code in data:
            return StoreResult(False, f'Zamowienie "{order.code}" juz istnieje. Uzyj "Nadpisz".')
        data[order.code] = order.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano zamowienie: "{order.code}".')

    def overwrite(self, order: OrderDef) -> StoreResult:
        data = self._read_all()
        data[order.code] = order.to_dict()
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
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
