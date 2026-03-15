from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_tab_modul_builds_resolved_domain_state_on_init(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "_resolved_domain_state")
    assert w._resolved_domain_state is not None

    assert w._resolved_domain_state.module_name == getattr(w._draft, "name", "")
    assert float(w._resolved_domain_state.width_mm) == float(w._draft.width_mm)
    assert float(w._resolved_domain_state.depth_mm) == float(w._draft.depth_mm)
    assert float(w._resolved_domain_state.height_mm) == float(w._draft.height_mm)


def test_tab_modul_updates_resolved_domain_state_after_loaded_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="WARDROBE_TEST",
        width_mm=900.0,
        depth_mm=0.0,
        height_mm=0.0,
        module_family="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        cabinet_kind="",
        ref_point="",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front"]),
        materials={},
        edgebands={},
        parts={},
    )

    w._apply_loaded_module(m)

    assert w._resolved_domain_state.module_name == "WARDROBE_TEST"
    assert w._resolved_domain_state.module_family_key == "wardrobe"
    assert w._resolved_domain_state.material_profile_key == "WARDROBE_GRAPHITE"
    assert w._resolved_domain_state.cabinet_kind == "tall"
    assert w._resolved_domain_state.ref_point == "LBB"
    assert float(w._resolved_domain_state.depth_mm) == 620.0
    assert float(w._resolved_domain_state.height_mm) == 2300.0
    assert w._resolved_domain_state.materials["side"] == "PB16"


def test_tab_modul_updates_resolved_domain_state_after_ui_change(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(777.0)
    w.dim.sp_d.setValue(333.0)
    w.dim.sp_h.setValue(444.0)

    w._on_any_change()

    assert float(w._resolved_domain_state.width_mm) == 777.0
    assert float(w._resolved_domain_state.depth_mm) == 333.0
    assert float(w._resolved_domain_state.height_mm) == 444.0
