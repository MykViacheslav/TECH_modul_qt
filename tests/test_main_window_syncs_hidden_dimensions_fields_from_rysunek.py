from PyQt6.QtWidgets import QApplication, QTabWidget

from src.app.main_window import MainWindow


def test_main_window_syncs_rysunek_save_to_hidden_dimensions_fields_in_modul(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()

    tabs = w.centralWidget()
    assert isinstance(tabs, QTabWidget)

    by_title = {}
    for i in range(tabs.count()):
        by_title[tabs.tabText(i)] = tabs.widget(i)

    modul = by_title["Modul"]
    rysunek = by_title["Ustawienia"]

    rysunek.draw_settings.set_from_settings({
        "rect_line_color": "#222222",
        "rect_line_width_px": 2,
        "dim_line_color": "#3377cc",
        "dim_line_width_px": 2,
        "grid_enabled": True,
        "show_front_part": True,
        "front_mode": "internal",
        "hinge_edge_offset_mm": 23.0,
        "auto_double_front_width_mm": 1005.0,
    })

    rysunek._save_ui_to_settings()

    assert float(modul.dim.sp_hinge_edge_offset.value()) == 23.0
    assert float(modul.dim.sp_auto_double_front_width.value()) == 1005.0
