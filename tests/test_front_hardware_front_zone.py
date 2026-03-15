from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef
from src.tabs.modul.tab_modul import FrontHardwareBlock, TabModul


def _make_module() -> ModuleDef:
    return ModuleDef(
        name="TEST_FRONT_ZONE",
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


def test_front_hardware_block_applies_front_zone_to_module():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_layout.setCurrentIndex(w.cb_front_layout.findData("overlay"))
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(600.0)
    w.sp_front_offset_bottom.setValue(18.0)

    m = w.apply_to_module(_make_module())

    assert m.front_layout == "overlay"
    assert m.front_height_mode == "offsets"
    assert m.front_offset_top_mm == 600.0
    assert m.front_offset_bottom_mm == 18.0


def test_front_hardware_block_reads_front_zone_from_module():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()

    m = _make_module()
    m.front_height_mode = "to_top_rail"
    m.front_offset_top_mm = 120.0
    m.front_offset_bottom_mm = 25.0

    w.set_from_module(m)

    assert w.cb_front_height_mode.currentData() == "to_top_rail"
    assert w.sp_front_offset_top.value() == 120.0
    assert w.sp_front_offset_bottom.value() == 25.0


def test_front_hardware_block_zone_summary_for_full_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("full"))

    txt = w.lab_zone_summary.text().lower()
    assert "pelna wysokosc" in txt or "pelna wysokosc" in txt
    assert w.sp_front_offset_top.isEnabled() is False
    assert w.sp_front_offset_bottom.isEnabled() is False


def test_front_hardware_block_zone_summary_for_offsets_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(120.0)
    w.sp_front_offset_bottom.setValue(30.0)

    txt = w.lab_zone_summary.text().lower()
    assert "gora" in txt or "gora" in txt
    assert "120.0" in txt
    assert "30.0" in txt
    assert w.sp_front_offset_top.isEnabled() is True
    assert w.sp_front_offset_bottom.isEnabled() is True


def test_front_hardware_block_zone_summary_for_to_top_rail_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("to_top_rail"))
    w.sp_front_offset_top.setValue(120.0)
    w.sp_front_offset_bottom.setValue(25.0)

    txt = w.lab_zone_summary.text().lower()
    assert "wienca" in txt or "wienca" in txt
    assert "25.0" in txt
    assert w.sp_front_offset_top.isEnabled() is False
    assert w.sp_front_offset_bottom.isEnabled() is True


def test_front_hardware_block_hides_irrelevant_rows_for_full_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("full"))

    assert w._is_form_row_visible(w.cb_top_ref_mode) is False
    assert w._is_form_row_visible(w.cb_bottom_ref_mode) is False
    assert w._is_form_row_visible(w.sp_front_offset_top) is False
    assert w._is_form_row_visible(w.sp_front_offset_bottom) is False


def test_front_hardware_block_shows_only_relevant_rows_for_to_top_rail_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("to_top_rail"))

    assert w._is_form_row_visible(w.cb_top_ref_mode) is True
    assert w._is_form_row_visible(w.cb_bottom_ref_mode) is True
    assert w._is_form_row_visible(w.sp_front_offset_top) is False
    assert w._is_form_row_visible(w.sp_front_offset_bottom) is True


def test_front_hardware_block_shows_only_offset_rows_for_offsets_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))

    assert w._is_form_row_visible(w.cb_top_ref_mode) is False
    assert w._is_form_row_visible(w.cb_bottom_ref_mode) is False
    assert w._is_form_row_visible(w.sp_front_offset_top) is True
    assert w._is_form_row_visible(w.sp_front_offset_bottom) is True


def test_front_hardware_block_reset_front_zone_for_offsets_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(140.0)
    w.sp_front_offset_bottom.setValue(45.0)

    w.btn_reset_front_zone.click()

    assert w.sp_front_offset_top.value() == 0.0
    assert w.sp_front_offset_bottom.value() == 0.0


def test_front_hardware_block_reset_front_zone_for_to_top_rail_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("to_top_rail"))
    w.sp_front_offset_top.setValue(140.0)
    w.sp_front_offset_bottom.setValue(45.0)

    w.btn_reset_front_zone.click()

    assert w.sp_front_offset_top.value() == 140.0
    assert w.sp_front_offset_bottom.value() == 0.0


