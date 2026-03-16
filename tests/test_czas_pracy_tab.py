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
    w.cb_pay_mode.setCurrentText("Godzinowa")
    w.sp_hourly_rate.setValue(50.0)

    w._save_hourly_rate()

    assert float(worker_store.get("Andrzej").hourly_rate) == 50.0
    assert worker_store.get("Andrzej").pay_mode == "Godzinowa"

    w.tbl_hours.setItem(0, 2, QTableWidgetItem("Montaz"))
    w.tbl_hours.setItem(0, 3, QTableWidgetItem("8:00"))
    w.tbl_hours.setItem(0, 4, QTableWidgetItem("16:30"))
    w.tbl_hours.setItem(0, 6, QTableWidgetItem("1.50"))
    w.tbl_hours.setItem(0, 7, QTableWidgetItem("25"))
    w.tbl_hours.setItem(0, 8, QTableWidgetItem("ORDER-1"))
    w.tbl_hours.setItem(0, 9, QTableWidgetItem("Pomiar i montaz"))
    w.tbl_hours.setItem(1, 2, QTableWidgetItem("Produkcja"))
    w.tbl_hours.setItem(1, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(1, 4, QTableWidgetItem("18"))
    w.tbl_hours.setItem(1, 8, QTableWidgetItem("ORDER-2"))

    w._save_sheet()

    sheet = work_time_store.get_sheet("Andrzej", 2026, 3)
    assert len(sheet.entries) == 2
    assert sheet.entries[0].work_type == "Montaz"
    assert sheet.entries[0].project_code == "ORDER-1"
    assert float(sheet.entries[0].hours) == 8.5
    assert float(sheet.entries[0].overtime_hours) == 1.5
    assert float(sheet.entries[0].extra_pay) == 25.0
    assert float(sheet.entries[1].hours) == 10.0
    assert w.lab_days.metric_value.text() == "2"  # type: ignore[attr-defined]
    assert w.lab_hours.metric_value.text() == "18.50"  # type: ignore[attr-defined]
    assert w.lab_overtime.metric_value.text() == "1.50"  # type: ignore[attr-defined]
    assert w.lab_cost.metric_value.text() == "1025.00 PLN"  # type: ignore[attr-defined]


def test_czas_pracy_tab_supports_daily_mode_with_overtime_and_extra(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.save_new(WorkerDef(name="Natalia", role="Projekt", pay_mode="Dniowka", daily_rate=400.0, hourly_rate=60.0))

    w = TabCzasPracy(worker_store=worker_store)
    w.cb_worker.setCurrentText("Natalia")
    w.cb_month.setCurrentIndex(1)  # Luty
    w.sp_year.setValue(2026)
    w.cb_pay_mode.setCurrentText("Dniowka")
    w.sp_daily_rate.setValue(400.0)
    w.sp_hourly_rate.setValue(60.0)

    w.tbl_hours.setItem(0, 2, QTableWidgetItem("Projekt / wycena"))
    w.tbl_hours.setItem(0, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(0, 4, QTableWidgetItem("17"))
    w.tbl_hours.setItem(0, 6, QTableWidgetItem("2"))
    w.tbl_hours.setItem(0, 7, QTableWidgetItem("50"))
    w.tbl_hours.setItem(1, 2, QTableWidgetItem("Praca na miejscu"))
    w.tbl_hours.setItem(1, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(1, 4, QTableWidgetItem("16"))

    w._refresh_summary()

    assert w.lab_days.metric_value.text() == "2"  # type: ignore[attr-defined]
    assert w.lab_hours.metric_value.text() == "17.00"  # type: ignore[attr-defined]
    assert w.lab_overtime.metric_value.text() == "2.00"  # type: ignore[attr-defined]
    assert w.lab_cost.metric_value.text() == "970.00 PLN"  # type: ignore[attr-defined]


def test_czas_pracy_tab_supports_stage_cost_modifiers(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.save_new(
        WorkerDef(
            name="Artem",
            role="Montaz",
            pay_mode="Godzinowa",
            hourly_rate=50.0,
            overtime_multiplier=1.5,
            delegation_day_addon_pln=120.0,
            montage_hour_addon_pln=10.0,
            onsite_hour_addon_pln=5.0,
            lacquer_hour_addon_pln=3.0,
        )
    )

    w = TabCzasPracy(worker_store=worker_store)
    w.cb_worker.setCurrentText("Artem")
    w.cb_month.setCurrentIndex(2)
    w.sp_year.setValue(2026)

    w.tbl_hours.setItem(0, 2, QTableWidgetItem("Montaz"))
    w.tbl_hours.setItem(0, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(0, 4, QTableWidgetItem("16"))
    w.tbl_hours.setItem(0, 6, QTableWidgetItem("2"))
    w.tbl_hours.setItem(1, 2, QTableWidgetItem("Delegacja / wyjazd"))
    w.tbl_hours.setItem(1, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(1, 4, QTableWidgetItem("16"))
    w.tbl_hours.setItem(2, 2, QTableWidgetItem("Lakiernia"))
    w.tbl_hours.setItem(2, 3, QTableWidgetItem("8"))
    w.tbl_hours.setItem(2, 4, QTableWidgetItem("12"))
    w.tbl_hours.setItem(2, 7, QTableWidgetItem("20"))

    w._refresh_summary()

    assert w.lab_days.metric_value.text() == "3"  # type: ignore[attr-defined]
    assert w.lab_hours.metric_value.text() == "20.00"  # type: ignore[attr-defined]
    assert w.lab_overtime.metric_value.text() == "2.00"  # type: ignore[attr-defined]
    assert w.lab_cost.metric_value.text() == "1382.00 PLN"  # type: ignore[attr-defined]
    assert "Dodatki etapow: 212.00 PLN" in w.lab_breakdown.text()
