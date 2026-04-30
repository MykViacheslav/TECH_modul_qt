from __future__ import annotations

from pathlib import Path

from src.domain.module_models import ModuleDef
from src.domain.operations.adapters.module_repository import JsonModuleRepository
from src.domain.operations.module_ops import ModuleOperations
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson


def _build_ops(tmp_path: Path) -> tuple[ModuleOperations, ModuleStoreJson]:
    modules_path = tmp_path / "modules.json"
    catalog_path = tmp_path / "catalog.json"
    store = ModuleStoreJson(path=modules_path)
    catalog = CatalogStoreJson(path=catalog_path)
    repo = JsonModuleRepository(store=store)
    return ModuleOperations(repository=repo, catalog=catalog), store


def test_set_depth_preview_does_not_persist(tmp_path: Path) -> None:
    ops, store = _build_ops(tmp_path)
    module = ModuleDef(module_id="MOD-1", name="M1", depth_mm=500.0)
    assert store.save_new(module).ok

    result = ops.set_depth("M1", depth_mm=650, mode="preview", source="test")
    assert result.status == "ok"
    assert result.can_apply is True
    assert result.changes[0].after == 650.0

    loaded = store.get("M1")
    assert loaded is not None
    assert loaded.depth_mm == 500.0


def test_set_depth_apply_persists(tmp_path: Path) -> None:
    ops, store = _build_ops(tmp_path)
    module = ModuleDef(module_id="MOD-2", name="M2", depth_mm=500.0)
    assert store.save_new(module).ok
    loaded = store.get("M2")
    assert loaded is not None

    result = ops.set_depth({"id": loaded.module_id}, depth_mm=640, mode="apply", source="test")
    assert result.status == "ok"
    assert result.can_apply is False

    loaded = store.get_by_id(loaded.module_id)
    assert loaded is not None
    assert loaded.depth_mm == 640.0


def test_set_width_out_of_range_returns_validation_error(tmp_path: Path) -> None:
    ops, store = _build_ops(tmp_path)
    module = ModuleDef(module_id="MOD-3", name="M3", width_mm=800.0)
    assert store.save_new(module).ok

    result = ops.set_width("M3", width_mm=999999, mode="preview", source="test")
    assert result.status == "validation_error"
    assert result.can_apply is False
    assert result.errors
    assert result.errors[0].code == "OUT_OF_RANGE"


def test_change_material_requires_existing_catalog_material(tmp_path: Path) -> None:
    ops, store = _build_ops(tmp_path)
    module = ModuleDef(module_id="MOD-4", name="M4")
    assert store.save_new(module).ok

    result = ops.change_material(
        "M4",
        material_key="UNKNOWN_MATERIAL",
        part_group="carcass",
        mode="preview",
        source="test",
    )

    assert result.status == "validation_error"
    assert result.errors
    assert result.errors[0].code == "UNKNOWN_MATERIAL"
