from __future__ import annotations

import asyncio

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_wall_config_uses_saved_wall_points() -> None:
    project_id = 24680
    wall_name = f"WEB_PROJECT_{project_id}"

    asyncio.run(
        main_api.apply_wall_operation(
            main_api.WallOperationRequest(
                action="wall.add_point",
                target=main_api.OperationTargetPayload(name=wall_name),
                params={"point_type": "bolt", "x_mm": 420, "y_mm": 560, "point_id": "pytest_cfg_pt"},
                source="pytest",
            )
        )
    )

    payload = asyncio.run(main_api.get_wall_config(project_id))
    assert int(payload["id"]) == project_id
    assert payload["wall_name"] == wall_name
    assert int(payload["points_count"]) >= 1
    assert int(payload["width"]) >= 720
    assert int(payload["height"]) >= 860


def test_wall_config_put_persists_dimensions(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "wall_config.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = int(manager.create_project("Wall cfg", "Client"))

    monkeypatch.setattr(main_api, "data_manager", manager)

    saved = asyncio.run(
        main_api.update_wall_config(
            project_id=project_id,
            payload=main_api.WallConfigUpdate(width=4420, height=2790, room_depth=3640),
        )
    )

    assert int(saved["width"]) == 4420
    assert int(saved["height"]) == 2790
    assert int(saved["room_depth"]) == 3640

    loaded = asyncio.run(main_api.get_wall_config(project_id))
    assert int(loaded["id"]) == project_id
    assert int(loaded["width"]) == 4420
    assert int(loaded["height"]) == 2790
    assert int(loaded["room_depth"]) == 3640
