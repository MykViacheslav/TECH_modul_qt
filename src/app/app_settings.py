from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class DrawingSettings:
    rect_line_color: str = "#000000"
    rect_line_width_px: int = 3

    dim_line_color: str = "#0066cc"
    dim_line_width_px: int = 3
    dim_end_style: str = "arrows"  # "arrows" | "ticks"

    grid_enabled: bool = True
    grid_step_mm: float = 50.0
    grid_color: str = "#e6e6e6"
    grid_width_px: int = 1

    show_front_part: bool = True          # tylko rysunek
    front_mode: str = "external"          # "external" | "internal"

    edgeband_color: str = "#cc0000"
    edgeband_width_px: int = 4

    # NOWE
    hinge_edge_offset_mm: float = 12.0
    auto_double_front_width_mm: float = 600.0


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    return _project_root() / "data"


def _settings_path() -> Path:
    return _data_dir() / "settings.json"


def _load_settings_data() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"drawing": DrawingSettings().__dict__}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_settings_data(data: Dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_drawing_settings() -> DrawingSettings:
    data = _load_settings_data()
    d = (data.get("drawing") or {}) if isinstance(data, dict) else {}

    base: Dict[str, Any] = DrawingSettings().__dict__.copy()
    for k, v in d.items():
        if k in base:
            base[k] = v

    def as_int(x, default: int) -> int:
        try:
            return int(x)
        except Exception:
            return default

    def as_float(x, default: float) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def as_bool(x, default: bool) -> bool:
        try:
            return bool(x)
        except Exception:
            return default

    front_mode = str(base.get("front_mode", "external")).strip().lower()
    if front_mode not in ("external", "internal"):
        front_mode = "external"

    dim_end_style = str(base.get("dim_end_style", "arrows")).strip().lower()
    if dim_end_style not in ("arrows", "ticks"):
        dim_end_style = "arrows"

    return DrawingSettings(
        rect_line_color=str(base["rect_line_color"]),
        rect_line_width_px=max(1, as_int(base["rect_line_width_px"], 3)),

        dim_line_color=str(base["dim_line_color"]),
        dim_line_width_px=max(1, as_int(base["dim_line_width_px"], 3)),
        dim_end_style=dim_end_style,

        grid_enabled=as_bool(base["grid_enabled"], True),
        grid_step_mm=max(5.0, as_float(base["grid_step_mm"], 50.0)),
        grid_color=str(base["grid_color"]),
        grid_width_px=max(1, as_int(base["grid_width_px"], 1)),

        show_front_part=as_bool(base.get("show_front_part", True), True),
        front_mode=front_mode,

        edgeband_color=str(base.get("edgeband_color", "#cc0000")),
        edgeband_width_px=max(1, as_int(base.get("edgeband_width_px", 4), 4)),

        hinge_edge_offset_mm=max(0.0, as_float(base.get("hinge_edge_offset_mm", 12.0), 12.0)),
        auto_double_front_width_mm=max(100.0, as_float(base.get("auto_double_front_width_mm", 600.0), 600.0)),
    )


def save_drawing_settings(s: DrawingSettings) -> None:
    data = _load_settings_data()

    front_mode = (s.front_mode or "external").strip().lower()
    if front_mode not in ("external", "internal"):
        front_mode = "external"

    dim_end_style = (s.dim_end_style or "arrows").strip().lower()
    if dim_end_style not in ("arrows", "ticks"):
        dim_end_style = "arrows"

    data["drawing"] = {
        "rect_line_color": s.rect_line_color,
        "rect_line_width_px": int(s.rect_line_width_px),

        "dim_line_color": s.dim_line_color,
        "dim_line_width_px": int(s.dim_line_width_px),
        "dim_end_style": dim_end_style,

        "grid_enabled": bool(s.grid_enabled),
        "grid_step_mm": float(s.grid_step_mm),
        "grid_color": s.grid_color,
        "grid_width_px": int(s.grid_width_px),

        "show_front_part": bool(s.show_front_part),
        "front_mode": front_mode,

        "edgeband_color": s.edgeband_color,
        "edgeband_width_px": int(s.edgeband_width_px),

        "hinge_edge_offset_mm": float(s.hinge_edge_offset_mm),
        "auto_double_front_width_mm": float(s.auto_double_front_width_mm),
    }

    _save_settings_data(data)


def load_modul_splitter_sizes(default: list[int] | None = None) -> list[int]:
    fallback = list(default or [360, 900, 360])
    if len(fallback) != 3:
        fallback = [360, 900, 360]

    data = _load_settings_data()
    ui = data.get("ui") or {}
    raw = ui.get("modul_splitter_sizes") or []

    if not isinstance(raw, list) or len(raw) != 3:
        return list(fallback)

    out: list[int] = []
    for value in raw:
        try:
            parsed = int(value)
        except Exception:
            return list(fallback)
        if parsed <= 0:
            return list(fallback)
        out.append(parsed)

    return out


def save_modul_splitter_sizes(sizes: list[int] | tuple[int, int, int]) -> None:
    if len(sizes) != 3:
        return

    normalized: list[int] = []
    for value in sizes:
        try:
            parsed = int(value)
        except Exception:
            return
        normalized.append(max(1, parsed))

    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    ui["modul_splitter_sizes"] = normalized
    data["ui"] = ui
    _save_settings_data(data)
