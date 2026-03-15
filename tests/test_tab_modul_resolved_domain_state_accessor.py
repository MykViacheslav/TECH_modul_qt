from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_tab_modul_returns_resolved_domain_state_dict_on_init(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    d = w.get_resolved_domain_state_dict()

    assert isinstance(d, dict)
    assert d["module_name"] == getattr(w._draft, "name", "")
    assert float(d["width_mm"]) == float(w._draft.width_mm)
    assert float(d["depth_mm"]) == float(w._draft.depth_mm)
    assert float(d["height_mm"]) == float(w._draft.height_mm)
    assert "materials" in d
    assert "edgebands" in d


def test_tab_modul_returns_updated_resolved_domain_state_dict_after_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="ACC_WARDROBE",
        width_mm=950.0,
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

    d = w.get_resolved_domain_state_dict()

    assert d["module_name"] == "ACC_WARDROBE"
    assert d["module_family_key"] == "wardrobe"
    assert d["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert d["cabinet_kind"] == "tall"
    assert d["ref_point"] == "LBB"
    assert float(d["width_mm"]) == 950.0
    assert float(d["depth_mm"]) == 620.0
    assert float(d["height_mm"]) == 2300.0
    assert d["materials"]["side"] == "PB16"
    assert d["edgebands"]["side"] == "ABS 2.0"
