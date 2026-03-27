from __future__ import annotations

from datetime import date, timedelta

import pytest
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from src.app.main_window import MainWindow
from src.storage.calendar_event_store_json import CalendarEventStoreJson


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.gui
def test_e2e_single_kitchen_order_flow_with_workers_costs_and_calendar(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    _app()

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    w = MainWindow()
    w.show()

    tab_workers = w._tabs_by_title["Pracownik"]
    workers = [
        ("W001", "Jan", "Kowalski", "Produkcja", "45"),
        ("W002", "Adam", "Nowak", "Produkcja", "44"),
        ("W003", "Piotr", "Zielinski", "CNC", "46"),
        ("W004", "Marek", "Wisniewski", "Montaż", "47"),
        ("W005", "Tomasz", "Wrobel", "Montaż", "47"),
        ("W006", "Kamil", "Mazur", "Lakiernia", "46"),
        ("W007", "Pawel", "Kaczmarek", "Pomiar", "43"),
        ("W008", "Lukasz", "Sikora", "Transport", "42"),
        ("W009", "Michal", "Zajac", "Magazyn", "41"),
    ]
    tab_workers.tbl.setRowCount(0)
    for row_data in workers:
        row = tab_workers.tbl.rowCount()
        tab_workers.tbl.insertRow(row)
        for col, value in enumerate(row_data):
            tab_workers.tbl.setItem(row, col, QTableWidgetItem(value))
    tab_workers._save_all()
    assert len(tab_workers._store.list_workers()) == 9

    tab_fixed = w._tabs_by_title["Wydatki stale firmy"]
    fixed_map = {"Wynajem": "12000", "Prad": "5000", "Leasingi": "7000"}
    for row in range(tab_fixed.tbl.rowCount()):
        name_item = tab_fixed.tbl.item(row, 0)
        if name_item is None:
            continue
        key = str(name_item.text() or "").strip()
        if key in fixed_map:
            tab_fixed.tbl.setItem(row, 1, QTableWidgetItem(fixed_map[key]))
    tab_fixed._recalculate_and_save()
    assert "24000.00" in tab_fixed.lab_sum.text()

    tab_variable = w._tabs_by_title["Wydatki zmienne"]
    tab_variable.sp_workers.setValue(9)
    tab_variable.sp_hours.setValue(220.0)
    for row in range(tab_variable.tbl.rowCount()):
        name_item = tab_variable.tbl.item(row, 0)
        if name_item is None:
            continue
        key = str(name_item.text() or "").strip()
        if key == "Zakupy materialow":
            tab_variable.tbl.setItem(row, 1, QTableWidgetItem("32000"))
    tab_variable._recalculate_and_save()
    assert "Suma razem:" in tab_variable.lab_sum_total.text()

    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_order.cb_client_name.setCurrentText("Klient Test Kuchnia")
    tab_order.cb_worker_name.setCurrentText("Jan Kowalski")
    tab_order.ed_order_code.setText("KUCHNIA-2026-001")
    tab_order.ed_order_id.setText("K-001")

    today = date.today()
    tab_order.ed_date_wycena.setDate(QDate(today.year, today.month, today.day))
    prod = today + timedelta(days=10)
    mont = today + timedelta(days=20)
    tab_order.ed_date_produkcja.setDate(QDate(prod.year, prod.month, prod.day))
    tab_order.ed_date_montaz.setDate(QDate(mont.year, mont.month, mont.day))

    QTest.mouseClick(tab_order.btn_save_order, Qt.MouseButton.LeftButton)
    QTest.mouseClick(tab_order.btn_go_to_sciana, Qt.MouseButton.LeftButton)

    tab_sciana = w._tabs_by_title["Sciana"]
    assert tab_sciana.cb_order.currentData() == "KUCHNIA-2026-001"
    assert tab_sciana.ed_order_id.text() == "K-001"

    cal_store = CalendarEventStoreJson(path=tmp_path / "calendar_events.json")
    order_events = [ev for ev in cal_store.list_events() if str(ev.order_code or "") == "KUCHNIA-2026-001"]
    assert len(order_events) >= 2
    assert any("Wycena" in str(ev.title or "") for ev in order_events)
    assert any("Montaz" in str(ev.title or "") for ev in order_events)

    tab_calendar = w._tabs_by_title["Kalendarz"]
    tab_calendar._on_data_change()
    listed_orders = [tab_calendar._lst_order_status.item(i).text() for i in range(tab_calendar._lst_order_status.count())]
    assert any("KUCHNIA-2026-001" in txt for txt in listed_orders)

    w.close()
