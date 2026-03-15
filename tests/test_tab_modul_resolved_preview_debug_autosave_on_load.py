from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef
from src.storage.resolved_preview_store_json import load_resolved_preview_payload


def test_tab_modul_autosaves_resolved_preview_debug_file_on_apply_when_env_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_WRITE_RESOLVED_DEBUG_ON_LOAD", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="AUTO_DEBUG_SAVE_LOAD",
        width_mm=970.0,
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

    data = load_resolved_preview_payload()

    assert data["module_name"] == "AUTO_DEBUG_SAVE_LOAD"
    assert data["module_family_key"] == "wardrobe"
    assert data["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert float(data["effective_dims"]["width_mm"]) == 970.0
    assert float(data["effective_dims"]["depth_mm"]) == 620.0
    assert float(data["effective_dims"]["height_mm"]) == 2300.0
    assert data["materials"]["side"] == "PB16"
    assert data["edgebands"]["side"] == "ABS 2.0"
