from __future__ import annotations

import asyncio
from pathlib import Path

from src.api import main_api
from src.domain.module_models import ModuleDef
from src.domain.operations.adapters.module_repository import JsonModuleRepository
from src.domain.operations.module_ops import ModuleOperations
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson


def _configure_test_operations(tmp_path: Path) -> tuple[ModuleStoreJson, list[str]]:
    modules_path = tmp_path / "modules.json"
    catalog_path = tmp_path / "catalog.json"

    store = ModuleStoreJson(path=modules_path)
    catalog = CatalogStoreJson(path=catalog_path)
    repo = JsonModuleRepository(store=store)

    assert store.save_new(ModuleDef(module_id="M1", name="BULK_1", depth_mm=500.0)).ok
    assert store.save_new(ModuleDef(module_id="M2", name="BULK_2", depth_mm=520.0)).ok
    one = store.get("BULK_1")
    two = store.get("BULK_2")
    assert one is not None and two is not None

    main_api.module_operations = ModuleOperations(repository=repo, catalog=catalog)
    return store, [str(one.module_id), str(two.module_id)]


def test_bulk_preview_and_apply_module_operation_endpoint(tmp_path: Path) -> None:
    store, module_ids = _configure_test_operations(tmp_path)

    preview_payload = asyncio.run(
        main_api.preview_bulk_module_operation(
            main_api.ModuleBulkOperationRequest(
                action="module.set_depth",
                module_ids=module_ids,
                params={"depth_mm": 650},
                source="pytest",
            )
        )
    )
    assert preview_payload["status"] == "ok"
    assert preview_payload["can_apply"] is True
    assert len(preview_payload["changes"]) == 2

    before_one = store.get_by_id(module_ids[0])
    before_two = store.get_by_id(module_ids[1])
    assert before_one is not None and before_two is not None
    assert float(before_one.depth_mm) == 500.0
    assert float(before_two.depth_mm) == 520.0

    apply_payload = asyncio.run(
        main_api.apply_bulk_module_operation(
            main_api.ModuleBulkOperationRequest(
                action="module.set_depth",
                module_ids=module_ids,
                params={"depth_mm": 650},
                source="pytest",
            )
        )
    )
    assert apply_payload["status"] == "ok"
    assert int(apply_payload["applied_count"]) == 2

    after_one = store.get_by_id(module_ids[0])
    after_two = store.get_by_id(module_ids[1])
    assert after_one is not None and after_two is not None
    assert float(after_one.depth_mm) == 650.0
    assert float(after_two.depth_mm) == 650.0

