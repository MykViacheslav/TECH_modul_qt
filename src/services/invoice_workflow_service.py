from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
import csv
from typing import Any

from src.app.app_settings import load_telegram_settings
from src.integrations.telegram_sender import send_text_message
from src.services.invoice_email_import_service import fetch_invoice_pdf_attachments
from src.services.invoice_pdf_import_service import (
    InvoiceLineItem,
    InvoiceParseResult,
    normalize_unit,
    parse_invoice_pdf_bytes,
    supported_invoice_units,
)
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.material_store_json import MaterialStoreJson


@dataclass(frozen=True)
class InvoiceSyncSummary:
    checked_files: int
    created_invoices: int
    updated_invoices: int
    parse_errors: int
    without_text: int
    pending_export: int
    telegram_notified: int
    telegram_error: str


@dataclass(frozen=True)
class MaterialExportSummary:
    invoice_id: str
    imported_lines: int
    skipped_lines: int


@dataclass(frozen=True)
class InvoiceImportResult:
    created: int
    updated: int
    total_candidates: int
    records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class InvoiceUnitStats:
    total_items: int
    units: tuple[tuple[str, int], ...]
    unknown_units: tuple[str, ...]


_INVOICE_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _safe_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except Exception:
        return 0.0


def _format_number(value: float, decimals: int = 2) -> str:
    text = f"{float(value or 0.0):.{int(decimals)}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload or b"").hexdigest()


def _prepare_payload_for_invoice_parser(payload: bytes, source_name: str) -> tuple[bytes, str]:
    file_name = str(source_name or "attachment.pdf").strip() or "attachment.pdf"
    suffix = Path(file_name).suffix.lower()
    if suffix not in _INVOICE_IMAGE_EXTS:
        return payload, file_name
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return payload, file_name
    try:
        with Image.open(BytesIO(payload)) as img:
            rgb = img.convert("RGB")
            buffer = BytesIO()
            rgb.save(buffer, format="PDF", resolution=300.0)
            pdf_payload = buffer.getvalue()
        converted_name = f"{Path(file_name).stem}.pdf"
        return (pdf_payload or payload), converted_name
    except Exception:
        return payload, file_name


def _invoice_key(value: str, fallback: str) -> str:
    raw = str(value or "").strip().upper()
    raw = re.sub(r"[^A-Z0-9]+", "", raw)
    if raw:
        return raw
    return fallback


def _is_meaningful_invoice_candidate(parsed: InvoiceParseResult) -> bool:
    if int(parsed.text_length or 0) < 24:
        return False
    if str(parsed.invoice_number or "").strip():
        return True
    has_supplier = bool(str(parsed.supplier or "").strip())
    has_date = bool(str(parsed.invoice_date or "").strip())
    has_amount = float(parsed.amount_due or 0.0) > 0.0 or float(parsed.total_gross or 0.0) > 0.0
    if has_amount and has_supplier and has_date:
        return True
    return len(tuple(parsed.items or ())) >= 2 and has_supplier


def _merge_invoice_candidates(base: InvoiceParseResult, extra: InvoiceParseResult) -> InvoiceParseResult:
    seen: set[tuple[str, str, str]] = set()
    merged_items: list[InvoiceLineItem] = []
    for row in tuple(base.items or ()) + tuple(extra.items or ()):
        key = (
            str(row.name or "").strip().lower(),
            f"{float(row.quantity or 0.0):.3f}",
            f"{float(row.total_price or 0.0):.2f}",
        )
        if key in seen:
            continue
        seen.add(key)
        merged_items.append(row)

    base_method = str(base.extraction_method or "").strip().lower()
    extra_method = str(extra.extraction_method or "").strip().lower()
    if base_method == extra_method:
        extraction_method = base_method or "text"
    else:
        extraction_method = "mixed"

    ai_used = bool(getattr(base, "ai_fallback_used", False) or getattr(extra, "ai_fallback_used", False))
    ai_conf = max(float(getattr(base, "ai_confidence", 0.0) or 0.0), float(getattr(extra, "ai_confidence", 0.0) or 0.0))
    ai_model = str(getattr(base, "ai_model", "") or "").strip() or str(getattr(extra, "ai_model", "") or "").strip()
    ai_error = str(getattr(base, "ai_error", "") or "").strip() or str(getattr(extra, "ai_error", "") or "").strip()

    return InvoiceParseResult(
        source_path=base.source_path,
        invoice_number=str(base.invoice_number or "").strip() or str(extra.invoice_number or "").strip(),
        invoice_date=str(base.invoice_date or "").strip() or str(extra.invoice_date or "").strip(),
        supplier=str(base.supplier or "").strip() or str(extra.supplier or "").strip(),
        text_length=int(base.text_length or 0) + int(extra.text_length or 0),
        items=tuple(merged_items),
        price_basis=(str(base.price_basis or "").strip().lower() or str(extra.price_basis or "").strip().lower() or "unknown"),
        total_net=max(float(base.total_net or 0.0), float(extra.total_net or 0.0)),
        total_vat=max(float(base.total_vat or 0.0), float(extra.total_vat or 0.0)),
        total_gross=max(float(base.total_gross or 0.0), float(extra.total_gross or 0.0)),
        amount_due=max(float(base.amount_due or 0.0), float(extra.amount_due or 0.0)),
        currency=str(base.currency or "").strip().upper() or str(extra.currency or "").strip().upper() or "PLN",
        buyer_nip=str(base.buyer_nip or "").strip() or str(extra.buyer_nip or "").strip(),
        is_msi_project_invoice=bool(base.is_msi_project_invoice or extra.is_msi_project_invoice),
        extraction_method=extraction_method,
        ocr_confidence=max(float(base.ocr_confidence or 0.0), float(extra.ocr_confidence or 0.0)),
        supplier_template=str(base.supplier_template or "").strip() or str(extra.supplier_template or "").strip(),
        ai_fallback_used=ai_used,
        ai_confidence=ai_conf,
        ai_model=ai_model,
        ai_error=ai_error,
    )


