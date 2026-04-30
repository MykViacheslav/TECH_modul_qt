from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVOICES_JSON = ROOT / "data" / "invoices.json"
DB_PATH = ROOT / "database" / "tech_modul.db"
FAKTURY_MARK = "\\faktury\\"


@dataclass
class ImportStats:
    invoices_added: int = 0
    invoices_skipped: int = 0
    materials_created: int = 0
    arrivals_added: int = 0
    line_skipped_noise: int = 0
    line_skipped_price: int = 0
    line_skipped_empty: int = 0


def _safe_float(value: Any) -> float:
    text = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _normalize_name(name: str) -> str:
    value = re.sub(r"\s+", " ", str(name or "").strip())
    return value.strip(" -;,.")


def _looks_like_noise_line(name: str) -> bool:
    low = str(name or "").strip().lower()
    if not low:
        return True
    noise_tokens = (
        "ogółem",
        "ogolem",
        "razem",
        "w tym",
        "podatek",
        "vat",
        "kwota",
        "należność",
        "naleznosc",
        "do zapłaty",
        "do zaplaty",
    )
    if any(tok in low for tok in noise_tokens):
        return True
    # Czynsze i wynajem nie są materiałem magazynowym.
    if "czynsz" in low or "wynajem" in low:
        return True
    return False


def _extract_thickness(name: str, raw_thickness: Any) -> int:
    direct = _safe_int(raw_thickness)
    if direct > 0:
        return direct
    low = str(name or "").lower()
    mm = re.search(r"(\d{1,2})\s*mm\b", low)
    if mm:
        return _safe_int(mm.group(1))
    # Nazwy płyt często kończą się "_18" albo "_18 "
    end = re.search(r"(?:_|\\b)(\d{1,2})(?:\\b|$)", low)
    if end:
        val = _safe_int(end.group(1))
        if 1 <= val <= 60:
            return val
    return 18


def _map_category(material_type: str, name: str) -> str:
    low = f"{str(material_type or '').lower()} {str(name or '').lower()}"
    if any(t in low for t in ("lakier", "farba", "bejca", "klej", "okleina", "folia", "aduro", "arova", "pigmopur")):
        return "finishes"
    if any(t in low for t in ("okuc", "zawias", "prowadnic", "uchwyt", "wkret", "śruba", "sruba", "movento", "tandem", "blum")):
        return "hardware"
    return "boards"


def _pick_unit(item: dict[str, Any]) -> str:
    unit = str(item.get("unit", "") or "").strip().lower()
    if unit:
        return unit
    return "szt"


def _pick_unit_price_net(item: dict[str, Any]) -> float:
    val = _safe_float(item.get("unit_price_net", 0.0))
    if val > 0:
        return val
    val = _safe_float(item.get("unit_price", 0.0))
    if val > 0:
        return val
    qty = max(_safe_float(item.get("quantity", 0.0)), 1.0)
    total = _safe_float(item.get("total_price_net", 0.0))
    if total <= 0:
        total = _safe_float(item.get("total_price", 0.0))
    return total / qty if total > 0 else 0.0


def _pick_line_total_gross(item: dict[str, Any]) -> float:
    gross = _safe_float(item.get("total_price_gross", 0.0))
    if gross > 0:
        return gross
    gross = _safe_float(item.get("total_price", 0.0))
    if gross > 0:
        return gross
    qty = max(_safe_float(item.get("quantity", 0.0)), 1.0)
    unit_gross = _safe_float(item.get("unit_price_gross", 0.0))
    if unit_gross > 0:
        return qty * unit_gross
    unit_net = _pick_unit_price_net(item)
    return qty * unit_net if unit_net > 0 else 0.0


def _load_manual_faktury() -> list[dict[str, Any]]:
    if not INVOICES_JSON.exists():
        raise FileNotFoundError(f"Nie znaleziono {INVOICES_JSON}")
    payload = json.loads(INVOICES_JSON.read_text(encoding="utf-8"))
    rows = payload.get("invoices", [])
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source", "") or "").strip().lower()
        source_path = str(row.get("source_path", "") or "").strip().lower()
        if source != "manual_pdf":
            continue
        if FAKTURY_MARK not in source_path:
            continue
        out.append(row)
    return out


def _invoice_exists(conn: sqlite3.Connection, nr: str, date: str, gross: float) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM invoices WHERE invoice_nr = ? AND date = ? AND ABS(gross_amount - ?) < 0.01 LIMIT 1",
        (nr, date, float(gross)),
    )
    return cur.fetchone() is not None


def _find_or_create_material(
    conn: sqlite3.Connection,
    *,
    name: str,
    price_net: float,
    thickness: int,
    category: str,
    unit: str,
    supplier: str,
    wholesaler: str,
) -> tuple[int, bool]:
    cur = conn.cursor()
    cur.execute("SELECT id FROM materials WHERE name = ? LIMIT 1", (name,))
    row = cur.fetchone()
    if row:
        return int(row[0]), False
    cur.execute(
        """
        INSERT INTO materials
        (name, price_per_m2, thickness, category, unit, is_library, stock_quantity, purchase_type, supplier, wholesaler, texture_url, color_hex)
        VALUES (?, ?, ?, ?, ?, 0, 0.0, 'invoice', ?, ?, '', '#ffffff')
        """,
        (name, float(price_net), int(thickness), category, unit, str(supplier or "").strip(), str(wholesaler or "").strip()),
    )
    return int(cur.lastrowid), True


