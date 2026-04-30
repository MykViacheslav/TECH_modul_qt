from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_workspace_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_summary.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_WS", "Client WS")

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_id, "M1", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client WS", "Order 1", "2026-06-20", 10000.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client WS", "Order 2", "2026-07-01", 5000.0, "PENDING"),
        )
        conn.commit()

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = asyncio.run(main_api.get_project_workspace_summary(project_id))
    finally:
        main_api.data_manager = previous_manager

    assert payload["project_id"] == project_id
    assert payload["project_title"] == "P_WS"
    assert payload["client_name"] == "Client WS"
    assert int(payload["modules_count"]) == 1
    assert int(payload["orders_count"]) == 2
    assert int(payload["draft_orders_count"]) == 1
    assert float(payload["total_budget"]) == 15000.0
    assert payload["latest_deadline"] == "2026-07-01"