def _split_pdf_pages_pypdf(payload: bytes) -> list[bytes]:
    """Split a multi-page PDF into individual 1-page PDFs using pypdf (no fitz required)."""
    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore
        from io import BytesIO
    except Exception:
        return []
    try:
        reader = PdfReader(BytesIO(payload))
        pages = []
        for i in range(len(reader.pages)):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            buf = BytesIO()
            writer.write(buf)
            pages.append(buf.getvalue())
        return pages
    except Exception:
        return []


def _parse_invoice_candidates_from_pdf(
    payload: bytes,
    *,
    source_name: str,
    source_path: Path,
) -> list[InvoiceParseResult]:
    # Try pypdf-based per-page split (works without fitz/PyMuPDF)
    page_payloads = _split_pdf_pages_pypdf(payload)
    if not page_payloads or len(page_payloads) <= 1:
        full = parse_invoice_pdf_bytes(payload, source_name=source_name, source_path=source_path)
        return [full]

    per_page: list[InvoiceParseResult] = []
    for idx, page_bytes in enumerate(page_payloads):
        page_source = Path(f"{source_path}#p{idx + 1}")
        parsed = parse_invoice_pdf_bytes(page_bytes, source_name=f"{source_name}#p{idx + 1}", source_path=page_source)
        if _is_meaningful_invoice_candidate(parsed):
            per_page.append(parsed)

    if per_page:
        merged: dict[str, InvoiceParseResult] = {}
        for idx, row in enumerate(per_page, start=1):
            inv_no = str(row.invoice_number or "").strip()
            supplier_key = str(row.supplier or "").strip().lower()
            date_key = str(row.invoice_date or "").strip()
            amount_val = max(float(row.amount_due or 0.0), float(row.total_gross or 0.0), float(row.total_net or 0.0))
            if inv_no:
                key = f"inv:{_invoice_key(inv_no, fallback=f'PAGE{idx:03d}')}"
            elif supplier_key and date_key and amount_val > 0:
                key = f"sig:{supplier_key}|{date_key}|{amount_val:.2f}"
            elif supplier_key and date_key:
                key = f"sd:{supplier_key}|{date_key}"
            elif supplier_key and amount_val > 0:
                key = f"sa:{supplier_key}|{amount_val:.2f}"
            else:
                key = f"page:{idx:03d}"
            if key in merged:
                merged[key] = _merge_invoice_candidates(merged[key], row)
            else:
                merged[key] = row

        split_candidates = [value for value in merged.values() if _is_meaningful_invoice_candidate(value)]
        if split_candidates:
            return split_candidates

    full = parse_invoice_pdf_bytes(payload, source_name=source_name, source_path=source_path)
    return [full]


