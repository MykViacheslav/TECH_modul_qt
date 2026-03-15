from PyQt6.QtWidgets import QApplication

from src.storage.default_module_store_json import load_default_module


def test_tab_modul_set_current_as_default_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    # --- ustaw VALID stan (zeby walidacja startowego przepuscila) ---
    w.vis.set_checked(set([
        "side_left", "side_right",
        "top", "bottom",
        "front", "back",
        "shelf",
    ]))

    # materialy (jesli API istnieje)
    if hasattr(w, "mat") and hasattr(w.mat, "set_materials"):
        w.mat.set_materials({"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"})

    # wymiary >= 100
    w.dim.sp_w.setValue(777.0)
    w.dim.sp_d.setValue(333.0)
    w.dim.sp_h.setValue(444.0)

    # dopchnij UI -> draft
    if hasattr(w, "_on_any_change"):
        w._on_any_change()
    elif hasattr(w, "_pull_ui_to_draft"):
        w._pull_ui_to_draft()

    # zapis startowego
    w._on_set_current_as_default()

    m = load_default_module()
    assert m is not None
    assert m.width_mm == 777.0
    assert m.depth_mm == 333.0
    assert m.height_mm == 444.0