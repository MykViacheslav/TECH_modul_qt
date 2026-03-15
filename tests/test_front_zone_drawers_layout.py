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


def _find_horizontal_lines_inside_rect(canvas, rect):
    out = []

    for item in canvas.scene.items():
        if not hasattr(item, "line"):
            continue

        try:
            ln = item.line()
        except Exception:
            continue

        x1 = float(ln.x1())
        x2 = float(ln.x2())
        y1 = float(ln.y1())
        y2 = float(ln.y2())

        # tylko poziome
        if abs(y1 - y2) > 0.1:
            continue

        y = y1

        # linia ma pokrywac szerokosc strefy frontu
        left = min(x1, x2)
        right = max(x1, x2)

        if abs(left - rect.left()) > 0.1:
            continue
        if abs(right - rect.right()) > 0.1:
            continue

        # tylko linie wewnetrzne, nie gorna / dolna krawedz samego rect
        if not (rect.top() + 0.1 < y < rect.bottom() - 0.1):
            continue

        out.append((left, y, right))

    # sort po Y
    out.sort(key=lambda t: t[1])
    return out


def test_drawer_splits_follow_front_zone_offsets_mode():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="DRAWERS_OFFSETS",
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

    # kontrola samej strefy frontu
    assert abs(r.top() - 120.0) < 0.1
    assert abs(r.height() - 570.0) < 0.1

    lines = _find_horizontal_lines_inside_rect(c, r)
    assert len(lines) == 2

    seg_h = r.height() / 3.0
    assert abs(lines[0][1] - (r.top() + seg_h)) < 0.1
    assert abs(lines[1][1] - (r.top() + 2.0 * seg_h)) < 0.1


def test_drawer_splits_follow_front_zone_to_top_rail_mode():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="DRAWERS_TOP_RAIL",
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
        drawer_count=4,
        front_layout="overlay",
        front_height_mode="to_top_rail",
        front_offset_top_mm=999.0,      # ma zostac zignorowane przez tryb
        front_offset_bottom_mm=40.0,
    )

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

    # dla PB18 / type2 gora powinna isc do wienca gornego = 18 mm
    assert abs(r.top() - 18.0) < 0.1
    assert abs(r.height() - 662.0) < 0.1

    lines = _find_horizontal_lines_inside_rect(c, r)
    assert len(lines) == 3

    seg_h = r.height() / 4.0
    assert abs(lines[0][1] - (r.top() + seg_h)) < 0.1
    assert abs(lines[1][1] - (r.top() + 2.0 * seg_h)) < 0.1
    assert abs(lines[2][1] - (r.top() + 3.0 * seg_h)) < 0.1


def test_doors_mode_does_not_create_drawer_split_lines_inside_front_zone():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="DOORS_NO_DRAWER_SPLITS",
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
        drawer_count=4,   # nawet jesli ktos zostawi liczbe > 1
        front_layout="overlay",
        front_height_mode="offsets",
        front_offset_top_mm=100.0,
        front_offset_bottom_mm=50.0,
    )

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

    lines = _find_horizontal_lines_inside_rect(c, r)
    assert len(lines) == 0