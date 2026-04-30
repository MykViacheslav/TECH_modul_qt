import json

from PyQt6.QtWidgets import QApplication


def test_bom_block_shows_hardware_costs(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import BomBlock

    custom_catalog = {
        "materials": [
            {"key": "PB18", "name_pl": "Plyta", "thickness_mm": 18.0, "price_pln_per_m2": 0.0},
            {"key": "MDF19", "name_pl": "MDF", "thickness_mm": 19.0, "price_pln_per_m2": 0.0},
        ],
        "edgebands": [
            {"key": "Brak", "name_pl": "Brak", "price_pln_per_m": 0.0},
        ],
        "hardware": [
            {"key": "hinge_blum", "name_pl": "Zawias Blum", "manufacturer": "blum", "category": "hinge", "unit": "szt", "price_pln": 10.0},
            {"key": "shelf_support_generic", "name_pl": "Polkotrzymacz", "manufacturer": "generic", "category": "shelf_support", "unit": "szt", "price_pln": 1.0},
            {"key": "divider_connector_generic", "name_pl": "Lacznik pionu", "manufacturer": "generic", "category": "divider_connector", "unit": "szt", "price_pln": 2.0},
            {"key": "wall_hanger_generic", "name_pl": "Zawieszka", "manufacturer": "generic", "category": "wall_hanger", "unit": "szt", "price_pln": 12.0},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog = CatalogStoreJson(path)
    bom = BomBlock(catalog)

    module = ModuleDef(
        width_mm=500.0,
        height_mm=700.0,
        cabinet_kind="upper",
        facade_mode="doors",
        hinge_vendor="blum",
        shelf_count=1,
        divider_count=1,
        visible_parts={"front", "shelf", "divider"},
        parts={
            "front": PartDef(id="front", name_pl="Front", material_key="MDF19", dims_mm={"w": 500.0, "h": 700.0, "t": 19.0}),
            "shelf_1": PartDef(id="shelf_1", name_pl="Polka 1", material_key="PB18", dims_mm={"w": 464.0, "h": 500.0, "t": 18.0}),
            "divider_1": PartDef(id="divider_1", name_pl="Pion 1", material_key="PB18", dims_mm={"w": 464.0, "h": 500.0, "t": 18.0}),
        },
    )

    bom.set_module(module)

    assert "Zawias Blum [blum]: 2 szt, 20.00 zl" in bom.v_hw.text()
    assert "Polkotrzymacz [generic]: 4 szt, 4.00 zl" in bom.v_hw.text()
    assert "Lacznik pionu [generic]: 4 szt, 8.00 zl" in bom.v_hw.text()
    assert "Zawieszka [generic]: 2 szt, 24.00 zl" in bom.v_hw.text()
    assert "RAZEM: 56.00 zl" in bom.v_hw.text()
    assert "Okucia: 56.00 zl" in bom.v_total.text()


def test_front_hardware_block_reads_vendors_from_catalog(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import FrontHardwareBlock

    custom_catalog = {
        "materials": [],
        "edgebands": [],
        "hardware": [
            {"key": "hinge_generic", "name_pl": "Zawias", "manufacturer": "generic", "category": "hinge", "unit": "szt", "price_pln": 3.0},
            {"key": "hinge_hafele", "name_pl": "Zawias Hafele", "manufacturer": "hafele", "category": "hinge", "unit": "szt", "price_pln": 7.0},
            {"key": "drawer_system_grass", "name_pl": "Szuflada Grass", "manufacturer": "grass", "category": "drawer_system", "unit": "kpl", "price_pln": 50.0},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    block = FrontHardwareBlock(CatalogStoreJson(path))

    hinge_vendors = {str(block.cb_hinge_vendor.itemData(i) or "") for i in range(block.cb_hinge_vendor.count())}
    drawer_vendors = {str(block.cb_drawer_vendor.itemData(i) or "") for i in range(block.cb_drawer_vendor.count())}

    assert {"generic", "hafele"} <= hinge_vendors
    assert {"generic", "grass"} <= drawer_vendors


def test_bom_block_shows_module_type_hardware_costs(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import BomBlock

    custom_catalog = {
        "materials": [],
        "edgebands": [],
        "hardware": [
            {"key": "cabinet_leg_generic", "name_pl": "Nozka meblowa", "manufacturer": "generic", "category": "cabinet_leg", "unit": "szt", "price_pln": 8.0},
            {"key": "plinth_clip_generic", "name_pl": "Klips cokolu", "manufacturer": "generic", "category": "plinth_clip", "unit": "szt", "price_pln": 1.5},
            {"key": "corner_connector_generic", "name_pl": "Lacznik szafki naroznej", "manufacturer": "generic", "category": "corner_connector", "unit": "kpl", "price_pln": 18.0},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(custom_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog = CatalogStoreJson(path)
    bom = BomBlock(catalog)

    module = ModuleDef(
        width_mm=1000.0,
        height_mm=720.0,
        module_type="corner",
        cabinet_kind="lower",
        visible_parts={"side_left", "side_right", "top", "bottom"},
    )

    bom.set_module(module)

    assert "Nozka meblowa [generic]: 6 szt, 48.00 zl" in bom.v_hw.text()
    assert "Klips cokolu [generic]: 2 szt, 3.00 zl" in bom.v_hw.text()
    assert "Lacznik szafki naroznej [generic]: 1 kpl, 18.00 zl" in bom.v_hw.text()
    assert "RAZEM: 69.00 zl" in bom.v_hw.text()

    module.module_type = "legs_plinth"
    bom.set_module(module)

    assert "Nozka meblowa [generic]: 6 szt, 48.00 zl" in bom.v_hw.text()
    assert "Klips cokolu [generic]: 2 szt, 3.00 zl" in bom.v_hw.text()
    assert "RAZEM: 51.00 zl" in bom.v_hw.text()
