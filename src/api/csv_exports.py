"""Phase 1 Safe Work Mode — read-only CSV export endpoints for core data.

Five SQLite-backed datasets and one JSON-backed dataset (work_time) are exposed
under `/api/export/csv/...` and `/api/export/json/...`. All endpoints are
read-only; they only execute SELECT queries (or read JSON files) and never
mutate the database. They are safe on prod.

Hooked into the main FastAPI app via `app.include_router(csv_export_router)`
in main_api.py.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from fastapi import APIRouter, HTTPException, Response

from src import safe_mode

csv_export_router = APIRouter(prefix="/api/export", tags=["export"])


def _csv_response(rows: Iterable[Sequence], headers: List[str], filename_stem: str) -> Response:
    """Build a CSV Response with UTF-8 BOM (Excel-friendly) and attachment header."""
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM so Excel reads UTF-8 correctly
    writer = csv.writer(buf, dialect="excel", lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_stem}_{timestamp}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _select_all(table: str, columns: List[str], order_by: str = "id") -> List[tuple]:
    """SELECT all rows from a table. Read-only. Honors safe_mode env-driven DB path."""
    db_path = safe_mode.get_db_path()
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if not existing_cols:
            raise HTTPException(status_code=404, detail=f"Table {table!r} does not exist")
        # Pick only the columns that actually exist (resilient to missing legacy columns).
        selected = [c for c in columns if c in existing_cols]
        if not selected:
            raise HTTPException(status_code=500, detail=f"No expected columns in {table!r}")
        order_clause = f"ORDER BY {order_by}" if order_by in existing_cols else ""
        cursor.execute(f"SELECT {', '.join(selected)} FROM {table} {order_clause}")
        rows = cursor.fetchall()
    # Pad to original column order (None for missing).
    col_index = {c: selected.index(c) if c in selected else None for c in columns}
    out: List[tuple] = []
    for r in rows:
        out.append(tuple(r[col_index[c]] if col_index[c] is not None else None for c in columns))
    return out


CLIENTS_COLUMNS = ["id", "name", "location", "address", "email", "phone", "type", "status"]
MATERIALS_COLUMNS = [
    "id", "name", "price_per_m2", "thickness", "material_code", "category",
    "material_kind", "unit", "stock_quantity", "min_stock", "purchase_type",
    "supplier", "wholesaler", "format_length_mm", "format_width_mm", "pack_size",
]
INVOICES_COLUMNS = [
    "id", "invoice_nr", "date", "nip", "supplier", "currency", "net_amount",
    "vat_amount", "gross_amount", "status", "source_filename", "parse_method",
    "parse_confidence", "duplicate_of_invoice_id", "created_at",
]
INVOICE_LINE_ITEMS_COLUMNS = [
    "id", "invoice_id", "line_no", "name_raw", "name_norm", "quantity", "unit",
    "unit_price_net", "unit_price_gross", "total_net", "total_gross", "vat_rate",
    "material_type", "thickness_mm", "review_status", "selected_material_id",
    "selected_material_name", "created_at", "updated_at",
]
CALENDAR_EVENTS_COLUMNS = [
    "id", "title", "date", "date_end", "all_day", "event_type", "station",
    "order_code", "worker_name", "client_name", "location", "notes", "status",
    "created_at",
]


@csv_export_router.get("/csv/clients")
def export_clients_csv() -> Response:
    rows = _select_all("clients", CLIENTS_COLUMNS, order_by="id")
    return _csv_response(rows, CLIENTS_COLUMNS, "clients")


@csv_export_router.get("/csv/materials")
def export_materials_csv() -> Response:
    rows = _select_all("materials", MATERIALS_COLUMNS, order_by="id")
    return _csv_response(rows, MATERIALS_COLUMNS, "materials")


@csv_export_router.get("/csv/invoices")
def export_invoices_csv() -> Response:
    rows = _select_all("invoices", INVOICES_COLUMNS, order_by="id")
    return _csv_response(rows, INVOICES_COLUMNS, "invoices")


@csv_export_router.get("/csv/invoice-line-items")
def export_invoice_line_items_csv() -> Response:
    rows = _select_all("invoice_line_items", INVOICE_LINE_ITEMS_COLUMNS, order_by="id")
    return _csv_response(rows, INVOICE_LINE_ITEMS_COLUMNS, "invoice_line_items")


@csv_export_router.get("/csv/calendar-events")
def export_calendar_events_csv() -> Response:
    rows = _select_all("calendar_events", CALENDAR_EVENTS_COLUMNS, order_by="id")
    return _csv_response(rows, CALENDAR_EVENTS_COLUMNS, "calendar_events")


@csv_export_router.get("/json/work-time")
def export_work_time_json() -> Response:
    """Work time is stored as a JSON document, not a SQL table. Stream it as-is.

    Phase 2 will likely migrate this to a table; until then the export is a
    direct dump of the raw JSON file (safe, read-only).
    """
    repo_root = safe_mode.get_repo_root()
    path = repo_root / "database" / "work_time.json"
    if not path.exists():
        # Empty document is fine — return an empty object rather than 404.
        body = json.dumps({}).encode("utf-8")
    else:
        body = path.read_bytes()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"work_time_{timestamp}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@csv_export_router.get("/status")
def export_status() -> dict:
    """Diagnostic: which env / DB is currently in use and which exports are available."""
    return {
        "safe_mode": safe_mode.env_summary(),
        "available": [
            "/api/export/csv/clients",
            "/api/export/csv/materials",
            "/api/export/csv/invoices",
            "/api/export/csv/invoice-line-items",
            "/api/export/csv/calendar-events",
            "/api/export/json/work-time",
        ],
    }
