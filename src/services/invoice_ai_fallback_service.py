from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError
from urllib import request

from src.services.invoice_pdf_import_service import (
    InvoiceLineItem,
    InvoiceParseResult,
    MSI_PROJECT_NIP,
    normalize_unit,
)

_AI_BREAKER_REASON = ""


def _to_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except Exception:
        return 0.0


def _normalize_date(value: str) -> str:
    raw = str(value or "").strip().replace(".", "-").replace("/", "-")
    if not raw:
        return ""
    parts = [p for p in raw.split("-") if p]
    if len(parts) != 3:
        return ""
    try:
        if len(parts[0]) == 4:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return ""
        return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        return ""


def _guess_material_type(name: str) -> str:
    low = str(name or "").strip().lower()
    rules = (
        ("okleina", ("okleina", "obrzeze", "obrzez")),
        ("okucie", ("zawias", "prowadnic", "wkret", "sruba", "uchwyt", "tandem", "blum")),
        ("lakier", ("lakier", "farba", "bejc")),
        ("profil", ("profil", "listwa", "ceownik", "katownik")),
        ("front", ("front", "drzwicz", "drzwi")),
        ("plyta", ("plyta", "mdf", "hdf", "laminat", "sklejka", "blat")),
        ("korpus", ("korpus",)),
    )
    for material_type, tokens in rules:
        if any(token in low for token in tokens):
            return material_type
    return "plyta"


def _extract_thickness(name: str) -> str:
    low = str(name or "").lower()
    match = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*mm\b", low)
    if match:
        return str(match.group(1)).replace(",", ".")
    return ""


def _clean_name(value: str) -> str:
    name = re.sub(r"\s+", " ", str(value or "").strip())
    name = re.sub(r"^\d+[.)-]?\s*", "", name)
    return name.strip(" -;,.")


