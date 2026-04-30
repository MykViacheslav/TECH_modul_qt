from src.core.module_parts_service import build_module_parts
from src.domain.module_models import ModuleDef
from src.storage.catalog_store_json import CatalogStoreJson


def test_material_plain_legacy_still_loads(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "PLAIN18",
                "name_pl": "Material legacy",
                "thickness_mm": 18.0,
            }
        ]
    )

    material = catalog.get_material("PLAIN18")
    assert material is not None
    assert material.core is None
    assert material.skins_left == []
    assert material.skins_right == []
    assert abs(catalog.material_thickness("PLAIN18", 0.0) - 18.0) < 0.001


def test_material_core_only_computes_total_thickness(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "CORE_ONLY",
                "name_pl": "Core only",
                "core": {"code": "pb18", "name_pl": "Plyta 18", "thickness_mm": 18.0},
                "skins_left": [],
                "skins_right": [],
            }
        ]
    )

    assert abs(catalog.material_thickness("CORE_ONLY", 0.0) - 18.0) < 0.001


def test_material_composite_one_sided_computes_total_thickness(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "ONE_SIDE",
                "name_pl": "One side veneer",
                "core": {"code": "pb18", "name_pl": "Plyta 18", "thickness_mm": 18.0},
                "skins_left": [{"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6}],
                "skins_right": [],
            }
        ]
    )

    assert abs(catalog.material_thickness("ONE_SIDE", 0.0) - 18.6) < 0.001


def test_material_composite_two_sided_computes_total_thickness(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "TWO_SIDE_MULTI",
                "name_pl": "Two side multi",
                "core": {"code": "mdf19", "name_pl": "MDF 19", "thickness_mm": 19.0},
                "skins_left": [
                    {"code": "primer_02", "name_pl": "Podklad 0.2", "thickness_mm": 0.2},
                    {"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6},
                ],
                "skins_right": [
                    {"code": "primer_02", "name_pl": "Podklad 0.2", "thickness_mm": 0.2},
                    {"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6},
                ],
            }
        ]
    )

    assert abs(catalog.material_thickness("TWO_SIDE_MULTI", 0.0) - 20.6) < 0.001


def test_material_store_preserves_composite_structure(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    source_row = {
        "key": "STORE_SHAPE",
        "name_pl": "Store shape",
        "core": {"code": "pb18", "name_pl": "Plyta 18", "thickness_mm": 18.0},
        "skins_left": [{"code": "hpl_08", "name_pl": "HPL 0.8", "thickness_mm": 0.8}],
        "skins_right": [{"code": "hpl_08", "name_pl": "HPL 0.8", "thickness_mm": 0.8}],
    }
    catalog.replace_catalog(materials=[source_row])

    exported = catalog.export_catalog()
    row = next(item for item in exported["materials"] if item["key"] == "STORE_SHAPE")
    assert isinstance(row.get("core"), dict)
    assert isinstance(row.get("skins_left"), list)
    assert isinstance(row.get("skins_right"), list)
    assert row["core"]["code"] == "pb18"
    assert len(row["skins_left"]) == 1
    assert len(row["skins_right"]) == 1
    assert abs(float(row.get("thickness_mm", 0.0)) - 19.6) < 0.001


def test_material_legacy_composite_fields_are_accepted(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "LEGACY_COMP",
                "name_pl": "Legacy composite",
                "thickness_mm": 18.0,
                "composite_enabled": 1,
                "core_material_key": "pb18",
                "core_thickness_mm": 17.2,
                "left_facing_key": "veneer_06",
                "left_facing_thickness_mm": 0.6,
                "right_facing_key": "veneer_06",
                "right_facing_thickness_mm": 0.6,
            }
        ]
    )

    material = catalog.get_material("LEGACY_COMP")
    assert material is not None
    assert material.composite_enabled is True
    assert abs(catalog.material_thickness("LEGACY_COMP", 0.0) - 18.4) < 0.001


def test_module_uses_material_thickness_from_composite_material(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    catalog.replace_catalog(
        materials=[
            {
                "key": "CARCASS_COMP",
                "name_pl": "Carcass composite",
                "core": {"code": "pb18", "name_pl": "Plyta 18", "thickness_mm": 18.0},
                "skins_left": [{"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6}],
                "skins_right": [{"code": "veneer_06", "name_pl": "Fornir 0.6", "thickness_mm": 0.6}],
            },
            {"key": "MDF19", "name_pl": "Front", "thickness_mm": 19.0},
            {"key": "HDF2.5", "name_pl": "Plecy", "thickness_mm": 2.5},
        ]
    )

    module = ModuleDef(
        name="COMP-MODULE",
        width_mm=900.0,
        depth_mm=560.0,
        height_mm=2200.0,
        materials={"carcass": "CARCASS_COMP", "front": "MDF19", "back": "HDF2.5"},
        visible_parts={"side_left", "side_right", "top", "bottom"},
    )
    parts = build_module_parts(module, catalog)

    assert abs(float(parts["side_left"].dims_mm["t"]) - 19.2) < 0.001
    assert abs(float(parts["top"].dims_mm["t"]) - 19.2) < 0.001


def test_default_catalog_contains_example_composite_seed_materials(tmp_path):
    catalog = CatalogStoreJson(tmp_path / "catalog.json")

    exported = catalog.export_catalog()
    materials = list(exported.get("materials", []) or [])
    material_map = {str(row.get("key", "") or ""): row for row in materials}

    for key in ("PB18_FORNIR_2S", "PB18_FORNIR_1S"):
        assert key in material_map, f"Missing seed composite material: {key}"

    two_sided = material_map["PB18_FORNIR_2S"]
    one_sided = material_map["PB18_FORNIR_1S"]

    assert isinstance(two_sided.get("core"), dict)
    assert isinstance(two_sided.get("skins_left"), list)
    assert isinstance(two_sided.get("skins_right"), list)
    assert len(two_sided.get("skins_left") or []) >= 1
    assert len(two_sided.get("skins_right") or []) >= 1

    assert isinstance(one_sided.get("core"), dict)
    assert isinstance(one_sided.get("skins_left"), list)
    assert isinstance(one_sided.get("skins_right"), list)
    assert len(one_sided.get("skins_left") or []) >= 1
    assert len(one_sided.get("skins_right") or []) == 0
