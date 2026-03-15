from PyQt6.QtWidgets import QApplication


def _set_combo_by_data(cb, value: str) -> None:
    idx = cb.findData(value)
    assert idx >= 0, f"Nie znaleziono data={value!r}"
    cb.setCurrentIndex(idx)


def test_selecting_material_profile_updates_group_fields_and_hardware(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    _set_combo_by_data(w.mat.cb_profile, "OAK_PREMIUM")

    assert w.mat.get_profile_key() == "OAK_PREMIUM"
    assert w.mat.get_materials() == {
        "carcass": "PB18",
        "front": "MDF19_LAK",
        "back": "HDF2.5",
    }
    assert w.mat.get_edgebands() == {
        "carcass": "ABS 2.0",
        "front": "ABS 2.0",
        "back": "Brak",
    }
    assert str(w.fhw.cb_hinge_vendor.currentData() or "") == "blum"
    assert str(w.fhw.cb_drawer_vendor.currentData() or "") == "blum"

    assert w._draft.material_profile_key == "OAK_PREMIUM"
    assert w._draft.materials["carcass"] == "PB18"
    assert w._draft.materials["front"] == "MDF19_LAK"
    assert w._draft.edgebands["carcass"] == "ABS 2.0"
    assert w._draft.edgebands["side"] == "ABS 2.0"
    assert w._draft.hinge_vendor == "blum"
    assert w._draft.drawer_vendor == "blum"
