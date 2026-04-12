from __future__ import annotations

import json

from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson


def test_client_store_assigns_stable_ids(tmp_path):
    store = ClientStoreJson(path=tmp_path / "clients.json")
    result = store.save_new(ClientDef(name="Klient A"))
    assert result.ok is True

    loaded = store.get("Klient A")
    assert loaded is not None
    assert loaded.id.startswith("cli_")
    assert loaded.client_id
    assert loaded.created_at
    assert loaded.updated_at


def test_client_store_migrates_legacy_records(tmp_path):
    path = tmp_path / "clients.json"
    path.write_text(json.dumps({"Legacy": {"name": "Legacy"}}, ensure_ascii=False, indent=2), encoding="utf-8")
    store = ClientStoreJson(path=path)
    loaded = store.get("Legacy")
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert loaded is not None
    assert loaded.id.startswith("cli_")
    assert raw["Legacy"]["id"].startswith("cli_")
    assert raw["Legacy"]["client_id"] == raw["Legacy"]["id"]


def test_client_store_overwrite_keeps_id_and_created_at(tmp_path, monkeypatch):
    store = ClientStoreJson(path=tmp_path / "clients.json")
    store.save_new(ClientDef(name="Klient B"))
    first = store.get("Klient B")
    assert first is not None

    monkeypatch.setattr(store, "_now_iso", lambda: "2099-01-01T00:00:00Z")
    overwrite_result = store.overwrite(ClientDef(name="Klient B", city="Gdansk"))
    second = store.get("Klient B")

    assert overwrite_result.ok is True
    assert second is not None
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.updated_at == "2099-01-01T00:00:00Z"


def test_order_store_assigns_stable_ids_and_rejects_duplicate(tmp_path):
    store = OrderStoreJson(path=tmp_path / "orders.json")
    first = store.save_new(OrderDef(code="ORD-1", client_name="A"))
    second = store.save_new(OrderDef(code="ORD-1", client_name="B"))
    loaded = store.get("ORD-1")

    assert first.ok is True
    assert second.ok is False
    assert loaded is not None
    assert loaded.id.startswith("ord_")
    assert loaded.order_id


def test_order_store_migrates_legacy_records(tmp_path):
    path = tmp_path / "orders.json"
    path.write_text(json.dumps({"ORD-L": {"code": "ORD-L"}}, ensure_ascii=False, indent=2), encoding="utf-8")
    store = OrderStoreJson(path=path)
    loaded = store.get("ORD-L")
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert loaded is not None
    assert loaded.id.startswith("ord_")
    assert raw["ORD-L"]["id"].startswith("ord_")
    assert raw["ORD-L"]["order_id"] == raw["ORD-L"]["id"]


def test_order_store_overwrite_keeps_id_and_updates_updated_at(tmp_path, monkeypatch):
    store = OrderStoreJson(path=tmp_path / "orders.json")
    store.save_new(OrderDef(code="ORD-2"))
    first = store.get("ORD-2")
    assert first is not None

    monkeypatch.setattr(store, "_now_iso", lambda: "2099-02-02T00:00:00Z")
    store.overwrite(OrderDef(code="ORD-2", status="Wycena"))
    second = store.get("ORD-2")
    assert second is not None
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.updated_at == "2099-02-02T00:00:00Z"


def test_worker_store_assigns_stable_ids(tmp_path):
    store = WorkerStoreJson(path=tmp_path / "workers.json")
    result = store.save_new(WorkerDef(name="Pracownik A"))
    assert result.ok is True
    loaded = store.get("Pracownik A")
    assert loaded is not None
    assert loaded.id.startswith("emp_")
    assert loaded.worker_id
    assert loaded.created_at
    assert loaded.updated_at


def test_worker_store_migrates_legacy_records_and_get_by_id(tmp_path):
    path = tmp_path / "workers.json"
    path.write_text(json.dumps({"Legacy W": {"name": "Legacy W"}}, ensure_ascii=False, indent=2), encoding="utf-8")
    store = WorkerStoreJson(path=path)
    loaded = store.get("Legacy W")
    assert loaded is not None
    assert loaded.id.startswith("emp_")
    found = store.get_by_id(loaded.id)
    assert found is not None
    assert found.name == "Legacy W"


def test_worker_store_overwrite_keeps_existing_business_worker_id(tmp_path, monkeypatch):
    store = WorkerStoreJson(path=tmp_path / "workers.json")
    store.save_new(WorkerDef(name="Pracownik B", worker_id="P0001"))
    first = store.get("Pracownik B")
    assert first is not None
    first_id = first.id
    first_created = first.created_at

    monkeypatch.setattr(store, "_now_iso", lambda: "2099-03-03T00:00:00Z")
    store.overwrite(WorkerDef(name="Pracownik B", worker_id="P0001", role="produkcja"))
    second = store.get("Pracownik B")
    assert second is not None
    assert second.id == first_id
    assert second.worker_id == "P0001"
    assert second.created_at == first_created
    assert second.updated_at == "2099-03-03T00:00:00Z"

