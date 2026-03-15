from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_tab_modul_returns_domain_debug_snapshot_on_init(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    snap = w.get_domain_debug_snapshot_dict()

    assert isinstance(snap, dict)
    assert "draft" in snap
    assert "resolved" in snap

    assert snap["draft"]["name"] == getattr(w._draft, "name", "")
    assert snap["resolved"]["module_name"] == getattr(w._draft, "name", "")


def test_tab_modul_returns_updated_domain_debug_snapshot_after_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="DEBUG_WARDROBE",
        width_mm=910.0,
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

    snap = w.get_domain_debug_snapshot_dict()

    assert snap["draft"]["name"] == "DEBUG_WARDROBE"
    assert float(snap["draft"]["width_mm"]) == 910.0
    assert float(snap["draft"]["depth_mm"]) == 0.0
    assert float(snap["draft"]["height_mm"]) == 0.0

    assert snap["resolved"]["module_name"] == "DEBUG_WARDROBE"
    assert snap["resolved"]["module_family_key"] == "wardrobe"
    assert snap["resolved"]["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert float(snap["resolved"]["width_mm"]) == 910.0
    assert float(snap["resolved"]["depth_mm"]) == 620.0
    assert float(snap["resolved"]["height_mm"]) == 2300.0
    assert snap["resolved"]["materials"]["side"] == "PB16"
    assert snap["resolved"]["edgebands"]["side"] == "ABS 2.0"
