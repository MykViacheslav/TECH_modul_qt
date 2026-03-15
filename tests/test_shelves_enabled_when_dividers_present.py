from PyQt6.QtWidgets import QApplication

def test_shelves_block_enabled_when_divider_present(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    # wlacz piony i ustaw 1
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "divider"]))
    w.dividers.set_values(1, "right")
    w._on_any_change()

    # blok polek ma byc aktywny (zeby dalo sie ustawic liczbe i strone)
    assert w.shelves.isEnabled()
def test_shelves_block_stays_enabled_when_count_is_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    w.shelves.set_value(0)
    w.dividers.set_values(0, "right")
    w._on_any_change()

    assert w.shelves.isEnabled()
