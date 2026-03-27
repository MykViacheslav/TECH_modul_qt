from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.app.main_window import MainWindow
from src.domain.worker_models import WorkerDef
from src.storage.calendar_event_store_json import CalendarEventStoreJson


def run() -> None:
    data_dir = Path(os.environ.get("TECH_MODUL_DATA_DIR", "").strip() or "")
    if not data_dir:
        data_dir = Path.cwd() / "tmp_e2e_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TECH_MODUL_DATA_DIR"] = str(data_dir)
    os.environ["TECH_MODUL_TESTING"] = "1"

    app = QApplication.instance() or QApplication([])
    QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
    QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
    QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes

    w = MainWindow()
    w.show()
    app.processEvents()

    tab_workers = w._tabs_by_title["Pracownik"]
    workers = [
        ("W001", "Jan", "Kowalski", "Produkcja", 45.0),
        ("W002", "Adam", "Nowak", "Produkcja", 44.0),
        ("W003", "Piotr", "Zielinski", "CNC", 46.0),
        ("W004", "Marek", "Wisniewski", "Montaz", 47.0),
        ("W005", "Tomasz", "Wrobel", "Montaz", 47.0),
        ("W006", "Kamil", "Mazur", "Lakiernia", 46.0),
        ("W007", "Pawel", "Kaczmarek", "Pomiar", 43.0),
        ("W008", "Lukasz", "Sikora", "Transport", 42.0),
        ("W009", "Michal", "Zajac", "Magazyn", 41.0),
    ]
    for wid, first, last, role, rate in workers:
        tab_workers._store.overwrite(
            WorkerDef(
                name=f"{first} {last}",
                worker_id=wid,
                first_name=first,
                last_name=last,
                role=role,
                hourly_rate=rate,
            )
        )
    tab_workers._load_workers()
    print("workers:", len(tab_workers._store.list_workers()))

    tab_fixed = w._tabs_by_title["Wydatki stale firmy"]
    fixed_values = {"Wynajem": "12000", "Prad": "5000", "Leasingi": "7000"}
    for row in range(tab_fixed.tbl.rowCount()):
        name_item = tab_fixed.tbl.item(row, 0)
        name = str(name_item.text() if name_item is not None else "").strip()
        value = fixed_values.get(name)
        if value is not None:
            tab_fixed.tbl.setItem(row, 1, QTableWidgetItem(value))
    tab_fixed._recalculate_and_save()
    print("fixed:", tab_fixed.lab_sum.text())

    tab_variable = w._tabs_by_title["Wydatki zmienne"]
    tab_variable.sp_workers.setValue(9)
    tab_variable.sp_hours.setValue(220.0)
    for row in range(tab_variable.tbl.rowCount()):
        name_item = tab_variable.tbl.item(row, 0)
        name = str(name_item.text() if name_item is not None else "").strip()
        if name == "Zakupy materialow":
            tab_variable.tbl.setItem(row, 1, QTableWidgetItem("32000"))
    tab_variable._recalculate_and_save()
    print("variable total:", tab_variable.lab_sum_total.text())

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
    tab_order._on_save_order_to_base()
    tab_order._on_go_to_sciana()
    app.processEvents()

    tab_sciana = w._tabs_by_title["Sciana"]
    print("sciana order:", tab_sciana.cb_order.currentData(), "order_id:", tab_sciana.ed_order_id.text())

    cal_store = CalendarEventStoreJson(path=data_dir / "calendar_events.json")
    events = [ev for ev in cal_store.list_events() if str(ev.order_code or "") == "KUCHNIA-2026-001"]
    print("calendar events for order:", len(events))

    tab_calendar = w._tabs_by_title["Kalendarz"]
    tab_calendar._on_data_change()
    listed = [tab_calendar._lst_order_status.item(i).text() for i in range(tab_calendar._lst_order_status.count())]
    print("calendar orders listed:", len(listed))

    assert tab_sciana.cb_order.currentData() == "KUCHNIA-2026-001"
    assert tab_sciana.ed_order_id.text() == "K-001"
    assert len(events) >= 2
    assert any("KUCHNIA-2026-001" in txt for txt in listed)
    print("E2E kitchen workflow: OK")

    w.close()


if __name__ == "__main__":
    run()
