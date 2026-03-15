from PyQt6.QtWidgets import QApplication

from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock


def test_tab_modul_uses_extracted_drawing_settings_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "draw_settings")
    assert isinstance(w.draw_settings, DrawingSettingsBlock)