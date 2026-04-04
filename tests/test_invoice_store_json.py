from __future__ import annotations

from src.storage.invoice_store_json import InvoiceStoreJson


def test_delete_invoice_removes_selected_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = InvoiceStoreJson()

    _, first = store.upsert_invoice({"invoice_number": "FV-01"})
    _, second = store.upsert_invoice({"invoice_number": "FV-02"})

    first_id = str(first.get("invoice_id", "") or "")
    second_id = str(second.get("invoice_id", "") or "")
    assert first_id
    assert second_id

    removed = store.delete_invoice(first_id)
    assert removed is True
    assert store.get(first_id) is None
    assert store.get(second_id) is not None


def test_delete_invoice_returns_false_for_missing_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = InvoiceStoreJson()

    _, created = store.upsert_invoice({"invoice_number": "FV-10"})
    existing_id = str(created.get("invoice_id", "") or "")

    removed = store.delete_invoice("UNKNOWN-ID")
    assert removed is False
    assert store.get(existing_id) is not None


def test_upsert_invoice_deduplicates_by_invoice_signature(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = InvoiceStoreJson()

    first_new, first = store.upsert_invoice(
        {
            "invoice_number": "FV/12/03/2026",
            "invoice_date": "2026-03-30",
            "supplier": "EGGER Polska",
            "buyer_nip": "7123413192",
            "amount_due": 258.00,
            "currency": "PLN",
            "payload_hash": "hash-1",
            "attachment_key": "mail:gmail_1:f1.pdf:aaaa",
        }
    )
    assert first_new is True
    first_id = str(first.get("invoice_id", "") or "")
    assert first_id

    second_new, second = store.upsert_invoice(
        {
            "invoice_number": "FV 12 03 2026",
            "invoice_date": "2026-03-30",
            "supplier": "Egger Polska",
            "buyer_nip": "712-341-31-92",
            "amount_due": 258.0,
            "currency": "PLN",
            "payload_hash": "hash-2",
            "attachment_key": "mail:gmail_2:f2.pdf:bbbb",
        }
    )
    assert second_new is False
    assert str(second.get("invoice_id", "") or "") == first_id

    rows = store.list_invoices()
    assert len(rows) == 1
