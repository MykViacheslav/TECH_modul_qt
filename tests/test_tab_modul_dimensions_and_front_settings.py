from PyQt6.QtWidgets import QApplication


def _set_combo_by_data(cb, value: str) -> None:
    idx = cb.findData(value)
    assert idx >= 0, f"Nie znaleziono wartosci data={value!r} w {cb}"
    cb.setCurrentIndex(idx)


def test_dimensions_change_updates_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(777.0)
    w.dim.sp_d.setValue(333.0)
    w.dim.sp_h.setValue(444.0)

    w._on_any_change()

    assert w._draft.width_mm == 777.0
    assert w._draft.depth_mm == 333.0
    assert w._draft.height_mm == 444.0


def test_module_type_updates_draft_and_reference_kind(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    _set_combo_by_data(w.ref.cb_module_type, "hanging")
    w._on_any_change()

    assert w._draft.module_type == "hanging"
    assert w._draft.cabinet_kind == "upper"
    assert w.ref.get_kind() == "upper"


def test_front_settings_are_saved_into_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # fronty musza byc widoczne
    w.vis.set_checked(set([
        "side_left", "side_right", "top", "bottom", "front"
    ]))

    _set_combo_by_data(w.fhw.cb_front_layout, "inset")
    _set_combo_by_data(w.fhw.cb_facade_mode, "drawers")
    w.fhw.sp_drawer_count.setValue(4)

    _set_combo_by_data(w.fhw.cb_hinge_vendor, "generic")
    _set_combo_by_data(w.fhw.cb_drawer_vendor, "generic")

    w.fhw.chk_tipon.setChecked(True)
    w.fhw.sp_rear.setValue(13.0)
    w.fhw.sp_tip.setValue(25.0)

    w._on_any_change()

    assert w._draft.front_layout == "inset"
    assert w._draft.facade_mode == "drawers"
    assert w._draft.drawer_count == 4
    assert w._draft.hinge_vendor == "generic"
    assert w._draft.drawer_vendor == "generic"
    assert w._draft.drawer_tip_on is True
    assert w._draft.drawer_rear_clearance_mm == 13.0
    assert w._draft.drawer_tip_on_clearance_mm == 25.0


def test_inset_front_rebuilds_part_between_sides(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # ustaw pelny korpus + front
    w.vis.set_checked(set([
        "side_left", "side_right", "top", "bottom", "front"
    ]))

    # wymiary
    w.dim.sp_w.setValue(800.0)
    w.dim.sp_d.setValue(500.0)
    w.dim.sp_h.setValue(700.0)

    # material standardowy
    if hasattr(w.mat, "set_materials"):
        w.mat.set_materials({
            "carcass": "PB18",
            "front": "MDF19",
            "back": "HDF2.5",
        })

    _set_combo_by_data(w.fhw.cb_front_layout, "inset")
    _set_combo_by_data(w.fhw.cb_facade_mode, "doors")

    w._on_any_change()

    front = w._draft.parts.get("front")
    assert front is not None, "Brak czesci 'front' po rebuild"

    # inset = pomiedzy bokami i pomiedzy wiencami
    # dla PB18 i wymiarow 800x700 => 764 x 664
    assert round(float(front.dims_mm["w"]), 3) == 764.0
    assert round(float(front.dims_mm["h"]), 3) == 664.0


def test_overlay_front_rebuilds_full_size_part(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set([
        "side_left", "side_right", "top", "bottom", "front"
    ]))

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_d.setValue(500.0)
    w.dim.sp_h.setValue(700.0)

    if hasattr(w.mat, "set_materials"):
        w.mat.set_materials({
            "carcass": "PB18",
            "front": "MDF19",
            "back": "HDF2.5",
        })

    _set_combo_by_data(w.fhw.cb_front_layout, "overlay")
    _set_combo_by_data(w.fhw.cb_facade_mode, "doors")

    w._on_any_change()

    front = w._draft.parts.get("front")
    assert front is not None, "Brak czesci 'front' po rebuild"

    # overlay = pelny wymiar frontu
    assert round(float(front.dims_mm["w"]), 3) == 800.0
    assert round(float(front.dims_mm["h"]), 3) == 700.0


def test_drawing_settings_block_stores_new_front_options():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import DrawingSettingsBlock

    b = DrawingSettingsBlock()

    b.sp_hinge_edge_offset.setValue(21.0)
    b.sp_auto_double_front_width.setValue(850.0)

    data = b.get_values()

    assert data["hinge_edge_offset_mm"] == 21.0
    assert data["auto_double_front_width_mm"] == 850.0
