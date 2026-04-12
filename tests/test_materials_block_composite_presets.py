from PyQt6.QtWidgets import QApplication


def test_materials_block_shows_composite_total_thickness_in_labels(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.materials_block import MaterialsBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "FRONT_COMP",
                "name_pl": "Front kompozyt",
                "core": {"code": "mdf19", "name_pl": "MDF 19", "thickness_mm": 19.0},
                "skins_left": [{"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6}],
                "skins_right": [{"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6}],
            }
        ]
    )

    block = MaterialsBlock(catalog)
    idx = block.cb_front.findData("FRONT_COMP")
    assert idx >= 0
    label = str(block.cb_front.itemText(idx) or "")
    assert "(20.2 mm)" in label


def test_materials_block_keeps_material_selection_after_catalog_reload(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.materials_block import MaterialsBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    block = MaterialsBlock(catalog)
    block.set_materials({"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"})

    catalog.replace_catalog(
        materials=[
            {
                "key": "PB18",
                "name_pl": "Korpus kompozyt",
                "core": {"code": "pb18", "name_pl": "Plyta 18", "thickness_mm": 18.0},
                "skins_left": [{"code": "hpl_08", "name_pl": "HPL 0.8", "thickness_mm": 0.8}],
                "skins_right": [{"code": "hpl_08", "name_pl": "HPL 0.8", "thickness_mm": 0.8}],
            },
            {"key": "MDF19", "name_pl": "MDF", "thickness_mm": 19.0},
            {"key": "HDF2.5", "name_pl": "HDF", "thickness_mm": 2.5},
        ]
    )

    block.reload_catalog()
    selected = block.get_materials()
    assert selected["carcass"] == "PB18"
    assert selected["front"] == "MDF19"
    assert selected["back"] == "HDF2.5"

