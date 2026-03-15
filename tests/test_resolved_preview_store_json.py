from src.storage.resolved_preview_store_json import (
    get_resolved_preview_debug_path,
    save_resolved_preview_payload,
    load_resolved_preview_payload,
)


def test_resolved_preview_store_json_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    payload = {
        "module_name": "DEBUG_A",
        "module_family_key": "wardrobe",
        "effective_dims": {
            "width_mm": 900.0,
            "depth_mm": 620.0,
            "height_mm": 2300.0,
        },
        "materials": {
            "side": "PB18_GRAPHITE",
        },
        "edgebands": {
            "side": "ABS_GRAPHITE_1MM",
        },
    }

    path = save_resolved_preview_payload(payload)
    loaded = load_resolved_preview_payload()

    assert path == get_resolved_preview_debug_path()
    assert loaded["module_name"] == "DEBUG_A"
    assert loaded["module_family_key"] == "wardrobe"
    assert float(loaded["effective_dims"]["depth_mm"]) == 620.0
    assert loaded["materials"]["side"] == "PB18_GRAPHITE"
    assert loaded["edgebands"]["side"] == "ABS_GRAPHITE_1MM"