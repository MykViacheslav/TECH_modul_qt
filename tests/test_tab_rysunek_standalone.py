from PyQt6.QtWidgets import QApplication

from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock


def test_tab_rysunek_uses_extracted_drawing_settings_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.rysunek.tab_rysunek import TabRysunek

    w = TabRysunek()

    assert hasattr(w, "draw_settings")
    assert isinstance(w.draw_settings, DrawingSettingsBlock)


def test_tab_rysunek_save_and_reload_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.rysunek.tab_rysunek import TabRysunek

    w1 = TabRysunek()

    w1.draw_settings.set_from_settings({
        "rect_line_color": "#111111",
        "rect_line_width_px": 2,
        "dim_line_color": "#2255aa",
        "dim_line_width_px": 3,
        "grid_enabled": False,
        "show_front_part": False,
        "front_mode": "internal",
        "hinge_edge_offset_mm": 15.5,
        "auto_double_front_width_mm": 777.0,
    })

    w1._save_ui_to_settings()

    w2 = TabRysunek()
    vals = w2.get_values_dict()

    assert vals["rect_line_color"] == "#111111"
    assert vals["rect_line_width_px"] == 2
    assert vals["dim_line_color"] == "#2255aa"
    assert vals["dim_line_width_px"] == 3
    assert vals["grid_enabled"] is False
    assert vals["show_front_part"] is False
    assert vals["front_mode"] == "internal"
    assert float(vals["hinge_edge_offset_mm"]) == 15.5
    assert float(vals["auto_double_front_width_mm"]) == 777.0