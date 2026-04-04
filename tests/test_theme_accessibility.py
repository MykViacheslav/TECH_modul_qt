from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.app.app_settings import (
    load_ui_theme_settings,
    save_ui_font_scale,
    save_ui_theme_settings,
)
from src.app.main_window import _apply_accessible_ui_scale, _theme_palette
from src.tabs.rysunek.tab_rysunek import TabRysunek


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_apply_high_contrast_theme_changes_colors(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_ui_theme_settings("day", "contrast")
    theme = load_ui_theme_settings()
    assert theme.mode == "day"
    assert theme.motif == "contrast"

    day_palette = _theme_palette("day", "contrast")
    night_palette = _theme_palette("night", "contrast")

    assert day_palette["window_bg"] != day_palette["text"]
    assert night_palette["window_bg"] != night_palette["text"]
    assert day_palette["scroll_handle"] != night_palette["scroll_handle"]


def test_apply_tech_theme_saved_and_palette_available(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_ui_theme_settings("night", "tech")
    theme = load_ui_theme_settings()
    assert theme.mode == "night"
    assert theme.motif == "tech"

    tech_palette = _theme_palette("night", "tech")
    assert tech_palette["window_bg"] != tech_palette["text"]
    assert tech_palette["scroll_handle"].startswith("#")


def test_widgets_have_accessible_names(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    _ = _app()

    tab = TabRysunek()

    assert tab.btn_load.accessibleName() == "settings_load"
    assert tab.btn_save.accessibleName() == "settings_save"
    assert tab.cb_mode.accessibleName() == "theme_mode"
    assert tab.cb_motif.accessibleName() == "theme_motif"
    assert tab.cb_motif.findData("tech") >= 0
    assert tab.cb_font_scale.accessibleName() == "theme_font_scale"
    assert tab.btn_apply_theme.accessibleName() == "theme_apply"


def test_font_scaling_applied(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = _app()

    save_ui_font_scale(0.85)
    _apply_accessible_ui_scale("day", "cream")
    small_size = app.font().pointSizeF()

    save_ui_font_scale(1.20)
    _apply_accessible_ui_scale("day", "cream")
    large_size = app.font().pointSizeF()

    assert large_size > small_size
    assert abs(float(app.property("_tech_modul_ui_font_scale") or 1.0) - 1.20) < 1e-9
