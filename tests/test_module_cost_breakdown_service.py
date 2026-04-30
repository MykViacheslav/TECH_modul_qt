import json


def test_module_cost_breakdown_service_counts_materials_edgeband_and_hardware(tmp_path):
    from src.core.costing.module_costs import calculate_module_cost_breakdown
    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson

    catalog_payload = {
        "materials": [
            {"key": "PB18", "name_pl": "Plyta test", "thickness_mm": 18.0, "price_pln_per_m2": 100.0},
        ],
        "edgebands": [
            {"key": "Brak", "name_pl": "Brak", "price_pln_per_m": 0.0},
            {"key": "ABS 0.8", "name_pl": "ABS 0,8", "price_pln_per_m": 5.0},
        ],
        "hardware": [
            {"key": "shelf_support_generic", "name_pl": "Polkotrzymacz", "manufacturer": "generic", "category": "shelf_support", "unit": "szt", "price_pln": 1.0},
        ],
    }

    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog = CatalogStoreJson(path)

    module = ModuleDef(
        cabinet_kind="upper",
        shelf_count=1,
        visible_parts={"shelf"},
        parts={
            "shelf_1": PartDef(
                id="shelf_1",
                name_pl="Polka 1",
                material_key="PB18",
                dims_mm={"w": 500.0, "h": 700.0, "t": 18.0},
                edge_banding={"top": "ABS 0.8"},
            ),
        },
    )

    breakdown = calculate_module_cost_breakdown(module, catalog)

    assert breakdown.material_total_pln == 35.0
    assert breakdown.edgeband_total_pln == 2.5
    # shelf supports: 1 shelf * 4 = 4 szt * 1.0 = 4.0
    # wall hangers (added because "upper"): 2 szt * 0.0 = 0.0
    assert breakdown.hardware_total_pln == 4.0
    assert breakdown.grand_total_pln == 41.5


def test_module_cost_breakdown_service_uses_catalog_hardware_vendor(tmp_path):
    from src.core.costing.module_costs import calculate_module_cost_breakdown
    from src.domain.module_models import ModuleDef, PartDef
    from src.storage.catalog_store_json import CatalogStoreJson

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    module = ModuleDef(
        width_mm=900.0,
        height_mm=900.0,
        facade_mode="doors",
        hinge_vendor="blum",
        visible_parts={"front"},
        parts={
            "front": PartDef(
                id="front",
                name_pl="Front",
                material_key="MDF19",
                dims_mm={"w": 900.0, "h": 900.0, "t": 19.0},
            ),
        },
    )

    breakdown = calculate_module_cost_breakdown(module, catalog, auto_double_front_width_mm=600.0)

    assert breakdown.hardware_total_pln > 0.0
    assert any("Blum" in line.label for line in breakdown.hardware_lines)
