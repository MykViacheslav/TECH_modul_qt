from __future__ import annotations

import asyncio
from pathlib import Path

from src.api import main_api
from src.domain.module_models import ModuleDef
from src.domain.operations.adapters.module_repository import JsonModuleRepository
from src.domain.operations.module_ops import ModuleOperations
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson


def _configure_test_operations(tmp_path: Path) -> tuple[ModuleStoreJson, str]:
    modules_path = tmp_path / "modules.json"
    catalog_path = tmp_path / "catalog.json"

    store = ModuleStoreJson(path=modules_path)
    catalog = CatalogStoreJson(path=catalog_path)
    repo = JsonModuleRepository(store=store)

    module = ModuleDef(module_id="MOD-ENDPOINT-1", name="M_ENDPOINT", depth_mm=500.0)
    assert store.save_new(module).ok
    saved = store.get("M_ENDPOINT")
    assert saved is not None

    main_api.module_operations = ModuleOperations(repository=repo, catalog=catalog)
    return store, str(saved.module_id)


def test_preview_and_apply_module_operation_endpoint(tmp_path: Path) -> None:
    store, module_id = _configure_test_operations(tmp_path)

    preview_payload = asyncio.run(
        main_api.preview_module_operation(
            main_api.ModuleOperationRequest(
                action="module.set_depth",
                target=main_api.OperationTargetPayload(id=module_id),
                params={"depth_mm": 650},
                source="pytest",
            )
        )
    )
    assert preview_payload["status"] == "ok"
    assert preview_payload["can_apply"] is True

    still_before = store.get_by_id(module_id)
    assert still_before is not None
    assert float(still_before.depth_mm) == 500.0

    apply_payload = asyncio.run(
        main_api.apply_module_operation(
            main_api.ModuleOperationRequest(
                action="module.set_depth",
                target=main_api.OperationTargetPayload(id=module_id),
                params={"depth_mm": 650},
                source="pytest",
            )
        )
    )
    assert apply_payload["status"] == "ok"
    assert apply_payload["can_apply"] is False

    after = store.get_by_id(module_id)
    assert after is not None
    assert float(after.depth_mm) == 650.0
