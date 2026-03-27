from __future__ import annotations

import json
from pathlib import Path

from src.storage.data_paths import data_dir


class QuotePricingStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else data_dir() / "quote_pricing.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        defaults = {
            "active_policy": "base",
            "policy_multipliers": {
                "base": 1.0,
                "dealer": 0.92,
                "promo": 0.88,
                "internal": 0.75,
            },
            "rules": {
                "processing_percent": 0.0,
                "assembly_percent": 0.0,
                "transport_flat": 0.0,
            },
            "active_role": "owner",
        }
        if not self.path.exists():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return defaults
        if not isinstance(payload, dict):
            return defaults
        out = dict(defaults)
        out["active_policy"] = str(payload.get("active_policy", out["active_policy"]) or out["active_policy"])
        raw_multipliers = payload.get("policy_multipliers", {})
        if isinstance(raw_multipliers, dict):
            multipliers = dict(out["policy_multipliers"])
            for key in ("base", "dealer", "promo", "internal"):
                try:
                    multipliers[key] = float(raw_multipliers.get(key, multipliers[key]))
                except Exception:
                    pass
            out["policy_multipliers"] = multipliers
        raw_rules = payload.get("rules", {})
        if isinstance(raw_rules, dict):
            rules = dict(out["rules"])
            for key in ("processing_percent", "assembly_percent", "transport_flat"):
                try:
                    rules[key] = float(raw_rules.get(key, rules[key]))
                except Exception:
                    pass
            out["rules"] = rules
        out["active_role"] = str(payload.get("active_role", out["active_role"]) or out["active_role"])
        return out

    def save(self, data: dict) -> None:
        payload = {
            "active_policy": str(data.get("active_policy", "base") or "base"),
            "policy_multipliers": {
                "base": float(data.get("policy_multipliers", {}).get("base", 1.0) or 1.0),
                "dealer": float(data.get("policy_multipliers", {}).get("dealer", 0.92) or 0.92),
                "promo": float(data.get("policy_multipliers", {}).get("promo", 0.88) or 0.88),
                "internal": float(data.get("policy_multipliers", {}).get("internal", 0.75) or 0.75),
            },
            "rules": {
                "processing_percent": float(data.get("rules", {}).get("processing_percent", 0.0) or 0.0),
                "assembly_percent": float(data.get("rules", {}).get("assembly_percent", 0.0) or 0.0),
                "transport_flat": float(data.get("rules", {}).get("transport_flat", 0.0) or 0.0),
            },
            "active_role": str(data.get("active_role", "owner") or "owner"),
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
