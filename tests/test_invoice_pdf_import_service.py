from __future__ import annotations

from pathlib import Path

from src.services.invoice_pdf_import_service import parse_invoice_pdf_bytes, parse_invoice_text


def test_parse_invoice_text_extracts_metadata_and_rows() -> None:
    text = """
FAKTURA VAT NR FV/12/03/2026
Data wystawienia: 2026-03-30
Sprzedawca: EGGER Polska Sp. z o.o.
1 PLYTA MDF 18 mm 2 szt 129,00 258,00
2 Obrzeze ABS 23 mb 3,50 80,50
Razem: 338,50
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_test.pdf"))

    assert parsed.invoice_number == "FV/12/03/2026"
    assert parsed.invoice_date == "2026-03-30"
    assert parsed.supplier == "EGGER Polska Sp. z o.o."
    assert len(parsed.items) == 2

    first = parsed.items[0]
    assert first.name.lower().startswith("plyta mdf")
    assert first.quantity == 2.0
    assert first.unit_price == 129.0
    assert first.total_price == 258.0
    assert first.material_type == "plyta"
    assert first.thickness_mm == "18"

    second = parsed.items[1]
    assert second.name.lower().startswith("obrzeze abs")
    assert second.quantity == 23.0
    assert second.unit == "mb"


def test_parse_invoice_text_handles_empty_input() -> None:
    parsed = parse_invoice_text("", source_path=Path("empty.pdf"))
    assert parsed.text_length == 0
    assert parsed.invoice_number == ""
    assert parsed.invoice_date == ""
    assert parsed.supplier == ""
    assert parsed.items == ()


def test_parse_invoice_pdf_bytes_raises_on_non_pdf() -> None:
    try:
        parse_invoice_pdf_bytes(b"not-a-pdf", source_name="bad.pdf")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "PDF" in str(exc)


def test_parse_invoice_text_handles_netto_brutto_and_amount_due() -> None:
    text = """
FAKTURA VAT NR FV/99/03/2026
Data wystawienia: 2026-03-30
Sprzedawca: Test Supplier
1 PLYTA MDF 18 mm 2,00 szt 129,00 258,00 23% 59,34 317,34
Razem netto 258,00
Razem brutto 317,34
Kwota do zaplaty 317,34
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_vat.pdf"))

    assert parsed.total_net == 258.0
    assert parsed.total_gross == 317.34
    assert parsed.amount_due == 317.34

    assert len(parsed.items) == 1
    row = parsed.items[0]
    assert row.quantity == 2.0
    assert abs(row.unit_price_net - 129.0) < 0.01
    assert abs(row.total_price_net - 258.0) < 0.01
    assert abs(row.total_price_gross - 317.34) < 0.01


def test_parse_invoice_text_ignores_date_rows_as_money() -> None:
    text = """
FAKTURA VAT NR FV/15/03/2026
Data wystawienia: 30.03.2026
Termin platnosci: 06.04.2026
Sprzedawca: Test Supplier
1 PLYTA MDF 18 mm 2 szt 129,00 258,00
Razem netto 258,00
Kwota VAT 59,34
Razem brutto 317,34
Do zaplaty 317,34
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_data.pdf"))

    assert parsed.invoice_date == "2026-03-30"
    assert len(parsed.items) == 1
    assert parsed.total_net == 258.0
    assert parsed.total_vat == 59.34
    assert parsed.total_gross == 317.34
    assert parsed.amount_due == 317.34


def test_parse_invoice_text_does_not_take_item_vat_as_summary_total() -> None:
    text = """
FAKTURA VAT NR FV/16/03/2026
Data wystawienia: 2026-03-30
Sprzedawca: Test Supplier
1 PLYTA MDF 18 mm 2,00 szt 129,00 258,00 VAT 23% 59,34 317,34
Razem netto 258,00
Kwota VAT 59,34
Razem brutto 317,34
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_vat_summary.pdf"))

    assert len(parsed.items) == 1
    assert parsed.total_net == 258.0
    assert parsed.total_vat == 59.34
    assert parsed.total_gross == 317.34
    assert abs(parsed.items[0].vat_amount - 59.34) < 0.01


def test_parse_invoice_text_extracts_buyer_nip_for_msi_project() -> None:
    text = """
FAKTURA VAT NR FV/20/03/2026
Sprzedawca: Dostawca Test
NIP: 525-000-11-22
Nabywca: MSI project sp. z o.o.
NIP: 712-341-31-92
1 PLYTA MDF 18 mm 1 szt 100,00 123,00
Razem netto 100,00
Kwota VAT 23,00
Razem brutto 123,00
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_msi_nip.pdf"))

    assert parsed.buyer_nip == "7123413192"
    assert parsed.is_msi_project_invoice is True


def test_parse_invoice_text_marks_mismatch_when_nip_is_different() -> None:
    text = """
FAKTURA VAT NR FV/21/03/2026
Nabywca: Inna Firma
NIP: 111-222-33-44
1 PLYTA MDF 18 mm 1 szt 100,00 123,00
"""
    parsed = parse_invoice_text(text, source_path=Path("faktura_other_nip.pdf"))

    assert parsed.buyer_nip == "1112223344"
    assert parsed.is_msi_project_invoice is False
