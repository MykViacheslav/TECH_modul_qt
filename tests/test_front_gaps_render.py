from PyQt6.QtWidgets import QApplication


def _find_scene_rect(canvas, key: str):
    for item in canvas.scene.items():
        try:
            if getattr(item, "key", None) == key and hasattr(item, "rect"):
                return item.rect()
        except Exception:
            pass

        try:
            if item.data(0) == key and hasattr(item, "rect"):
                return item.rect()
        except Exception:
            pass
    return None


def _find_line_by_key(canvas, key: str):
    for item in canvas.scene.items():
        try:
            if getattr(item, "key", None) == key and hasattr(item, "line"):
                return item.line()
        except Exception:
            pass

        try:
            if item.data(0) == key and hasattr(item, "line"):
                return item.line()
        except Exception:
            pass
    return None


def _make_module():
    from src.domain.module_models import ModuleDef

    return ModuleDef(
        name="FRONT_GAPS_RENDER",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        carcass_joint_type="type2",
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF3"},
        parts={},
        facade_mode="doors",
        drawer_count=1,
        front_layout="overlay",
        front_height_mode="full",
        front_offset_top_mm=0.0,
        front_offset_bottom_mm=0.0,
    )


def test_overlay_front_gaps_change_real_front_rect():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    setattr(m, "front_gap_left_mm", 1.5)
    setattr(m, "front_gap_right_mm", 2.5)
    setattr(m, "front_gap_top_mm", 3.0)
    setattr(m, "front_gap_bottom_mm", 4.0)

    c = ViewsCanvas()
    c.render_module(
        m,
        fit=False,
        selected_part_key="front",
        show_dimensions=False,
        show_view_labels=False,
    )

    r = _find_scene_rect(c, "front__front")
    assert r is not None

    assert abs(r.left() - 3.5) < 0.1
    assert abs(r.top() - 3.0) < 0.1
    assert abs(r.width() - 792.0) < 0.1
    assert abs(r.height() - 713.0) < 0.1


def test_inset_front_gaps_change_real_front_rect():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    m.front_layout = "inset"

    setattr(m, "front_gap_left_mm", 2.0)
    setattr(m, "front_gap_right_mm", 3.0)
    setattr(m, "front_gap_top_mm", 1.5)
    setattr(m, "front_gap_bottom_mm", 2.5)

    c = ViewsCanvas()
    c.render_module(
        m,
        fit=False,
        selected_part_key="front",
        show_dimensions=False,
        show_view_labels=False,
    )

    r = _find_scene_rect(c, "front__front")
    assert r is not None

    assert abs(r.left() - 20.0) < 0.1
    assert abs(r.top() - 1.5) < 0.1
    assert abs(r.width() - 759.0) < 0.1
    assert abs(r.height() - 716.0) < 0.1


def test_drawer_splits_follow_gap_between_vertical():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="DRAWERS_GAP_VERTICAL",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        carcass_joint_type="type2",
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF3"},
        parts={},
        facade_mode="drawers",
        drawer_count=3,
        front_layout="overlay",
        front_height_mode="offsets",
        front_offset_top_mm=120.0,
        front_offset_bottom_mm=30.0,
    )

    setattr(m, "front_gap_between_vertical_mm", 2.0)

    c = ViewsCanvas()
    c.render_module(
        m,
        fit=False,
        selected_part_key="front",
        show_dimensions=False,
        show_view_labels=False,
    )

    r = _find_scene_rect(c, "front__front")
    assert r is not None
    assert abs(r.top() - 120.0) < 0.1
    assert abs(r.height() - 570.0) < 0.1

    line1 = _find_line_by_key(c, "front__drawer_split_1")
    line2 = _find_line_by_key(c, "front__drawer_split_2")

    assert line1 is not None
    assert line2 is not None

    assert abs(line1.y1() - 309.6667) < 0.2
    assert abs(line2.y1() - 500.3333) < 0.2