from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from src.api import main_api
from src.api.data_manager import TechModulDataManager
import src.storage.work_time_store_json as work_time_store_json
import src.storage.worker_store_json as worker_store_json
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson


def test_global_finance_summary_exposes_hour_costs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    db_path = tmp_path / "global_finance_summary.db"
    manager = TechModulDataManager(db_path=str(db_path))
    manager.create_project("P_GFS", "Client GFS")
    expense_store = CompanyExpensesStoreJson()
    expense_store.save_items("fixed", [{"name": "Wynajem", "amount": 1600.0}])
    expense_store.save_workforce(workers_count=2, hours_per_worker=160.0)

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                payment_method TEXT,
                date TEXT,
                notes TEXT
            )
            """
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "Client GFS", "Order 1", "2026-06-11", 5000.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO payments (amount, payment_method, date, notes) VALUES (?, ?, ?, ?)",
            (123.45, "gotowka", "2026-04-26", "cash test"),
        )
        conn.commit()

    fake_worker_with_rate = SimpleNamespace(
        name="Worker A",
        hourly_rate=50.0,
        daily_rate=0.0,
        pay_mode="Godzinowa",
        overtime_multiplier=1.0,
        delegation_day_addon_pln=0.0,
        montage_hour_addon_pln=10.0,
        onsite_hour_addon_pln=0.0,
        lacquer_hour_addon_pln=5.0,
    )
    fake_worker_missing_rate = SimpleNamespace(
        name="Worker B",
        hourly_rate=0.0,
        daily_rate=0.0,
        pay_mode="Godzinowa",
        overtime_multiplier=1.0,
        delegation_day_addon_pln=0.0,
        montage_hour_addon_pln=0.0,
        onsite_hour_addon_pln=0.0,
        lacquer_hour_addon_pln=0.0,
    )

    fake_sheets = [
        SimpleNamespace(
            worker_name="Worker A",
            year=2026,
            month=4,
            entries=[
                SimpleNamespace(
                    day=1,
                    date_iso="2026-04-01",
                    work_type="Montaz",
                    hours=4.0,
                    overtime_hours=0.0,
                    extra_pay=0.0,
                    project_code="",
                ),
                SimpleNamespace(
                    day=2,
                    date_iso="2026-04-02",
                    work_type="Lakiernia",
                    hours=2.0,
                    overtime_hours=0.0,
                    extra_pay=0.0,
                    project_code="",
                ),
            ],
        ),
    ]

    class FakeWorkStore:
        def list_sheets(self):
            return fake_sheets

    class FakeWorkerStore:
        def list_workers(self):
            return [fake_worker_with_rate, fake_worker_missing_rate]

    previous_manager = main_api.data_manager
    previous_kiosk = main_api.kiosk_service
    try:
        monkeypatch.setattr(work_time_store_json, "WorkTimeStoreJson", FakeWorkStore)
        monkeypatch.setattr(worker_store_json, "WorkerStoreJson", FakeWorkerStore)
        main_api.data_manager = manager
        main_api.kiosk_service = SimpleNamespace(list_workers=lambda: [{"worker_id": "W1"}, {"worker_id": "W2"}])

        payload = asyncio.run(main_api.get_global_finance_summary())
    finally:
        main_api.data_manager = previous_manager
        main_api.kiosk_service = previous_kiosk

    assert payload["finance"]["cash_in_hand"] == 123.45
    assert payload["production"]["total_orders"] == 1
    assert payload["production"]["active_projects"] >= 1

    assert payload["hr"]["total_hours"] == 6.0
    assert payload["hr"]["estimated_payroll_net"] == 350.0
    assert payload["hr"]["average_hour_cost"] == 63.33
    assert payload["hr"]["direct_hour_cost"] == 58.33
    assert payload["hr"]["active_workers"] == 2
    assert payload["hr"]["workers_total"] == 2
    assert payload["hr"]["workers_with_rate"] == 1
    assert payload["hr"]["workers_missing_rate"] == 1
    assert payload["hr"]["payroll_confidence"] == "PARTIAL"

    assert payload["cost_insights"]["fixed_overhead_monthly"] == 1600.0
    assert payload["cost_insights"]["overhead_hour_cost"] == 5.0
    assert payload["cost_insights"]["employee_hour_cost"] == 63.33
    assert payload["cost_insights"]["service_hour_cost"] == 65.0
    assert payload["cost_insights"]["lacquer_hour_cost"] == 60.0
    assert payload["cost_insights"]["production_hour_cost"] == 60.0
    assert payload["cost_insights"]["confidence"] == "PARTIAL"
    assert payload["cost_insights"]["notes"]
