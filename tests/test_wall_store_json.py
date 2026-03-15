from src.domain.wall_models import WallLayoutDef, WallObstacleDef
from src.storage.wall_store_json import WallStoreJson


def test_wall_store_json_persists_client_order_and_obstacles(tmp_path):
    store = WallStoreJson(path=tmp_path / "walls.json")

    wall = WallLayoutDef(
        name="SCIANA_TEST",
        client_name="Jan Kowalski",
        order_name="ZAM-2026-03",
        layout_type="l",
        wall_a_width_mm=4200.0,
        obstacles=[
            WallObstacleDef(kind="window", name="Okno glowne", x_mm=800.0, bottom_offset_mm=900.0, width_mm=1200.0, height_mm=1400.0),
        ],
    )

    result = store.save_new(wall)
    assert result.ok

    loaded = store.get("SCIANA_TEST")
    assert loaded is not None
    assert loaded.client_name == "Jan Kowalski"
    assert loaded.order_name == "ZAM-2026-03"
    assert loaded.layout_type == "l"
    assert len(loaded.obstacles) == 1

    loaded.client_name = "Anna Nowak"
    loaded.order_name = "ZAM-2026-04"
    overwrite = store.overwrite(loaded)
    assert overwrite.ok

    reloaded = store.get("SCIANA_TEST")
    assert reloaded is not None
    assert reloaded.client_name == "Anna Nowak"
    assert reloaded.order_name == "ZAM-2026-04"
