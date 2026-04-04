from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class MaterialStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "baza_materialu.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            # Create empty structure
            write_json_atomic(self._path, {}, ensure_ascii=False, indent=2)

    def load(self) -> Dict[str, Any]:
        return read_json_file(self._path, default={}, expected_type=dict)

    def save(self, data: Dict[str, Any]) -> None:
        payload = data if isinstance(data, dict) else {}
        write_json_atomic(self._path, payload, ensure_ascii=False, indent=2)

    def update_material_last_price(self, material_id: str, last_price: float, supplier: str = "") -> bool:
        """Update last price and supplier for a material."""
        if not material_id:
            return False
        data = self.load()
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            return False
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("id", "")) == material_id:
                row["ostatnia_cena"] = str(last_price) if last_price else ""
                if supplier:
                    row["dostawca"] = supplier
                self.save(data)
                return True
        return False

    def get_material_stock(self, material_id: str) -> float:
        """Return stock quantity (ilosc_magazyn) for a material."""
        data = self.load()
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            return 0.0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("id", "")) == material_id:
                stock_str = str(row.get("ilosc_magazyn", "") or "")
                try:
                    return float(stock_str) if stock_str else 0.0
                except ValueError:
                    return 0.0
        return 0.0

    def list_materials(self) -> List[Dict[str, Any]]:
        data = self.load()
        rows = data.get("rows", [])
        return [row for row in rows if isinstance(row, dict)]
