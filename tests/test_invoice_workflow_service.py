from __future__ import annotations

from pathlib import Path

from src.services.invoice_email_import_service import InvoiceMailAttachment
from src.services.invoice_pdf_import_service import parse_invoice_text
from src.services.invoice_workflow_service import (
    export_invoice_to_material_store,
    notify_unsent_invoice_alerts,
    sync_invoices_from_local_dirs,
    sync_invoices_from_mail,
)
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.material_store_json import MaterialStoreJson


def test_sync_invoices_from_mail_deduplicates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    attachments = [
        InvoiceMailAttachment(
            source="gmail",
            message_id="gmail_1",
            subject="Faktura test",
            sender="Egger",
            received_at="2026-03-30T10:00:00+00:00",
            filename="f1.pdf",
            payload=b"%PDF-1",
        ),
        InvoiceMailAttachment(
            source="gmail",
            message_id="gmail_1",
            subject="Faktura test",
            sender="Egger",
            received_at="2026-03-30T10:00:00+00:00",
            filename="f1.pdf",
            payload=b"%PDF-1",
        ),
    ]

    monkeypatch.setattr(
        "src.services.invoice_workflow_service.fetch_invoice_pdf_attachments",
        lambda worker_name, max_messages: attachments,
    )
    monkeypatch.setattr(
        "src.services.invoice_workflow_service.parse_invoice_pdf_bytes",
        lambda payload, source_name, source_path: parse_invoice_text(
            """
FAKTURA VAT NR FV/12/03/2026
Data wystawienia: 2026-03-30
Sprzedawca: EGGER Polska
1 PLYTA MDF 18 mm 2 szt 129,00 258,00
""",
            source_path=Path(source_name),
        ),
    )

    summary = sync_invoices_from_mail(send_telegram_notifications=False)

    assert summary.checked_files == 2
    assert summary.created_invoices == 1
    assert summary.updated_invoices == 1


def test_export_invoice_to_material_store_marks_exported(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    invoice_store = InvoiceStoreJson()
    material_store = MaterialStoreJson()

    _, invoice = invoice_store.upsert_invoice(
        {
            "invoice_number": "FV-01",
            "invoice_date": "2026-03-30",
            "supplier": "Egger",
            "items": [
                {
                    "name": "Plyta MDF 18",
                    "quantity": 2.0,
                    "unit": "szt",
                    "unit_price": 129.0,
                    "total_price": 258.0,
                    "material_type": "plyta",
                    "thickness_mm": "18",
                }
            ],
            "items_count": 1,
            "total_amount": 258.0,
        }
    )

    result = export_invoice_to_material_store(
        str(invoice.get("invoice_id", "")),
        invoice_store=invoice_store,
        material_store=material_store,
    )

    assert result.imported_lines == 1
    assert result.skipped_lines == 0

    rows = material_store.list_materials()
    assert len(rows) == 1
    assert rows[0].get("numer_faktury", "") == "FV-01"

    refreshed = invoice_store.get(str(invoice.get("invoice_id", "")))
    assert refreshed is not None
    assert bool(refreshed.get("exported_to_material", False)) is True


def test_notify_unsent_invoice_alerts_marks_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    invoice_store = InvoiceStoreJson()
    _, invoice = invoice_store.upsert_invoice(
        {
            "invoice_number": "FV-02",
            "invoice_date": "2026-03-30",
            "supplier": "Swisskrono",
            "items": [],
            "items_count": 0,
            "total_amount": 0.0,
            "telegram_sent": False,
        }
    )

    class _T:
        enabled = True
        bot_token = "token"
        chat_id = "chat"

    sent_payloads: list[str] = []

    monkeypatch.setattr("src.services.invoice_workflow_service.load_telegram_settings", lambda: _T())
    monkeypatch.setattr(
        "src.services.invoice_workflow_service.send_text_message",
        lambda bot_token, chat_id, text: sent_payloads.append(text),
    )

    sent, error = notify_unsent_invoice_alerts(store=invoice_store)
    assert error == ""
    assert sent == 1
    assert len(sent_payloads) == 1

    refreshed = invoice_store.get(str(invoice.get("invoice_id", "")))
    assert refreshed is not None
    assert bool(refreshed.get("telegram_sent", False)) is True


def test_sync_invoices_stores_buyer_nip_and_msi_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    attachments = [
        InvoiceMailAttachment(
            source="gmail",
            message_id="gmail_2",
            subject="Faktura MSI",
            sender="Dostawca",
            received_at="2026-03-30T11:00:00+00:00",
            filename="f_msi.pdf",
            payload=b"%PDF-2",
        ),
    ]

    monkeypatch.setattr(
        "src.services.invoice_workflow_service.fetch_invoice_pdf_attachments",
        lambda worker_name, max_messages: attachments,
    )
    monkeypatch.setattr(
        "src.services.invoice_workflow_service.parse_invoice_pdf_bytes",
        lambda payload, source_name, source_path: parse_invoice_text(
            """
FAKTURA VAT NR FV/33/03/2026
Nabywca: MSI project
NIP: 712-341-31-92
1 PLYTA MDF 18 mm 1 szt 100,00 123,00
""",
            source_path=Path(source_name),
        ),
    )

    summary = sync_invoices_from_mail(send_telegram_notifications=False)
    assert summary.created_invoices == 1

    invoice_store = InvoiceStoreJson()
    rows = invoice_store.list_invoices()
    assert len(rows) == 1
    assert str(rows[0].get("buyer_nip", "")) == "7123413192"
    assert bool(rows[0].get("is_msi_project_invoice", False)) is True


def test_sync_invoices_from_local_dirs_scans_downloads_folder(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    invoice_store = InvoiceStoreJson()

    downloads = tmp_path / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    (downloads / "a.pdf").write_bytes(b"%PDF-A")
    (downloads / "b.pdf").write_bytes(b"%PDF-B")
    (downloads / "notes.txt").write_text("not-pdf", encoding="utf-8")

    seen_names: list[str] = []
    states = {"a.pdf": True, "b.pdf": False}

    def _fake_import(path: Path, *, store: InvoiceStoreJson | None = None):
        seen_names.append(path.name)
        return states.get(path.name, False), {"invoice_id": path.stem}

    monkeypatch.setattr(
        "src.services.invoice_workflow_service.import_invoice_pdf_file",
        _fake_import,
    )

    checked, created, updated, errors = sync_invoices_from_local_dirs(
        [downloads],
        store=invoice_store,
    )

    assert checked == 2
    assert created == 1
    assert updated == 1
    assert errors == 0
    assert set(seen_names) == {"a.pdf", "b.pdf"}
