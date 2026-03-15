from PyQt6.QtWidgets import QApplication


def test_part_def_material_override_roundtrip():
    from src.domain.module_models import PartDef

    p1 = PartDef(
        key="side_left",
        name_pl="Bok lewy",
        material_key="PB16",
        material_override_key="PB16",
        dims_mm={"w": 500.0, "h": 720.0, "t": 16.0},
        edge_banding={"left": "ABS 0.8"},
    )

    p2 = PartDef.from_dict(p1.to_dict())

    assert p2.material_key == "PB16"
    assert p2.material_override_key == "PB16"
    assert p2.dims_mm["t"] == 16.0


def test_selected_part_material_override_persists_after_rebuild(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.vis.set_checked({"side_left", "side_right", "top", "bottom", "front", "back"})
    w._on_any_change()

    w._selected_part_key = "side_left"
    w.tree.select_part("side_left")
    w._render_right()

    idx = w.bom.cb_part_material.findData("PB16")
    assert idx >= 0
    w.bom.cb_part_material.setCurrentIndex(idx)

    assert w._draft.parts["side_left"].material_key == "PB16"
    assert getattr(w._draft.parts["side_left"], "material_override_key", "") == "PB16"

    w.shelves.set_value(1)
    w._on_any_change()

    assert w._draft.parts["side_left"].material_key == "PB16"
    assert getattr(w._draft.parts["side_left"], "material_override_key", "") == "PB16"
    assert w._draft.parts["side_right"].material_key == w._draft.materials["carcass"]


def test_reset_part_material_override_returns_group_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.vis.set_checked({"side_left", "side_right", "top", "bottom"})
    w.mat.set_materials({"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"})
    w._on_any_change()

    w._selected_part_key = "side_left"
    w.tree.select_part("side_left")
    w._render_right()

    idx = w.bom.cb_part_material.findData("PB16")
    assert idx >= 0
    w.bom.cb_part_material.setCurrentIndex(idx)
    assert w._draft.parts["side_left"].material_key == "PB16"

    w.bom.btn_reset_part_material.click()

    assert w._draft.parts["side_left"].material_key == "PB18"
    assert getattr(w._draft.parts["side_left"], "material_override_key", "") == ""
