from PyQt6.QtWidgets import QApplication


def test_catalog_store_exposes_default_material_profiles(tmp_path):
    from src.storage.catalog_store_json import CatalogStoreJson

    catalog = CatalogStoreJson(tmp_path / "catalog.json")

    profile = catalog.get_material_profile("STD_WHITE")

    assert profile.key == "STD_WHITE"
    assert profile.name_pl == "Standard bialy"
    assert profile.material_map["carcass"] == "PB18"
    assert profile.material_map["front"] == "MDF19"
    assert profile.edgeband_map["carcass"] == "ABS 0.8"
    assert profile.hardware_vendor_map["hinge"] == "generic"


def test_catalog_editor_dialog_saves_material_profiles(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    dlg = CatalogEditorDialog(None, catalog)

    profiles = dlg.page_profiles.table

    profiles.item(0, 1).setText("Bialy premium")
    profiles.item(0, 3).setText("PB16")
    profiles.item(0, 4).setText("MDF19_LAK")
    profiles.item(0, 6).setText("ABS 2.0")
    profiles.item(0, 9).setText("blum")
    profiles.item(0, 10).setText("blum")

    dlg._save_and_accept()

    saved = catalog.get_material_profile("STD_WHITE")

    assert saved.name_pl == "Bialy premium"
    assert saved.material_map["carcass"] == "PB16"
    assert saved.material_map["front"] == "MDF19_LAK"
    assert saved.edgeband_map["carcass"] == "ABS 2.0"
    assert saved.hardware_vendor_map["hinge"] == "blum"
    assert saved.hardware_vendor_map["drawer_system"] == "blum"


def test_materials_block_reads_profiles_from_catalog(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import MaterialsBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        material_profiles=[
            {
                "key": "STD_WHITE",
                "name_pl": "Standard bialy",
                "description": "Profil bazowy",
                "material_map": {"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
                "edgeband_map": {"carcass": "ABS 0.8", "front": "ABS 0.8", "back": "Brak"},
                "hardware_vendor_map": {"hinge": "generic", "drawer_system": "generic"},
            },
            {
                "key": "CUSTOM_LAK",
                "name_pl": "Lakier klienta",
                "description": "Profil testowy z katalogu",
                "material_map": {"carcass": "PB16", "front": "MDF19_LAK", "back": "HDF3"},
                "edgeband_map": {"carcass": "ABS 2.0", "front": "ABS 2.0", "back": "Brak"},
                "hardware_vendor_map": {"hinge": "blum", "drawer_system": "hettich"},
            },
        ]
    )

    block = MaterialsBlock(catalog)

    idx = block.cb_profile.findData("CUSTOM_LAK")
    assert idx >= 0

    block.cb_profile.setCurrentIndex(idx)

    assert block.get_profile_key() == "CUSTOM_LAK"
    assert "Profil testowy z katalogu" in block.lab_profile_desc.text()
