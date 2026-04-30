from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtWidgets import QApplication


def _scene_has_key(canvas, key: str) -> bool:
    for item in canvas.scene.items():
        try:
            if item.data(0) == key:
                return True
        except Exception:
            pass
    return False


def test_front_zone_handles_hidden_for_full_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("full")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w._on_any_change()

    assert _scene_has_key(w.canvas, "front_zone_handle__top") is False
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom") is False
    assert _scene_has_key(w.canvas, "front_zone_handle__top__label") is False
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom__label") is False


def test_front_zone_handles_visible_for_offsets_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(120.0)
    w.fhw.sp_front_offset_bottom.setValue(30.0)
    w._on_any_change()

    assert _scene_has_key(w.canvas, "front_zone_handle__top") is True
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom") is True
    assert _scene_has_key(w.canvas, "front_zone_handle__top__label") is True
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom__label") is True


def test_front_zone_handles_for_to_top_rail_show_only_bottom(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w._on_any_change()

    assert _scene_has_key(w.canvas, "front_zone_handle__top") is False
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom") is True
    assert _scene_has_key(w.canvas, "front_zone_handle__top__label") is False
    assert _scene_has_key(w.canvas, "front_zone_handle__bottom__label") is True


def test_front_zone_click_sets_active_handle_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w._on_any_change()
    w._on_front_zone_handle_clicked("front_zone_handle__top")

    assert w.canvas.active_front_zone_handle_key() == "front_zone_handle__top"


def test_selecting_non_front_clears_active_handle_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w._on_any_change()
    w._on_front_zone_handle_clicked("front_zone_handle__bottom")
    assert w.canvas.active_front_zone_handle_key() == "front_zone_handle__bottom"

    w._on_selected_part("side_left")
    assert w.canvas.active_front_zone_handle_key() == ""
