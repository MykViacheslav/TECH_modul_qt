from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


@contextmanager
def _patched_globals(
    manager: TechModulDataManager,
    *,
    operations_store_cls=None,
    kiosk_service=None,
    work_time_store=None,
):
    previous_manager = main_api.data_manager
    previous_kiosk = main_api.kiosk_service
    previous_work_time = main_api.work_time_store
    previous_ops_cls = None

    if operations_store_cls is not None:
        import src.core.operations_store as operations_store_module

        previous_ops_cls = operations_store_module.OperationsStore
        operations_store_module.OperationsStore = operations_store_cls

    try:
        main_api.data_manager = manager
        if kiosk_service is not None:
            main_api.kiosk_service = kiosk_service
        if work_time_store is not None:
            main_api.work_time_store = work_time_store
        yield
    finally:
        main_api.data_manager = previous_manager
        main_api.kiosk_service = previous_kiosk
        main_api.work_time_store = previous_work_time
        if previous_ops_cls is not None:
            import src.core.operations_store as operations_store_module

            operations_store_module.OperationsStore = previous_ops_cls


class _IssueStub:
    def __init__(self, *, overdue: bool, priority_manual: str, status: str = "otwarte") -> None:
        self.priority_manual = priority_manual
        self.status = status
        self._overdue = overdue

    def is_overdue(self) -> bool:
        return self._overdue


class _RouteStub:
    def __init__(self, *, task_type: str, planned_date: str, status: str = "aktywne") -> None:
        self.task_type = task_type
        self.planned_date = planned_date
        self.status = status


class _OperationsStoreStub:
    def list_issues(self):
        return [
            _IssueStub(overdue=True, priority_manual="krytyczny"),
            _IssueStub(overdue=False, priority_manual="normalny"),
        ]

    def list_routes(self):
        return [
            _RouteStub(task_type="ciecie", planned_date="2026-04-01"),
            _RouteStub(task_type="montaz", planned_date="2026-05-01"),
        ]

    def list_priority_candidates(self, status: str = "all"):
        return [1, 2, 3]


class _KioskServiceStub:
    def list_workers(self):
        return [
            {
                "active": True,
                "session": {"project_code": "PRJ-1", "order_id": "12", "workstation": "st-1"},
            },
            {
                "active": True,
                "session": {"project_code": "", "order_id": "", "workstation": ""},
            },
            {"active": False, "session": {}},
        ]


class _WorkTimeStoreReadyStub:
    class _Entry:
        def __init__(self, date_iso: str, hours: float):
            self.date_iso = date_iso
            self.hours = hours

    class _Sheet:
        def __init__(self, entries):
            self.entries = entries

    def list_sheets(self):
        return [self._Sheet([self._Entry("2026-04-20", 8.0), self._Entry("2026-04-24", 6.5)])]


class _WorkTimeStoreFailStub:
    def list_sheets(self):
        raise RuntimeError("store offline")


def _seed_orders_and_service_rows(db_path: Path, project_id: int) -> None:
    service_rows = [
        {
            "serviceMode": "service-cut-edge",
            "servicePricing": {
                "pricing_status": "manual_review",
                "manual_review_reasons": ["missing_base_material_id", "missing_edge_material"],
                "validation_flags": ["edge_config_incomplete"],
            },
        },
        {
            "serviceMode": "service-front-cnc-lacquer",
            "servicePricing": {
                "pricing_status": "ready",
                "manual_review_reasons": [],
                "validation_flags": [],
            },
        },
    ]
    spec_json = {"service_rows": service_rows}

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status, spec_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                "Client D1",
                "Order D1",
                "2026-05-10",
                10000.0,
                "DRAFT",
                json.dumps(spec_json),
            ),
        )
        conn.commit()


def _seed_invoice(manager: TechModulDataManager) -> None:
    imported = manager.import_invoice_with_lines(
        invoice_nr="FV-DASH-1",
        invoice_date="2026-04-24",
        nip="1234567890",
        supplier="SUP-D",
        currency="PLN",
        total_net=100.0,
        total_vat=23.0,
        total_gross=123.0,
        payload_hash="dash-hash-1",
        source_filename="dash.pdf",
        parse_method="test",
        parse_confidence=0.99,
        line_items=[
            {
                "name": "L1",
                "raw_line": "L1",
                "quantity": 1.0,
                "unit": "szt",
                "unit_price_net": 100.0,
                "unit_price_gross": 123.0,
                "total_price_net": 100.0,
                "total_price_gross": 123.0,
                "confidence": 0.55,
            }
        ],
    )
    assert imported["is_duplicate"] is False


