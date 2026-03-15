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


def _make_module():
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="FRONT_REF_RENDER",
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
        front_height_mode="to_top_rail",
        front_offset_top_mm=0.0,
        front_offset_bottom_mm=0.0,
    )
    return m


def test_front_reference_top_start_reaches_module_top():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    setattr(m, "front_top_ref_mode", "rail_start")
    setattr(m, "front_bottom_ref_mode", "rail_end")

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front", show_dimensions=False, show_view_labels=False)

    r = _find_scene_rect(c, "front__front")
    assert r is not None
    assert abs(r.top() - 0.0) < 0.1
    assert abs(r.height() - 720.0) < 0.1


def test_front_reference_top_center_hits_half_top_rail():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    setattr(m, "front_top_ref_mode", "rail_center")
    setattr(m, "front_bottom_ref_mode", "rail_end")

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front", show_dimensions=False, show_view_labels=False)

    r = _find_scene_rect(c, "front__front")
    assert r is not None
    assert abs(r.top() - 9.0) < 0.1
    assert abs(r.height() - 711.0) < 0.1


def test_front_reference_bottom_start_stops_at_inner_edge_of_bottom_rail():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    setattr(m, "front_top_ref_mode", "rail_end")
    setattr(m, "front_bottom_ref_mode", "rail_start")

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front", show_dimensions=False, show_view_labels=False)

    r = _find_scene_rect(c, "front__front")
    assert r is not None
    assert abs(r.top() - 18.0) < 0.1
    assert abs(r.height() - 684.0) < 0.1


def test_front_reference_bottom_center_stops_at_half_bottom_rail():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = _make_module()
    setattr(m, "front_top_ref_mode", "rail_end")
    setattr(m, "front_bottom_ref_mode", "rail_center")

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front", show_dimensions=False, show_view_labels=False)

    r = _find_scene_rect(c, "front__front")
    assert r is not None
    assert abs(r.top() - 18.0) < 0.1
    assert abs(r.height() - 693.0) < 0.1