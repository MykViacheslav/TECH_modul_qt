import json

from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_tab_modul_returns_resolved_preview_payload_json_on_init(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    txt = w.get_resolved_preview_payload_json()
    data = json.loads(txt)

    assert isinstance(txt, str)
    assert isinstance(data, dict)

    assert data["module_name"] == getattr(w._draft, "name", "")
    assert "effective_dims" in data
    assert "materials" in data
    assert "edgebands" in data


def test_tab_modul_returns_updated_resolved_preview_payload_json_after_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="JSON_WARDROBE",
        width_mm=930.0,
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

    txt = w.get_resolved_preview_payload_json()
    data = json.loads(txt)

    assert data["module_name"] == "JSON_WARDROBE"
    assert data["module_family_key"] == "wardrobe"
    assert data["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert data["cabinet_kind"] == "tall"
    assert data["ref_point"] == "LBB"

    assert float(data["effective_dims"]["width_mm"]) == 930.0
    assert float(data["effective_dims"]["depth_mm"]) == 620.0
    assert float(data["effective_dims"]["height_mm"]) == 2300.0

    assert data["materials"]["side"] == "PB16"
    assert data["edgebands"]["side"] == "ABS 2.0"
