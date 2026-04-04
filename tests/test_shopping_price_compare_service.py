import json
from pathlib import Path

from src.services.shopping_price_compare_service import ShoppingPriceCompareService
from src.storage.shopping_list_store_json import ShoppingListStoreJson
from src.storage.supplier_price_store_json import SupplierPriceStoreJson


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_recommendation_prefers_cheapest_brutto(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    _write_json(
        tmp_path / "supplier_prices.json",
        [
            {
                "offer_id": "A1",
                "material_id": "M0002",
                "material_name": "Front lakierowany",
                "supplier": "Hurtownia A",
                "unit": "kg",
                "unit_price": 12.0,
                "price_basis": "brutto",
                "source": "manual",
                "note": "",
                "updated_at": "2026-03-30",
            },
            {
                "offer_id": "B1",
                "material_id": "M0002",
                "material_name": "Front lakierowany",
                "supplier": "Hurtownia B",
                "unit": "kg",
                "unit_price": 10.0,
                "price_basis": "brutto",
                "source": "manual",
                "note": "",
                "updated_at": "2026-03-30",
            },
            {
                "offer_id": "C1",
                "material_id": "M0002",
                "material_name": "Front lakierowany",
                "supplier": "Hurtownia Netto",
                "unit": "kg",
                "unit_price": 7.0,
                "price_basis": "netto",
                "source": "manual",
                "note": "",
                "updated_at": "2026-03-30",
            },
        ],
    )

    _write_json(
        tmp_path / "invoices.json",
        {
            "invoices": [
                {
                    "invoice_id": "INV1",
                    "supplier": "FakturaShop",
                    "invoice_number": "FV/1/03/2026",
                    "invoice_date": "2026-03-29",
                    "price_basis": "brutto",
                    "items": [
                        {
                            "name": "Front lakierowany",
                            "unit": "kg",
                            "unit_price_gross": 11.0,
                        }
                    ],
                }
            ]
        },
    )

    _write_json(
        tmp_path / "baza_materialu.json",
        {
            "rows": [
                {
                    "id": "M0002",
                    "nazwa": "Front lakierowany",
                    "dostawca": "Stary Dostawca",
                    "ostatnia_cena": "13.00",
                    "parametry": "jedn: kg | cena: brutto",
                    "data_zakupu": "2026-03-20",
                }
            ]
        },
    )

    rec = ShoppingPriceCompareService().recommend_for_item(
        material_id="M0002",
        material_name="Front lakierowany",
        quantity=2.0,
        unit="kg",
        preferred_basis="brutto",
        current_unit_price=12.0,
    )

    assert rec is not None
    assert rec.best_offer.supplier == "Hurtownia B"
    assert abs(rec.best_offer.unit_price - 10.0) < 0.0001
    assert rec.compare_basis == "brutto"
    assert rec.warning
    assert rec.best_total == 20.0
    assert rec.potential_saving == 4.0


def test_recommendation_falls_back_to_unknown_when_no_brutto(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    _write_json(
        tmp_path / "supplier_prices.json",
        [
            {
                "offer_id": "U1",
                "material_id": "M1000",
                "material_name": "Wkret 4x40",
                "supplier": "Sklep Unknown",
                "unit": "szt",
                "unit_price": 8.0,
                "price_basis": "unknown",
                "source": "manual",
                "note": "",
                "updated_at": "2026-03-30",
            },
            {
                "offer_id": "N1",
                "material_id": "M1000",
                "material_name": "Wkret 4x40",
                "supplier": "Sklep Netto",
                "unit": "szt",
                "unit_price": 7.0,
                "price_basis": "netto",
                "source": "manual",
                "note": "",
                "updated_at": "2026-03-30",
            },
        ],
    )

    rec = ShoppingPriceCompareService().recommend_for_item(
        material_id="M1000",
        material_name="Wkret 4x40",
        quantity=1.0,
        unit="szt",
        preferred_basis="brutto",
    )

    assert rec is not None
    assert rec.compare_basis == "unknown"
    assert rec.best_offer.supplier == "Sklep Unknown"
    assert "Brak ofert w cenie brutto" in rec.warning


def test_add_shopping_item_autofills_recommendation(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    supplier_store = SupplierPriceStoreJson()
    supplier_store.upsert_row(
        {
            "material_id": "M0099",
            "material_name": "Plyta test",
            "supplier": "MegaHurt",
            "unit": "m2",
            "unit_price": 33.5,
            "price_basis": "brutto",
            "source": "manual",
            "note": "konkurencja",
        }
    )

    store = ShoppingListStoreJson()
    item = store.add_shopping_item(
        material_id="M0099",
        material_name="Plyta test",
        quantity=3.0,
        unit="m2",
    )

    assert item.supplier == "MegaHurt"
    assert abs(item.price_estimate - 33.5) < 0.0001
