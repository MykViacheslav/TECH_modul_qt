import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication


def test_catalog_store_exposes_pricing_fields(tmp_path):
    from src.storage.catalog_store_json import CatalogStoreJson

    catalog = CatalogStoreJson(tmp_path / "catalog.json")

    pb18 = catalog.get_material("PB18")
    assert pb18 is not None
    assert float(pb18.price_pln_per_m2) > 0.0
    assert pb18.material_group == "carcass_board"

    abs08 = catalog.get_edgeband("ABS 0.8")
    assert abs08 is not None
    assert float(abs08.price_pln_per_m) > 0.0
    assert float(abs08.thickness_mm) == 0.8

    mdf_lak = catalog.get_material("MDF19_LAK")
    assert mdf_lak is not None
    assert mdf_lak.finish_group == "lacquer"
    assert mdf_lak.manufacturer

    hinge = catalog.find_hardware("hinge", "blum")
    assert hinge is not None
    assert hinge.category == "hinge"
    assert hinge.manufacturer == "blum"
    assert float(hinge.price_pln) > 0.0


def test_materials_block_labels_show_price_per_m2(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import MaterialsBlock

    custom_catalog = {
        "materials": [
            {"key": "PB18", "name_pl": "Plyta test", "thickness_mm": 18.0, "price_pln_per_m2": 99.0},
            {"key": "MDF19", "name_pl": "MDF test", "thickness_mm": 19.0, "price_pln_per_m2": 155.5},
            {"key": "HDF3", "name_pl": "HDF test", "thickness_mm": 3.0, "price_pln_per_m2": 21.0},
        ],
        "edgebands": [
            {"key": "Brak", "name_pl": "Brak"},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog = CatalogStoreJson(path)
    block = MaterialsBlock(catalog)

    idx = block.cb_carcass.findData("PB18")
    assert idx >= 0
    assert "99.00 zl/m2" in block.cb_carcass.itemText(idx)


def test_bom_block_shows_material_costs(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import BomBlock

    custom_catalog = {
        "materials": [
            {"key": "PB18", "name_pl": "Plyta test", "thickness_mm": 18.0, "price_pln_per_m2": 100.0},
            {"key": "MDF19", "name_pl": "MDF test", "thickness_mm": 19.0, "price_pln_per_m2": 200.0},
        ],
        "edgebands": [
            {"key": "Brak", "name_pl": "Brak", "price_pln_per_m": 0.0},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog = CatalogStoreJson(path)
    bom = BomBlock(catalog)

    module = ModuleDef(
        parts={
            "side_left": PartDef(
                id="side_left",
                name_pl="Bok lewy",
                material_key="PB18",
                dims_mm={"w": 500.0, "h": 700.0, "t": 18.0},
                edge_banding={},
            ),
            "front": PartDef(
                id="front",
                name_pl="Front",
                material_key="MDF19",
                dims_mm={"w": 500.0, "h": 700.0, "t": 19.0},
                edge_banding={},
            ),
        }
    )

    bom.set_module(module)

    txt = bom.v_sum.text()
    assert "35.00 zl" in txt
    assert "70.00 zl" in txt
    assert "RAZEM: 105.00 zl" in txt
