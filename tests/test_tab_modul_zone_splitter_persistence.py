from PyQt6.QtWidgets import QApplication


def test_tab_modul_uses_saved_zone_splitter_sizes(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    from src.app.app_settings import save_modul_splitter_sizes

    save_modul_splitter_sizes([410, 880, 390])

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert w._load_zone_splitter_sizes() == [410, 880, 390]
    assert w._zone_splitter_saved_sizes == [410, 880, 390]


def test_tab_modul_saves_zone_splitter_sizes_back_to_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.app.app_settings import load_modul_splitter_sizes
    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w._save_zone_splitter_sizes([470, 760, 350])

    assert w._zone_splitter_saved_sizes == [470, 760, 350]
    assert load_modul_splitter_sizes() == [470, 760, 350]
