import json

from PyQt6.QtWidgets import QApplication


def test_bom_block_total_cost_includes_materials_and_edgeband(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import BomBlock

    custom_catalog = {
        "materials": [
            {"key": "PB18", "name_pl": "Plyta test", "thickness_mm": 18.0, "price_pln_per_m2": 100.0},
        ],
        "edgebands": [
            {"key": "Brak", "name_pl": "Brak", "price_pln_per_m": 0.0},
            {"key": "ABS 0.8", "name_pl": "ABS 0,8", "price_pln_per_m": 5.0},
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
                edge_banding={"left": "ABS 0.8"},
            ),
        }
    )

    bom.set_module(module)

    txt = bom.v_total.text()
    assert "Materialy: 35.00 zl" in txt
    assert "Okleina: 3.50 zl" in txt
    assert "RAZEM: 38.50 zl" in txt


def test_bom_block_total_cost_handles_lacquered_material_price(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import BomBlock

    custom_catalog = {
        "materials": [
            {"key": "MDF19", "name_pl": "MDF", "thickness_mm": 19.0, "price_pln_per_m2": 100.0},
            {"key": "MDF19_LAK", "name_pl": "MDF lakierowany", "thickness_mm": 19.0, "price_pln_per_m2": 220.0},
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
            "front": PartDef(
                id="front",
                name_pl="Front",
                material_key="MDF19_LAK",
                dims_mm={"w": 500.0, "h": 700.0, "t": 19.0},
                edge_banding={},
            ),
        }
    )

    bom.set_module(module)

    txt = bom.v_total.text()
    assert "Materialy: 77.00 zl" in txt
    assert "Okleina: 0.00 zl" in txt
    assert "RAZEM: 77.00 zl" in txt
