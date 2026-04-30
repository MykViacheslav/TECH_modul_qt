from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_project_assembly_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "tech_modul_test.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_SUMMARY", "Client")

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_id, "M1", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_id, "M2", 800, 700, 520),
        )
        conn.commit()

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = asyncio.run(main_api.get_project_assembly_summary(project_id))
    finally:
        main_api.data_manager = previous_manager

    assert payload["project_id"] == project_id
    assert payload["modules_count"] == 2
    assert float(payload["total_width_mm"]) == 1400.0
    assert float(payload["total_height_mm"]) == 1420.0
    assert float(payload["total_depth_mm"]) == 1020.0
    assert float(payload["total_volume_l"]) == 507.2
    assert float(payload["avg_width_mm"]) == 700.0
    assert float(payload["avg_height_mm"]) == 710.0
    assert float(payload["avg_depth_mm"]) == 510.0
