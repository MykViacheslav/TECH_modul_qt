from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson


def test_client_store_json_roundtrip(tmp_path):
    store = ClientStoreJson(path=tmp_path / "clients.json")

    result = store.save_new(
        ClientDef(
            name="Klient Test",
            phone="123456789",
            email="test@example.com",
            city="Krakow",
            notes="Staly klient",
        )
    )
    assert result.ok

    loaded = store.get("Klient Test")
    assert loaded is not None
    assert loaded.phone == "123456789"
    assert loaded.email == "test@example.com"
    assert loaded.city == "Krakow"


def test_order_store_json_roundtrip(tmp_path):
    store = OrderStoreJson(path=tmp_path / "orders.json")

    result = store.save_new(
        OrderDef(
            code="ORD-100",
            client_name="Klient Test",
            worker_name="Monter 1",
            status="Wycena",
            site_address="Warszawa, ul. Prosta 10",
            notes="Kuchnia L",
        )
    )
    assert result.ok

    loaded = store.get("ORD-100")
    assert loaded is not None
    assert loaded.client_name == "Klient Test"
    assert loaded.worker_name == "Monter 1"
    assert loaded.status == "Wycena"
    assert loaded.site_address == "Warszawa, ul. Prosta 10"


def test_worker_store_json_roundtrip(tmp_path):
    store = WorkerStoreJson(path=tmp_path / "workers.json")

    result = store.save_new(
        WorkerDef(
            name="Jan Monter",
            role="Pomiar / montaz",
            phone="600700800",
            email="jan@example.com",
            notes="Region poludnie",
        )
    )
    assert result.ok

    loaded = store.get("Jan Monter")
    assert loaded is not None
    assert loaded.role == "Pomiar / montaz"
    assert loaded.phone == "600700800"
    assert loaded.email == "jan@example.com"
