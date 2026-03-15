from __future__ import annotations

import json
import os
from typing import Any, Dict


def _get_data_dir() -> str:
    root = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if root:
        os.makedirs(root, exist_ok=True)
        return root

    base = os.path.join(os.getcwd(), "data")
    os.makedirs(base, exist_ok=True)
    return base


def get_resolved_preview_debug_path() -> str:
    data_dir = _get_data_dir()
    return os.path.join(data_dir, "resolved_preview_debug.json")


def save_resolved_preview_payload(payload: Dict[str, Any]) -> str:
    path = get_resolved_preview_debug_path()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

    return path


def load_resolved_preview_payload() -> Dict[str, Any]:
    path = get_resolved_preview_debug_path()

    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}