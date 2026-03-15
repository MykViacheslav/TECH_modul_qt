from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from src.domain.module_models import ModuleDef


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    return _project_root() / "data"


def _default_path() -> Path:
    return _data_dir() / "default_module.json"


def _is_valid_default(m: ModuleDef) -> tuple[bool, str]:
    l_val = float(getattr(m, "width_mm", 0) or 0)
    w_val = float(getattr(m, "depth_mm", 0) or 0)
    h_val = float(getattr(m, "height_mm", 0) or 0)
    visible_parts = set(getattr(m, "visible_parts", set()) or set())
    materials = dict(getattr(m, "materials", {}) or {})

    if l_val < 100 or w_val < 100 or h_val < 100:
        return False, "Wymiary startowe musza byc >= 100 mm (L/W/H)."
    if not visible_parts:
        return False, "Musisz zaznaczyc przynajmniej 1 element (Widoczne elementy)."
    if "carcass" not in materials:
        return False, "Brak materialu korpusu (Materialy modulu)."
    return True, ""


def load_default_module() -> Optional[ModuleDef]:
    path = _default_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        module = ModuleDef.from_dict(raw)
        ok, _msg = _is_valid_default(module)
        if not ok:
            # Auto-usuwanie zlego startowego, zeby nie psul kolejnych uruchomien.
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None
        return module
    except Exception:
        return None


def save_default_module(m: ModuleDef) -> None:
    ok, msg = _is_valid_default(m)
    if not ok:
        raise ValueError(msg)

    path = _default_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(m.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def clear_default_module() -> None:
    path = _default_path()
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
