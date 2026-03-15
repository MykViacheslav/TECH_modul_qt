from PyQt6.QtWidgets import QApplication


def test_drawer_front_has_saved_drawer_count(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))

    idx = w.fhw.cb_facade_mode.findData("drawers")
    if idx >= 0:
        w.fhw.cb_facade_mode.setCurrentIndex(idx)

    if hasattr(w.fhw, "sp_drawer_count"):
        w.fhw.sp_drawer_count.setValue(3)

    w._on_any_change()

    assert int(getattr(w._draft, "drawer_count", 0)) == 3
    assert str(getattr(w._draft, "facade_mode", "")) == "drawers"