def test_front_hardware_block_normalize_offsets_clamps_to_height():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(500.0)
    w.sp_front_offset_bottom.setValue(400.0)

    changed = w.normalize_front_zone(module_height_mm=720.0, top_rail_thickness_mm=18.0)

    assert changed is True
    assert w.sp_front_offset_top.value() + w.sp_front_offset_bottom.value() <= 718.0


def test_front_hardware_block_normalize_to_top_rail_clamps_bottom():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("to_top_rail"))
    w.sp_front_offset_top.setValue(999.0)
    w.sp_front_offset_bottom.setValue(999.0)

    changed = w.normalize_front_zone(module_height_mm=720.0, top_rail_thickness_mm=18.0)

    assert changed is True
    assert w.sp_front_offset_top.value() == 999.0
    assert w.sp_front_offset_bottom.value() <= 700.0


def test_front_hardware_block_has_persistent_zone_context():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.set_zone_context("Wybrano front do edycji.")

    assert "wybrano front" in w.lab_zone_context.text().lower()

    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(80.0)
    w.sp_front_offset_bottom.setValue(20.0)

    assert "wybrano front" in w.lab_zone_context.text().lower()


def test_front_hardware_block_clear_zone_context_restores_default_message():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.set_zone_context("Testowy kontekst")
    assert "testowy" in w.lab_zone_context.text().lower()

    w.clear_zone_context()
    txt = w.lab_zone_context.text().lower()

    assert "aktywna edycja" in txt


def test_front_hardware_block_front_summary_for_drawers_offsets_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_layout.setCurrentIndex(w.cb_front_layout.findData("overlay"))
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("offsets"))
    w.sp_front_offset_top.setValue(120.0)
    w.sp_front_offset_bottom.setValue(30.0)
    w.cb_facade_mode.setCurrentIndex(w.cb_facade_mode.findData("drawers"))
    w.sp_drawer_count.setValue(3)

    txt = w.lab_front_summary.text().lower()

    assert "nakladany" in txt or "nakladany" in txt
    assert "offsety" in txt
    assert "120.0" in txt
    assert "30.0" in txt
    assert "szuflady" in txt
    assert "3" in txt


def test_front_hardware_block_front_summary_for_doors_full_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_layout.setCurrentIndex(w.cb_front_layout.findData("inset"))
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("full"))
    w.cb_facade_mode.setCurrentIndex(w.cb_facade_mode.findData("doors"))

    txt = w.lab_front_summary.text().lower()

    assert "wewnetrzny" in txt or "wewnetrzny" in txt
    assert "pelna wysokosc" in txt or "pelna wysokosc" in txt
    assert "drzwi" in txt


def test_front_hardware_block_front_summary_for_to_top_rail_mode():
    app = QApplication.instance() or QApplication([])

    w = FrontHardwareBlock()
    w.cb_front_height_mode.setCurrentIndex(w.cb_front_height_mode.findData("to_top_rail"))
    w.sp_front_offset_bottom.setValue(55.0)
    w.cb_facade_mode.setCurrentIndex(w.cb_facade_mode.findData("drawers"))
    w.sp_drawer_count.setValue(4)

    txt = w.lab_front_summary.text().lower()

    assert "wienca" in txt or "wienca" in txt
    assert "55.0" in txt
    assert "szuflady" in txt
    assert "4" in txt


def test_tab_modul_normalizes_front_zone_when_height_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = TabModul()

    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.dim.sp_h.setValue(720.0)
    w.fhw.sp_front_offset_top.setValue(500.0)
    w.fhw.sp_front_offset_bottom.setValue(200.0)
    w._on_any_change()

    assert w.fhw.sp_front_offset_top.value() + w.fhw.sp_front_offset_bottom.value() <= 718.0

    w.dim.sp_h.setValue(300.0)
    w._on_any_change()

    assert w.fhw.sp_front_offset_top.value() + w.fhw.sp_front_offset_bottom.value() <= 298.0


def test_tab_modul_selecting_front_sets_zone_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = TabModul()
    w._on_selected_part("front")

    txt = w.fhw.lab_zone_context.text().lower()
    assert "wybrano front" in txt or "front" in txt


def test_tab_modul_selecting_non_front_clears_to_default_zone_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = TabModul()
    w._on_selected_part("front")
    assert "front" in w.fhw.lab_zone_context.text().lower()

    w._on_selected_part("side_left")
    txt = w.fhw.lab_zone_context.text().lower()

    assert "aktywna edycja" in txt
