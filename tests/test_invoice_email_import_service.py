from __future__ import annotations

from src.services.invoice_email_import_service import (
    InvoiceMailAttachment,
    fetch_invoice_pdf_attachments,
)


def _sample_attachment(source: str) -> InvoiceMailAttachment:
    return InvoiceMailAttachment(
        source=source,
        message_id=f"{source}_1",
        subject="Faktura test",
        sender="test@example.com",
        received_at="2026-03-30T10:00:00+00:00",
        filename="faktura.pdf",
        payload=b"%PDF-1.4",
    )


def test_fetch_invoice_pdf_attachments_prefers_gmail(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_gmail_invoice_pdf_attachments",
        lambda max_messages, worker_name: [_sample_attachment("gmail")],
    )
    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_imap_invoice_pdf_attachments",
        lambda max_messages: [_sample_attachment("imap")],
    )

    rows = fetch_invoice_pdf_attachments(worker_name="user", max_messages=10)
    assert len(rows) == 1
    assert rows[0].source == "gmail"


def test_fetch_invoice_pdf_attachments_fallback_to_imap(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_gmail_invoice_pdf_attachments",
        lambda max_messages, worker_name: [],
    )
    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_imap_invoice_pdf_attachments",
        lambda max_messages: [_sample_attachment("imap")],
    )

    rows = fetch_invoice_pdf_attachments(worker_name="user", max_messages=10)
    assert len(rows) == 1
    assert rows[0].source == "imap"


def test_fetch_invoice_pdf_attachments_raises_on_errors(monkeypatch) -> None:
    def _gmail_error(max_messages, worker_name):
        raise RuntimeError("gmail down")

    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_gmail_invoice_pdf_attachments",
        _gmail_error,
    )
    monkeypatch.setattr(
        "src.services.invoice_email_import_service._fetch_imap_invoice_pdf_attachments",
        lambda max_messages: [],
    )

    try:
        fetch_invoice_pdf_attachments(worker_name="user", max_messages=10)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Gmail" in str(exc)
