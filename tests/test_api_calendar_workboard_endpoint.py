from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


class _RouteStub:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "ROUTE-1")
        self.project_name = kwargs.get("project_name", "P_CAL_WORK")
        self.project_id = kwargs.get("project_id", "")
        self.client_name = kwargs.get("client_name", "Client A")
        self.task_type = kwargs.get("task_type", "cnc")
        self.status = kwargs.get("status", "w_trakcie")
        self.planned_date = kwargs.get("planned_date", "2026-06-12")
        self.crew = kwargs.get("crew", "Marek")
        self.issue_id = kwargs.get("issue_id", "ISS-1")


class _IssueStub:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "ISS-1")
        self.project_name = kwargs.get("project_name", "P_CAL_WORK")
        self.project_id = kwargs.get("project_id", "")
        self.client_name = kwargs.get("client_name", "Client A")
        self.title = kwargs.get("title", "Brak materialu")
        self.status = kwargs.get("status", "nowe")
        self.priority_manual = kwargs.get("priority_manual", "normalny")
        self.owner = kwargs.get("owner", "Jan")
        self.due_date = kwargs.get("due_date", "2026-06-15")
        self.created_at = kwargs.get("created_at", "2026-06-10 09:00:00")
        self._is_overdue = bool(kwargs.get("is_overdue", False))

    def is_overdue(self) -> bool:
        return self._is_overdue


class _OperationsStoreStub:
    def list_routes(self):
        return [
            _RouteStub(
                id="ROUTE-A",
                project_name="P_CAL_WORK",
                task_type="oklejanie",
                status="planowane",
                planned_date="2026-06-11",
                crew="Marek, Ola",
            )
        ]

    def filter_issues(self, active_only: bool = False):
        return [
            _IssueStub(
                id="ISS-A",
                project_name="P_CAL_WORK",
                title="Krytyczna poprawka",
                priority_manual="krytyczny",
                is_overdue=True,
                owner="Jan",
                due_date="2026-06-01",
            )
        ]


class _KioskServiceStub:
    def list_workers(self):
        return [
            {"name": "Marek", "active": True, "session": {"project_code": "P_CAL_WORK"}},
            {"name": "Ola", "active": True, "session": {"project_code": "P_CAL_WORK"}},
            {"name": "Nieaktywny", "active": False, "session": {}},
        ]


@contextmanager
def _patched_globals(manager: TechModulDataManager):
    previous_manager = main_api.data_manager
    previous_kiosk = main_api.kiosk_service
    import src.core.operations_store as operations_store_module

    previous_ops_cls = operations_store_module.OperationsStore
    try:
        main_api.data_manager = manager
        main_api.kiosk_service = _KioskServiceStub()
        operations_store_module.OperationsStore = _OperationsStoreStub
        yield
    finally:
        main_api.data_manager = previous_manager
        main_api.kiosk_service = previous_kiosk
        operations_store_module.OperationsStore = previous_ops_cls


def test_calendar_workboard_returns_merged_work_items(tmp_path: Path) -> None:
    db_path = tmp_path / "calendar_workboard.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_CAL_WORK", "Client CAL")
    manager.create_order(
        project_id=project_id,
        client_name="Client CAL",
        title="Order C",
        deadline_from="2026-06-10",
        deadline_to="2026-06-12",
    )

    with _patched_globals(manager):
        payload = asyncio.run(
            main_api.get_calendar_workboard(
                project_id=project_id,
                days_back=60,
                days_forward=120,
                limit=200,
                include_undated=True,
            )
        )

    assert payload["status"] == "ok"
    assert int(payload["project_id"]) == project_id
    assert str(payload["project_title"]) == "P_CAL_WORK"
    assert int(payload["summary"]["total_items"]) >= 3
    assert int(payload["summary"]["active_workers_count"]) == 2
    assert payload["confidence"] in {"READY", "PARTIAL"}

    kinds = {str(item.get("kind")) for item in payload["items"]}
    assert "order_event" in kinds
    assert "production_task" in kinds
    assert "issue" in kinds

    issue_items = [item for item in payload["items"] if str(item.get("kind")) == "issue"]
    assert issue_items
    assert issue_items[0]["color_key"] == "red"
    assert issue_items[0]["is_overdue"] is True


def test_calendar_workboard_filters_by_project(tmp_path: Path) -> None:
    db_path = tmp_path / "calendar_workboard_scope.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_a = manager.create_project("P_A", "Client A")
    project_b = manager.create_project("P_B", "Client B")
    manager.create_order(
        project_id=project_a,
        client_name="Client A",
        title="Order A",
        deadline_from="2026-07-10",
        deadline_to="2026-07-11",
    )
    manager.create_order(
        project_id=project_b,
        client_name="Client B",
        title="Order B",
        deadline_from="2026-08-10",
        deadline_to="2026-08-11",
    )

    with _patched_globals(manager):
        payload_a = asyncio.run(main_api.get_calendar_workboard(project_id=project_a))
        payload_b = asyncio.run(main_api.get_calendar_workboard(project_id=project_b))

    order_items_a = [item for item in payload_a["items"] if item.get("source") == "order_calendar"]
    order_items_b = [item for item in payload_b["items"] if item.get("source") == "order_calendar"]
    assert len(order_items_a) == 1
    assert len(order_items_b) == 1
    assert str(order_items_a[0]["title"]) == "Order A"
    assert str(order_items_b[0]["title"]) == "Order B"
    assert payload_a["project_title"] == "P_A"
    assert payload_b["project_title"] == "P_B"
