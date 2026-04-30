from __future__ import annotations

import asyncio

from src.api import main_api


def test_project_wall_summary_endpoint_counts_points() -> None:
    project_id = 98765
    wall_name = f"WEB_PROJECT_{project_id}"

    asyncio.run(
        main_api.apply_wall_operation(
            main_api.WallOperationRequest(
                action="wall.add_point",
                target=main_api.OperationTargetPayload(name=wall_name),
                params={"point_type": "bolt", "x_mm": 100, "y_mm": 120, "point_id": "pytest_wall_summary_point"},
                source="pytest",
            )
        )
    )

    payload = asyncio.run(main_api.get_project_wall_summary(project_id))
    assert payload["project_id"] == project_id
    assert payload["wall_name"] == wall_name
    assert int(payload["points_count"]) >= 1
