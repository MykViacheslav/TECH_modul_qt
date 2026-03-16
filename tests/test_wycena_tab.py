from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def test_wycena_tab_lists_assemblies_and_saves_commercial_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-WYCENA-01",
            order_name="ORDER-WYCENA-01",
            client_name="Klient Wycena",
        )
    )

    w = TabWycena(assembly_store=assembly_store)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-WYCENA-01"

    w.tbl_assemblies.selectRow(0)
    w.sp_labor.setValue(120.0)
    w.sp_transport.setValue(45.0)
    w.sp_montage.setValue(80.0)
    w.sp_margin.setValue(15.0)

    QTest.mouseClick(w.btn_save, Qt.MouseButton.LeftButton)

    saved = assembly_store.get("KOMPLET-WYCENA-01")
    assert saved is not None
    assert float(saved.labor_cost_pln) == 120.0
    assert float(saved.transport_cost_pln) == 45.0
    assert float(saved.montage_cost_pln) == 80.0
    assert float(saved.margin_percent) == 15.0
    assert "Nadpisano komplet" in w.lab_status.text()


def test_wycena_tab_filters_by_order_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-A", order_name="ORDER-A", client_name="Klient A"))
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-B", order_name="ORDER-B", client_name="Klient B"))

    w = TabWycena(assembly_store=assembly_store)

    idx = w.cb_order.findData("ORDER-B")
    assert idx >= 0
    w.cb_order.setCurrentIndex(idx)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-B"


def test_wycena_tab_can_load_labor_from_work_time(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef
    from src.domain.worker_models import WorkerDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")

    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-WYCENA-02",
            order_name="ORDER-WYCENA-02",
            client_name="Klient Robocizna",
        )
    )
    worker_store.save_new(WorkerDef(name="Natalia", role="Projekt", pay_mode="Dniowka", daily_rate=400.0, hourly_rate=60.0))
    worker_store.save_new(WorkerDef(name="Artem", role="Montaz", pay_mode="Godzinowa", hourly_rate=50.0))
    work_time_store.save_sheet(
        WorkerMonthSheetDef(
            worker_name="Natalia",
            year=2026,
            month=3,
            entries=[
                WorkTimeEntryDef(
                    day=1,
                    date_iso="2026-03-01",
                    work_type="Projekt / wycena",
                    hours=8.0,
                    overtime_hours=1.0,
                    extra_pay=20.0,
                    project_code="ORDER-WYCENA-02",
                )
            ],
        )
    )
    work_time_store.save_sheet(
        WorkerMonthSheetDef(
            worker_name="Artem",
            year=2026,
            month=3,
            entries=[
                WorkTimeEntryDef(
                    day=2,
                    date_iso="2026-03-02",
                    work_type="Montaz",
                    hours=5.0,
                    project_code="KOMPLET-WYCENA-02",
                )
            ],
        )
    )

    w = TabWycena(
        assembly_store=assembly_store,
        worker_store=worker_store,
        work_time_store=work_time_store,
    )
    w.tbl_assemblies.selectRow(0)

    assert w.lab_time_days.text() == "2"
    assert w.lab_time_hours.text() == "13.00 h"
    assert w.lab_time_extra.text() == "20.00 zl"
    assert w.lab_time_cost.text() == "730.00 zl"

    QTest.mouseClick(w.btn_load_labor_from_time, Qt.MouseButton.LeftButton)

    assert float(w.sp_labor.value()) == 730.0
    assert "Czas pracy" in w.lab_status.text()


def test_wycena_tab_applies_stage_cost_modifiers_from_work_time(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef
    from src.domain.worker_models import WorkerDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")

    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-WYCENA-03",
            order_name="ORDER-WYCENA-03",
            client_name="Klient Etapy",
        )
    )
    worker_store.save_new(
        WorkerDef(
            name="Wolodymyr",
            role="Montaz",
            pay_mode="Godzinowa",
            hourly_rate=50.0,
            overtime_multiplier=1.5,
            delegation_day_addon_pln=120.0,
            montage_hour_addon_pln=10.0,
            lacquer_hour_addon_pln=3.0,
        )
    )
    work_time_store.save_sheet(
        WorkerMonthSheetDef(
            worker_name="Wolodymyr",
            year=2026,
            month=3,
            entries=[
                WorkTimeEntryDef(
                    day=1,
                    date_iso="2026-03-01",
                    work_type="Montaz",
                    hours=8.0,
                    overtime_hours=2.0,
                    project_code="ORDER-WYCENA-03",
                ),
                WorkTimeEntryDef(
                    day=2,
                    date_iso="2026-03-02",
                    work_type="Delegacja / wyjazd",
                    hours=8.0,
                    project_code="KOMPLET-WYCENA-03",
                ),
                WorkTimeEntryDef(
                    day=3,
                    date_iso="2026-03-03",
                    work_type="Lakiernia",
                    hours=4.0,
                    extra_pay=20.0,
                    project_code="ORDER-WYCENA-03",
                ),
            ],
        )
    )

    w = TabWycena(
        assembly_store=assembly_store,
        worker_store=worker_store,
        work_time_store=work_time_store,
    )
    w.tbl_assemblies.selectRow(0)

    assert w.lab_time_days.text() == "3"
    assert w.lab_time_hours.text() == "20.00 h"
    assert w.lab_time_overtime.text() == "150.00 zl"
    assert w.lab_time_stage_extra.text() == "212.00 zl"
    assert w.lab_time_extra.text() == "20.00 zl"
    assert w.lab_time_cost.text() == "1382.00 zl"

    QTest.mouseClick(w.btn_load_labor_from_time, Qt.MouseButton.LeftButton)

    assert float(w.sp_labor.value()) == 1382.0
