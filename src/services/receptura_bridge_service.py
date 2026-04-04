from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return float(default)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_key(value: str) -> str:
    raw = "".join(ch for ch in str(value or "").upper() if ch.isalnum() or ch in ("_", "-"))
    return raw[:60] or "REC"


def quick_quote_id_from_receptura_id(
    receptura_id: str,
    *,
    existing_ids: set[str] | None = None,
) -> str:
    ids = {str(x or "").strip() for x in (existing_ids or set()) if str(x or "").strip()}
    seed = _normalize_key(f"QREC_{receptura_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    candidate = seed
    suffix = 2
    while candidate in ids:
        candidate = f"{seed}_{suffix}"
        suffix += 1
    return candidate


def build_quick_quote_entry_from_receptura(
    row: dict[str, Any],
    *,
    existing_ids: set[str] | None = None,
) -> dict[str, Any]:
    receptura_id = _normalize_text(row.get("id", ""))
    name = _normalize_text(row.get("name", "Material z receptury")) or "Material z receptury"
    unit = _normalize_text(row.get("unit", "szt")).lower() or "szt"
    qty = max(0.0, _safe_float(row.get("quantity", 0.0)))
    price_net = max(0.0, _safe_float(row.get("price_net", 0.0)))
    vat = max(0.0, _safe_float(row.get("vat_percent", 23.0), 23.0))
    value_net = round(price_net * (qty if qty > 0 else 1.0), 2)

    quick_id = quick_quote_id_from_receptura_id(receptura_id or "R", existing_ids=existing_ids)
    vat_text = f"{int(round(vat))}%" if abs(vat - round(vat)) < 0.0001 else f"{vat:.2f}%"

    section_title = f"{name} | {qty:.3f} {unit}" if qty > 0 else f"{name} | 1 {unit}"
    price_text = f"{value_net:.2f} zl"
    return {
        "id": quick_id,
        "client": "RECEPTURA",
        "price": price_text,
        "vat": vat_text,
        "margin": "0.00%",
        "sections": [
            {
                "id": receptura_id or "-",
                "title": section_title,
                "price": price_text,
            }
        ],
        "source": "receptura",
        "receptura_id": receptura_id,
    }


def catalog_material_key_from_receptura_id(receptura_id: str) -> str:
    raw_id = _normalize_key(receptura_id or "R")
    return f"REC_{raw_id}"


def _guess_material_group(material_type: str, name: str) -> str:
    low = f"{material_type} {name}".lower()
    if any(token in low for token in ("plecy", "hdf", "tyl")):
        return "back_board"
    if any(token in low for token in ("front", "drzwi", "drzwicz")):
        return "front_board"
    if any(token in low for token in ("korpus", "plyta", "mdf", "blat", "laminat")):
        return "carcass_board"
    return "carcass_board"


def _guess_thickness_mm(name: str, notes: str) -> float:
    text = f"{name} {notes}"
    match = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*mm\b", text.lower())
    if not match:
        return 18.0
    value = _safe_float(str(match.group(1) or "").replace(",", "."), 18.0)
    return value if value > 0 else 18.0


def build_catalog_material_from_receptura(row: dict[str, Any]) -> dict[str, Any]:
    receptura_id = _normalize_text(row.get("id", "")) or "R"
    name = _normalize_text(row.get("name", "")) or f"Receptura {receptura_id}"
    material_type = _normalize_text(row.get("material_type", "")) or "receptura"
    notes = _normalize_text(row.get("notes", ""))
    unit = _normalize_text(row.get("unit", "")).lower()
    price_net = max(0.0, _safe_float(row.get("price_net", 0.0)))

    return {
        "key": catalog_material_key_from_receptura_id(receptura_id),
        "name_pl": name,
        "thickness_mm": round(_guess_thickness_mm(name, notes), 2),
        "manufacturer": "Receptura",
        "material_type": material_type,
        "material_group": _guess_material_group(material_type, name),
        "finish_group": "",
        "price_pln_per_m2": round(price_net, 2),
        "price_note": f"Receptura {receptura_id} | jednostka: {unit or '-'}",
    }
