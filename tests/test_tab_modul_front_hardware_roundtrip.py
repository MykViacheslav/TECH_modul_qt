from PyQt6.QtWidgets import QApplication


def test_fhw_fields_are_saved_into_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # ustaw UI w bloku Fronty i okucia
    def set_data(cb, val: str):
        idx = cb.findData(val)
        if idx >= 0:
            cb.setCurrentIndex(idx)

    set_data(w.fhw.cb_front_layout, "inset")
    set_data(w.fhw.cb_facade_mode, "drawers")
    set_data(w.fhw.cb_hinge_vendor, "generic")
    set_data(w.fhw.cb_drawer_vendor, "generic")

    w.fhw.chk_tipon.setChecked(True)
    w.fhw.sp_rear.setValue(12.0)
    w.fhw.sp_tip.setValue(25.0)

    # pull UI -> draft
    w._on_any_change()

    assert w._draft.front_layout == "inset"
    assert w._draft.facade_mode == "drawers"
    assert w._draft.drawer_tip_on is True
    assert abs(w._draft.drawer_rear_clearance_mm - 12.0) < 0.001
    assert abs(w._draft.drawer_tip_on_clearance_mm - 25.0) < 0.001