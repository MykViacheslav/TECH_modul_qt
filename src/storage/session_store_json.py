from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.domain.module_models import ModuleDef


def _project_root() -> Path:
    # .../src/storage/session_store_json.py -> .../ (root projektu)
    return Path(__file__).resolve().parents[2]


def _session_path() -> Path:
    return _project_root() / "data" / "session_last.json"


def load_last_session() -> Optional[Tuple[ModuleDef, Dict[str, Any]]]:
    path = _session_path()
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        mod_raw = data.get("module")
        ui = data.get("ui") or {}
        if not isinstance(mod_raw, dict):
            return None
        if not isinstance(ui, dict):
            ui = {}
        m = ModuleDef.from_dict(mod_raw)
        return m, ui
    except Exception:
        return None


def save_last_session(module: ModuleDef, ui_state: Dict[str, Any]) -> None:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "module": module.to_dict(),
        "ui": dict(ui_state or {}),
    }

    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def clear_last_session() -> None:
    path = _session_path()
    try:
        path.unlink(missing_ok=True)  # Python 3.10 OK
    except Exception:
        pass