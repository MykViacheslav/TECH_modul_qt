import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic

class MaterialUsageStoreJson:
    """Stores deductions/usage of materials assigned to specific orders or general waste."""
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "zuzycie_materialu.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, {"usages": []}, ensure_ascii=False, indent=2)

    def log_usage(self, material_id: str, quantity: float, order_id: str, note: str = "") -> str:
        data = read_json_file(self._path, default={"usages": []})
        usage_id = uuid.uuid4().hex[:8].upper()
        entry = {
            "usage_id": usage_id,
            "material_id": material_id,
            "quantity": quantity,
            "order_id": order_id,
            "note": note,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data["usages"].append(entry)
        write_json_atomic(self._path, data)
        return usage_id

    def list_usages(self, order_id: str | None = None) -> List[Dict[str, Any]]:
        data = read_json_file(self._path, default={"usages": []})
        usages = data.get("usages", [])
        if order_id:
            return [u for u in usages if u.get("order_id") == order_id]
        return usages
