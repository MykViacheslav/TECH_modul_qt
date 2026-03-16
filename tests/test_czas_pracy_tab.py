from PyQt6.QtWidgets import QApplication, QTableWidgetItem


def test_czas_pracy_tab_saves_hourly_rate_and_month_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    worker_store.save_new(WorkerDef(name="Andrzej", role="Produkcja"))

    w = TabCzasPracy(worker_store=worker_store, work_time_store=work_time_store)
    w.cb_worker.setCurrentText("Andrzej")
    w.cb_month.setCurrentIndex(2)  # Marzec
    w.sp_year.setValue(2026)
    w.sp_hourly_rate.setValue(50.0)

    w._save_hourly_rate()

    assert float(worker_store.get("Andrzej").hourly_rate) == 50.0

    w.tbl_hours.setItem(0, 2, QTableWidgetItem("8:00"))
    w.tbl_hours.setItem(0, 3, QTableWidgetItem("16:30"))
    w.tbl_hours.setItem(0, 5, QTableWidgetItem("ORDER-1"))
    w.tbl_hours.setItem(0, 6, QTableWidgetItem("Pomiar i montaz"))
    w.tbl_hours.setItem(1, 2, QTableWidgetItem("8"))
    w.tbl_hours.setItem(1, 3, QTableWidgetItem("18"))
    w.tbl_hours.setItem(1, 5, QTableWidgetItem("ORDER-2"))

    w._save_sheet()

    sheet = work_time_store.get_sheet("Andrzej", 2026, 3)
    assert len(sheet.entries) == 2
    assert sheet.entries[0].project_code == "ORDER-1"
    assert float(sheet.entries[0].hours) == 8.5
    assert float(sheet.entries[1].hours) == 10.0
    assert w.lab_days.metric_value.text() == "2"  # type: ignore[attr-defined]
    assert w.lab_hours.metric_value.text() == "18.50"  # type: ignore[attr-defined]
    assert w.lab_cost.metric_value.text() == "925.00 PLN"  # type: ignore[attr-defined]
