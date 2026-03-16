from PyQt6.QtCore import QDate, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def test_kalendarz_tab_lists_orders_and_saves_stage_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.domain.worker_models import WorkerDef
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")

    worker_store.save_new(WorkerDef(name="Jan Montaz", role="Montaz"))
    order_store.save_new(
        OrderDef(
            code="ORD-KAL-01",
            client_name="Klient Kalendarz",
            worker_name="Jan Montaz",
            status="W produkcji",
            progress_percent=45.0,
        )
    )

    w = TabKalendarz(order_store=order_store, worker_store=worker_store)

    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 2).text() == "ORD-KAL-01"

    w.tbl_orders.selectRow(0)
    w.cb_calendar_status.setCurrentText("Montaz")
    w.sp_calendar_progress.setValue(70)
    w.cb_calendar_stage.setCurrentText("Montaz")
    w.chk_no_date.setChecked(False)
    w.de_calendar_date.setDate(QDate(2026, 3, 20))
    w.cb_calendar_worker.setCurrentText("Jan Montaz")
    w.ed_calendar_note.setText("Termin potwierdzony z klientem")

    QTest.mouseClick(w.btn_save, Qt.MouseButton.LeftButton)

    saved = order_store.get("ORD-KAL-01")
    assert saved is not None
    assert saved.status == "Montaz"
    assert float(saved.progress_percent) == 70.0
    assert saved.calendar_stage == "Montaz"
    assert saved.calendar_date == "2026-03-20"
    assert saved.worker_name == "Jan Montaz"
    assert saved.calendar_note == "Termin potwierdzony z klientem"
    assert len(saved.status_history) == 1
    assert saved.status_history[0]["from_status"] == "W produkcji"
    assert saved.status_history[0]["to_status"] == "Montaz"
    assert saved.status_history[0]["changed_by"] == "Jan Montaz"
    assert "Nadpisano zamowienie" in w.lab_status.text()


def test_kalendarz_tab_metrics_include_scheduled_and_overdue(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-KAL-02",
            client_name="Klient A",
            status="Wycena",
            progress_percent=10.0,
            calendar_stage="Pomiar",
            calendar_date="2020-01-01",
        )
    )
    order_store.save_new(
        OrderDef(
            code="ORD-KAL-03",
            client_name="Klient B",
            status="Montaz",
            progress_percent=80.0,
            calendar_stage="Montaz",
            calendar_date="2030-01-01",
        )
    )

    w = TabKalendarz(order_store=order_store)

    assert w.lab_metric_total.metric_value.text() == "2"  # type: ignore[attr-defined]
    assert w.lab_metric_scheduled.metric_value.text() == "2"  # type: ignore[attr-defined]
    assert w.lab_metric_overdue.metric_value.text() == "1"  # type: ignore[attr-defined]
    assert w.lab_metric_montage.metric_value.text() == "1"  # type: ignore[attr-defined]
    assert w.tbl_workload.rowCount() == 1
    assert w.tbl_workload.item(0, 0).text() == "[brak]"
    assert w.tbl_workload.item(0, 1).text() == "2"


def test_kalendarz_tab_shows_status_history_for_selected_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-KAL-04",
            client_name="Klient Historia",
            status="Produkcja",
            progress_percent=60.0,
            status_history=[
                {
                    "changed_at": "2026-03-15 10:30",
                    "from_status": "Wycena",
                    "to_status": "Produkcja",
                    "changed_by": "Jan Test",
                    "note": "Klient zaakceptowal i rusza produkcja",
                }
            ],
        )
    )

    w = TabKalendarz(order_store=order_store)
    w.tbl_orders.selectRow(0)

    assert w.tbl_status_history.rowCount() == 1
    assert w.tbl_status_history.item(0, 1).text() == "Wycena"
    assert w.tbl_status_history.item(0, 2).text() == "Produkcja"
    assert w.tbl_status_history.item(0, 3).text() == "Jan Test"
    assert "Klient zaakceptowal" in w.lab_history_note.text()
