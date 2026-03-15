from PyQt6.QtWidgets import QApplication

from src.app.app_settings import DrawingSettings, save_drawing_settings


def test_tab_modul_reload_drawing_settings_syncs_hidden_dimensions_fields(tmp_path, monkeypatch):
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
            show_front_part=True,
            front_mode="internal",
            hinge_edge_offset_mm=19.5,
            auto_double_front_width_mm=901.0,
        )
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.reload_drawing_settings_from_storage()

    assert float(w.dim.sp_hinge_edge_offset.value()) == 19.5
    assert float(w.dim.sp_auto_double_front_width.value()) == 901.0