def _line_to_dict(line: InvoiceLineItem) -> dict[str, Any]:
    unit = normalize_unit(str(line.unit or "").strip())
    return {
        "name": str(line.name or "").strip(),
        "quantity": float(line.quantity or 0.0),
        "unit": unit,
        "parse_source": str(getattr(line, "parse_source", "generic") or "generic").strip().lower(),
        "unit_price": float(line.unit_price or 0.0),
        "total_price": float(line.total_price or 0.0),
        "unit_price_net": float(getattr(line, "unit_price_net", 0.0) or 0.0),
        "unit_price_gross": float(getattr(line, "unit_price_gross", 0.0) or 0.0),
        "total_price_net": float(getattr(line, "total_price_net", 0.0) or 0.0),
        "total_price_gross": float(getattr(line, "total_price_gross", 0.0) or 0.0),
        "vat_amount": float(getattr(line, "vat_amount", 0.0) or 0.0),
        "vat_rate": str(getattr(line, "vat_rate", "") or "").strip(),
        "price_basis": str(getattr(line, "price_basis", "") or "").strip().lower(),
        "material_type": str(line.material_type or "").strip().lower(),
        "thickness_mm": str(line.thickness_mm or "").strip(),
        "raw_line": str(line.raw_line or "").strip(),
    }


def _build_invoice_payload(
    *,
    parsed: InvoiceParseResult | None,
    source: str,
    source_path: str,
    attachment_name: str,
    attachment_key: str,
    payload_hash: str,
    message_id: str = "",
    subject: str = "",
    sender: str = "",
    received_at: str = "",
    parse_error: str = "",
) -> dict[str, Any]:
    items = [_line_to_dict(line) for line in (parsed.items if parsed is not None else ())]
    parser_counts = {"template": 0, "fallback": 0, "generic": 0}
    for row in items:
        src = str(row.get("parse_source", "") or "generic").strip().lower()
        if src.startswith("template:"):
            parser_counts["template"] += 1
        elif src.startswith("fallback:"):
            parser_counts["fallback"] += 1
        else:
            parser_counts["generic"] += 1
    known_units = set(supported_invoice_units())
    units_detected_set: set[str] = set()
    for row in items:
        unit = normalize_unit(str(row.get("unit", "") or "").strip())
        if unit:
            units_detected_set.add(unit)
    units_detected = sorted(units_detected_set)
    unknown_units = sorted([unit for unit in units_detected if unit not in known_units])
    total_amount = 0.0
    total_net = 0.0
    total_gross = 0.0
    for row in items:
        total = _safe_float(row.get("total_price", 0.0))
        if total > 0:
            total_amount += total
        total_net += _safe_float(row.get("total_price_net", 0.0))
        total_gross += _safe_float(row.get("total_price_gross", 0.0))

    invoice_number = str(parsed.invoice_number or "").strip() if parsed is not None else ""
    invoice_date = str(parsed.invoice_date or "").strip() if parsed is not None else ""
    supplier = str(parsed.supplier or "").strip() if parsed is not None else ""
    text_length = int(parsed.text_length or 0) if parsed is not None else 0
    parsed_price_basis = str(getattr(parsed, "price_basis", "") or "").strip().lower() if parsed is not None else ""
    parsed_total_net = _safe_float(getattr(parsed, "total_net", 0.0) if parsed is not None else 0.0)
    parsed_total_vat = _safe_float(getattr(parsed, "total_vat", 0.0) if parsed is not None else 0.0)
    parsed_total_gross = _safe_float(getattr(parsed, "total_gross", 0.0) if parsed is not None else 0.0)
    parsed_amount_due = _safe_float(getattr(parsed, "amount_due", 0.0) if parsed is not None else 0.0)
    currency = str(getattr(parsed, "currency", "PLN") if parsed is not None else "PLN").strip().upper() or "PLN"
    buyer_nip = str(getattr(parsed, "buyer_nip", "") if parsed is not None else "").strip()
    is_msi_project_invoice = bool(getattr(parsed, "is_msi_project_invoice", False) if parsed is not None else False)
    extraction_method = str(getattr(parsed, "extraction_method", "") if parsed is not None else "").strip().lower() or "text"
    ocr_confidence = _safe_float(getattr(parsed, "ocr_confidence", 0.0) if parsed is not None else 0.0)
    supplier_template = str(getattr(parsed, "supplier_template", "") if parsed is not None else "").strip().lower()
    ai_fallback_used = bool(getattr(parsed, "ai_fallback_used", False) if parsed is not None else False)
    ai_confidence = _safe_float(getattr(parsed, "ai_confidence", 0.0) if parsed is not None else 0.0)
    ai_model = str(getattr(parsed, "ai_model", "") if parsed is not None else "").strip()
    ai_error = str(getattr(parsed, "ai_error", "") if parsed is not None else "").strip()

    if parsed_total_net > 0:
        total_net = parsed_total_net
    if parsed_total_gross > 0:
        total_gross = parsed_total_gross
    total_vat = parsed_total_vat if parsed_total_vat > 0 else max(0.0, total_gross - total_net)
    if total_gross <= 0 and total_net > 0:
        total_gross = total_net

    # Sanity normalize totals for OCR scans where lines from summary table get mixed.
    if items:
        items_net_sum = sum(_safe_float(row.get("total_price_net", 0.0)) for row in items)
        items_gross_sum = sum(_safe_float(row.get("total_price_gross", 0.0)) for row in items)
    else:
        items_net_sum = 0.0
        items_gross_sum = 0.0

    if total_net <= 0 and items_net_sum > 0:
        total_net = items_net_sum
    elif items_net_sum > 0 and total_net > 0 and items_net_sum > (total_net * 1.15):
        total_net = items_net_sum
    if total_gross <= 0:
        if items_gross_sum > 0:
            total_gross = items_gross_sum
        elif total_net > 0:
            total_gross = total_net
    elif items_gross_sum > 0 and total_gross > 0 and items_gross_sum > (total_gross * 1.15):
        total_gross = items_gross_sum

    if total_gross > 0 and total_net > 0 and total_gross + 0.01 < total_net:
        if items_gross_sum >= items_net_sum > 0:
            total_net = items_net_sum
            total_gross = items_gross_sum
        else:
            total_gross = total_net

    if total_vat > 0 and total_net > 0 and total_vat > (total_net * 0.55):
        total_vat = max(0.0, total_gross - total_net)
    elif total_vat <= 0 and total_gross > 0 and total_net > 0:
        total_vat = max(0.0, total_gross - total_net)
    elif total_vat > 0 and total_gross >= total_net:
        diff = abs((total_gross - total_net) - total_vat)
        if diff > max(2.0, total_vat * 0.20):
            total_vat = max(0.0, total_gross - total_net)

    amount_due = parsed_amount_due if parsed_amount_due > 0 else (total_gross if total_gross > 0 else total_net)
    if amount_due > 0 and total_gross > 0 and amount_due > (total_gross * 3.0):
        amount_due = total_gross
    if amount_due > 0 and total_net > 0 and amount_due < (total_net * 0.50):
        amount_due = total_gross if total_gross > 0 else total_net

    if total_amount <= 0:
        total_amount = amount_due
    extraction_low_quality = extraction_method in {"ocr", "mixed", "none"} or extraction_method.startswith("ocr")
    if extraction_method.endswith("+ai") or extraction_method == "ai":
        extraction_low_quality = False
    needs_review = bool(
        parse_error
        or ai_error
        or len(items) == 0
        or (parsed_price_basis or "unknown") == "unknown"
        or (extraction_low_quality and not ai_fallback_used)
        or (ai_fallback_used and ai_confidence < 0.60)
        or bool(unknown_units)
    )

    return {
        "source": source,
        "source_path": source_path,
        "attachment_name": attachment_name,
        "attachment_key": attachment_key,
        "payload_hash": payload_hash,
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "received_at": received_at,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "supplier": supplier,
        "supplier_template": supplier_template,
        "ai_fallback_used": ai_fallback_used,
        "ai_confidence": round(ai_confidence, 3),
        "ai_model": ai_model,
        "ai_error": ai_error,
        "text_length": text_length,
        "has_text": bool(text_length > 0),
        "extraction_method": extraction_method,
        "ocr_confidence": round(ocr_confidence, 3),
        "needs_review": needs_review,
        "price_basis": parsed_price_basis or "unknown",
        "total_net": round(total_net, 2),
        "total_vat": round(total_vat, 2),
        "total_gross": round(total_gross, 2),
        "amount_due": round(amount_due, 2),
        "currency": currency,
        "buyer_nip": buyer_nip,
        "is_msi_project_invoice": is_msi_project_invoice,
        "parse_error": str(parse_error or "").strip(),
        "items": items,
        "items_count": len(items),
        "parser_counts": parser_counts,
        "units_detected": units_detected,
        "unknown_units": unknown_units,
        "total_amount": round(total_amount, 2),
    }