def _add_arrival(
    conn: sqlite3.Connection,
    *,
    material_id: int,
    quantity: float,
    unit: str,
    document_nr: str,
    price_total: float,
    date: str,
    supplier: str,
    wholesaler: str,
) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM arrivals
        WHERE material_id = ?
          AND ABS(quantity - ?) < 0.0001
          AND unit = ?
          AND document_nr = ?
          AND (supplier = ? OR supplier = '' OR ? = '')
          AND (wholesaler = ? OR wholesaler = '' OR ? = '')
          AND ABS(price_total - ?) < 0.01
          AND date = ?
        LIMIT 1
        """,
        (
            int(material_id),
            float(quantity),
            unit,
            document_nr,
            str(supplier or "").strip(),
            str(supplier or "").strip(),
            str(wholesaler or "").strip(),
            str(wholesaler or "").strip(),
            float(price_total),
            date,
        ),
    )
    if cur.fetchone() is not None:
        return False

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO arrivals (material_id, quantity, unit, purchase_type, document_nr, supplier, wholesaler, price_total, date)
        VALUES (?, ?, ?, 'invoice', ?, ?, ?, ?, ?)
        """,
        (int(material_id), float(quantity), unit, document_nr, str(supplier or "").strip(), str(wholesaler or "").strip(), float(price_total), date),
    )
    cur.execute(
        "UPDATE materials SET stock_quantity = stock_quantity + ?, is_library = 0 WHERE id = ?",
        (float(quantity), int(material_id)),
    )
    return True


def run_import() -> dict[str, Any]:
    rows = _load_manual_faktury()
    stats = ImportStats()
    imported_invoices: list[str] = []
    category_counter: dict[str, int] = {"boards": 0, "hardware": 0, "finishes": 0}

    with sqlite3.connect(DB_PATH) as conn:
        for row in rows:
            invoice_number = str(row.get("invoice_number", "") or "").strip()
            attachment_name = str(row.get("attachment_name", "") or "").strip()
            supplier = _normalize_name(str(row.get("supplier", "") or "").strip())
            invoice_date = str(row.get("invoice_date", "") or "").strip()
            if not invoice_date:
                invoice_date = str(row.get("received_at", "") or "")[:10]
            if not invoice_number:
                invoice_number = attachment_name or str(row.get("invoice_id", "") or "").strip()[:12]
            if not supplier:
                supplier = "Nieznany dostawca"

            total_net = _safe_float(row.get("total_net", 0.0))
            total_vat = _safe_float(row.get("total_vat", 0.0))
            total_gross = _safe_float(row.get("total_gross", 0.0))
            buyer_nip = str(row.get("buyer_nip", "") or "").strip()
            folder = f"Faktury/{supplier}"

            if _invoice_exists(conn, invoice_number, invoice_date, total_gross):
                stats.invoices_skipped += 1
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO invoices (invoice_nr, date, nip, net_amount, vat_amount, gross_amount, folder, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'IMPORTED')
                    """,
                    (invoice_number, invoice_date, buyer_nip, total_net, total_vat, total_gross, folder),
                )
                stats.invoices_added += 1
                imported_invoices.append(invoice_number)

            items = row.get("items", []) or []
            for item in items:
                if not isinstance(item, dict):
                    stats.line_skipped_empty += 1
                    continue
                name = _normalize_name(str(item.get("name", "") or "").strip())
                if not name:
                    stats.line_skipped_empty += 1
                    continue
                if _looks_like_noise_line(name):
                    stats.line_skipped_noise += 1
                    continue

                qty = _safe_float(item.get("quantity", 0.0))
                if qty <= 0:
                    qty = 1.0
                unit = _pick_unit(item)
                unit_price_net = _pick_unit_price_net(item)
                if unit_price_net <= 0:
                    stats.line_skipped_price += 1
                    continue
                line_total_gross = _pick_line_total_gross(item)
                thickness = _extract_thickness(name, item.get("thickness_mm", ""))
                material_type = str(item.get("material_type", "") or "").strip().lower()
                category = _map_category(material_type, name)

                material_id, created = _find_or_create_material(
                    conn,
                    name=name,
                    price_net=unit_price_net,
                    thickness=thickness,
                    category=category,
                    unit=unit,
                    supplier=supplier,
                    wholesaler=supplier,
                )
                if created:
                    stats.materials_created += 1
                category_counter[category] = category_counter.get(category, 0) + 1

                doc_nr = f"{invoice_number} | {supplier}"
                inserted = _add_arrival(
                    conn,
                    material_id=material_id,
                    quantity=qty,
                    unit=unit,
                    document_nr=doc_nr[:250],
                    price_total=line_total_gross if line_total_gross > 0 else unit_price_net * qty,
                    date=invoice_date or "",
                    supplier=supplier,
                    wholesaler=supplier,
                )
                if inserted:
                    stats.arrivals_added += 1

        conn.commit()

    return {
        "db_path": str(DB_PATH),
        "source_invoices": len(rows),
        "stats": stats.__dict__,
        "category_lines_added": category_counter,
        "imported_invoices_preview": imported_invoices[:20],
    }


if __name__ == "__main__":
    result = run_import()
    print(json.dumps(result, ensure_ascii=False, indent=2))
