from src.core.module_parts_service import build_module_parts
from src.domain.module_models import ModuleDef
from src.storage.catalog_store_json import CatalogStoreJson


def test_build_module_parts_creates_shelves_on_both_sides_when_requested(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    m = ModuleDef(
        name="BOTH-SHELVES",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=700.0,
        shelf_count=2,
        divider_count=1,
        shelf_mount="both",
        visible_parts={"side_left", "side_right", "top", "bottom", "divider", "shelf"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )

    parts = build_module_parts(m, CatalogStoreJson())

    assert "shelf_left_1" in parts
    assert "shelf_right_1" in parts
    assert "shelf_left_2" in parts
    assert "shelf_right_2" in parts
