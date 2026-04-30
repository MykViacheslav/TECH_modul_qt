from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_project_mvp_readiness_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "mvp_readiness.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = 987654

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, title, client_name) VALUES (?, ?, ?)",
            (project_id, "P_MVP", "Client MVP"),
        )
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_id, "MVP_MOD", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client MVP", "Order MVP", "2026-09-01", 1000.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO materials (name, price_per_m2, thickness) VALUES (?, ?, ?)",
            ("MVP Material", 10.0, 18),
        )
        cursor.execute(
            "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
            ("MVP Client", "Warszawa", "person", "active"),
        )
        conn.commit()

    wall_name = f"WEB_PROJECT_{project_id}"
    asyncio.run(
        main_api.apply_wall_operation(
            main_api.WallOperationRequest(
                action="wall.add_point",
                target=main_api.OperationTargetPayload(name=wall_name),
                params={"point_type": "bolt", "x_mm": 100, "y_mm": 100, "point_id": "mvp_ready_pt"},
                source="pytest",
            )
        )
    )

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = main_api.get_project_mvp_readiness(project_id)
    finally:
        main_api.data_manager = previous_manager

    assert payload["project_id"] == project_id
    assert payload["ready"] is True
    assert payload["missing"] == []
    assert payload["missing_labels"] == []
    assert payload["missing_details"] == []
    assert int(payload["score"]["passed_checks"]) == 5
    assert int(payload["score"]["total_checks"]) == 5
    assert int(payload["score"]["percent"]) == 100
    assert payload["next_actions"] == []
    assert payload["next_action"] is None
