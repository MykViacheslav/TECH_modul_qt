from PyQt6.QtWidgets import QApplication

from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock


def test_tab_modul_keeps_draw_settings_object_but_hides_it_in_modul(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "draw_settings")
    assert isinstance(w.draw_settings, DrawingSettingsBlock)
    assert w.draw_settings.isHidden() is True