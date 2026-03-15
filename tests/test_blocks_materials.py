from PyQt6.QtWidgets import QApplication


def test_materials_block_set_get():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import MaterialsBlock
    from src.storage.catalog_store_json import CatalogStoreJson

    cat = CatalogStoreJson()
    m = MaterialsBlock(cat)

    m.set_materials({"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"})
    got = m.get_materials()
    assert got["carcass"] == "PB18"
    assert got["front"] == "MDF19"
    assert got["back"] == "HDF2.5"


def test_materials_block_set_get_group_edgebands():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import MaterialsBlock
    from src.storage.catalog_store_json import CatalogStoreJson

    cat = CatalogStoreJson()
    m = MaterialsBlock(cat)

    m.set_edgebands({"carcass": "ABS 2.0", "front": "ABS 0.8", "back": "Brak"})
    got = m.get_edgebands()
    assert got["carcass"] == "ABS 2.0"
    assert got["front"] == "ABS 0.8"
    assert got["back"] == "Brak"
