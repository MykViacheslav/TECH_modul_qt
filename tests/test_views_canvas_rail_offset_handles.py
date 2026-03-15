from PyQt6.QtWidgets import QApplication


def _scene_has_key(canvas, key: str) -> bool:
    for item in canvas.scene.items():
        try:
            if item.data(0) == key:
                return True
        except Exception:
            pass
    return False


def _scene_key_count(canvas, key: str) -> int:
    n = 0
    for item in canvas.scene.items():
        try:
            if item.data(0) == key:
                n += 1
        except Exception:
            pass
    return n


def _scene_label_text(canvas, key: str) -> str:
    for item in canvas.scene.items():
        try:
            if item.data(0) == key and hasattr(item, "text"):
                return str(item.text())
            if item.data(0) == key and hasattr(item, "toPlainText"):
                return str(item.toPlainText())
        except Exception:
            pass
    return ""


def test_rail_offset_handles_visible_when_top_and_bottom_are_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()
    w._on_selected_part("top")

    assert _scene_has_key(w.canvas, "rail_offset_handle__top") is True
    assert _scene_has_key(w.canvas, "rail_offset_handle__bottom") is True


def test_rail_offset_handles_are_hidden_while_front_is_selected(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()
    w._on_selected_part("front")

    assert _scene_has_key(w.canvas, "rail_offset_handle__top") is False
    assert _scene_has_key(w.canvas, "rail_offset_handle__bottom") is False


def test_rail_offset_handles_hidden_when_top_and_bottom_are_not_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "front"]))
    w._on_any_change()

    assert _scene_has_key(w.canvas, "rail_offset_handle__top") is False
    assert _scene_has_key(w.canvas, "rail_offset_handle__bottom") is False


def test_rail_offset_handles_show_current_offset_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()
    w._on_selected_part("top")

    top_label = _scene_label_text(w.canvas, "rail_offset_handle__top__label")
    bottom_label = _scene_label_text(w.canvas, "rail_offset_handle__bottom__label")

    assert "GORA" in top_label
    assert "100.0 mm" in top_label
    assert "DOL" in bottom_label
    assert "50.0 mm" in bottom_label


def test_active_rail_offset_handle_shows_guide_line(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()
    w._on_selected_part("top")

    w._on_rail_offset_handle_clicked("rail_offset_handle__top")

    assert _scene_has_key(w.canvas, "rail_offset_handle__top__guide") is True
    assert _scene_has_key(w.canvas, "rail_offset_handle__bottom__guide") is False



def test_rail_offset_handles_show_square_grabbers(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w._on_any_change()
    w._on_selected_part("top")

    assert _scene_key_count(w.canvas, "rail_offset_handle__top") >= 3
    assert _scene_key_count(w.canvas, "rail_offset_handle__bottom") >= 3
