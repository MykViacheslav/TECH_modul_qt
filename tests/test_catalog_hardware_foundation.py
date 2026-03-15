import json

from PyQt6.QtWidgets import QApplication


def test_catalog_store_lists_hardware_manufacturers_and_fallbacks(tmp_path):
    from src.storage.catalog_store_json import CatalogStoreJson

    custom_catalog = {
        "materials": [],
        "edgebands": [],
        "hardware": [
            {"key": "hinge_generic", "name_pl": "Zawias", "manufacturer": "generic", "category": "hinge", "unit": "szt", "price_pln": 3.0},
            {"key": "hinge_hafele", "name_pl": "Zawias Hafele", "manufacturer": "hafele", "category": "hinge", "unit": "szt", "price_pln": 7.5},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog = CatalogStoreJson(path)

    assert {"generic", "hafele"} <= set(catalog.list_hardware_manufacturers("hinge"))
    assert catalog.find_hardware("hinge", "hafele").key == "hinge_hafele"
    assert catalog.find_hardware("hinge", "missing").key == "hinge_generic"


def test_catalog_editor_dialog_saves_material_and_hardware_prices(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    dlg = CatalogEditorDialog(None, catalog)

    materials = dlg.page_materials.table
    hardware = dlg.page_hardware.table

    materials.item(0, 2).setText("Kronospan")
    materials.item(0, 7).setText("88.5")

    hardware.item(0, 2).setText("hafele")
    hardware.item(0, 6).setText("6.4")

    dlg._save_and_accept()

    saved_material = catalog.get_material("PB18")
    saved_hardware = catalog.get_hardware("hinge_generic")

    assert saved_material is not None
    assert saved_material.manufacturer == "Kronospan"
    assert float(saved_material.price_pln_per_m2) == 88.5

    assert saved_hardware is not None
    assert saved_hardware.manufacturer == "hafele"
    assert float(saved_hardware.price_pln) == 6.4
