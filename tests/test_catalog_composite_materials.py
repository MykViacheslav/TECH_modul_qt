from PyQt6.QtWidgets import QApplication


def test_catalog_store_uses_composite_thickness_sum(tmp_path):
    from src.storage.catalog_store_json import CatalogStoreJson

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "PB18_COMP_1S",
                "name_pl": "Plyta kompozyt 1S",
                "thickness_mm": 18.0,
                "composite_enabled": 1,
                "core_material_key": "PB18",
                "core_thickness_mm": 17.2,
                "left_facing_key": "Fornir 0.6",
                "left_facing_thickness_mm": 0.6,
                "right_facing_key": "",
                "right_facing_thickness_mm": 0.0,
            }
        ]
    )

    assert abs(catalog.material_thickness("PB18_COMP_1S", 18.0) - 17.8) < 0.001

    mat = catalog.get_material("PB18_COMP_1S")
    assert mat is not None
    assert mat.composite_enabled is True
    assert abs(float(mat.core_thickness_mm) - 17.2) < 0.001
    assert abs(float(mat.left_facing_thickness_mm) - 0.6) < 0.001
    assert abs(float(mat.right_facing_thickness_mm) - 0.0) < 0.001


def test_catalog_editor_dialog_saves_composite_fields(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    dlg = CatalogEditorDialog(None, catalog)
    table = dlg.page_materials.table

    def _col(label: str) -> int:
        for idx in range(table.columnCount()):
            header = table.horizontalHeaderItem(idx)
            if header is not None and str(header.text() or "").strip() == label:
                return idx
        raise AssertionError(f"Brak kolumny: {label}")

    row_pb18 = -1
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and str(item.text() or "").strip() == "PB18":
            row_pb18 = row
            break
    assert row_pb18 >= 0

    table.item(row_pb18, _col("Kompozyt (0/1)")).setText("1")
    table.item(row_pb18, _col("Rdzen - klucz")).setText("PB18")
    table.item(row_pb18, _col("Rdzen mm")).setText("17.2")
    table.item(row_pb18, _col("Okladzina L - klucz")).setText("Fornir 0.6")
    table.item(row_pb18, _col("Okladzina L mm")).setText("0.6")
    table.item(row_pb18, _col("Okladzina P - klucz")).setText("Fornir 0.6")
    table.item(row_pb18, _col("Okladzina P mm")).setText("0.6")

    dlg._save_and_accept()

    saved = catalog.get_material("PB18")
    assert saved is not None
    assert saved.composite_enabled is True
    assert abs(float(saved.core_thickness_mm) - 17.2) < 0.001
    assert abs(float(saved.left_facing_thickness_mm) - 0.6) < 0.001
    assert abs(float(saved.right_facing_thickness_mm) - 0.6) < 0.001
    assert abs(catalog.material_thickness("PB18", 18.0) - 18.4) < 0.001