def import_invoice_pdf_file(
    path: Path,
    *,
    store: InvoiceStoreJson | None = None,
) -> tuple[bool, dict[str, Any]]:
    result = import_invoice_pdf_file_multi(path, store=store)
    if result.created > 0 and result.records:
        return True, dict(result.records[0])
    if result.records:
        return False, dict(result.records[0])
    return False, {}


def import_invoice_pdf_file_multi(
    path: Path,
    *,
    store: InvoiceStoreJson | None = None,
) -> InvoiceImportResult:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku PDF: {file_path}")
    payload = file_path.read_bytes()
    parser_payload, parser_name = _prepare_payload_for_invoice_parser(payload, file_path.name)
    parsed_candidates = _parse_invoice_candidates_from_pdf(
        parser_payload,
        source_name=parser_name,
        source_path=file_path,
    )
    digest = _payload_hash(payload)
    target = store if store is not None else InvoiceStoreJson()
    created = 0
    updated = 0
    stored_records: list[dict[str, Any]] = []

    for idx, parsed in enumerate(parsed_candidates, start=1):
        key = _invoice_key(parsed.invoice_number, fallback=f"p{idx:03d}")
        candidate_hash = _payload_hash(payload + f":{key}:{idx}".encode("utf-8"))
        attachment_key = f"manual:{file_path.name}:{digest[:16]}:{idx:03d}:{key}"
        record = _build_invoice_payload(
            parsed=parsed,
            source="manual_pdf",
            source_path=str(file_path),
            attachment_name=file_path.name,
            attachment_key=attachment_key,
            payload_hash=candidate_hash,
        )
        is_new, stored = target.upsert_invoice(record)
        stored_records.append(stored)
        if is_new:
            created += 1
        else:
            updated += 1

    return InvoiceImportResult(
        created=created,
        updated=updated,
        total_candidates=len(parsed_candidates),
        records=tuple(stored_records),
    )


