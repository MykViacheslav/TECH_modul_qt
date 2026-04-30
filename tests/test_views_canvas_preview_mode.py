from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtWidgets import QApplication, QGraphicsTextItem

from src.domain.module_models import ModuleDef


def _scene_texts(scene) -> list[str]:
    out: list[str] = []
    for it in scene.items():
        if isinstance(it, QGraphicsTextItem):
            txt = (it.toPlainText() or "").strip()
            if txt:
                out.append(txt)
    return out


def _scene_text_items(scene, prefix: str) -> list[QGraphicsTextItem]:
    out: list[QGraphicsTextItem] = []
    for it in scene.items():
        if isinstance(it, QGraphicsTextItem):
            txt = (it.toPlainText() or "").strip()
            if txt.startswith(prefix):
                out.append(it)
    return out


def _make_module() -> ModuleDef:
    return ModuleDef(
        name="PREVIEW_TEST",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=700.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back"]),
        materials={},
        edgebands={},
        parts={},
    )


def test_views_canvas_normal_mode_shows_technical_overlays(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    canvas = ViewsCanvas()
    canvas.render_module(_make_module(), fit=False, selected_part_key="side_left")

    texts = _scene_texts(canvas.scene)

    assert "PRZOD" in texts
    assert "GORA" in texts
    assert any(t.startswith("L = ") for t in texts)
    assert any(t.startswith("H = ") for t in texts)
    assert any(t.startswith("W = ") for t in texts)


def test_views_canvas_preview_mode_hides_view_labels_but_keeps_dimensions(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    canvas = ViewsCanvas()
    canvas.set_preview_mode(True)
    canvas.render_module(_make_module(), fit=False, selected_part_key="side_left")

    texts = _scene_texts(canvas.scene)

    assert "PRZOD" not in texts
    assert "GORA" not in texts
    assert any(t.startswith("L = ") for t in texts)
    assert any(t.startswith("H = ") for t in texts)
    assert any(t.startswith("W = ") for t in texts)

    l_items = _scene_text_items(canvas.scene, "L = ")
    h_items = _scene_text_items(canvas.scene, "H = ")
    w_items = _scene_text_items(canvas.scene, "W = ")

    assert len(l_items) == 1
    assert len(h_items) == 1
    assert len(w_items) == 1
    assert abs(h_items[0].rotation() + 90.0) < 0.1
    assert abs(w_items[0].rotation() + 90.0) < 0.1


def test_tab_modul_sets_canvas_preview_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w.canvas, "is_preview_mode")
    assert w.canvas.is_preview_mode() is True
