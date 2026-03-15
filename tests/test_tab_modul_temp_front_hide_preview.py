from PyQt6.QtWidgets import QApplication


def _scene_has_key(canvas, key: str) -> bool:
    for item in canvas.scene.items():
        try:
            if getattr(item, "key", None) == key:
                return True
        except Exception:
            pass

        try:
            if item.data(0) == key:
                return True
        except Exception:
            pass

    return False


def test_tab_modul_temp_front_hide_checkbox_controls_canvas_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w.fhw, "chk_temp_hide_front")
    assert hasattr(w.canvas, "is_preview_front_hidden")

    assert w.canvas.is_preview_front_hidden() is False

    w.fhw.chk_temp_hide_front.setChecked(True)
    QApplication.processEvents()
    assert w.canvas.is_preview_front_hidden() is True

    w.fhw.chk_temp_hide_front.setChecked(False)
    QApplication.processEvents()
    assert w.canvas.is_preview_front_hidden() is False


def test_tab_modul_temp_front_hide_really_hides_front_in_preview_scene(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # ustaw stan, w ktorym front normalnie powinien byc widoczny
    idx = w.fhw.cb_front_layout.findData("overlay")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    idx = w.fhw.cb_front_height_mode.findData("full")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)
    w._on_any_change()
    QApplication.processEvents()

    # kontrolnie: front powinien istniec w scenie przed ukryciem
    assert _scene_has_key(w.canvas, "front__front") is True

    # w wielu przypadkach front w rzucie z gory tez jest rysowany
    had_top_front_before = _scene_has_key(w.canvas, "front__top")

    # ukryj front tylko w podgladzie
    w.fhw.chk_temp_hide_front.setChecked(True)
    QApplication.processEvents()
    w._on_any_change()
    QApplication.processEvents()

    # najwazniejsze: front z przodu ma zniknac
    assert _scene_has_key(w.canvas, "front__front") is False

    # jezeli front z gory byl rysowany przed ukryciem,
    # po ukryciu tez powinien zniknac
    if had_top_front_before:
        assert _scene_has_key(w.canvas, "front__top") is False

    # przywroc front
    w.fhw.chk_temp_hide_front.setChecked(False)
    QApplication.processEvents()
    w._on_any_change()
    QApplication.processEvents()

    assert _scene_has_key(w.canvas, "front__front") is True

    if had_top_front_before:
        assert _scene_has_key(w.canvas, "front__top") is True


def test_front_hardware_temp_preview_ui_shows_clear_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import FrontHardwareBlock

    w = FrontHardwareBlock()

    assert hasattr(w, "preview_box")
    assert hasattr(w, "lab_temp_front_preview_state")
    assert hasattr(w, "btn_temp_show_front_again")

    assert w.chk_temp_hide_front.isChecked() is False
    assert "widoczny" in w.lab_temp_front_preview_state.text().lower()
    assert w.btn_temp_show_front_again.isHidden() is True

    w.chk_temp_hide_front.setChecked(True)
    QApplication.processEvents()

    assert "ukryty" in w.lab_temp_front_preview_state.text().lower()
    assert w.btn_temp_show_front_again.isHidden() is False
    assert w.btn_temp_show_front_again.isEnabled() is True

    w.btn_temp_show_front_again.click()
    QApplication.processEvents()

    assert w.chk_temp_hide_front.isChecked() is False
    assert "widoczny" in w.lab_temp_front_preview_state.text().lower()
    assert w.btn_temp_show_front_again.isHidden() is True