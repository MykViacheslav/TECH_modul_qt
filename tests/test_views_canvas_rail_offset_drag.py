from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def test_rail_offset_drag_updates_top_offset(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(0.0)
    w.dim.sp_bottom_rail_offset.setValue(0.0)
    w._on_any_change()

    w.canvas.sig_rail_offset_handle_dragged.emit("rail_offset_handle__top", 100.0)
    QApplication.processEvents()

    assert abs(w.dim.sp_top_rail_offset.value() - 100.0) < 0.1
    assert abs(w.dim.sp_bottom_rail_offset.value() - 0.0) < 0.1


def test_rail_offset_drag_updates_bottom_offset(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()

    w.canvas.sig_rail_offset_handle_dragged.emit("rail_offset_handle__bottom", 640.0)
    QApplication.processEvents()

    assert abs(w.dim.sp_top_rail_offset.value() - 100.0) < 0.1
    assert abs(w.dim.sp_bottom_rail_offset.value() - 62.0) < 0.1



def _scene_item_rect(canvas, key: str):
    for item in canvas.scene.items():
        try:
            if item.data(0) == key and hasattr(item, "sceneBoundingRect"):
                return item.sceneBoundingRect()
        except Exception:
            pass
    return None


def _send_mouse_event(widget, event_type, pos, button, buttons):
    posf = QPointF(float(pos.x()), float(pos.y()))
    global_pos = widget.mapToGlobal(pos)
    global_posf = QPointF(float(global_pos.x()), float(global_pos.y()))
    event = QMouseEvent(event_type, posf, global_posf, button, buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)
    QApplication.processEvents()


def test_rail_offset_drag_works_with_real_mouse_events(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.resize(1400, 900)
    w.show()
    QTest.qWait(80)

    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(0.0)
    w.dim.sp_bottom_rail_offset.setValue(0.0)
    w._on_any_change()
    QApplication.processEvents()
    QTest.qWait(30)

    rect = _scene_item_rect(w.canvas, "rail_offset_handle__top")
    assert rect is not None

    view = w.canvas.view
    viewport = view.viewport()

    start_scene = rect.center()
    end_scene = QPointF(start_scene.x(), 110.0)

    start_pos = view.mapFromScene(start_scene)
    end_pos = view.mapFromScene(end_scene)

    _send_mouse_event(
        viewport,
        QEvent.Type.MouseButtonPress,
        start_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _send_mouse_event(
        viewport,
        QEvent.Type.MouseMove,
        end_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
    )
    _send_mouse_event(
        viewport,
        QEvent.Type.MouseButtonRelease,
        end_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )

    assert abs(w.dim.sp_top_rail_offset.value() - 110.0) < 5.0
