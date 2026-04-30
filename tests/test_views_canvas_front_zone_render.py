from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtWidgets import QApplication


def _find_scene_rect(canvas, key: str):
    for item in canvas.scene.items():
        try:
            if item.data(0) == key and hasattr(item, "rect"):
                return item.rect()
        except Exception:
            pass
    return None


def test_tab_modul_renders_front_zone_full_height_in_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_layout.findData("overlay")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    idx = w.fhw.cb_front_height_mode.findData("full")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(600.0)
    w.fhw.sp_front_offset_bottom.setValue(18.0)

    w._on_any_change()

    r = _find_scene_rect(w.canvas, "front__front")
    assert r is not None

    assert abs(r.left() - 2.0) < 0.1
    assert abs(r.top() - 0.0) < 0.1
    assert abs(r.width() - 796.0) < 0.1
    assert abs(r.height() - 720.0) < 0.1


def test_tab_modul_renders_front_zone_with_offsets_in_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_layout.findData("overlay")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(600.0)
    w.fhw.sp_front_offset_bottom.setValue(18.0)

    w._on_any_change()

    r = _find_scene_rect(w.canvas, "front__front")
    assert r is not None

    assert abs(r.left() - 2.0) < 0.1
    assert abs(r.top() - 600.0) < 0.1
    assert abs(r.width() - 796.0) < 0.1
    assert abs(r.height() - 102.0) < 0.1


def test_tab_modul_renders_front_zone_to_top_rail_with_bottom_offset_in_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_layout.findData("overlay")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    idx = w.fhw.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(999.0)   # ma byc ignorowane
    w.fhw.sp_front_offset_bottom.setValue(40.0)

    w._on_any_change()

    r = _find_scene_rect(w.canvas, "front__front")
    assert r is not None

    assert abs(r.left() - 2.0) < 0.1
    assert abs(r.top() - 18.0) < 0.1
    assert abs(r.width() - 796.0) < 0.1
    assert abs(r.height() - 662.0) < 0.1
