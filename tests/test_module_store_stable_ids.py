from __future__ import annotations

import json

from src.core.stable_record_id import ensure_module_record_id, new_record_id
from src.domain.module_models import ModuleDef
from src.storage.module_store_json import ModuleStoreJson


def test_generate_module_id():
    first = new_record_id("mod")
    second = new_record_id("mod")
    assert first.startswith("mod_")
    assert second.startswith("mod_")
    assert first != second


def test_ensure_module_id_for_legacy_record():
    legacy = {"name": "LEGACY_MOD"}
    migrated = ensure_module_record_id(legacy)
    assert migrated["id"].startswith("mod_")
    assert migrated["module_id"] == migrated["id"]


def test_save_new_module_rejects_duplicate_name(tmp_path):
    store = ModuleStoreJson(path=tmp_path / "modules.json")
    first = ModuleDef(name="DUPLICATE_TEST", width_mm=800.0)
    second = ModuleDef(name="DUPLICATE_TEST", width_mm=900.0)

    first_result = store.save_new(first)
    second_result = store.save_new(second)
    loaded = store.get("DUPLICATE_TEST")

    assert first_result.ok is True
    assert second_result.ok is False
    assert loaded is not None
    assert loaded.width_mm == 800.0


def test_overwrite_module_keeps_same_id(tmp_path):
    store = ModuleStoreJson(path=tmp_path / "modules.json")
    original = ModuleDef(name="OVERWRITE_ID_TEST", width_mm=810.0)
    store.save_new(original)

    before = store.get("OVERWRITE_ID_TEST")
    assert before is not None
    before_id = str(before.module_id or "")

    changed = ModuleDef(name="OVERWRITE_ID_TEST", width_mm=930.0)
    overwrite_result = store.overwrite(changed)
    after = store.get("OVERWRITE_ID_TEST")

    assert overwrite_result.ok is True
    assert after is not None
    assert after.width_mm == 930.0
    assert str(after.module_id or "") == before_id
    assert before_id.startswith("mod_")


def test_delete_module_removes_record(tmp_path):
    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="DELETE_ID_TEST"))

    delete_result = store.delete("DELETE_ID_TEST")

    assert delete_result.ok is True
    assert store.get("DELETE_ID_TEST") is None


def test_legacy_modules_json_still_loads(tmp_path):
    path = tmp_path / "modules.json"
    path.write_text(
        json.dumps(
            {
                "LEGACY_JSON_TEST": {
                    "name": "LEGACY_JSON_TEST",
                    "width_mm": 700.0,
                    "depth_mm": 500.0,
                    "height_mm": 700.0,
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    store = ModuleStoreJson(path=path)
    loaded = store.get("LEGACY_JSON_TEST")
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert loaded is not None
    assert loaded.name == "LEGACY_JSON_TEST"
    assert str(loaded.module_id or "").startswith("mod_")
    assert raw["LEGACY_JSON_TEST"]["id"].startswith("mod_")
    assert raw["LEGACY_JSON_TEST"]["module_id"] == raw["LEGACY_JSON_TEST"]["id"]

