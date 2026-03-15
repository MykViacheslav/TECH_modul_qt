from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_tab_modul_returns_resolved_preview_payload_on_init(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    payload = w.get_resolved_preview_payload_dict()

    assert isinstance(payload, dict)
    assert payload["module_name"] == getattr(w._draft, "name", "")
    assert "effective_dims" in payload
    assert float(payload["effective_dims"]["width_mm"]) == float(w._draft.width_mm)
    assert float(payload["effective_dims"]["depth_mm"]) == float(w._draft.depth_mm)
    assert float(payload["effective_dims"]["height_mm"]) == float(w._draft.height_mm)
    assert "materials" in payload
    assert "edgebands" in payload


def test_tab_modul_returns_resolved_preview_payload_after_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="PREVIEW_WARDROBE",
        width_mm=940.0,
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

    payload = w.get_resolved_preview_payload_dict()

    assert payload["module_name"] == "PREVIEW_WARDROBE"
    assert payload["module_family_key"] == "wardrobe"
    assert payload["material_profile_key"] == "WARDROBE_GRAPHITE"
    assert payload["cabinet_kind"] == "tall"
    assert payload["ref_point"] == "LBB"

    assert float(payload["effective_dims"]["width_mm"]) == 940.0
    assert float(payload["effective_dims"]["depth_mm"]) == 620.0
    assert float(payload["effective_dims"]["height_mm"]) == 2300.0

    assert payload["materials"]["side"] == "PB16"
    assert payload["edgebands"]["side"] == "ABS 2.0"
