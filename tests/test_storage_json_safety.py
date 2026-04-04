from __future__ import annotations

import json

import pytest

from src.domain.order_models import OrderDef
from src.storage.material_store_json import MaterialStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.safe_json_io import JsonFileCorruptedError, read_json_file


def test_order_store_raises_on_corrupted_json_and_does_not_overwrite(tmp_path):
    path = tmp_path / "orders.json"
    corrupted_text = '{"schema_version": 2, "items": {"ORD-1": '
    path.write_text(corrupted_text, encoding="utf-8")

    store = OrderStoreJson(path=path)
    with pytest.raises(JsonFileCorruptedError):
        store.list_codes()

    assert path.read_text(encoding="utf-8") == corrupted_text
    assert not (tmp_path / "orders.json.bak").exists()


def test_order_store_write_creates_backup(tmp_path):
    path = tmp_path / "orders.json"
    initial_payload = {
        "schema_version": 2,
        "items": {
            "ORD-OLD": {
                "code": "ORD-OLD",
                "client_name": "Klient A",
                "status": "Nowe",
            }
        },
    }
    path.write_text(json.dumps(initial_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    store = OrderStoreJson(path=path)
    result = store.overwrite(OrderDef(code="ORD-OLD", client_name="Klient B", status="Wycena"))
    assert result.ok is True

    backup_path = tmp_path / "orders.json.bak"
    assert backup_path.exists()
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup["items"]["ORD-OLD"]["client_name"] == "Klient A"

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["items"]["ORD-OLD"]["client_name"] == "Klient B"


def test_material_store_write_creates_backup(tmp_path):
    path = tmp_path / "baza_materialu.json"
    path.write_text(json.dumps({"rows": [{"id": "M1"}]}, ensure_ascii=False, indent=2), encoding="utf-8")

    store = MaterialStoreJson(path=path)
    store.save({"rows": [{"id": "M2"}]})

    backup_path = tmp_path / "baza_materialu.json.bak"
    assert backup_path.exists()
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup["rows"][0]["id"] == "M1"

    current = json.loads(path.read_text(encoding="utf-8"))
    assert current["rows"][0]["id"] == "M2"


def test_read_json_file_recovers_from_backup_when_primary_is_corrupted(tmp_path):
    path = tmp_path / "orders.json"
    backup_path = tmp_path / "orders.json.bak"

    path.write_text('{"schema_version": 2, "items": ', encoding="utf-8")
    backup_payload = {"schema_version": 2, "items": {"ORD-1": {"code": "ORD-1"}}}
    backup_path.write_text(json.dumps(backup_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    recovered = read_json_file(path, default={}, expected_type=dict)
    assert isinstance(recovered, dict)
    assert recovered.get("items", {}).get("ORD-1", {}).get("code") == "ORD-1"
