import json
from pathlib import Path

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
    mode_idx = w.cb_quote_mode.findData("assemblies")
    if mode_idx >= 0:
        w.cb_quote_mode.setCurrentIndex(mode_idx)

    idx = w.cb_order.findData("ORDER-B")
    assert idx >= 0
    w.cb_order.setCurrentIndex(idx)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-B"


def test_wycena_tab_open_assembly_locks_order_context(tmp_path, monkeypatch):
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

    w.open_assembly_for_pricing("KOMPLET-B")

    assert str(w.cb_quote_mode.currentData() or "") == "assemblies"
    assert str(w.cb_order.currentData() or "") == "ORDER-B"
    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-B"
    assert w._selected_name() == "KOMPLET-B"


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


def test_wycena_tab_quick_mode_can_filter_by_quick_quote_id(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setattr(
        "src.tabs.wycena.tab_wycena.quick_quote_archive_path",
        lambda: tmp_path / "quick_quote_archive.json",
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.wycena.tab_wycena import TabWycena

    payload = [
        {"id": "Q001", "client": "K0001", "price": "100.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
        {"id": "Q002", "client": "K0002", "price": "200.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
    ]
    (tmp_path / "quick_quote_archive.json").write_text(json.dumps(payload), encoding="utf-8")

    w = TabWycena()
    idx_mode = w.cb_quote_mode.findData("quick")
    assert idx_mode >= 0
    w.cb_quote_mode.setCurrentIndex(idx_mode)

    assert w.tbl_assemblies.rowCount() == 2
    idx_pick = w.cb_quick_pick.findData("Q002")
    assert idx_pick >= 0
    w.cb_quick_pick.setCurrentIndex(idx_pick)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "Q002"


def test_wycena_tab_quick_mode_can_add_and_remove_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setattr(
        "src.tabs.wycena.tab_wycena.quick_quote_archive_path",
        lambda: tmp_path / "quick_quote_archive.json",
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.wycena.tab_wycena import TabWycena

    payload = [
        {"id": "Q001", "client": "K0001", "price": "100.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
    ]
    archive_path = tmp_path / "quick_quote_archive.json"
    archive_path.write_text(json.dumps(payload), encoding="utf-8")

    w = TabWycena()
    idx_mode = w.cb_quote_mode.findData("quick")
    assert idx_mode >= 0
    w.cb_quote_mode.setCurrentIndex(idx_mode)

    assert w.tbl_assemblies.columnCount() == 7
    assert w.tbl_assemblies.horizontalHeaderItem(1).text() == "Klient"
    assert w.tbl_assemblies.rowCount() == 1

    monkeypatch.setattr(w, "_choose_quick_quote_id", lambda entries: "Q001")
    QTest.mouseClick(w.btn_quick_add, Qt.MouseButton.LeftButton)
    data_after_add = json.loads(archive_path.read_text(encoding="utf-8"))
    assert len(data_after_add) == 1
    assert w.tbl_assemblies.rowCount() == 1

    w.tbl_assemblies.selectRow(0)
    QTest.mouseClick(w.btn_quick_remove, Qt.MouseButton.LeftButton)
    data_after_remove = json.loads(archive_path.read_text(encoding="utf-8"))
    assert len(data_after_remove) == 0


def test_wycena_tab_quick_mode_allows_edit_vat_margin_price(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setattr(
        "src.tabs.wycena.tab_wycena.quick_quote_archive_path",
        lambda: tmp_path / "quick_quote_archive.json",
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.wycena.tab_wycena import TabWycena

    payload = [
        {"id": "Q001", "client": "K0001", "price": "100.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
    ]
    archive_path = tmp_path / "quick_quote_archive.json"
    archive_path.write_text(json.dumps(payload), encoding="utf-8")

    w = TabWycena()
    idx_mode = w.cb_quote_mode.findData("quick")
    assert idx_mode >= 0
    w.cb_quote_mode.setCurrentIndex(idx_mode)

    assert w.tbl_assemblies.rowCount() == 1
    for col in (2, 3):
        item = w.tbl_assemblies.item(0, col)
        assert item is not None
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEditable)
    material_item = w.tbl_assemblies.item(0, 4)
    assert material_item is not None
    assert not bool(material_item.flags() & Qt.ItemFlag.ItemIsEditable)

    vat_item = w.tbl_assemblies.item(0, 2)
    margin_item = w.tbl_assemblies.item(0, 3)
    assert vat_item is not None
    assert margin_item is not None

    vat_item.setText("8")
    margin_item = w.tbl_assemblies.item(0, 3)
    assert margin_item is not None
    margin_item.setText("12.5")

    data = json.loads(archive_path.read_text(encoding="utf-8"))
    assert data[0]["vat"] == "8%"
    assert data[0]["margin"] == "12.50%"
    assert data[0]["price"] == "100.00 zl"


def test_wycena_tab_quick_mode_uses_real_hour_rate_from_expenses(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setattr(
        "src.tabs.wycena.tab_wycena.quick_quote_archive_path",
        lambda: tmp_path / "quick_quote_archive.json",
    )

    app = QApplication.instance() or QApplication([])

    from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    payload = [
        {"id": "Q001", "client": "K0001", "price": "100.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
    ]
    (tmp_path / "quick_quote_archive.json").write_text(json.dumps(payload), encoding="utf-8")

    expense_store = CompanyExpensesStoreJson()
    expense_store.save_items("fixed", [{"name": "Wynajem", "amount": 1600.0}])
    expense_store.save_items("variable", [{"name": "Paliwo", "amount": 3200.0}])
    expense_store.save_workforce(workers_count=2, hours_per_worker=160.0)  # 4800 / 320h = 15 zl/h

    w = TabWycena()
    idx_mode = w.cb_quote_mode.findData("quick")
    assert idx_mode >= 0
    w.cb_quote_mode.setCurrentIndex(idx_mode)
    w.tbl_assemblies.selectRow(0)

    w.sp_quick_hours.setValue(10.0)

    assert "15.00 zl/h" in w.lab_quick_rate.text()
    assert "150.00 zl" in w.lab_quick_labor_cost.text()
    assert w.tbl_assemblies.item(0, 5).text() == "250.00 zl"
    assert w.tbl_assemblies.item(0, 6).text() == "307.50 zl"


def test_wycena_tab_quick_mode_uses_selected_worker_hourly_rate(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setattr(
        "src.tabs.wycena.tab_wycena.quick_quote_archive_path",
        lambda: tmp_path / "quick_quote_archive.json",
    )

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    payload = [
        {"id": "Q001", "client": "K0001", "price": "100.00 zl", "vat": "23%", "margin": "0.00%", "sections": []},
    ]
    (tmp_path / "quick_quote_archive.json").write_text(json.dumps(payload), encoding="utf-8")

    expense_store = CompanyExpensesStoreJson()
    expense_store.save_items("fixed", [{"name": "Wynajem", "amount": 1600.0}])
    expense_store.save_items("variable", [{"name": "Paliwo", "amount": 3200.0}])
    expense_store.save_workforce(workers_count=2, hours_per_worker=160.0)  # fallback 15 zl/h

    worker_store = WorkerStoreJson()
    worker_store.save_new(WorkerDef(name="Monter 1", role="Montaz", pay_mode="Godzinowa", hourly_rate=60.0))

    w = TabWycena(worker_store=worker_store)
    idx_mode = w.cb_quote_mode.findData("quick")
    assert idx_mode >= 0
    w.cb_quote_mode.setCurrentIndex(idx_mode)
    w.tbl_assemblies.selectRow(0)

    idx_worker = w.cb_quick_worker.findData("Monter 1")
    assert idx_worker >= 0
    w.cb_quick_worker.setCurrentIndex(idx_worker)
    w.sp_quick_hours.setValue(2.0)

    assert "60.00 zl/h" in w.lab_quick_rate.text()
    assert "Monter 1" in w.lab_quick_rate_source.text()
    assert "120.00 zl" in w.lab_quick_labor_cost.text()


def test_wycena_tab_spinboxes_are_optimized_for_fast_amount_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from PyQt6.QtWidgets import QAbstractSpinBox

    from src.tabs.wycena.tab_wycena import TabWycena

    w = TabWycena()
    for spin in (w.sp_labor, w.sp_transport, w.sp_montage, w.sp_margin, w.sp_quick_transport, w.sp_quick_hours, w.sp_quick_montage):
        assert spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
        assert spin.keyboardTracking() is False


def test_wycena_tab_applies_pricing_policy_and_rules_to_editor_totals(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-POLICY-01",
            order_name="ORDER-P1",
            client_name="Klient P1",
            labor_cost_pln=100.0,
            margin_percent=0.0,
        )
    )

    w = TabWycena(assembly_store=assembly_store)
    w.tbl_assemblies.selectRow(0)
    w.sp_rule_processing.setValue(10.0)
    w.sp_rule_assembly.setValue(5.0)
    w.sp_rule_transport.setValue(20.0)
    idx_dealer = w.cb_policy.findData("dealer")
    assert idx_dealer >= 0
    w.cb_policy.setCurrentIndex(idx_dealer)
    w._refresh_editor_totals()

    # technical total is 0.00 for empty assembly, so rules add only flat transport
    assert w.lab_base_total.text() == "120.00 zl"
    assert w.lab_sale_total.text() == "110.40 zl"


def test_wycena_tab_role_visibility_hides_columns_for_production(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-ROLE-01", order_name="ORDER-R1", client_name="Klient R1"))

    w = TabWycena(assembly_store=assembly_store)
    idx_prod = w.cb_role.findData("production")
    assert idx_prod >= 0
    w.cb_role.setCurrentIndex(idx_prod)
    w._refresh_table()

    assert w.tbl_assemblies.isColumnHidden(5) is True
    assert w.tbl_assemblies.isColumnHidden(6) is True


def test_wycena_tab_exports_purchase_csv_and_profit_report(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena import tab_wycena as module

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-EXPORT-01", order_name="ORDER-E1", client_name="Klient E1"))

    w = module.TabWycena(assembly_store=assembly_store)
    w.tbl_assemblies.selectRow(0)

    export_csv = Path(tmp_path) / "zakup.csv"
    export_report = Path(tmp_path) / "rentownosc.txt"
    paths = [str(export_csv), str(export_report)]

    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (paths.pop(0), ""))

    w._on_export_purchase_csv()
    w._on_export_profitability_report()

    assert export_csv.exists()
    assert "Modul;Typ;Kod;Nazwa;Ilosc;Jednostka;Koszt [zl]" in export_csv.read_text(encoding="utf-8")
    assert export_report.exists()
    assert "Raport rentownosci" in export_report.read_text(encoding="utf-8")


def test_wycena_tab_owner_can_edit_policy_multipliers(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-MULT-01", order_name="ORDER-M1", client_name="Klient M1", labor_cost_pln=200.0))

    w = TabWycena(assembly_store=assembly_store)
    w.tbl_assemblies.selectRow(0)
    w.sp_policy_dealer.setValue(0.5)
    idx_dealer = w.cb_policy.findData("dealer")
    assert idx_dealer >= 0
    w.cb_policy.setCurrentIndex(idx_dealer)
    w._refresh_editor_totals()

    assert "x0.50" in w.lab_policy_info.text()
    assert w.lab_sale_total.text() == "100.00 zl"
