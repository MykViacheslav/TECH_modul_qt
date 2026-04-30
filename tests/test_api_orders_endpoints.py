from __future__ import annotations

from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager
from fastapi import HTTPException


def test_create_and_list_orders_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "orders_test.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_ORDERS", "Client Orders")

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager

        create_payload = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Klient A",
                title="Kuchnia test",
                deadline="2026-05-01",
                deadline_from="2026-04-30",
                deadline_to="2026-05-01",
                budget=12345.0,
                status="DRAFT",
            )
        )
        assert create_payload["status"] == "success"
        assert int(create_payload["id"]) > 0

        listed = main_api.get_orders()
        assert len(listed) >= 1
        first = listed[0]
        assert int(first["project_id"]) == project_id
        assert first["client_name"] == "Klient A"
        assert first["title"] == "Kuchnia test"
        assert first["deadline_from"] == "2026-04-30"
        assert first["deadline_to"] == "2026-05-01"
        assert str(first["status"]).upper() == "DRAFT"

        events = manager.get_project_calendar_events(project_id=project_id)
        assert len(events) >= 1
        matching = [e for e in events if int(e["order_id"]) == int(create_payload["id"])]
        assert len(matching) == 1
        assert matching[0]["date_from"] == "2026-04-30"
        assert matching[0]["date_to"] == "2026-05-01"
    finally:
        main_api.data_manager = previous_manager


def test_list_orders_can_filter_by_project(tmp_path: Path) -> None:
    db_path = tmp_path / "orders_filter_test.db"
    manager = TechModulDataManager(db_path=str(db_path))
    p1 = manager.create_project("P1", "Client 1")
    p2 = manager.create_project("P2", "Client 2")

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager

        main_api.create_order(
            main_api.OrderCreate(
                project_id=p1,
                client_name="Client 1",
                title="Order P1",
                budget=1000.0,
                status="DRAFT",
            )
        )
        main_api.create_order(
            main_api.OrderCreate(
                project_id=p2,
                client_name="Client 2",
                title="Order P2",
                budget=2000.0,
                status="DRAFT",
            )
        )

        filtered = main_api.get_orders(project_id=p1)
    finally:
        main_api.data_manager = previous_manager

    assert len(filtered) == 1
    assert int(filtered[0]["project_id"]) == p1
    assert filtered[0]["title"] == "Order P1"


def test_create_order_rejects_invalid_deadline_range(tmp_path: Path) -> None:
    db_path = tmp_path / "orders_invalid_range.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_BAD_RANGE", "Client BR")

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        try:
            main_api.create_order(
                main_api.OrderCreate(
                    project_id=project_id,
                    client_name="Klient X",
                    title="Bad range",
                    deadline_from="2026-05-20",
                    deadline_to="2026-05-10",
                )
            )
            assert False, "Expected HTTPException for invalid range"
        except HTTPException as exc:
            assert exc.status_code == 400
    finally:
        main_api.data_manager = previous_manager
