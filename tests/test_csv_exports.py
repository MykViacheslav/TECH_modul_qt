"""Tests for src/api/csv_exports.py — Phase 1 emergency CSV export endpoints.

Each test uses the `isolated_db_path` conftest fixture, which sets
`TECH_MODUL_DB_PATH` to a tmp_path DB. The export endpoints call
`safe_mode.get_db_path()` which honors that override, so we get full
isolation per test without touching prod data.

For tables that aren't auto-created by the legacy data_manager (e.g.,
`calendar_events`), we create them inline with the same column set the
exporter expects.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api import csv_exports


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_csv(response) -> list[list[str]]:
    """Decode a CSV Response body (with BOM) into a list of rows."""
    body = response.body
    assert body[:3] == b"\xef\xbb\xbf", "CSV must start with UTF-8 BOM for Excel"
    text = body.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _create_clients(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                address TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                type TEXT DEFAULT 'person',
                status TEXT DEFAULT 'active'
            )
            """
        )


def _create_materials(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price_per_m2 REAL,
                thickness INTEGER,
                material_code TEXT DEFAULT '',
                category TEXT DEFAULT 'boards',
                material_kind TEXT DEFAULT 'other',
                unit TEXT DEFAULT 'm2',
                stock_quantity REAL DEFAULT 0.0,
                min_stock REAL DEFAULT 0.0,
                purchase_type TEXT DEFAULT 'nothing',
                supplier TEXT DEFAULT '',
                wholesaler TEXT DEFAULT '',
                format_length_mm REAL DEFAULT 0.0,
                format_width_mm REAL DEFAULT 0.0,
                pack_size REAL DEFAULT 0.0
            )
            """
        )


def _create_invoices(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_nr TEXT,
                date TEXT,
                nip TEXT,
                supplier TEXT DEFAULT '',
                currency TEXT DEFAULT 'PLN',
                net_amount REAL DEFAULT 0,
                vat_amount REAL DEFAULT 0,
                gross_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'DRAFT',
                source_filename TEXT DEFAULT '',
                parse_method TEXT DEFAULT '',
                parse_confidence REAL DEFAULT 0.0,
                duplicate_of_invoice_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _create_invoice_line_items(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                line_no INTEGER DEFAULT 0,
                name_raw TEXT DEFAULT '',
                name_norm TEXT DEFAULT '',
                quantity REAL DEFAULT 0.0,
                unit TEXT DEFAULT '',
                unit_price_net REAL DEFAULT 0.0,
                unit_price_gross REAL DEFAULT 0.0,
                total_net REAL DEFAULT 0.0,
                total_gross REAL DEFAULT 0.0,
                vat_rate TEXT DEFAULT '',
                material_type TEXT DEFAULT '',
                thickness_mm TEXT DEFAULT '',
                review_status TEXT DEFAULT 'needs_review',
                selected_material_id INTEGER,
                selected_material_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _create_calendar_events(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT,
                date_end TEXT,
                all_day INTEGER DEFAULT 0,
                event_type TEXT,
                station TEXT,
                order_code TEXT,
                worker_name TEXT,
                client_name TEXT,
                location TEXT,
                notes TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---------------------------------------------------------------------------
# Clients export
# ---------------------------------------------------------------------------

def test_export_clients_returns_csv_with_seeded_row(isolated_db_path: Path):
    _create_clients(isolated_db_path)
    with sqlite3.connect(str(isolated_db_path)) as conn:
        conn.execute(
            "INSERT INTO clients (name, location, email, phone, type, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Acme Sp. z o.o.", "Warszawa", "biuro@acme.pl", "123456789", "company", "active"),
        )
        conn.commit()

    response = csv_exports.export_clients_csv()
    assert response.status_code == 200
    assert response.media_type.startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "clients_" in response.headers["content-disposition"]

    rows = _decode_csv(response)
    assert rows[0] == csv_exports.CLIENTS_COLUMNS
    assert len(rows) == 2
    data = dict(zip(rows[0], rows[1]))
    assert data["name"] == "Acme Sp. z o.o."
    assert data["location"] == "Warszawa"
    assert data["email"] == "biuro@acme.pl"


def test_export_clients_empty_table_returns_header_only(isolated_db_path: Path):
    _create_clients(isolated_db_path)

    response = csv_exports.export_clients_csv()
    rows = _decode_csv(response)
    assert rows == [csv_exports.CLIENTS_COLUMNS]


def test_export_clients_missing_db_returns_empty(isolated_db_path: Path):
    # Do not create any tables; DB file does not exist yet.
    assert not isolated_db_path.exists()
    response = csv_exports.export_clients_csv()
    rows = _decode_csv(response)
    # No header either when the DB is missing — the helper returns [] rows.
    # The CSV writer still writes the header row, so we expect only the header.
    assert rows[0] == csv_exports.CLIENTS_COLUMNS
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Materials export
# ---------------------------------------------------------------------------

def test_export_materials_returns_csv(isolated_db_path: Path):
    _create_materials(isolated_db_path)
    with sqlite3.connect(str(isolated_db_path)) as conn:
        conn.execute(
            "INSERT INTO materials (name, price_per_m2, thickness, material_code, supplier, unit) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Plyta MDF 18mm", 99.5, 18, "MDF-18", "Egger", "m2"),
        )
        conn.commit()

    response = csv_exports.export_materials_csv()
    rows = _decode_csv(response)
    assert rows[0] == csv_exports.MATERIALS_COLUMNS
    data = dict(zip(rows[0], rows[1]))
    assert data["name"] == "Plyta MDF 18mm"
    assert float(data["price_per_m2"]) == 99.5
    assert data["material_code"] == "MDF-18"
    assert data["supplier"] == "Egger"


# ---------------------------------------------------------------------------
# Invoices export
# ---------------------------------------------------------------------------

def test_export_invoices_returns_csv(isolated_db_path: Path):
    _create_invoices(isolated_db_path)
    with sqlite3.connect(str(isolated_db_path)) as conn:
        conn.execute(
            "INSERT INTO invoices (invoice_nr, date, nip, supplier, net_amount, vat_amount, gross_amount, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("FV/2026/01/001", "2026-01-15", "1234567890", "Hurtownia X", 1000.0, 230.0, 1230.0, "PAID"),
        )
        conn.commit()

    response = csv_exports.export_invoices_csv()
    rows = _decode_csv(response)
    assert rows[0] == csv_exports.INVOICES_COLUMNS
    data = dict(zip(rows[0], rows[1]))
    assert data["invoice_nr"] == "FV/2026/01/001"
    assert data["nip"] == "1234567890"
    assert float(data["gross_amount"]) == 1230.0


# ---------------------------------------------------------------------------
# Invoice line items export
# ---------------------------------------------------------------------------

def test_export_invoice_line_items_returns_csv(isolated_db_path: Path):
    _create_invoices(isolated_db_path)
    _create_invoice_line_items(isolated_db_path)
    with sqlite3.connect(str(isolated_db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO invoices (invoice_nr, date, supplier) VALUES (?, ?, ?)",
            ("FV/2026/01/001", "2026-01-15", "Hurtownia X"),
        )
        invoice_id = cur.lastrowid
        cur.execute(
            "INSERT INTO invoice_line_items (invoice_id, line_no, name_raw, quantity, unit, unit_price_net, total_net) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (invoice_id, 1, "Plyta MDF 18mm", 5.0, "m2", 99.5, 497.5),
        )
        conn.commit()

    response = csv_exports.export_invoice_line_items_csv()
    rows = _decode_csv(response)
    assert rows[0] == csv_exports.INVOICE_LINE_ITEMS_COLUMNS
    data = dict(zip(rows[0], rows[1]))
    assert data["name_raw"] == "Plyta MDF 18mm"
    assert float(data["quantity"]) == 5.0
    assert float(data["total_net"]) == 497.5


# ---------------------------------------------------------------------------
# Calendar events export
# ---------------------------------------------------------------------------

def test_export_calendar_events_returns_csv(isolated_db_path: Path):
    _create_calendar_events(isolated_db_path)
    with sqlite3.connect(str(isolated_db_path)) as conn:
        conn.execute(
            "INSERT INTO calendar_events (title, date, event_type, station, status) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Montaz Kuchni", "2026-05-04", "montaz", "MONTAZ", "PLANNED"),
        )
        conn.commit()

    response = csv_exports.export_calendar_events_csv()
    rows = _decode_csv(response)
    assert rows[0] == csv_exports.CALENDAR_EVENTS_COLUMNS
    data = dict(zip(rows[0], rows[1]))
    assert data["title"] == "Montaz Kuchni"
    assert data["date"] == "2026-05-04"
    assert data["event_type"] == "montaz"


# ---------------------------------------------------------------------------
# Work time JSON export
# ---------------------------------------------------------------------------

def test_export_work_time_returns_existing_json(monkeypatch, tmp_path):
    # Use a fake repo root so we don't read or modify the real database/work_time.json.
    fake_root = tmp_path / "fakeroot"
    (fake_root / "database").mkdir(parents=True)
    sample = {"sessions": [{"worker": "Anna", "minutes": 30}]}
    (fake_root / "database" / "work_time.json").write_text(json.dumps(sample), encoding="utf-8")

    from src import safe_mode
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)

    response = csv_exports.export_work_time_json()
    assert response.status_code == 200
    assert response.media_type == "application/json"
    assert "work_time_" in response.headers["content-disposition"]
    parsed = json.loads(response.body.decode("utf-8"))
    assert parsed == sample


def test_export_work_time_returns_empty_when_missing(monkeypatch, tmp_path):
    fake_root = tmp_path / "fakeroot"
    (fake_root / "database").mkdir(parents=True)
    # Note: no work_time.json file is created.

    from src import safe_mode
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)

    response = csv_exports.export_work_time_json()
    assert response.status_code == 200
    assert json.loads(response.body.decode("utf-8")) == {}


# ---------------------------------------------------------------------------
# Status diagnostic
# ---------------------------------------------------------------------------

def test_export_status_reports_test_env_and_lists_endpoints():
    payload = csv_exports.export_status()
    assert payload["safe_mode"]["env"] == "test"
    assert payload["safe_mode"]["pytest_active"] is True
    assert "/api/export/csv/clients" in payload["available"]
    assert "/api/export/csv/materials" in payload["available"]
    assert "/api/export/csv/invoices" in payload["available"]
    assert "/api/export/csv/invoice-line-items" in payload["available"]
    assert "/api/export/csv/calendar-events" in payload["available"]
    assert "/api/export/json/work-time" in payload["available"]


# ---------------------------------------------------------------------------
# Resilience: missing table should 404, not crash
# ---------------------------------------------------------------------------

def test_export_raises_404_when_table_missing(isolated_db_path: Path):
    # Touch the DB but do not create the clients table.
    sqlite3.connect(str(isolated_db_path)).close()
    with pytest.raises(HTTPException) as exc:
        csv_exports.export_clients_csv()
    assert exc.value.status_code == 404
