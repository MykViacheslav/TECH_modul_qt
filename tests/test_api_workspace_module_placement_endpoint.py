from __future__ import annotations

import asyncio
import sqlite3

import pytest
from fastapi import HTTPException

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_update_project_module_placement_endpoint_persists_real_module(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workspace_api.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Workspace MVP", "Test Client"))
    module_id = int(manager.add_project_module(project_id, "MVP Modul", 600, 720, 560))

    monkeypatch.setattr(main_api, "data_manager", manager)

    payload = asyncio.run(
        main_api.update_project_module_placement(
            project_id=project_id,
            module_id=module_id,
            payload=main_api.ModulePlacementUpdate(x_mm=420.0, y_mm=0.0),
        )
    )
    assert payload["status"] == "success"
    assert int(payload["module_id"]) == module_id
    assert float(payload["placement"]["x_mm"]) == 420.0

    modules = manager.get_project_modules(project_id)
    selected = [row for row in modules if int(row.get("id", -1)) == module_id]
    assert len(selected) == 1
    assert float(selected[0].get("x", -1.0)) == 420.0
    assert float(selected[0].get("y", -1.0)) == 0.0


def test_update_project_module_placement_requires_any_field(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workspace_api_empty.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Workspace MVP", "Test Client"))
    module_id = int(manager.add_project_module(project_id, "MVP Modul", 600, 720, 560))

    monkeypatch.setattr(main_api, "data_manager", manager)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            main_api.update_project_module_placement(
                project_id=project_id,
                module_id=module_id,
                payload=main_api.ModulePlacementUpdate(),
            )
        )
    assert int(exc.value.status_code) == 400


def test_update_project_module_placement_floor_module_forces_y_to_zero(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workspace_api_floor_mount.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Workspace MVP", "Test Client"))
    module_id = int(manager.add_project_module(project_id, "Base modul", 600, 720, 560))

    monkeypatch.setattr(main_api, "data_manager", manager)

    payload = asyncio.run(
        main_api.update_project_module_placement(
            project_id=project_id,
            module_id=module_id,
            payload=main_api.ModulePlacementUpdate(x_mm=320.0, y_mm=380.0),
        )
    )

    assert payload["status"] == "success"
    assert float(payload["placement"]["x_mm"]) == 320.0
    assert float(payload["placement"]["y_mm"]) == 0.0

    modules = manager.get_project_modules(project_id)
    selected = [row for row in modules if int(row.get("id", -1)) == module_id]
    assert len(selected) == 1
    assert float(selected[0].get("y", -1.0)) == 0.0


def test_update_project_module_placement_wall_module_keeps_y_value(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workspace_api_wall_mount.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Workspace MVP", "Test Client"))
    module_id = int(manager.add_project_module(project_id, "Wall modul", 800, 720, 350))

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE project_modules SET module_family = ? WHERE id = ?",
            ("wall_hanging", module_id),
        )
        conn.commit()

    monkeypatch.setattr(main_api, "data_manager", manager)

    payload = asyncio.run(
        main_api.update_project_module_placement(
            project_id=project_id,
            module_id=module_id,
            payload=main_api.ModulePlacementUpdate(y_mm=640.0),
        )
    )

    assert payload["status"] == "success"
    assert float(payload["placement"]["y_mm"]) == 640.0

    modules = manager.get_project_modules(project_id)
    selected = [row for row in modules if int(row.get("id", -1)) == module_id]
    assert len(selected) == 1
    assert float(selected[0].get("y", -1.0)) == 640.0


def test_update_project_module_placement_floor_module_resets_y_even_on_x_only_update(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workspace_api_floor_x_only.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Workspace MVP", "Test Client"))
    module_id = int(manager.add_project_module(project_id, "Floor modul", 600, 720, 560))
    manager.update_module_property(module_id, "y", 255.0)

    monkeypatch.setattr(main_api, "data_manager", manager)

    payload = asyncio.run(
        main_api.update_project_module_placement(
            project_id=project_id,
            module_id=module_id,
            payload=main_api.ModulePlacementUpdate(x_mm=210.0),
        )
    )

    assert payload["status"] == "success"
    assert float(payload["placement"]["x_mm"]) == 210.0
    assert float(payload["placement"]["y_mm"]) == 0.0

    modules = manager.get_project_modules(project_id)
    selected = [row for row in modules if int(row.get("id", -1)) == module_id]
    assert len(selected) == 1
    assert float(selected[0].get("y", -1.0)) == 0.0
