from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_projects_mvp_readiness_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "projects_mvp_readiness_summary.db"
    manager = TechModulDataManager(db_path=str(db_path))
    ready_project_id = 770001
    not_ready_project_id = 770002

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, title, client_name) VALUES (?, ?, ?)",
            (ready_project_id, "P_READY", "Client Ready"),
        )
        cursor.execute(
            "INSERT INTO projects (id, title, client_name) VALUES (?, ?, ?)",
            (not_ready_project_id, "P_NOT_READY", "Client Not Ready"),
        )
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (ready_project_id, "READY_MOD", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (ready_project_id, "Client Ready", "Order Ready", "2026-10-01", 1500.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO materials (name, price_per_m2, thickness) VALUES (?, ?, ?)",
            ("READY_MATERIAL", 12.5, 18),
        )
        cursor.execute(
            "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
            ("READY_CLIENT", "Warszawa", "person", "active"),
        )
        conn.commit()

    wall_name = f"WEB_PROJECT_{ready_project_id}"
    asyncio.run(
        main_api.apply_wall_operation(
            main_api.WallOperationRequest(
                action="wall.add_point",
                target=main_api.OperationTargetPayload(name=wall_name),
                params={"point_type": "bolt", "x_mm": 120, "y_mm": 220, "point_id": "ready_summary_pt"},
                source="pytest",
            )
        )
    )

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = main_api.get_projects_mvp_readiness_summary()
    finally:
        main_api.data_manager = previous_manager

    assert payload["total_projects"] == 2
    assert payload["ready_projects"] == 1
    assert payload["not_ready_projects"] == 1
    assert float(payload["avg_readiness_score"]) == 70.0
    assert int(payload["readiness_bands"]["critical"]) == 1
    assert int(payload["readiness_bands"]["risk"]) == 0
    assert int(payload["readiness_bands"]["ready"]) == 1
    assert isinstance(payload["generated_at"], str)
    assert "T" in payload["generated_at"]
    assert int(payload["blocking_reasons"]["has_modules"]) == 1
    assert int(payload["blocking_reasons"]["has_orders"]) == 1
    assert int(payload["blocking_reasons"]["has_wall_points"]) == 1
    assert len(payload["blocking_reasons_details"]) >= 3
    labels = {str(item["check"]): str(item["label"]) for item in payload["blocking_reasons_details"]}
    assert labels["has_modules"] == "Brak modułów"
    assert labels["has_orders"] == "Brak zamówień"
    assert payload["projects"][0]["project_id"] == not_ready_project_id
    assert int(payload["projects"][0]["readiness_score"]) == 40
    assert int(payload["projects"][1]["readiness_score"]) == 100
    assert isinstance(payload["projects"][0]["next_actions"], list)
    assert isinstance(payload["projects"][0]["missing_details"], list)
    assert isinstance(payload["projects"][0]["missing_labels"], list)
    assert len(payload["projects"][0]["next_actions"]) >= 1
    assert isinstance(payload["projects"][0]["next_actions"][0]["route"], str)
    action_codes = [str(item["code"]) for item in payload["action_queue"]]
    assert "add_module" in action_codes
    assert "create_order" in action_codes
    assert "add_wall_point" in action_codes
    by_code = {str(item["code"]): item for item in payload["action_queue"]}
    assert int(by_code["add_module"]["affected_projects"]) == 1
    assert str(by_code["add_module"]["route"]) == "/configuration"
    assert str(by_code["create_order"]["route"]) == "/orders/new"
    assert str(by_code["add_wall_point"]["route"]) == "/wall"
    assert str(payload["next_global_action"]["code"]) == "add_module"
    assert str(payload["next_global_action"]["route"]) == "/configuration"

    by_project = {int(item["project_id"]): item for item in payload["projects"]}
    assert by_project[ready_project_id]["ready"] is True
    assert by_project[not_ready_project_id]["ready"] is False
    assert by_project[not_ready_project_id]["missing_count"] >= 1
    assert str(by_project[not_ready_project_id]["next_action"]["code"]) == "add_module"
