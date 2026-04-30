from __future__ import annotations

from pathlib import Path

from src.domain.operations.adapters.wall_repository import JsonWallRepository
from src.domain.operations.wall_ops import WallOperations
from src.storage.wall_store_json import WallStoreJson


def _build_ops(tmp_path: Path) -> tuple[WallOperations, WallStoreJson]:
    walls_path = tmp_path / "walls.json"
    store = WallStoreJson(path=walls_path)
    repo = JsonWallRepository(store=store)
    return WallOperations(repository=repo), store


def test_add_point_preview_and_apply(tmp_path: Path) -> None:
    ops, store = _build_ops(tmp_path)
    wall_name = "WALL_TEST"

    preview = ops.execute(
        "wall.add_point",
        target={"name": wall_name},
        params={"point_type": "bolt", "x_mm": 120, "y_mm": 240},
        mode="preview",
        source="test",
    ).to_dict()
    assert preview["status"] == "ok"
    assert preview["can_apply"] is True

    initial = store.get(wall_name)
    assert initial is None or len(initial.obstacles) == 0

    apply = ops.execute(
        "wall.add_point",
        target={"name": wall_name},
        params={"point_type": "bolt", "x_mm": 120, "y_mm": 240},
        mode="apply",
        source="test",
    ).to_dict()
    assert apply["status"] == "ok"
    assert apply["can_apply"] is False

    after = store.get(wall_name)
    assert after is not None
    assert len(after.obstacles) == 1


def test_remove_point_validation_when_missing(tmp_path: Path) -> None:
    ops, _ = _build_ops(tmp_path)
    wall_name = "WALL_TEST_2"

    result = ops.execute(
        "wall.remove_point",
        target={"name": wall_name},
        params={"point_id": "missing"},
        mode="preview",
        source="test",
    ).to_dict()

    assert result["status"] == "validation_error"
    assert result["can_apply"] is False
    assert result["errors"][0]["code"] == "POINT_NOT_FOUND"

