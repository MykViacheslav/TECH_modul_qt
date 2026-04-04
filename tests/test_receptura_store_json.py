from __future__ import annotations

from src.storage.receptura_store_json import RecepturaStoreJson


def test_receptura_store_assigns_incremental_ids(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = RecepturaStoreJson()

    is_new_1, row_1 = store.upsert(
        {
            "name": "Plyta 18 biala",
            "material_type": "plyta",
            "unit": "m2",
            "quantity": 2.5,
            "price_net": 45.0,
            "vat_percent": 23.0,
        }
    )
    is_new_2, row_2 = store.upsert(
        {
            "name": "Obrzeze ABS",
            "material_type": "okleina",
            "unit": "mb",
            "quantity": 12.0,
            "price_net": 2.5,
            "vat_percent": 23.0,
        }
    )

    assert is_new_1 is True
    assert is_new_2 is True
    assert row_1["id"] == "R0001"
    assert row_2["id"] == "R0002"
    assert store.next_id() == "R0003"


def test_receptura_store_overwrite_keeps_id_and_updates_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = RecepturaStoreJson()

    _, row = store.upsert(
        {
            "name": "Front lakier",
            "material_type": "front",
            "unit": "szt",
            "quantity": 1.0,
            "price_net": 120.0,
            "vat_percent": 23.0,
        }
    )
    row_id = str(row.get("id", "") or "")

    is_new, updated = store.upsert(
        {
            "id": row_id,
            "name": "Front lakier premium",
            "material_type": "front",
            "unit": "szt",
            "quantity": 2.0,
            "price_net": 150.0,
            "vat_percent": 8.0,
            "for_quote": True,
            "for_module": False,
        }
    )

    assert is_new is False
    assert updated["id"] == row_id
    assert updated["name"] == "Front lakier premium"
    assert abs(float(updated["price_gross"]) - 162.0) < 0.01
    loaded = store.get(row_id)
    assert loaded is not None
    assert loaded["for_module"] is False


def test_receptura_store_filters_rows_for_quote_and_module(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = RecepturaStoreJson()

    store.upsert(
        {
            "name": "Pozycja Q",
            "material_type": "plyta",
            "unit": "szt",
            "quantity": 1,
            "price_net": 10,
            "vat_percent": 23,
            "for_quote": True,
            "for_module": False,
        }
    )
    store.upsert(
        {
            "name": "Pozycja M",
            "material_type": "okucie",
            "unit": "szt",
            "quantity": 1,
            "price_net": 10,
            "vat_percent": 23,
            "for_quote": False,
            "for_module": True,
        }
    )

    quote_names = [str(x.get("name", "")) for x in store.list_for_quote()]
    module_names = [str(x.get("name", "")) for x in store.list_for_module()]

    assert quote_names == ["Pozycja Q"]
    assert module_names == ["Pozycja M"]
