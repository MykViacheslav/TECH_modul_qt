from PyQt6.QtWidgets import QApplication


def _find_scene_rect(canvas, key: str):
    for item in canvas.scene.items():
        try:
            if item.data(0) == key and hasattr(item, "rect"):
                return item.rect()
        except Exception:
            pass
    return None


def _set_combo_by_data(cb, value: str) -> None:
    idx = cb.findData(value)
    assert idx >= 0, f"Nie znaleziono data={value!r}"
    cb.setCurrentIndex(idx)


def test_top_and_bottom_rail_offsets_are_saved_into_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)

    w._on_any_change()

    assert float(getattr(w._draft, "top_rail_offset_mm", 0.0)) == 100.0
    assert float(getattr(w._draft, "bottom_rail_offset_mm", 0.0)) == 50.0


def test_preview_renders_shifted_top_and_bottom_rails(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "divider"]))
    w.dividers.set_values(1, "right")

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)

    w._on_any_change()

    r_top = _find_scene_rect(w.canvas, "top")
    r_bottom = _find_scene_rect(w.canvas, "bottom")
    r_div = _find_scene_rect(w.canvas, "divider_1")

    assert r_top is not None
    assert r_bottom is not None
    assert r_div is not None

    assert abs(r_top.top() - 100.0) < 0.1
    assert abs(r_bottom.top() - 652.0) < 0.1
    assert abs(r_div.top() - 118.0) < 0.1
    assert abs(r_div.height() - 534.0) < 0.1


def test_front_to_top_rail_respects_shifted_rail_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))

    w.dim.sp_w.setValue(800.0)
    w.dim.sp_h.setValue(720.0)
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)

    _set_combo_by_data(w.fhw.cb_front_layout, "overlay")
    _set_combo_by_data(w.fhw.cb_front_height_mode, "to_top_rail")
    _set_combo_by_data(w.fhw.cb_top_ref_mode, "rail_end")
    _set_combo_by_data(w.fhw.cb_bottom_ref_mode, "rail_end")

    w.fhw.sp_front_offset_bottom.setValue(40.0)

    w._on_any_change()

    r = _find_scene_rect(w.canvas, "front__front")
    assert r is not None

    assert abs(r.top() - 118.0) < 0.1
    assert abs(r.height() - 512.0) < 0.1


def test_bom_shows_top_and_bottom_rail_offsets(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    w.dim.sp_top_rail_offset.setValue(100.0)
    w.dim.sp_bottom_rail_offset.setValue(50.0)
    w._on_any_change()

    txt = w.bom.v_offsets.text().lower()
    assert "gora 100.0 mm" in txt
    assert "dol 50.0 mm" in txt
