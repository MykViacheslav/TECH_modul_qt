from PyQt6.QtWidgets import QApplication, QGraphicsRectItem

from src.domain.module_models import ModuleDef
from src.tabs.modul.views_canvas import ViewsCanvas


def _make_module(width: float = 800.0, depth: float = 500.0, height: float = 700.0) -> ModuleDef:
    return ModuleDef(
        name="STACK_TEST",
        width_mm=width,
        depth_mm=depth,
        height_mm=height,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={},
    )


def _item_rect_by_key(canvas: ViewsCanvas, key: str):
    for item in canvas.scene.items():
        if not isinstance(item, QGraphicsRectItem):
            continue
        try:
            item_key = str(item.data(0) or "")
        except Exception:
            item_key = ""
        if item_key == key:
            return item.rect()
    return None


def test_views_canvas_keeps_front_and_top_on_one_vertical_stack(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    canvas = ViewsCanvas()
    canvas.set_preview_mode(True)
    canvas.render_module(_make_module(), fit=False, selected_part_key="front")

    front_rect = _item_rect_by_key(canvas, "front__front")
    top_rect = _item_rect_by_key(canvas, "front__top")

    assert front_rect is not None
    assert top_rect is not None
    assert top_rect.top() > front_rect.bottom()


def test_views_canvas_refreshes_front_and_top_after_dimension_change(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    canvas = ViewsCanvas()
    canvas.set_preview_mode(True)

    module = _make_module(width=800.0, depth=500.0, height=700.0)
    canvas.render_module(module, fit=False, selected_part_key="front")
    first_front = _item_rect_by_key(canvas, "front__front")
    first_top = _item_rect_by_key(canvas, "front__top")

    assert first_front is not None
    assert first_top is not None

    module.width_mm = 950.0
    module.height_mm = 780.0
    canvas.render_module(module, fit=False, selected_part_key="front")
    second_front = _item_rect_by_key(canvas, "front__front")
    second_top = _item_rect_by_key(canvas, "front__top")

    assert second_front is not None
    assert second_top is not None
    assert second_front.width() > first_front.width()
    assert second_top.width() > first_top.width()
    assert second_top.top() > first_top.top()