def sync_invoices_from_mail(
    *,
    worker_name: str = "",
    max_messages: int = 20,
    store: InvoiceStoreJson | None = None,
    send_telegram_notifications: bool = True,
) -> InvoiceSyncSummary:
    target = store if store is not None else InvoiceStoreJson()
    attachments = fetch_invoice_pdf_attachments(worker_name=worker_name, max_messages=max_messages)

    checked = 0
    created = 0
    updated = 0
    parse_errors = 0
    without_text = 0

    for attachment in attachments:
        checked += 1
        digest = _payload_hash(attachment.payload)
        attachment_key = f"{attachment.source}:{attachment.message_id}:{attachment.filename}:{digest[:16]}"
        parser_payload, parser_name = _prepare_payload_for_invoice_parser(attachment.payload, attachment.filename)

        parsed_candidates: list[InvoiceParseResult] = []
        parse_error = ""
        source_path = Path(f"{attachment.message_id}_{attachment.filename}")
        try:
            parsed_candidates = _parse_invoice_candidates_from_pdf(
                parser_payload,
                source_name=parser_name or source_path.name,
                source_path=source_path,
            )
            if not parsed_candidates:
                without_text += 1
            elif all(int(parsed.text_length or 0) <= 0 for parsed in parsed_candidates):
                without_text += 1
        except Exception as exc:
            parse_errors += 1
            parse_error = str(exc)
            parsed_candidates = []

        if not parsed_candidates:
            payload_row = _build_invoice_payload(
                parsed=None,
                source=f"mail_{attachment.source}",
                source_path=str(source_path),
                attachment_name=attachment.filename,
                attachment_key=attachment_key,
                payload_hash=digest,
                message_id=attachment.message_id,
                subject=attachment.subject,
                sender=attachment.sender,
                received_at=attachment.received_at,
                parse_error=parse_error or "Brak danych do odczytu.",
            )
            is_new, _ = target.upsert_invoice(payload_row)
            if is_new:
                created += 1
            else:
                updated += 1
            continue

        for idx, parsed in enumerate(parsed_candidates, start=1):
            key = _invoice_key(parsed.invoice_number, fallback=f"p{idx:03d}")
            candidate_hash = _payload_hash(attachment.payload + f":{key}:{idx}".encode("utf-8"))
            payload_row = _build_invoice_payload(
                parsed=parsed,
                source=f"mail_{attachment.source}",
                source_path=str(source_path),
                attachment_name=attachment.filename,
                attachment_key=f"{attachment_key}:{idx:03d}:{key}",
                payload_hash=candidate_hash,
                message_id=attachment.message_id,
                subject=attachment.subject,
                sender=attachment.sender,
                received_at=attachment.received_at,
                parse_error=parse_error,
            )
            is_new, _ = target.upsert_invoice(payload_row)
            if is_new:
                created += 1
            else:
                updated += 1

    pending_export = target.count_pending_export()
    telegram_count = 0
    telegram_error = ""
    if send_telegram_notifications:
        telegram_count, telegram_error = notify_unsent_invoice_alerts(store=target)

    return InvoiceSyncSummary(
        checked_files=checked,
        created_invoices=created,
        updated_invoices=updated,
        parse_errors=parse_errors,
        without_text=without_text,
        pending_export=pending_export,
        telegram_notified=telegram_count,
        telegram_error=telegram_error,
    )


