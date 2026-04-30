from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_db_overview_and_materials_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "db_overview.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_DB", "Client DB")

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
            (project_id, "M_DB", 600, 720, 500),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client DB", "Order DB", "2026-08-01", 9999.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO materials (name, price_per_m2, thickness) VALUES (?, ?, ?)",
            ("Material Test", 12.34, 18),
        )
        cursor.execute(
            "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
            ("Client Test", "Warszawa", "person", "active"),
        )
        conn.commit()

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        overview = asyncio.run(main_api.get_db_overview())
        materials = asyncio.run(main_api.get_materials())
    finally:
        main_api.data_manager = previous_manager

    assert int(overview["projects_count"]) >= 1
    assert int(overview["modules_count"]) >= 1
    assert int(overview["orders_count"]) >= 1
    assert int(overview["materials_count"]) >= 1
    assert int(overview["clients_count"]) >= 1
    assert len(materials) >= 1
    assert all("price" in row for row in materials)


def test_create_material_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "db_material_create.db"
    manager = TechModulDataManager(db_path=str(db_path))

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        created = asyncio.run(
            main_api.create_material(
                main_api.MaterialCreate(name="Material New", price_per_m2=55.5, thickness=19)
            )
        )
        assert created["status"] == "success"
        assert int(created["id"]) > 0
        materials = asyncio.run(main_api.get_materials())
    finally:
        main_api.data_manager = previous_manager

    assert len(materials) >= 1
    assert any(m["name"] == "Material New" for m in materials)
