from PyQt6.QtWidgets import QApplication

from src.app.app_settings import DrawingSettings, save_drawing_settings


def test_tab_modul_reload_drawing_settings_from_storage_updates_hidden_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_drawing_settings(
        DrawingSettings(
            rect_line_color="#111111",
            rect_line_width_px=2,
            dim_line_color="#2255aa",
            dim_line_width_px=3,
            grid_enabled=False,
            grid_step_mm=50.0,
            grid_color="#dddddd",
            grid_width_px=1,
            show_front_part=False,
            front_mode="internal",
            hinge_edge_offset_mm=18.5,
            auto_double_front_width_mm=888.0,
        )
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.reload_drawing_settings_from_storage()

    vals = w.draw_settings.to_settings()

    assert vals["rect_line_color"] == "#111111"
    assert vals["rect_line_width_px"] == 2
    assert vals["dim_line_color"] == "#2255aa"
    assert vals["dim_line_width_px"] == 3
    assert vals["grid_enabled"] is False
    assert vals["show_front_part"] is False
    assert vals["front_mode"] == "internal"
    assert float(vals["hinge_edge_offset_mm"]) == 18.5
    assert float(vals["auto_double_front_width_mm"]) == 888.0

    assert w.sessview.chk_hide_front.isChecked() is True