def sync_invoices_from_local_dirs(
    dirs: list[Path | str],
    *,
    store: InvoiceStoreJson | None = None,
    recursive: bool = False,
    max_files: int = 300,
) -> tuple[int, int, int, int]:
    target = store if store is not None else InvoiceStoreJson()

    # Pre-populate specific dirs if none provided OR just ensure they exist.
    search_dirs = list(dirs) if dirs else [
        Path.home() / "Downloads",
        Path(r"C:\Users\mykyt\Downloads"),
        Path(r"C:\PythonProject\TECH_modul\Faktury"),
    ]

    unique_paths: dict[str, Path] = {}
    for raw_dir in search_dirs:
        folder = Path(raw_dir).expanduser()
        if not folder.exists() or not folder.is_dir():
            continue
        iterator = folder.rglob("*.pdf") if recursive else folder.glob("*.pdf")
        for pdf_path in iterator:
            try:
                key = str(pdf_path.resolve()).strip().lower()
            except Exception:
                key = str(pdf_path).strip().lower()
            if not key:
                continue
            unique_paths[key] = pdf_path

    files: list[Path] = list(unique_paths.values())
    files.sort(
        key=lambda p: float(p.stat().st_mtime) if p.exists() else 0.0,
        reverse=True,
    )
    if max_files > 0:
        files = files[: int(max_files)]

    checked = 0
    created = 0
    updated = 0
    errors = 0

    for file_path in files:
        checked += 1
        try:
            is_new, _ = import_invoice_pdf_file(file_path, store=target)
            if is_new:
                created += 1
            else:
                updated += 1
        except Exception:
            errors += 1

    return checked, created, updated, errors


def collect_invoice_unit_stats(
    *,
    store: InvoiceStoreJson | None = None,
    invoices: list[dict[str, Any]] | None = None,
) -> InvoiceUnitStats:
    source_rows = invoices if invoices is not None else (store.list_invoices() if store is not None else InvoiceStoreJson().list_invoices())
    known_units = set(supported_invoice_units())
    unit_counts: dict[str, int] = {}
    unknown: set[str] = set()
    total_items = 0

    for invoice in source_rows:
        if not isinstance(invoice, dict):
            continue
        for item in invoice.get("items", []):
            if not isinstance(item, dict):
                continue
            total_items += 1
            unit = normalize_unit(str(item.get("unit", "") or "").strip())
            if not unit:
                continue
            unit_counts[unit] = int(unit_counts.get(unit, 0)) + 1
            if unit not in known_units:
                unknown.add(unit)

    sorted_units = tuple(sorted(unit_counts.items(), key=lambda row: (-int(row[1]), str(row[0]))))
    return InvoiceUnitStats(
        total_items=total_items,
        units=sorted_units,
        unknown_units=tuple(sorted(unknown)),
    )


def notify_unsent_invoice_alerts(
    *,
    store: InvoiceStoreJson | None = None,
    limit: int = 8,
) -> tuple[int, str]:
    target = store if store is not None else InvoiceStoreJson()
    unsent = target.list_unsent_telegram(limit=max(1, int(limit or 8)))
    if not unsent:
        return 0, ""

    settings = load_telegram_settings()
    if not (settings.enabled and str(settings.bot_token or "").strip() and str(settings.chat_id or "").strip()):
        return 0, ""

    lines = ["TECH_modul: nowe faktury do weryfikacji"]
    for row in unsent:
        inv_no = str(row.get("invoice_number", "") or "").strip()
        supplier = str(row.get("supplier", "") or row.get("sender", "") or "-").strip()
        amount = _safe_float(row.get("total_amount", 0.0))
        date_label = str(row.get("invoice_date", "") or "").strip()
        if not date_label:
            date_label = str(row.get("received_at", "") or "")[:10]

        code = inv_no or str(row.get("attachment_name", "") or str(row.get("invoice_id", "") or "-")).strip()
        lines.append(f"- {code} | {supplier} | {amount:.2f} zl | {date_label or '-'}")

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3880].rstrip() + "\n...(skrocone)"

    try:
        send_text_message(
            bot_token=str(settings.bot_token),
            chat_id=str(settings.chat_id),
            text=text,
        )
    except Exception as exc:
        return 0, str(exc)

    sent_ids = [str(row.get("invoice_id", "") or "").strip() for row in unsent]
    target.mark_telegram_sent(sent_ids)
    return len([x for x in sent_ids if x]), ""


