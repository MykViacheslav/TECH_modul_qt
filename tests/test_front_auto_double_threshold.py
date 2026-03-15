from PyQt6.QtWidgets import QApplication


def _find_part(scene, key: str):
    for it in scene.items():
        if getattr(it, "key", None) == key:
            return it
    return None


def _find_front_center_split_lines(scene, front_item):
    if front_item is None or not hasattr(front_item, "rect"):
        return []

    fr = front_item.rect()
    cx = fr.left() + (fr.width() / 2.0)
    top = fr.top()
    bottom = fr.bottom()

    found = []

    for it in scene.items():
        if not hasattr(it, "line"):
            continue

        try:
            ln = it.line()
        except Exception:
            continue

        x1 = float(ln.x1())
        x2 = float(ln.x2())
        y1 = float(ln.y1())
        y2 = float(ln.y2())

        is_vertical = abs(x1 - x2) < 0.001
        if not is_vertical:
            continue

        x = x1
        y_min = min(y1, y2)
        y_max = max(y1, y2)

        near_front_center = abs(x - cx) <= 2.0
        spans_front_height = abs(y_min - top) <= 2.0 and abs(y_max - bottom) <= 2.0

        if near_front_center and spans_front_height:
            found.append(it)

    return found


def _debug_vertical_lines(scene):
    out = []

    for it in scene.items():
        if not hasattr(it, "line"):
            continue

        try:
            ln = it.line()
        except Exception:
            continue

        x1 = float(ln.x1())
        x2 = float(ln.x2())
        y1 = float(ln.y1())
        y2 = float(ln.y2())

        if abs(x1 - x2) < 0.001:
            out.append((round(x1, 2), round(min(y1, y2), 2), round(max(y1, y2), 2)))

    out.sort()
    return out


def test_auto_double_front_threshold_700_is_single(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    from src.core.drawing_settings import DrawingSettings, save_drawing_settings

    save_drawing_settings(
        DrawingSettings(
            auto_double_front_width_mm=800.0,
            hinge_edge_offset_mm=12.0,
        )
    )

    w = TabModul()

    w.vis.set_checked(set([
        "side_left", "side_right", "top", "bottom", "front"
    ]))

    w.dim.sp_w.setValue(700.0)
    w.dim.sp_d.setValue(525.0)
    w.dim.sp_h.setValue(800.0)

    idx = w.fhw.cb_facade_mode.findData("doors")
    assert idx >= 0
    w.fhw.cb_facade_mode.setCurrentIndex(idx)

    idx = w.fhw.cb_front_layout.findData("overlay")
    assert idx >= 0
    w.fhw.cb_front_layout.setCurrentIndex(idx)

    w._on_any_change()
    w.canvas.render_module(w._draft, fit=False, selected_part_key="front__front")

    front = _find_part(w.canvas.scene, "front__front")
    assert front is not None

    split_lines = _find_front_center_split_lines(w.canvas.scene, front)
    assert len(split_lines) == 0, f"Nie powinno byc podzialu frontu dla 700 mm. Linie: {_debug_vertical_lines(w.canvas.scene)}"


def test_auto_double_front_threshold_900_is_double(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    from src.core.drawing_settings import DrawingSettings, save_drawing_settings

    save_drawing_settings(
        DrawingSettings(
            auto_double_front_width_mm=800.0,
            hinge_edge_offset_mm=12.0,
        )
    )

    w = TabModul()

    w.vis.set_checked(set([
        "side_left", "side_right", "top", "bottom", "front"
    ]))

    w.dim.sp_w.setValue(900.0)
    w.dim.sp_d.setValue(525.0)
    w.dim.sp_h.setValue(800.0)

    idx = w.fhw.cb_facade_mode.findData("doors")
    assert idx >= 0
    w.fhw.cb_facade_mode.setCurrentIndex(idx)

    idx = w.fhw.cb_front_layout.findData("overlay")
    assert idx >= 0
    w.fhw.cb_front_layout.setCurrentIndex(idx)

    w._on_any_change()
    w.canvas.render_module(w._draft, fit=False, selected_part_key="front__front")

    front = _find_part(w.canvas.scene, "front__front")
    assert front is not None

    split_lines = _find_front_center_split_lines(w.canvas.scene, front)
    assert len(split_lines) == 1, f"Powinna byc 1 linia podzialu frontu dla 900 mm. Linie: {_debug_vertical_lines(w.canvas.scene)}"


def test_drawing_settings_save_and_load_auto_double_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.core.drawing_settings import (
        DrawingSettings,
        save_drawing_settings,
        load_drawing_settings,
    )

    save_drawing_settings(
        DrawingSettings(
            auto_double_front_width_mm=850.0,
            hinge_edge_offset_mm=21.0,
        )
    )

    s = load_drawing_settings()

    assert float(s.auto_double_front_width_mm) == 850.0
    assert float(s.hinge_edge_offset_mm) == 21.0