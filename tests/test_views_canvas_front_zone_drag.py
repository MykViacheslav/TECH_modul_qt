from PyQt6.QtWidgets import QApplication


def test_front_zone_drag_updates_top_offset_in_offsets_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(120.0)
    w.fhw.sp_front_offset_bottom.setValue(30.0)
    w._on_any_change()

    w.canvas.sig_front_zone_handle_dragged.emit("front_zone_handle__top", 140.0)
    QApplication.processEvents()

    assert abs(w.fhw.sp_front_offset_top.value() - 140.0) < 0.1
    assert abs(w.fhw.sp_front_offset_bottom.value() - 30.0) < 0.1


def test_front_zone_drag_updates_bottom_offset_in_offsets_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(120.0)
    w.fhw.sp_front_offset_bottom.setValue(30.0)
    w._on_any_change()

    w.canvas.sig_front_zone_handle_dragged.emit("front_zone_handle__bottom", 650.0)
    QApplication.processEvents()

    assert abs(w.fhw.sp_front_offset_top.value() - 120.0) < 0.1
    assert abs(w.fhw.sp_front_offset_bottom.value() - 70.0) < 0.1


def test_front_zone_drag_updates_bottom_offset_in_to_top_rail_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_bottom.setValue(0.0)
    w._on_any_change()

    w.canvas.sig_front_zone_handle_dragged.emit("front_zone_handle__bottom", 680.0)
    QApplication.processEvents()

    assert abs(w.fhw.sp_front_offset_bottom.value() - 40.0) < 0.1