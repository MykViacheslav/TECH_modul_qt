from PyQt6.QtWidgets import QApplication

from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock


def test_drawing_settings_block_roundtrip():
    app = QApplication.instance() or QApplication([])

    w = DrawingSettingsBlock()

    data = {
        "rect_line_color": "#111111",
        "rect_line_width_px": 2,
        "dim_line_color": "#2255aa",
        "dim_line_width_px": 3,
        "grid_enabled": False,
        "show_front_part": False,
        "front_mode": "internal",
        "hinge_edge_offset_mm": 15.5,
        "auto_double_front_width_mm": 777.0,
    }

    w.set_from_settings(data)
    out = w.to_settings()

    assert out["rect_line_color"] == "#111111"
    assert out["rect_line_width_px"] == 2
    assert out["dim_line_color"] == "#2255aa"
    assert out["dim_line_width_px"] == 3
    assert out["grid_enabled"] is False
    assert out["show_front_part"] is False
    assert out["front_mode"] == "internal"
    assert float(out["hinge_edge_offset_mm"]) == 15.5
    assert float(out["auto_double_front_width_mm"]) == 777.0