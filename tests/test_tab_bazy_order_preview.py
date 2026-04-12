from PyQt6.QtWidgets import QApplication


def _find_row_by_first_col(table, value: str) -> int:
    wanted = str(value or "").strip()
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and str(item.text() or "").strip() == wanted:
            return row
    return -1


def test_tab_bazy_orders_has_preview_table_with_costs_and_time(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])
    _ = app

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.domain.order_models import OrderDef
    from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef
    from src.domain.worker_models import WorkerDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-PREVIEW-1",
            client_name="Client A",
            status="Nowe",
            quote_items=[{"name": "Szafka", "kind": "Modul", "quantity": "2"}],
            material_choices=[{"scope": "Front", "material": "MDF", "color": "Bialy", "status": "Wybrane finalnie"}],
        )
    )

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-PREVIEW-1",
            order_name="ORD-PREVIEW-1",
            labor_cost_pln=120.0,
            transport_cost_pln=30.0,
            montage_cost_pln=50.0,
        )
    )

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.save_new(
        WorkerDef(
            name="Jan Worker",
            pay_mode="Godzinowa",
            hourly_rate=50.0,
        )
    )

    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    work_time_store.save_sheet(
        WorkerMonthSheetDef(
            worker_name="Jan Worker",
            year=2026,
            month=4,
            entries=[
                WorkTimeEntryDef(
                    entry_id="T1",
                    day=1,
                    date_iso="2026-04-01",
                    work_type="Praca na miejscu",
                    hours=2.0,
                    overtime_hours=0.0,
                    extra_pay=0.0,
                    project_code="ORD-PREVIEW-1",
                )
            ],
        )
    )

    w = TabBazy(
        order_store=order_store,
        assembly_store=assembly_store,
        worker_store=worker_store,
        work_time_store=work_time_store,
    )
    w._reload_orders_tab()

    assert hasattr(w, "tbl_order_preview")
    assert w._order_editor_hidden.isVisible() is False
    assert w.btn_order_clear.isVisible() is False
    assert w.tbl_order_preview.rowCount() >= 3

    summary_row = _find_row_by_first_col(w.tbl_order_preview, "RAZEM")
    assert summary_row >= 0
    assert w.tbl_order_preview.item(summary_row, 4).text() == "200.00"
    assert w.tbl_order_preview.item(summary_row, 5).text() == "2.00"
    assert "Koszt czasu pracy: 100.00 zl" in w.lab_order_preview_info.text()
