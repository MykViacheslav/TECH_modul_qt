from PyQt6.QtWidgets import QApplication


def _make_module():
    from src.domain.module_models import ModuleDef

    return ModuleDef(
        name="TEST_FRONT_REFS",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        module_family="base",
        material_profile_key="TEST",
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front"]),
        materials={},
        edgebands={},
        parts={},
    )


def _load_module_from_store_by_name(w, name: str):
    store = w._store

    for fn_name in ("load", "load_module", "get", "read"):
        if not hasattr(store, fn_name):
            continue

        fn = getattr(store, fn_name)
        try:
            raw = fn(name)
        except TypeError:
            continue

        return raw

    raise AssertionError("Store nie ma metody load/load_module/get/read.")


def test_front_hardware_block_applies_reference_and_gaps_to_module():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import FrontHardwareBlock

    w = FrontHardwareBlock()

    idx = w.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.cb_front_height_mode.setCurrentIndex(idx)

    idx = w.cb_top_ref_mode.findData("rail_center")
    if idx >= 0:
        w.cb_top_ref_mode.setCurrentIndex(idx)

    idx = w.cb_bottom_ref_mode.findData("rail_start")
    if idx >= 0:
        w.cb_bottom_ref_mode.setCurrentIndex(idx)

    w.sp_gap_left.setValue(1.5)
    w.sp_gap_right.setValue(2.0)
    w.sp_gap_top.setValue(2.5)
    w.sp_gap_bottom.setValue(3.0)
    w.sp_gap_between_vertical.setValue(2.0)

    m = w.apply_to_module(_make_module())

    assert getattr(m, "front_top_ref_mode", None) == "rail_center"
    assert getattr(m, "front_bottom_ref_mode", None) == "rail_start"
    assert abs(float(getattr(m, "front_gap_left_mm", 0.0)) - 1.5) < 0.1
    assert abs(float(getattr(m, "front_gap_right_mm", 0.0)) - 2.0) < 0.1
    assert abs(float(getattr(m, "front_gap_top_mm", 0.0)) - 2.5) < 0.1
    assert abs(float(getattr(m, "front_gap_bottom_mm", 0.0)) - 3.0) < 0.1
    assert abs(float(getattr(m, "front_gap_between_vertical_mm", 0.0)) - 2.0) < 0.1


def test_front_hardware_block_reads_reference_and_gaps_from_module():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import FrontHardwareBlock

    w = FrontHardwareBlock()
    m = _make_module()

    setattr(m, "front_top_ref_mode", "rail_center")
    setattr(m, "front_bottom_ref_mode", "rail_start")
    setattr(m, "front_gap_left_mm", 1.5)
    setattr(m, "front_gap_right_mm", 2.0)
    setattr(m, "front_gap_top_mm", 2.5)
    setattr(m, "front_gap_bottom_mm", 3.0)
    setattr(m, "front_gap_between_vertical_mm", 2.0)

    w.set_from_module(m)

    assert w.cb_top_ref_mode.currentData() == "rail_center"
    assert w.cb_bottom_ref_mode.currentData() == "rail_start"
    assert abs(w.sp_gap_left.value() - 1.5) < 0.1
    assert abs(w.sp_gap_right.value() - 2.0) < 0.1
    assert abs(w.sp_gap_top.value() - 2.5) < 0.1
    assert abs(w.sp_gap_bottom.value() - 3.0) < 0.1
    assert abs(w.sp_gap_between_vertical.value() - 2.0) < 0.1


def test_front_hardware_block_summary_shows_references_and_gaps():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import FrontHardwareBlock

    w = FrontHardwareBlock()

    idx = w.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.cb_front_height_mode.setCurrentIndex(idx)

    idx = w.cb_top_ref_mode.findData("rail_center")
    if idx >= 0:
        w.cb_top_ref_mode.setCurrentIndex(idx)

    idx = w.cb_bottom_ref_mode.findData("rail_end")
    if idx >= 0:
        w.cb_bottom_ref_mode.setCurrentIndex(idx)

    idx = w.cb_facade_mode.findData("drawers")
    if idx >= 0:
        w.cb_facade_mode.setCurrentIndex(idx)

    w.sp_drawer_count.setValue(4)
    w.sp_gap_left.setValue(1.5)
    w.sp_gap_right.setValue(2.0)
    w.sp_gap_top.setValue(2.5)
    w.sp_gap_bottom.setValue(3.0)
    w.sp_gap_between_vertical.setValue(2.0)

    txt = w.lab_front_summary.text().lower()

    assert "1/2" in txt or "pol" in txt or "pol" in txt
    assert "szuflady" in txt
    assert "4" in txt
    assert "1.5" in txt
    assert "2.0" in txt
    assert "2.5" in txt
    assert "3.0" in txt


def test_store_roundtrip_restores_references_and_gaps(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.ed_name.setText("TEST_FRONT_REFS_GAPS_STORE")
    w.dim.sp_w.setValue(800.0)
    w.dim.sp_d.setValue(560.0)
    w.dim.sp_h.setValue(720.0)

    idx = w.fhw.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    idx = w.fhw.cb_top_ref_mode.findData("rail_center")
    if idx >= 0:
        w.fhw.cb_top_ref_mode.setCurrentIndex(idx)

    idx = w.fhw.cb_bottom_ref_mode.findData("rail_start")
    if idx >= 0:
        w.fhw.cb_bottom_ref_mode.setCurrentIndex(idx)

    w.fhw.sp_gap_left.setValue(1.5)
    w.fhw.sp_gap_right.setValue(2.0)
    w.fhw.sp_gap_top.setValue(2.5)
    w.fhw.sp_gap_bottom.setValue(3.0)
    w.fhw.sp_gap_between_vertical.setValue(2.0)

    w._on_any_change()
    w._on_dim_save_clicked()

    loaded = _load_module_from_store_by_name(w, "TEST_FRONT_REFS_GAPS_STORE")
    w._apply_loaded_module(loaded)

    assert w.fhw.cb_top_ref_mode.currentData() == "rail_center"
    assert w.fhw.cb_bottom_ref_mode.currentData() == "rail_start"
    assert abs(w.fhw.sp_gap_left.value() - 1.5) < 0.1
    assert abs(w.fhw.sp_gap_right.value() - 2.0) < 0.1
    assert abs(w.fhw.sp_gap_top.value() - 2.5) < 0.1
    assert abs(w.fhw.sp_gap_bottom.value() - 3.0) < 0.1
    assert abs(w.fhw.sp_gap_between_vertical.value() - 2.0) < 0.1