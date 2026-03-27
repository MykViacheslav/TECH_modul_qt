"""
Testy dla TabBazaMaterialu.

Uruchomienie:
    pytest tests/test_tab_bazy.py -v

Wymagania:
    pip install pytest pytest-qt pyqt6
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Upewnij sie ze modul jest dostepny
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tab_baza_materialu import TabBazaMaterialu, SHARED_MATERIAL_TYPES, BLOCKED_MATERIAL_TYPES


# ─── fixture: widget z tymczasowym katalogiem danych ────────────────────────

@pytest.fixture
def widget(qtbot, tmp_path):
    os.environ["TECH_MODUL_DATA_DIR"] = str(tmp_path)
    w = TabBazaMaterialu()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    yield w
    os.environ.pop("TECH_MODUL_DATA_DIR", None)


# ─── 1. Budowanie widgetu ────────────────────────────────────────────────────

def test_widget_builds(widget):
    """Widget tworzy sie bez wyjatkow."""
    assert widget is not None


def test_default_type_rows_loaded(widget):
    """Po starcie tabela typow zawiera domyslne typy z SHARED_MATERIAL_TYPES."""
    loaded = set()
    for row in range(widget.tbl_types.rowCount()):
        item = widget.tbl_types.item(row, 1)
        if item:
            loaded.add(item.text().strip().lower())
    for typ in SHARED_MATERIAL_TYPES:
        assert typ in loaded, f"Brak domyslnego typu: {typ}"


def test_main_table_has_17_columns(widget):
    assert widget.tbl.columnCount() == 17


def test_prod_table_has_2_columns(widget):
    assert widget.tbl_prod.columnCount() == 2


def test_work_table_has_2_columns(widget):
    assert widget.tbl_work.columnCount() == 2


# ─── 2. Dodawanie typow ──────────────────────────────────────────────────────

def test_add_type(widget, qtbot):
    before = widget.tbl_types.rowCount()
    widget.ed_type_typ.setText("testtyp")
    widget.ed_type_nazwa.setText("Testowy")
    widget._confirm_type_entry()
    assert widget.tbl_types.rowCount() == before + 1
    types = [
        widget.tbl_types.item(r, 1).text()
        for r in range(widget.tbl_types.rowCount())
        if widget.tbl_types.item(r, 1)
    ]
    assert "testtyp" in types


def test_add_type_duplicate_ignored(widget):
    widget.ed_type_typ.setText("korpus")
    widget.ed_type_nazwa.setText("Korpus2")
    before = widget.tbl_types.rowCount()
    widget._confirm_type_entry()
    assert widget.tbl_types.rowCount() == before


def test_add_blocked_type_ignored(widget):
    widget.ed_type_typ.setText("inne")
    widget.ed_type_nazwa.setText("Inne")
    before = widget.tbl_types.rowCount()
    widget._confirm_type_entry()
    assert widget.tbl_types.rowCount() == before


def test_remove_type(widget, qtbot):
    widget.ed_type_typ.setText("dousuniecia")
    widget._confirm_type_entry()
    before = widget.tbl_types.rowCount()
    # zaznacz ostatni wiersz
    widget.tbl_types.selectRow(before - 1)
    widget._remove_selected_type_rows()
    assert widget.tbl_types.rowCount() == before - 1


# ─── 3. Dodawanie producentow ────────────────────────────────────────────────

def test_add_producer(widget):
    widget.ed_prod_nazwa.setText("IKEA")
    widget._confirm_prod_entry()
    options = widget._prod_options()
    assert "IKEA" in options


def test_add_producer_duplicate_ignored(widget):
    widget.ed_prod_nazwa.setText("EGGER")
    widget._confirm_prod_entry()
    before = widget.tbl_prod.rowCount()
    widget.ed_prod_nazwa.setText("EGGER")
    widget._confirm_prod_entry()
    assert widget.tbl_prod.rowCount() == before


def test_producer_appears_in_entry_combo(widget):
    widget.ed_prod_nazwa.setText("KRONOSPAN")
    widget._confirm_prod_entry()
    widget._show_material_entry_bar()
    items = [widget.cb_mat_producent.itemText(i) for i in range(widget.cb_mat_producent.count())]
    assert "KRONOSPAN" in items


# ─── 4. Dodawanie pracownikow ────────────────────────────────────────────────

def test_add_worker(widget):
    widget.ed_work_nazwa.setText("Jan Kowalski")
    widget._confirm_work_entry()
    assert "Jan Kowalski" in widget._work_options()


def test_worker_appears_in_entry_combo(widget):
    widget.ed_work_nazwa.setText("Anna Nowak")
    widget._confirm_work_entry()
    widget._show_material_entry_bar()
    items = [widget.cb_mat_pracownik.itemText(i) for i in range(widget.cb_mat_pracownik.count())]
    assert "Anna Nowak" in items


# ─── 5. Dodawanie materialow ─────────────────────────────────────────────────

def test_add_material_row(widget):
    before = widget.tbl.rowCount()
    widget._show_material_entry_bar()
    widget.ed_mat_nazwa.setText("Plyta MDF 18mm")
    widget._confirm_material_entry()
    assert widget.tbl.rowCount() == before + 1


def test_material_id_format(widget):
    widget._show_material_entry_bar()
    widget.ed_mat_nazwa.setText("Test")
    widget._confirm_material_entry()
    row = widget.tbl.rowCount() - 1
    id_item = widget.tbl.item(row, 0)
    assert id_item is not None
    assert id_item.text().startswith("M")


def test_material_id_unique(widget):
    for name in ("Mat A", "Mat B", "Mat C"):
        widget._show_material_entry_bar()
        widget.ed_mat_nazwa.setText(name)
        widget._confirm_material_entry()
    ids = [widget.tbl.item(r, 0).text() for r in range(widget.tbl.rowCount())]
    assert len(ids) == len(set(ids)), "ID materialow nie sa unikalne"


# ─── 6. Auto-podpinanie Nazwy z TYP ─────────────────────────────────────────

def test_sync_name_on_type_change(widget):
    widget._show_material_entry_bar()
    # wybierz typ 'plyta' – Nazwa powinna sie auto-uzupelnic
    options = widget._type_options()
    if "plyta" in options:
        widget.cb_mat_typ.setCurrentText("plyta")
        widget._sync_material_entry_name()
        name = widget.ed_mat_nazwa.text().strip()
        assert name != "", "Nazwa nie zostala auto-uzupelniona"


def test_sync_name_not_overwrite_manual(widget):
    widget._show_material_entry_bar()
    widget.ed_mat_nazwa.setText("Reczna nazwa")
    widget._last_synced_name = ""  # symuluj ze uzytkownik sam wpisal
    widget._sync_material_entry_name()
    assert widget.ed_mat_nazwa.text() == "Reczna nazwa"


# ─── 7. Zapis i odczyt JSON ──────────────────────────────────────────────────

def test_save_and_reload(widget, tmp_path):
    # Dodaj producenta
    widget.ed_prod_nazwa.setText("SaveTest")
    widget._confirm_prod_entry()
    # Dodaj pracownika
    widget.ed_work_nazwa.setText("Adam Testowy")
    widget._confirm_work_entry()
    # Dodaj material
    widget._show_material_entry_bar()
    widget.ed_mat_nazwa.setText("Plyta zapisana")
    widget._confirm_material_entry()

    # Sprawdz ze plik JSON istnieje
    store = Path(tmp_path) / "baza_materialu.json"
    assert store.exists()
    data = json.loads(store.read_text(encoding="utf-8"))
    assert "types" in data
    assert "producenci" in data
    assert "pracownicy" in data
    assert "rows" in data

    # Producent i pracownik zapisani
    prod_names = [e.get("producent") for e in data["producenci"]]
    assert "SaveTest" in prod_names
    work_names = [e.get("pracownik") for e in data["pracownicy"]]
    assert "Adam Testowy" in work_names

    # Material zapisany
    row_names = [e.get("nazwa") for e in data["rows"]]
    assert "Plyta zapisana" in row_names


def test_reload_restores_data(tmp_path):
    """Drugi widget zaladowany z tego samego pliku ma te same dane."""
    import os
    os.environ["TECH_MODUL_DATA_DIR"] = str(tmp_path)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    w1 = TabBazaMaterialu()
    w1.ed_prod_nazwa.setText("ReloadProducent")
    w1._confirm_prod_entry()
    w1.ed_work_nazwa.setText("ReloadPracownik")
    w1._confirm_work_entry()
    w1._show_material_entry_bar()
    w1.ed_mat_nazwa.setText("ReloadMaterial")
    w1._confirm_material_entry()

    w2 = TabBazaMaterialu()
    assert "ReloadProducent" in w2._prod_options()
    assert "ReloadPracownik" in w2._work_options()
    names = [w2.tbl.item(r, 2).text() for r in range(w2.tbl.rowCount()) if w2.tbl.item(r, 2)]
    assert "ReloadMaterial" in names

    os.environ.pop("TECH_MODUL_DATA_DIR", None)


# ─── 8. Filtry ───────────────────────────────────────────────────────────────

def test_filter_hides_non_matching_rows(widget):
    for name in ("AlphaPlyta", "BetaFront", "GammaOkleina"):
        widget._show_material_entry_bar()
        widget.ed_mat_nazwa.setText(name)
        widget._confirm_material_entry()

    # filtruj po "Alpha"
    widget._filter_inputs[2].setText("Alpha")

    visible = [
        r for r in range(widget.tbl.rowCount())
        if not widget.tbl.isRowHidden(r)
    ]
    assert len(visible) == 1
    assert widget.tbl.item(visible[0], 2).text() == "AlphaPlyta"


def test_clear_filter_shows_all(widget):
    for name in ("X", "Y"):
        widget._show_material_entry_bar()
        widget.ed_mat_nazwa.setText(name)
        widget._confirm_material_entry()

    widget._filter_inputs[2].setText("X")
    widget._clear_filters()
    hidden = [r for r in range(widget.tbl.rowCount()) if widget.tbl.isRowHidden(r)]
    assert hidden == []


# ─── 9. Toggle paneli ────────────────────────────────────────────────────────

def test_toggle_types_panel(widget):
    assert widget.types_body.isVisible()
    widget.btn_toggle_types.setChecked(False)
    assert not widget.types_body.isVisible()
    widget.btn_toggle_types.setChecked(True)
    assert widget.types_body.isVisible()


def test_toggle_prod_panel(widget):
    assert widget.prod_body.isVisible()
    widget.btn_toggle_prod.setChecked(False)
    assert not widget.prod_body.isVisible()
    widget.btn_toggle_prod.setChecked(True)
    assert widget.prod_body.isVisible()


def test_toggle_work_panel(widget):
    assert widget.work_body.isVisible()
    widget.btn_toggle_work.setChecked(False)
    assert not widget.work_body.isVisible()
    widget.btn_toggle_work.setChecked(True)
    assert widget.work_body.isVisible()