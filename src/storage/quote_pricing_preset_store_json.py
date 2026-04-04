from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class QuotePricingPresetStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else data_dir() / "quote_pricing_presets.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        raw = read_json_file(self.path, default=[], expected_type=list)
        return [p for p in raw if isinstance(p, dict)]

    def save_preset(
        self,
        name: str,
        transport_flat: float,
        montage_flat: float,
        margin_percent: float,
    ) -> dict:
        presets = self.load()
        preset: dict = {
            "id": str(uuid.uuid4()),
            "name": str(name).strip(),
            "transport_flat": float(transport_flat),
            "montage_flat": float(montage_flat),
            "margin_percent": float(margin_percent),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        presets.append(preset)
        write_json_atomic(self.path, presets, ensure_ascii=False, indent=2)
        return preset

    def delete_preset(self, preset_id: str) -> bool:
        presets = self.load()
        filtered = [p for p in presets if p.get("id") != preset_id]
        if len(filtered) == len(presets):
            return False
        write_json_atomic(self.path, filtered, ensure_ascii=False, indent=2)
        return True
