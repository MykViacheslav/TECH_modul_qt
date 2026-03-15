from PyQt6.QtWidgets import QApplication

from src.app.app_settings import DrawingSettings, save_drawing_settings


def test_tab_modul_effective_drawing_helpers_prefer_draw_settings_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_drawing_settings(
        DrawingSettings(
            hinge_edge_offset_mm=12.0,
            auto_double_front_width_mm=600.0,
        )
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # storage mowi co innego
    w.dim.sp_hinge_edge_offset.setValue(99.0)
    w.dim.sp_auto_double_front_width.setValue(1999.0)

    # zrodlem prawdy ma byc draw_settings
    w.draw_settings.set_from_settings({
        "hinge_edge_offset_mm": 21.5,
        "auto_double_front_width_mm": 905.0,
    })

    assert float(w.get_effective_hinge_edge_offset_mm()) == 21.5
    assert float(w.get_effective_auto_double_front_width_mm()) == 905.0


def test_tab_modul_effective_drawing_helpers_fallback_to_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_drawing_settings(
        DrawingSettings(
            hinge_edge_offset_mm=18.0,
            auto_double_front_width_mm=880.0,
        )
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # symulacja awarii / braku widgetu draw_settings
    w.draw_settings = None

    assert float(w.get_effective_hinge_edge_offset_mm()) == 18.0
    assert float(w.get_effective_auto_double_front_width_mm()) == 880.0