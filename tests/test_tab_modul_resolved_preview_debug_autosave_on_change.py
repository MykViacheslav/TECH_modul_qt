from PyQt6.QtWidgets import QApplication

from src.storage.resolved_preview_store_json import load_resolved_preview_payload


def test_tab_modul_autosaves_resolved_preview_debug_file_on_change_when_env_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_WRITE_RESOLVED_DEBUG_ON_CHANGE", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_w.setValue(888.0)
    w.dim.sp_d.setValue(444.0)
    w.dim.sp_h.setValue(555.0)

    w._on_any_change()

    data = load_resolved_preview_payload()

    assert data["module_name"] == getattr(w._draft, "name", "")
    assert float(data["effective_dims"]["width_mm"]) == 888.0
    assert float(data["effective_dims"]["depth_mm"]) == 444.0
    assert float(data["effective_dims"]["height_mm"]) == 555.0
    assert "materials" in data
    assert "edgebands" in data