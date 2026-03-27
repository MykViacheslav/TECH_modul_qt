from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow


def test_main_window_syncs_rysunek_save_to_modul(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()

    modul = w._tabs_by_title["Modul"]
    rysunek = w._tabs_by_title["Ustawienia"]

    rysunek.draw_settings.set_from_settings({
        "rect_line_color": "#222222",
        "rect_line_width_px": 2,
        "dim_line_color": "#3377cc",
        "dim_line_width_px": 2,
        "grid_enabled": True,
        "show_front_part": False,
        "front_mode": "internal",
        "hinge_edge_offset_mm": 21.0,
        "auto_double_front_width_mm": 999.0,
    })

    rysunek._save_ui_to_settings()

    vals = modul.draw_settings.to_settings()

    assert vals["rect_line_color"] == "#222222"
    assert vals["dim_line_color"] == "#3377cc"
    assert vals["show_front_part"] is False
    assert vals["front_mode"] == "internal"
    assert float(vals["hinge_edge_offset_mm"]) == 21.0
    assert float(vals["auto_double_front_width_mm"]) == 999.0

    assert modul.sessview.chk_hide_front.isChecked() is True
