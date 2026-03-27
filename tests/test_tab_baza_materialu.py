from __future__ import annotations

import json
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QComboBox

from src.tabs.baza_materialu.tab_baza_materialu import BLOCKED_MATERIAL_TYPES, TabBazaMaterialu


def _app():
    return QApplication.instance() or QApplication([])


def _cell_text(table, row: int, col: int) -> str:
    widget = table.cellWidget(row, col)
    if isinstance(widget, QComboBox):
        return str(widget.currentText() or "")
    item = table.item(row, col)
    return str(item.text() if item is not None else "")


def _find_row_by_cell_text(table, column: int, expected: str) -> int:
    for row in range(table.rowCount()):
        if _cell_text(table, row, column) == expected:
            return row
    return -1


@pytest.mark.gui
def test_baza_materialu_loads_default_types_when_store_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    assert w.tbl_types.rowCount() > 0

    loaded_types = []
    for row in range(w.tbl_types.rowCount()):
        loaded_types.append(str(w.tbl_types.item(row, 1).text()).strip())

    assert "korpus" in loaded_types
    assert "front" in loaded_types
    assert "plecy" in loaded_types
    assert "lakier" in loaded_types


@pytest.mark.gui
def test_add_new_type_updates_types_table_and_material_combo(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    before_count = w.tbl_types.rowCount()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("test_typ")
    w.ed_type_nazwa.setText("Test Typ")
    w._confirm_type_entry()

    assert w.tbl_types.rowCount() == before_count + 1

    loaded_types = []
    for row in range(w.tbl_types.rowCount()):
        loaded_types.append(str(w.tbl_types.item(row, 1).text()).strip())

    assert "test_typ" in loaded_types
    assert "test_typ" in [w.cb_mat_typ.itemText(i) for i in range(w.cb_mat_typ.count())]


@pytest.mark.gui
def test_duplicate_type_is_not_added_twice(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    initial_types = []
    for row in range(w.tbl_types.rowCount()):
        initial_types.append(str(w.tbl_types.item(row, 1).text()).strip())

    assert "korpus" in initial_types

    before_count = w.tbl_types.rowCount()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("korpus")
    w.ed_type_nazwa.setText("Korpus duplikat")
    w._confirm_type_entry()

    assert w.tbl_types.rowCount() == before_count


@pytest.mark.gui
def test_blocked_type_inne_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()
    before_count = w.tbl_types.rowCount()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("inne")
    w.ed_type_nazwa.setText("Inne")
    w._confirm_type_entry()

    assert w.tbl_types.rowCount() == before_count


@pytest.mark.gui
def test_add_material_row_creates_row_and_assigns_combo_type(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    before_count = w.tbl.rowCount()

    w._show_material_entry_bar()
    w.cb_mat_typ.setCurrentText("korpus")
    w.ed_mat_nazwa.setText("Plyta Egger")
    w.ed_mat_producent.setText("Egger")
    w.ed_mat_szer.setText("2070")
    w.ed_mat_dlug.setText("2800")
    w.ed_mat_grub.setText("18")
    w.ed_mat_param.setText("U999 ST2")
    w.ed_mat_cena.setText("299")
    w.ed_mat_ilosc.setText("10")
    w.ed_mat_spisano.setText("2")
    w.ed_mat_magazyn.setText("8")
    w.ed_mat_pracownik.setText("Jan")
    w.ed_mat_data.setText("2026-03-22")
    w.ed_mat_zakup.setText("Tak")
    w.ed_mat_faktura.setText("FV/1/03/2026")
    w.ed_mat_data_zakupu.setText("2026-03-20")
    w._confirm_material_entry()

    assert w.tbl.rowCount() == before_count + 1

    found = False
    for row in range(w.tbl.rowCount()):
        if _cell_text(w.tbl, row, 2) == "Plyta Egger":
            found = True
            assert _cell_text(w.tbl, row, 1) == "korpus"
            assert _cell_text(w.tbl, row, 3) == "Egger"
            assert _cell_text(w.tbl, row, 9) == "10"
            break

    assert found, "Nie znaleziono dodanego materiału w tabeli"


@pytest.mark.gui
def test_quantity_warning_marks_cells_when_stock_is_lower_than_required(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._insert_material_row(
        [
            "M0001",
            "korpus",
            "Plyta test",
            "Test",
            "2070",
            "2800",
            "18",
            "Param",
            "100",
            "10",
            "8",
            "4",
            "Jan",
            "2026-03-22",
            "Tak",
            "FV-1",
            "2026-03-21",
        ]
    )

    target_row = -1
    for row in range(w.tbl.rowCount()):
        if _cell_text(w.tbl, row, 0) == "M0001":
            target_row = row
            break

    assert target_row >= 0

    item_spisano = w.tbl.item(target_row, 10)
    item_magazyn = w.tbl.item(target_row, 11)

    assert item_spisano is not None
    assert item_magazyn is not None

    bg_spisano = item_spisano.data(Qt.ItemDataRole.BackgroundRole)
    bg_magazyn = item_magazyn.data(Qt.ItemDataRole.BackgroundRole)

    assert bg_spisano is not None
    assert bg_magazyn is not None


@pytest.mark.gui
def test_filter_hides_non_matching_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._insert_material_row(
        [
            "M0001",
            "korpus",
            "Plyta Egger",
            "Egger",
            "2070",
            "2800",
            "18",
            "",
            "100",
            "4",
            "0",
            "4",
            "Jan",
            "2026-03-22",
            "Tak",
            "FV-1",
            "2026-03-21",
        ]
    )
    w._insert_material_row(
        [
            "M0002",
            "lakier",
            "Lakier biały",
            "ICA",
            "",
            "",
            "",
            "",
            "50",
            "3",
            "0",
            "3",
            "Anna",
            "2026-03-22",
            "Tak",
            "FV-2",
            "2026-03-21",
        ]
    )

    w.filter_panel.setVisible(True)
    w._filter_inputs[2].setText("Egger")
    w._apply_filters()

    visible_rows = []
    hidden_rows = []
    for row in range(w.tbl.rowCount()):
        if w.tbl.isRowHidden(row):
            hidden_rows.append(row)
        else:
            visible_rows.append(row)

    assert len(visible_rows) == 1
    assert _cell_text(w.tbl, visible_rows[0], 2) == "Plyta Egger"
    assert len(hidden_rows) >= 1


@pytest.mark.gui
def test_save_store_creates_json_file_with_types_and_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._insert_material_row(
        [
            "M0001",
            "korpus",
            "Plyta Egger",
            "Egger",
            "2070",
            "2800",
            "18",
            "U999",
            "299",
            "5",
            "1",
            "4",
            "Jan",
            "2026-03-22",
            "Tak",
            "FV-10",
            "2026-03-21",
        ]
    )

    w._save_store()

    store_path = Path(tmp_path) / "baza_materialu.json"
    assert store_path.exists()

    raw = json.loads(store_path.read_text(encoding="utf-8"))
    assert "types" in raw
    assert "rows" in raw
    assert isinstance(raw["types"], list)
    assert isinstance(raw["rows"], list)
    assert len(raw["rows"]) >= 1


@pytest.mark.gui
def test_load_store_restores_saved_material_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    store_path = Path(tmp_path) / "baza_materialu.json"
    payload = {
        "types": [
            {"id": "T0001", "typ": "korpus", "nazwa": "Korpus"},
            {"id": "T0002", "typ": "lakier", "nazwa": "Lakier"},
        ],
        "rows": [
            {
                "id": "M0001",
                "typ": "lakier",
                "nazwa": "Lakier test",
                "producent": "ICA",
                "szerokosc": "",
                "dlugosc": "",
                "grubosc": "",
                "parametry": "Mat",
                "cena_zl": "120",
                "ilosc": "2",
                "spisano_zamowienie": "0",
                "ilosc_magazyn": "2",
                "pracownik": "Adam",
                "data_wpisu": "2026-03-22",
                "zakup": "Tak",
                "numer_faktury": "FV-22",
                "data_zakupu": "2026-03-21",
            }
        ],
        "main_table_layout": {},
    }
    store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    w = TabBazaMaterialu()

    assert w.tbl.rowCount() >= 1

    found = False
    for row in range(w.tbl.rowCount()):
        if _cell_text(w.tbl, row, 0) == "M0001":
            found = True
            assert _cell_text(w.tbl, row, 1) == "lakier"
            assert _cell_text(w.tbl, row, 2) == "Lakier test"
            break

    assert found, "Nie odtworzono zapisanego materiału"


@pytest.mark.gui
def test_remove_selected_material_row_works(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._insert_material_row(
        [
            "M0001",
            "korpus",
            "Do usuniecia",
            "Egger",
            "2070",
            "2800",
            "18",
            "",
            "100",
            "1",
            "0",
            "1",
            "Jan",
            "2026-03-22",
            "Tak",
            "FV-3",
            "2026-03-21",
        ]
    )

    row_to_remove = -1
    for row in range(w.tbl.rowCount()):
        if _cell_text(w.tbl, row, 2) == "Do usuniecia":
            row_to_remove = row
            break

    assert row_to_remove >= 0

    w.tbl.selectRow(row_to_remove)
    w._remove_selected_rows()

    for row in range(w.tbl.rowCount()):
        assert _cell_text(w.tbl, row, 2) != "Do usuniecia"


@pytest.mark.gui
def test_remove_selected_type_row_refreshes_material_combos(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("test_combo")
    w.ed_type_nazwa.setText("Test Combo")
    w._confirm_type_entry()

    type_row = -1
    for row in range(w.tbl_types.rowCount()):
        if str(w.tbl_types.item(row, 1).text()).strip() == "test_combo":
            type_row = row
            break

    assert type_row >= 0

    w.tbl_types.selectRow(type_row)
    w._remove_selected_type_rows()

    available = [w.cb_mat_typ.itemText(i) for i in range(w.cb_mat_typ.count())]
    assert "test_combo" not in available


@pytest.mark.gui
def test_type_entry_adds_typ_and_name_in_same_row(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("okucie_test")
    w.ed_type_nazwa.setText("Okucie Test")
    w._confirm_type_entry()

    row = _find_row_by_cell_text(w.tbl_types, 1, "okucie_test")
    assert row >= 0
    assert _cell_text(w.tbl_types, row, 2) == "Okucie Test"


@pytest.mark.gui
def test_type_entry_confirms_on_enter_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()
    before = w.tbl_types.rowCount()

    w._show_type_entry_bar()
    w.ed_type_typ.setText("fornir")
    w.ed_type_nazwa.setText("Fornir")
    QTest.keyClick(w.ed_type_nazwa, Qt.Key.Key_Return)

    assert w.tbl_types.rowCount() == before + 1
    assert w.type_entry_bar.isVisible() is False
    row = _find_row_by_cell_text(w.tbl_types, 1, "fornir")
    assert row >= 0
    assert _cell_text(w.tbl_types, row, 2) == "Fornir"


@pytest.mark.gui
def test_material_entry_confirms_on_enter_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()
    before = w.tbl.rowCount()

    w._show_material_entry_bar()
    w.cb_mat_typ.setCurrentText("korpus")
    w.ed_mat_nazwa.setText("Plyta Enter")
    w.ed_mat_producent.setText("Egger")
    QTest.keyClick(w.ed_mat_nazwa, Qt.Key.Key_Return)

    assert w.tbl.rowCount() == before + 1
    assert w.material_entry_bar.isVisible() is False
    row = _find_row_by_cell_text(w.tbl, 2, "Plyta Enter")
    assert row >= 0
    assert _cell_text(w.tbl, row, 1) == "korpus"


@pytest.mark.gui
def test_filter_panel_toggles_visibility_and_button_text(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = TabBazaMaterialu()

    assert w.filter_panel.isVisible() is False
    assert w.btn_toggle_filter.text() == "Filtr"

    w._toggle_filter_panel()
    assert w.filter_panel.isVisible() is True
    assert w.btn_toggle_filter.text() == "Ukryj filtr"

    w._toggle_filter_panel()
    assert w.filter_panel.isVisible() is False
    assert w.btn_toggle_filter.text() == "Filtr"


@pytest.mark.gui
def test_blocked_type_from_store_is_removed_and_material_type_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    store_path = Path(tmp_path) / "baza_materialu.json"
    payload = {
        "types": [
            {"id": "T0001", "typ": "inne", "nazwa": "Inne"},
            {"id": "T0002", "typ": "korpus", "nazwa": "Korpus"},
        ],
        "rows": [
            {
                "id": "M0001",
                "typ": "inne",
                "nazwa": "Niepoprawny typ",
                "producent": "X",
                "szerokosc": "",
                "dlugosc": "",
                "grubosc": "",
                "parametry": "",
                "cena_zl": "",
                "ilosc": "",
                "spisano_zamowienie": "",
                "ilosc_magazyn": "",
                "pracownik": "",
                "data_wpisu": "",
                "zakup": "",
                "numer_faktury": "",
                "data_zakupu": "",
            }
        ],
        "main_table_layout": {},
    }
    store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    w = TabBazaMaterialu()
    options = [w.cb_mat_typ.itemText(i) for i in range(w.cb_mat_typ.count())]

    assert all(opt not in BLOCKED_MATERIAL_TYPES for opt in options)
    assert "inne" not in options

    row = _find_row_by_cell_text(w.tbl, 0, "M0001")
    assert row >= 0
    assert _cell_text(w.tbl, row, 1) in options
    assert _cell_text(w.tbl, row, 1) != "inne"

