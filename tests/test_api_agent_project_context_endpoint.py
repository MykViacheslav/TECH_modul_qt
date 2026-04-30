from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_agent_command_uses_requested_project_context(tmp_path: Path) -> None:
    db_path = tmp_path / "agent_project_context.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_1 = manager.create_project("P1", "Client 1")
    project_2 = manager.create_project("P2", "Client 2")

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_1, "M_P1", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_2, "M_P2", 900, 720, 500),
        )
        conn.commit()

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        response = asyncio.run(
            main_api.execute_agent_command(
                main_api.CommandRequest(text="ustaw szerokosc na 700", project_id=project_2)
            )
        )
    finally:
        main_api.data_manager = previous_manager

    assert response["type"] == "preview"
    assert len(response["changes"]) == 1
    change = response["changes"][0]
    assert change["name"] == "M_P2"
    assert int(change["old"]) == 900
    assert int(change["new"]) == 700
