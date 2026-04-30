from __future__ import annotations

import asyncio
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api import main_api
from src.api.data_manager import TechModulDataManager


@contextmanager
def _patched_manager(manager: TechModulDataManager):
    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        yield
    finally:
        main_api.data_manager = previous_manager


def _import_invoice(
    manager: TechModulDataManager,
    *,
    payload_hash: str,
    invoice_nr: str = "FV/1/2026",
    invoice_date: str = "2026-04-22",
    supplier: str = "SUP-A",
    gross: float = 123.45,
    confidence: float = 0.95,
    unit: str = "szt",
) -> dict:
    return manager.import_invoice_with_lines(
        invoice_nr=invoice_nr,
        invoice_date=invoice_date,
        nip="1234567890",
        supplier=supplier,
        currency="PLN",
        total_net=100.0,
        total_vat=23.0,
        total_gross=gross,
        payload_hash=payload_hash,
        source_filename=f"{invoice_nr}.pdf",
        parse_method="test",
        parse_confidence=confidence,
        line_items=[
            {
                "name": "Pozycja testowa",
                "raw_line": "Pozycja testowa 1 szt",
                "quantity": 1.0,
                "unit": unit,
                "unit_price_net": 100.0,
                "unit_price_gross": 123.0,
                "total_price_net": 100.0,
                "total_price_gross": 123.0,
                "vat_rate": "23",
                "parse_source": "ocr",
                "confidence": confidence,
            }
        ],
    )


def test_duplicate_invoice_import_by_hash_and_signature(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "invoice_dedupe.db"))
    first = _import_invoice(manager, payload_hash="abc123")
    assert first["is_duplicate"] is False
    invoice_id = int(first["invoice_id"])
    assert invoice_id > 0
    assert len(manager.get_invoice_line_items(invoice_id)) == 1

    dup_hash = _import_invoice(manager, payload_hash="abc123")
    assert dup_hash["is_duplicate"] is True
    assert dup_hash["duplicate_reason"] == "payload_hash"
    assert int(dup_hash["invoice_id"]) == invoice_id

    dup_signature = _import_invoice(manager, payload_hash="other-hash")
    assert dup_signature["is_duplicate"] is True
    assert dup_signature["duplicate_reason"] == "invoice_signature"
    assert int(dup_signature["invoice_id"]) == invoice_id


def test_patch_line_blocks_confirm_without_selected_material_id(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "line_confirm_guard.db"))
    imported = _import_invoice(manager, payload_hash="h-1")
    invoice_id = int(imported["invoice_id"])
    line = manager.get_invoice_line_items(invoice_id)[0]
    line_id = int(line["id"])

    with _patched_manager(manager):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                main_api.patch_invoice_line_item(
                    invoice_id,
                    line_id,
                    main_api.InvoiceLineItemUpdate(review_status="confirmed"),
                )
            )
        assert exc.value.status_code == 400


def test_patch_line_blocks_low_confidence_and_confirm_export_skips_it(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "line_low_conf.db"))
    imported = _import_invoice(manager, payload_hash="h-low", confidence=0.2)
    invoice_id = int(imported["invoice_id"])
    line = manager.get_invoice_line_items(invoice_id)[0]
    line_id = int(line["id"])
    mat_id = manager.create_material(name="Klej test", price_per_m2=10.0, thickness=1, unit="szt")

    with _patched_manager(manager):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                main_api.patch_invoice_line_item(
                    invoice_id,
                    line_id,
                    main_api.InvoiceLineItemUpdate(
                        review_status="confirmed",
                        selected_material_id=mat_id,
                        selected_material_name="Klej test",
                    ),
                )
            )
        assert exc.value.status_code == 400

    # Even if status was forced outside API, confirm/export must still skip invalid line.
    ok = manager.update_invoice_line_item(
        invoice_id=invoice_id,
        line_item_id=line_id,
        updates={
            "review_status": "confirmed",
            "selected_material_id": mat_id,
            "selected_material_name": "Klej test",
        },
    )
    assert ok is True
    summary = manager.confirm_invoice_to_arrivals(invoice_id=invoice_id)
    assert int(summary["arrivals_created"]) == 0
    assert int(summary["price_history_written"]) == 0
    assert int(summary["skipped_lines"]) == 1


