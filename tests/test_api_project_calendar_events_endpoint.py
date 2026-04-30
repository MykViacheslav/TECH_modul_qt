from __future__ import annotations

import asyncio
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_project_calendar_events_endpoint_returns_events_for_project(tmp_path: Path) -> None:
    db_path = tmp_path / "calendar_events_endpoint.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_CAL", "Client CAL")

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        created = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Client CAL",
                title="Order CAL",
                deadline_from="2026-06-10",
                deadline_to="2026-06-12",
            )
        )
        payload = asyncio.run(main_api.get_project_calendar_events(project_id))
    finally:
        main_api.data_manager = previous_manager

    assert int(payload["project_id"]) == project_id
    assert len(payload["events"]) >= 1
    matched = [event for event in payload["events"] if int(event["order_id"]) == int(created["id"])]
    assert len(matched) == 1
    assert matched[0]["date_from"] == "2026-06-10"
    assert matched[0]["date_to"] == "2026-06-12"