def _next_material_id(rows: list[dict[str, Any]]) -> str:
    # Use same logic as in MaterialStoreJson but on a local list
    max_num = 0
    for row in rows:
        raw = str(row.get("id", "") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            try:
                max_num = max(max_num, int(digits))
            except ValueError:
                pass
    return f"M{max_num + 1:04d}"


def _next_type_id(types: list[dict[str, Any]]) -> str:
    max_num = 0
    for row in types:
        raw = str(row.get("id", "") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            continue
        try:
            max_num = max(max_num, int(digits))
        except Exception:
            continue
    return f"T{max_num + 1:04d}"


def _ensure_type_exists(types: list[dict[str, Any]], typ: str, supplier: str) -> None:
    typ_norm = str(typ or "").strip().lower()
    if not typ_norm:
        return
    for row in types:
        if str(row.get("typ", "") or "").strip().lower() == typ_norm:
            if not str(row.get("producent", "") or "").strip() and supplier:
                row["producent"] = supplier
            return

    types.append(
        {
            "id": _next_type_id(types),
            "typ": typ_norm,
            "nazwa": typ_norm.capitalize(),
            "producent": supplier,
        }
    )


def _suggest_warehouse_for_material_type(material_type: str) -> tuple[str, str]:
    typ = str(material_type or "").strip().lower()
    if typ in {"okucie", "profil"}:
        return "MAG003", "okucia_akcesoria"
    if typ in {"plyta", "korpus", "front", "plecy", "okleina"}:
        return "MAG002", "plyty_fronty"
    return "MAG001", "glowny"


def _material_line_exists(
    rows: list[dict[str, Any]],
    *,
    name: str,
    supplier: str,
    invoice_number: str,
    quantity: float,
    unit_price: float,
) -> bool:
    name_norm = str(name or "").strip().lower()
    supplier_norm = str(supplier or "").strip().lower()
    invoice_norm = str(invoice_number or "").strip().lower()

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_name = str(row.get("nazwa", "") or "").strip().lower()
        row_supplier = str(row.get("producent", "") or "").strip().lower()
        row_invoice = str(row.get("numer_faktury", "") or "").strip().lower()
        if row_name != name_norm or row_supplier != supplier_norm or row_invoice != invoice_norm:
            continue
        row_qty = _safe_float(row.get("ilosc", 0.0))
        row_price = _safe_float(row.get("cena_zl", 0.0))
        if abs(row_qty - float(quantity or 0.0)) < 0.0001 and abs(row_price - float(unit_price or 0.0)) < 0.01:
            return True
    return False


def export_invoice_to_material_store(
    invoice_id: str,
    *,
    invoice_store: InvoiceStoreJson | None = None,
    material_store: MaterialStoreJson | None = None,
    discount_percent: float = 0.0,
    warehouse_typ: str | None = None,
) -> MaterialExportSummary:
    inv_store = invoice_store if invoice_store is not None else InvoiceStoreJson()
    mat_store = material_store if material_store is not None else MaterialStoreJson()

    invoice = inv_store.get(invoice_id)
    if invoice is None:
        raise ValueError(f"Nie znaleziono faktury: {invoice_id}")

    raw_items = invoice.get("items", [])
    items = [dict(item) for item in raw_items if isinstance(item, dict)]
    if not items:
        return MaterialExportSummary(invoice_id=str(invoice_id), imported_lines=0, skipped_lines=0)

    payload = mat_store.load()
    if not isinstance(payload, dict):
        payload = {}

    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    types = payload.get("types", [])
    if not isinstance(types, list):
        types = []

    imported = 0
    skipped = 0
    created_material_ids: list[str] = []
    supplier = str(invoice.get("supplier", "") or invoice.get("sender", "") or "").strip()
    invoice_number = str(invoice.get("invoice_number", "") or "").strip() or str(invoice.get("attachment_name", "") or "").strip()
    invoice_date = str(invoice.get("invoice_date", "") or "").strip()
    source_path = str(invoice.get("source_path", "") or "").strip()
    attachment_name = str(invoice.get("attachment_name", "") or "").strip()
    if not invoice_date:
        invoice_date = str(invoice.get("received_at", "") or "")[:10]
    today = datetime.now().strftime("%Y-%m-%d")

    purchase_chan = str(invoice.get("purchase_channel", "faktura") or "").strip().lower()
    channel_label = "Faktura"
    if purchase_chan == "paragon":
        channel_label = "Paragon"
    elif purchase_chan == "cash":
        channel_label = "Gotówka"

    for item in items:
        name = str(item.get("name", "") or "").strip()
        if not name:
            skipped += 1
            continue

        quantity = _safe_float(item.get("quantity", 0.0))
        # Get base unit price
        unit_price_base = _safe_float(item.get("unit_price_gross", 0.0))
        if unit_price_base <= 0:
            unit_price_base = _safe_float(item.get("unit_price", 0.0))
        if unit_price_base <= 0:
            unit_price_base = _safe_float(item.get("unit_price_net", 0.0))
        
        total_price_base = _safe_float(item.get("total_price", 0.0))
        
        # Apply discount
        multiplier = 1.0 - (float(discount_percent or 0.0) / 100.0)
        unit_price = unit_price_base * multiplier
        total_price = total_price_base * multiplier

        if quantity <= 0:
            quantity = 1.0
        if unit_price <= 0 and total_price > 0:
            unit_price = total_price / quantity
        if unit_price <= 0:
            skipped += 1
            continue

        if _material_line_exists(
            rows,
            name=name,
            supplier=supplier,
            invoice_number=invoice_number,
            quantity=quantity,
            unit_price=unit_price,
        ):
            skipped += 1
            continue

        material_type = str(item.get("material_type", "") or "").strip().lower() or "plyta"
        thickness_mm = str(item.get("thickness_mm", "") or "").strip()
        unit = normalize_unit(str(item.get("unit", "") or "").strip())
        price_basis = str(item.get("price_basis", "") or invoice.get("price_basis", "") or "unknown").strip().lower()
        
        if warehouse_typ and str(warehouse_typ).strip():
            # Find ID for the name or use as name
            # For simplicity, if override matches name, we use it.
            # In a real system we'd lookup ID by name.
            warehouse_id = "MAG_CUSTOM"
            warehouse_typ_final = str(warehouse_typ).strip()
            # Try to match existing
            if warehouse_typ_final == "okucia_akcesoria": warehouse_id = "MAG003"
            elif warehouse_typ_final == "plyty_fronty": warehouse_id = "MAG002"
            elif warehouse_typ_final == "glowny": warehouse_id = "MAG001"
        else:
            warehouse_id, warehouse_typ_final = _suggest_warehouse_for_material_type(material_type)
            
        param_parts: list[str] = []
        if unit:
            param_parts.append(f"jedn: {unit}")
        if price_basis in {"netto", "brutto"}:
            param_parts.append(f"cena: {price_basis}")
        params = " | ".join(param_parts)

        _ensure_type_exists(types, material_type, supplier)
        material_id = _next_material_id(rows)

        row_data = {
            "id": material_id,
            "typ": material_type,
            "nazwa": name,
            "producent": supplier,
            "szerokosc": "",
            "dlugosc": "",
            "grubosc": thickness_mm,
            "parametry": params,
            "cena_zl": _format_number(unit_price, 2),
            "ilosc": _format_number(quantity, 3),
            "spisano_zamowienie": "",
            "ilosc_magazyn": _format_number(quantity, 3),
            "magazyn_id": warehouse_id,
            "magazyn_typ": warehouse_typ_final,
            "pracownik": "",
            "data_wpisu": today,
            "zakup": f"{channel_label}: {invoice_number} ({price_basis})" if price_basis in {"netto", "brutto"} else f"{channel_label}: {invoice_number}",
            "numer_faktury": invoice_number,
            "data_zakupu": invoice_date,
            "suma_zam_kw": _format_number(unit_price * quantity, 2),
            "suma_za_szt": _format_number(unit_price * quantity, 2),
            "source_invoice_id": str(invoice_id or "").strip(),
            "source_invoice_supplier": supplier,
            "source_invoice_number": invoice_number,
            "source_invoice_date": invoice_date,
            "source_invoice_attachment": attachment_name,
            "source_invoice_source_path": source_path,
        }
        rows.append(row_data)
        created_material_ids.append(material_id)
        imported += 1

    if imported > 0:
        payload["rows"] = rows
        payload["types"] = types
        if not isinstance(payload.get("pracownicy", []), list):
            payload["pracownicy"] = []
        mat_store.save(payload)

    if imported > 0 or skipped > 0:
        inv_store.mark_exported(
            str(invoice_id),
            exported_material_ids=created_material_ids,
            imported_lines=imported,
            skipped_lines=skipped,
        )

    return MaterialExportSummary(
        invoice_id=str(invoice_id),
        imported_lines=imported,
        skipped_lines=skipped,
    )


def export_pending_invoices_to_material_store(
    *,
    invoice_store: InvoiceStoreJson | None = None,
    material_store: MaterialStoreJson | None = None,
) -> tuple[int, int, int]:
    inv_store = invoice_store if invoice_store is not None else InvoiceStoreJson()
    mat_store = material_store if material_store is not None else MaterialStoreJson()

    invoices = inv_store.list_invoices()
    exported_invoices = 0
    imported_lines = 0
    skipped_lines = 0

    for invoice in invoices:
        if bool(invoice.get("exported_to_material", False)):
            continue
        invoice_id = str(invoice.get("invoice_id", "") or "").strip()
        if not invoice_id:
            continue
        result = export_invoice_to_material_store(
            invoice_id,
            invoice_store=inv_store,
            material_store=mat_store,
        )
        if result.imported_lines > 0 or result.skipped_lines > 0:
            exported_invoices += 1
            imported_lines += result.imported_lines
            skipped_lines += result.skipped_lines

    return exported_invoices, imported_lines, skipped_lines