def test_confirm_export_is_idempotent_and_links_arrivals_and_price_history(tmp_path: Path) -> None:
    db_path = tmp_path / "confirm_idempotent.db"
    manager = TechModulDataManager(db_path=str(db_path))
    imported = manager.import_invoice_with_lines(
        invoice_nr="FV/2/2026",
        invoice_date="2026-04-22",
        nip="1234567890",
        supplier="SUP-B",
        currency="PLN",
        total_net=200.0,
        total_vat=46.0,
        total_gross=246.0,
        payload_hash="hash-2",
        source_filename="fv2.pdf",
        parse_method="test",
        parse_confidence=0.99,
        line_items=[
            {
                "name": "L1",
                "raw_line": "L1",
                "quantity": 2.0,
                "unit": "szt",
                "unit_price_net": 10.0,
                "unit_price_gross": 12.3,
                "total_price_net": 20.0,
                "total_price_gross": 24.6,
                "confidence": 0.9,
            },
            {
                "name": "L2",
                "raw_line": "L2",
                "quantity": 1.0,
                "unit": "szt",
                "unit_price_net": 30.0,
                "unit_price_gross": 36.9,
                "total_price_net": 30.0,
                "total_price_gross": 36.9,
                "confidence": 0.9,
            },
        ],
    )
    invoice_id = int(imported["invoice_id"])
    mat_id = manager.create_material(name="Material confirm", price_per_m2=15.0, thickness=18, unit="szt")
    for row in manager.get_invoice_line_items(invoice_id):
        manager.update_invoice_line_item(
            invoice_id=invoice_id,
            line_item_id=int(row["id"]),
            updates={
                "review_status": "confirmed",
                "selected_material_id": mat_id,
                "selected_material_name": "Material confirm",
            },
        )

    first = manager.confirm_invoice_to_arrivals(invoice_id=invoice_id)
    assert int(first["arrivals_created"]) == 2
    assert int(first["price_history_written"]) == 2
    assert str(first["status"]) == "CONFIRMED"

    second = manager.confirm_invoice_to_arrivals(invoice_id=invoice_id)
    assert int(second["arrivals_created"]) == 0
    assert int(second["price_history_written"]) == 0
    assert int(second["skipped_lines"]) == 2
    assert str(second["status"]) == "CONFIRMED"

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM arrivals WHERE invoice_id = ?", (invoice_id,))
        assert int(cur.fetchone()[0]) == 2
        cur.execute(
            "SELECT COUNT(*) FROM arrivals WHERE invoice_id = ? AND invoice_line_item_id IS NOT NULL",
            (invoice_id,),
        )
        assert int(cur.fetchone()[0]) == 2
        cur.execute("SELECT COUNT(*) FROM price_history WHERE invoice_id = ?", (invoice_id,))
        assert int(cur.fetchone()[0]) == 2


def test_invoice_status_transitions_partial_then_confirmed(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "invoice_status.db"))
    imported = manager.import_invoice_with_lines(
        invoice_nr="FV/3/2026",
        invoice_date="2026-04-22",
        nip="1234567890",
        supplier="SUP-C",
        currency="PLN",
        total_net=300.0,
        total_vat=69.0,
        total_gross=369.0,
        payload_hash="hash-3",
        source_filename="fv3.pdf",
        parse_method="test",
        parse_confidence=0.99,
        line_items=[
            {
                "name": "A",
                "raw_line": "A",
                "quantity": 1.0,
                "unit": "szt",
                "unit_price_net": 10.0,
                "unit_price_gross": 12.3,
                "total_price_net": 10.0,
                "total_price_gross": 12.3,
                "confidence": 0.9,
            },
            {
                "name": "B",
                "raw_line": "B",
                "quantity": 1.0,
                "unit": "szt",
                "unit_price_net": 20.0,
                "unit_price_gross": 24.6,
                "total_price_net": 20.0,
                "total_price_gross": 24.6,
                "confidence": 0.9,
            },
        ],
    )
    invoice_id = int(imported["invoice_id"])
    mat_id = manager.create_material(name="Material status", price_per_m2=20.0, thickness=18, unit="szt")
    lines = manager.get_invoice_line_items(invoice_id)
    first_line_id = int(lines[0]["id"])
    second_line_id = int(lines[1]["id"])

    manager.update_invoice_line_item(
        invoice_id=invoice_id,
        line_item_id=first_line_id,
        updates={
            "review_status": "confirmed",
            "selected_material_id": mat_id,
            "selected_material_name": "Material status",
        },
    )
    partial = manager.confirm_invoice_to_arrivals(invoice_id=invoice_id)
    assert str(partial["status"]) == "PARTIAL"

    manager.update_invoice_line_item(
        invoice_id=invoice_id,
        line_item_id=second_line_id,
        updates={
            "review_status": "confirmed",
            "selected_material_id": mat_id,
            "selected_material_name": "Material status",
        },
    )
    done = manager.confirm_invoice_to_arrivals(invoice_id=invoice_id, line_item_ids=[second_line_id])
    assert str(done["status"]) == "CONFIRMED"

