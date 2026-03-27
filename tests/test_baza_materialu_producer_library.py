from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.baza_materialu.tab_baza_materialu import TabBazaMaterialu


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _find_row(table, column: int, expected: str) -> int:
    for row in range(table.rowCount()):
        item = table.item(row, column)
        text = str(item.text() if item is not None else "")
        if text == expected:
            return row
    return -1


@pytest.mark.gui
def test_baza_materialu_imports_selected_rows_from_producer_library(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()
    before_rows = w.tbl.rowCount()

    w.btn_toggle_library.setChecked(True)
    producer_idx = w.cb_library_producer.findData("EGGER")
    assert producer_idx >= 0
    w.cb_library_producer.setCurrentIndex(producer_idx)

    assert w.tbl_library.rowCount() >= 1
    w.tbl_library.selectRow(0)
    w.btn_import_library_selected.click()

    assert w.tbl.rowCount() == before_rows + 1
    imported_row = _find_row(w.tbl, 3, "EGGER")
    assert imported_row >= 0
    assert str(w.tbl.item(imported_row, 2).text() if w.tbl.item(imported_row, 2) is not None else "").strip()
    w.close()


@pytest.mark.gui
def test_baza_materialu_import_from_library_creates_missing_type(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()
    existing_types = [str(w.tbl_types.item(r, 1).text() if w.tbl_types.item(r, 1) is not None else "").strip() for r in range(w.tbl_types.rowCount())]
    assert "system_przesuwny" not in existing_types

    w.btn_toggle_library.setChecked(True)
    producer_idx = w.cb_library_producer.findData("SEVROLL")
    assert producer_idx >= 0
    w.cb_library_producer.setCurrentIndex(producer_idx)

    assert w.tbl_library.rowCount() >= 1
    w.btn_import_library_all_visible.click()

    types_after = [str(w.tbl_types.item(r, 1).text() if w.tbl_types.item(r, 1) is not None else "").strip() for r in range(w.tbl_types.rowCount())]
    assert "system_przesuwny" in types_after
    imported_row = _find_row(w.tbl, 3, "SEVROLL")
    assert imported_row >= 0
    assert str(w.tbl.item(imported_row, 1).text() if w.tbl.item(imported_row, 1) is not None else "") == "system_przesuwny"
    w.close()
