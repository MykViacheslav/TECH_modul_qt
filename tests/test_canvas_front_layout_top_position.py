from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef
from src.app.app_settings import load_drawing_settings, save_drawing_settings, DrawingSettings


def _scene_key_map(canvas):
    keys = []
    items = []
    for it in canvas.scene.items():
        try:
            k = it.data(0)
        except Exception:
            k = None
        if isinstance(k, str) and k:
            keys.append(k)
            items.append((k, it))
    return keys, items


def _top_view_bottom_from_side_left(items):
    # side_left istnieje w PRZOD i GORA; bierzemy ten o najwiekszym y => to jest GORA
    cands = []
    for k, it in items:
        if k == "side_left":
            try:
                r = it.rect()
                cands.append((float(r.y()), float(r.bottom())))
            except Exception:
                pass
    assert cands, "Brak side_left w scenie"
    return max(cands, key=lambda x: x[0])[1]


def _front_top_rect(items):
    for k, it in items:
        if k == "front__top":
            r = it.rect()
            return float(r.y()), float(r.height())
    return None


def test_front_overlay_is_outside_top_view(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    # front widoczny
    s = load_drawing_settings()
    save_drawing_settings(DrawingSettings(**{**s.__dict__, "show_front_part": True}))

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = ModuleDef(
        name="X",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={}
    )
    # wymagamy pola front_layout
    m.front_layout = "overlay"

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front")

    keys, items = _scene_key_map(c)
    assert "front__top" in keys

    top_bottom = _top_view_bottom_from_side_left(items)
    ft = _front_top_rect(items)
    assert ft is not None
    front_y, front_h = ft

    assert front_h > 0.5
    assert front_y > top_bottom  # overlay ma byc na zewnatrz


def test_front_inset_is_inside_top_view(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    s = load_drawing_settings()
    save_drawing_settings(DrawingSettings(**{**s.__dict__, "show_front_part": True}))

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = ModuleDef(
        name="X",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={}
    )
    m.front_layout = "inset"

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front")

    keys, items = _scene_key_map(c)
    assert "front__top" in keys

    top_bottom = _top_view_bottom_from_side_left(items)
    ft = _front_top_rect(items)
    assert ft is not None
    front_y, front_h = ft

    assert front_h > 0.5
    assert (front_y + front_h) <= (top_bottom + 0.5)  # inset ma byc w srodku