def test_dashboard_v1_payload_contains_operational_blocks(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard_v1.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_DASH", "Client DASH")
    _seed_orders_and_service_rows(db_path, project_id)
    manager.create_material(name="Mat low", price_per_m2=9.0, thickness=18, unit="m2", stock_quantity=0.0, min_stock=10.0)
    manager.add_arrival(
        material_id=1,
        quantity=5,
        price_total=50,
        unit="m2",
        purchase_type="invoice",
        document_nr="ARR-1",
        arrival_date="2026-04-24",
    )
    _seed_invoice(manager)

    with _patched_globals(
        manager,
        operations_store_cls=_OperationsStoreStub,
        kiosk_service=_KioskServiceStub(),
        work_time_store=_WorkTimeStoreReadyStub(),
    ):
        payload = main_api.get_dashboard_v1(period_days=30, top_limit=5)

    assert payload["period_days"] == 30
    assert "operational_summary" in payload
    assert "pricing_quality" in payload
    assert "production_risk" in payload
    assert "kiosk_labor_activity" in payload
    assert "materials_procurement" in payload
    assert "invoice_processing_control" in payload

    assert payload["operational_summary"]["source_route"] == "/workspace"
    assert payload["pricing_quality"]["source_route"] == "/orders/new"
    assert payload["production_risk"]["source_route"] == "/operations"
    assert payload["kiosk_labor_activity"]["source_route"] == "/time-tracking"
    assert payload["materials_procurement"]["source_route"] == "/database/warehouse"
    assert payload["invoice_processing_control"]["source_route"] == "/database/invoices"

    assert int(payload["pricing_quality"]["total_service_items"]) == 2
    assert int(payload["pricing_quality"]["ready_items_count"]) == 1
    assert int(payload["pricing_quality"]["manual_review_items_count"]) == 1
    assert int(payload["pricing_quality"]["missing_mandatory_inputs_count"]) >= 1
    assert int(payload["production_risk"]["critical_issues_count"]) == 1
    assert int(payload["kiosk_labor_activity"]["active_kiosk_sessions_count"]) == 2
    assert int(payload["kiosk_labor_activity"]["sessions_missing_linkage_count"]) == 1
    assert int(payload["materials_procurement"]["low_stock_materials_count"]) >= 1
    assert int(payload["invoice_processing_control"]["imported_invoices_count"]) >= 1
    assert int(payload["invoice_processing_control"]["low_confidence_line_count"]) >= 1


def test_dashboard_v1_sets_partial_confidence_when_sources_incomplete(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard_v1_partial.db"
    manager = TechModulDataManager(db_path=str(db_path))
    manager.create_project("P_DASH_EMPTY", "Client DASH EMPTY")

    with _patched_globals(
        manager,
        operations_store_cls=_OperationsStoreStub,
        kiosk_service=_KioskServiceStub(),
        work_time_store=_WorkTimeStoreFailStub(),
    ):
        payload = main_api.get_dashboard_v1(period_days=14, top_limit=3)

    assert payload["period_days"] == 14
    assert payload["pricing_quality"]["confidence"] == "PARTIAL"
    assert payload["kiosk_labor_activity"]["confidence"] == "PARTIAL"
    assert payload["kiosk_labor_activity"]["logged_hours_quality"] == "PARTIAL"


def test_dashboard_v1_uses_confidence_contract_and_avoids_fake_finance_board(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard_v1_contract.db"
    manager = TechModulDataManager(db_path=str(db_path))
    manager.create_project("P_DASH_CONTRACT", "Client DASH CONTRACT")

    with _patched_globals(
        manager,
        operations_store_cls=_OperationsStoreStub,
        kiosk_service=_KioskServiceStub(),
        work_time_store=_WorkTimeStoreReadyStub(),
    ):
        payload = main_api.get_dashboard_v1(period_days=7, top_limit=3)

    block_names = [
        "operational_summary",
        "pricing_quality",
        "production_risk",
        "kiosk_labor_activity",
        "materials_procurement",
        "invoice_processing_control",
    ]
    for block in block_names:
        assert "confidence" in payload[block]
        assert payload[block]["confidence"] in {"READY", "PARTIAL"}
        assert isinstance(payload[block].get("source_route", ""), str)
        assert payload[block]["source_route"].startswith("/")

    # Dashboard V1 is operational only: no executive-finance board payload here.
    forbidden_top_level = {"finance", "profit", "forecast", "pnl", "cashflow"}
    assert forbidden_top_level.isdisjoint(set(payload.keys()))
