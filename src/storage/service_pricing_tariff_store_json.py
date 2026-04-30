from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.storage.data_paths import data_dir


SERVICE_PRICING_TARIFFS_SCHEMA_VERSION = "service_pricing_tariffs_v1"


class ServicePricingTariffStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else data_dir() / "service_pricing_tariffs.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def defaults() -> Dict[str, Any]:
        return {
            "schema_version": SERVICE_PRICING_TARIFFS_SCHEMA_VERSION,
            "drilling": {
                "base_per_hole": 0.55,
                "diameter_breakpoints_mm": {"small_max": 4.0, "medium_max": 8.0},
                "diameter_band_surcharge": {"small": 0.0, "medium": 0.12, "large": 0.25},
                "depth_surcharge_per_hole": {"deep_from_mm": 16.0, "deep_surcharge": 0.1},
            },
            "grooves": {
                "setup_per_groove": 2.5,
                "per_meter": 6.5,
                "depth_factor": {"deep_from_mm": 8.0, "deep_multiplier": 1.15},
            },
            "milling": {
                "setup_per_path": 4.0,
                "per_meter": 15.0,
                "per_arc": 0.35,
                "estimated_length_multiplier": 0.9,
            },
            "tooling": {
                "baseline_tools": 1,
                "per_additional_tool": 2.0,
            },
            "complexity": {
                "bands": [
                    {"code": "low", "max_score": 20, "multiplier": 1.0},
                    {"code": "medium", "max_score": 60, "multiplier": 1.12},
                    {"code": "high", "max_score": 120, "multiplier": 1.25},
                    {"code": "very_high", "max_score": 999999, "multiplier": 1.4},
                ]
            },
            "manual_modes": {
                "service-cut": {"cut_per_m2": 35.0},
                "service-cut-edge": {"cut_per_m2": 35.0, "edge_per_mb": 12.0},
                "service-front-cnc-lacquer": {
                    "cnc_per_m2": {"line": 45.0, "classic": 60.0, "premium": 75.0, "custom": 90.0},
                    "front_model_setup": 25.0,
                    "lacquer_per_m2": {"one_side": 55.0, "two_sides": 90.0},
                },
                "service-veneer": {
                    "veneer_per_m2_side": 70.0,
                    "veneer_lacquer_per_m2": {"one_side": 40.0, "two_sides": 70.0},
                    "edge_per_mb": 8.0,
                },
                "service-bent-elements": {
                    "shape_per_m2": {"arc": 70.0, "wave": 95.0, "custom": 130.0},
                    "complexity_multiplier": {"1": 1.0, "2": 1.5, "3": 2.0},
                    "small_radius_threshold_mm": 180.0,
                    "small_radius_surcharge_per_item": 25.0,
                },
            },
            "materials": {
                "default_base_price_per_m2": 85.0,
                "thickness_multipliers": {"19": 1.0, "22": 1.17, "28": 1.38},
            },
            "layers": {
                "role_surcharge_per_m2": {
                    "overlay": 9.0,
                    "decorative_layer": 14.0,
                    "reinforcement": 11.0,
                    "glued_mdf": 13.0,
                    "veneer_layer": 18.0,
                    "substrate_addition": 10.0,
                }
            },
        }

    def load(self) -> Dict[str, Any]:
        defaults = self.defaults()
        if not self.path.exists():
            return defaults
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return defaults
        if not isinstance(raw, dict):
            return defaults

        out = dict(defaults)
        for key in defaults.keys():
            if isinstance(raw.get(key), dict) and isinstance(defaults[key], dict):
                merged = dict(defaults[key])
                merged.update(raw.get(key, {}))
                out[key] = merged
            elif key in raw:
                out[key] = raw[key]
        if not isinstance(out.get("schema_version"), str) or not str(out.get("schema_version", "")).strip():
            out["schema_version"] = SERVICE_PRICING_TARIFFS_SCHEMA_VERSION
        return out

    def save(self, payload: Dict[str, Any]) -> None:
        data = self.defaults()
        if isinstance(payload, dict):
            for key in data.keys():
                if key in payload:
                    data[key] = payload[key]
        if not isinstance(data.get("schema_version"), str) or not str(data.get("schema_version", "")).strip():
            data["schema_version"] = SERVICE_PRICING_TARIFFS_SCHEMA_VERSION
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