def _extract_json_payload(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else None
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            loaded = json.loads(candidate)
            return loaded if isinstance(loaded, dict) else None
        except Exception:
            return None
    return None


def _build_prompt(text: str) -> list[dict[str, str]]:
    schema_hint = {
        "invoice_number": "string",
        "invoice_date": "YYYY-MM-DD",
        "supplier": "string",
        "buyer_nip": "string",
        "currency": "PLN/EUR/USD",
        "price_basis": "netto|brutto|mixed|unknown",
        "total_net": 0.0,
        "total_vat": 0.0,
        "total_gross": 0.0,
        "amount_due": 0.0,
        "confidence": 0.0,
        "items": [
            {
                "name": "string",
                "quantity": 0.0,
                "unit": "szt|mb|m|m2|kg|l|itp",
                "unit_price_net": 0.0,
                "unit_price_gross": 0.0,
                "total_price_net": 0.0,
                "total_price_gross": 0.0,
                "vat_rate": "23",
                "material_type": "plyta|okucie|okleina|profil|lakier|front|korpus|inne",
                "thickness_mm": "string",
            }
        ],
    }
    system = (
        "Jestes parserem faktur OCR. "
        "Zwroc TYLKO poprawny JSON, bez markdown. "
        "Nie mieszaj netto/brutto. "
        "Gdy nie wiesz: pusty string albo 0."
    )
    user = (
        "Wyodrebnij dane faktury z tekstu OCR.\n"
        "Wymagany format JSON:\n"
        f"{json.dumps(schema_hint, ensure_ascii=False)}\n\n"
        "Tekst OCR:\n"
        f"{text[:22000]}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _call_openai_chat(messages: list[dict[str, str]]) -> tuple[dict[str, Any] | None, str]:
    global _AI_BREAKER_REASON
    if _AI_BREAKER_REASON:
        return None, _AI_BREAKER_REASON

    api_key = str(os.environ.get("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        return None, "Brak OPENAI_API_KEY."

    enabled = str(os.environ.get("TECH_MODUL_INVOICE_AI_FALLBACK", "0") or "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None, "Fallback AI wylaczony (TECH_MODUL_INVOICE_AI_FALLBACK!=1)."

    model = str(os.environ.get("TECH_MODUL_INVOICE_AI_MODEL", "gpt-4o-mini") or "").strip() or "gpt-4o-mini"
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) == 429:
            _AI_BREAKER_REASON = "Fallback AI zatrzymany: limit API (HTTP 429)."
            return None, _AI_BREAKER_REASON
        return None, f"Blad polaczenia z API: HTTP {int(getattr(exc, 'code', 0) or 0)}"
    except Exception as exc:
        return None, f"Blad polaczenia z API: {exc}"

    try:
        parsed = json.loads(raw)
    except Exception as exc:
        return None, f"Niepoprawna odpowiedz API: {exc}"

    try:
        content = (
            parsed.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
    except Exception:
        content = ""
    obj = _extract_json_payload(str(content or ""))
    if obj is None:
        return None, "Model nie zwrocil poprawnego JSON."
    obj["_ai_model"] = model
    return obj, ""


def _build_items(items_payload: Any) -> tuple[InvoiceLineItem, ...]:
    if not isinstance(items_payload, list):
        return tuple()
    out: list[InvoiceLineItem] = []
    seen: set[tuple[str, str, str]] = set()
    for row in items_payload:
        if not isinstance(row, dict):
            continue
        name = _clean_name(str(row.get("name", "") or ""))
        if sum(1 for ch in name if ch.isalpha()) < 3:
            continue
        quantity = _to_float(row.get("quantity", 0.0))
        if quantity <= 0:
            quantity = 1.0
        unit = normalize_unit(str(row.get("unit", "") or ""))
        unit_net = _to_float(row.get("unit_price_net", 0.0))
        unit_gross = _to_float(row.get("unit_price_gross", 0.0))
        total_net = _to_float(row.get("total_price_net", 0.0))
        total_gross = _to_float(row.get("total_price_gross", 0.0))
        if total_net <= 0 and unit_net > 0:
            total_net = unit_net * quantity
        if total_gross <= 0 and unit_gross > 0:
            total_gross = unit_gross * quantity
        if total_net <= 0 and total_gross > 0:
            total_net = total_gross
        if total_gross <= 0 and total_net > 0:
            total_gross = total_net
        if unit_net <= 0 and total_net > 0 and quantity > 0:
            unit_net = total_net / quantity
        if unit_gross <= 0 and total_gross > 0 and quantity > 0:
            unit_gross = total_gross / quantity
        if unit_net <= 0 and unit_gross > 0:
            unit_net = unit_gross
        if unit_gross <= 0 and unit_net > 0:
            unit_gross = unit_net

        material_type = str(row.get("material_type", "") or "").strip().lower() or _guess_material_type(name)
        thickness = str(row.get("thickness_mm", "") or "").strip() or _extract_thickness(name)
        vat_rate = str(row.get("vat_rate", "") or "").strip().replace(",", ".")

        key = (
            name.lower(),
            f"{quantity:.3f}",
            f"{total_net:.2f}",
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(
            InvoiceLineItem(
                name=name,
                quantity=quantity,
                unit=unit,
                unit_price=unit_net,
                total_price=total_net,
                material_type=material_type or "plyta",
                thickness_mm=thickness,
                raw_line="ai_fallback",
                unit_price_net=unit_net,
                unit_price_gross=unit_gross,
                total_price_net=total_net,
                total_price_gross=total_gross,
                vat_amount=max(0.0, total_gross - total_net),
                vat_rate=vat_rate,
                price_basis="netto",
                parse_source="ai_fallback",
            )
        )
    return tuple(out)


def try_parse_invoice_text_with_ai(
    *,
    text: str,
    source_path: Path,
    base_result: InvoiceParseResult,
) -> tuple[InvoiceParseResult | None, str]:
    messages = _build_prompt(str(text or ""))
    data, err = _call_openai_chat(messages)
    if data is None:
        return None, err

    invoice_number = str(data.get("invoice_number", "") or "").strip()
    invoice_date = _normalize_date(str(data.get("invoice_date", "") or ""))
    supplier = str(data.get("supplier", "") or "").strip()
    buyer_nip = "".join(ch for ch in str(data.get("buyer_nip", "") or "") if ch.isdigit())
    currency = str(data.get("currency", "PLN") or "PLN").strip().upper() or "PLN"
    price_basis = str(data.get("price_basis", "") or "").strip().lower()
    if price_basis not in {"netto", "brutto", "mixed", "unknown"}:
        price_basis = "unknown"

    total_net = _to_float(data.get("total_net", 0.0))
    total_vat = _to_float(data.get("total_vat", 0.0))
    total_gross = _to_float(data.get("total_gross", 0.0))
    amount_due = _to_float(data.get("amount_due", 0.0))

    items = _build_items(data.get("items", []))
    if total_net <= 0:
        total_net = sum(max(0.0, row.total_price_net) for row in items)
    if total_gross <= 0:
        total_gross = sum(max(0.0, row.total_price_gross) for row in items) or total_net
    if total_vat <= 0 and total_gross >= total_net > 0:
        total_vat = total_gross - total_net
    if amount_due <= 0:
        amount_due = total_gross if total_gross > 0 else total_net

    confidence = _to_float(data.get("confidence", 0.0))
    confidence = min(1.0, max(0.0, confidence))
    ai_model = str(data.get("_ai_model", "") or "").strip()

    extraction_method = str(base_result.extraction_method or "").strip().lower()
    if extraction_method in {"ocr", "mixed", "text"}:
        extraction_method = f"{extraction_method}+ai"
    else:
        extraction_method = "ai"

    parsed = InvoiceParseResult(
        source_path=source_path,
        invoice_number=invoice_number or base_result.invoice_number,
        invoice_date=invoice_date or base_result.invoice_date,
        supplier=supplier or base_result.supplier,
        text_length=max(len(str(text or "")), int(base_result.text_length or 0)),
        items=items if items else base_result.items,
        price_basis=price_basis if price_basis != "unknown" else base_result.price_basis,
        total_net=total_net if total_net > 0 else base_result.total_net,
        total_vat=total_vat if total_vat > 0 else base_result.total_vat,
        total_gross=total_gross if total_gross > 0 else base_result.total_gross,
        amount_due=amount_due if amount_due > 0 else base_result.amount_due,
        currency=currency or base_result.currency,
        buyer_nip=buyer_nip or base_result.buyer_nip,
        is_msi_project_invoice=(buyer_nip == MSI_PROJECT_NIP) if buyer_nip else base_result.is_msi_project_invoice,
        extraction_method=extraction_method,
        ocr_confidence=max(float(base_result.ocr_confidence or 0.0), 0.0),
        supplier_template=base_result.supplier_template,
        ai_fallback_used=True,
        ai_confidence=confidence,
        ai_model=ai_model,
        ai_error="",
    )
    return parsed, ""
