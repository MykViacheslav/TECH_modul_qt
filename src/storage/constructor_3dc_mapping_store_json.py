from __future__ import annotations

from pathlib import Path

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class Constructor3dcMappingStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else data_dir() / "constructor_3dc_mapping.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, dict[str, str]]:
        default = {
            "material_map": {},
            "edgeband_map": {},
            "hardware_map": {},
            "operation_map": {},
        }
        raw = read_json_file(self.path, default=default, expected_type=dict)
        if not isinstance(raw, dict):
            return dict(default)
        out: dict[str, dict[str, str]] = {}
        for key in ("material_map", "edgeband_map", "hardware_map", "operation_map"):
            section = raw.get(key, {})
            if not isinstance(section, dict):
                out[key] = {}
                continue
            clean: dict[str, str] = {}
            for raw_k, raw_v in section.items():
                map_key = str(raw_k or "").strip()
                map_val = str(raw_v or "").strip()
                if map_key:
                    clean[map_key] = map_val
            out[key] = clean
        return out

    def save(self, payload: dict[str, dict[str, str]]) -> None:
        clean: dict[str, dict[str, str]] = {
            "material_map": {},
            "edgeband_map": {},
            "hardware_map": {},
            "operation_map": {},
        }
        for key in clean.keys():
            section = payload.get(key, {})
            if not isinstance(section, dict):
                continue
            for raw_k, raw_v in section.items():
                map_key = str(raw_k or "").strip()
                map_val = str(raw_v or "").strip()
                if map_key:
                    clean[key][map_key] = map_val
        write_json_atomic(self.path, clean, ensure_ascii=False, indent=2)
