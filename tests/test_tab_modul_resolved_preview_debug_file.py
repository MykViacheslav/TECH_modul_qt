from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef
from src.storage.resolved_preview_store_json import load_resolved_preview_payload


def test_tab_modul_saves_resolved_preview_payload_debug_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="DEBUG_FILE_WARDROBE",
        width_mm=960.0,
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

    path = w.save_resolved_preview_payload_debug_file()
    data = load_resolved_preview_payload()

    assert isinstance(path, str)
    assert data["module_name"] == "DEBUG_FILE_WARDROBE"
    assert data["module_family_key"] == "wardrobe"
    assert data["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert float(data["effective_dims"]["width_mm"]) == 960.0
    assert float(data["effective_dims"]["depth_mm"]) == 620.0
    assert float(data["effective_dims"]["height_mm"]) == 2300.0
    assert data["materials"]["side"] == "PB16"
    assert data["edgebands"]["side"] == "ABS 2.0"
