from PyQt6.QtWidgets import QApplication


def test_shelves_count_rebuilds_parts(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    # wlacz polki i ustaw 2
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "shelf"]))
    w.shelves.set_value(2)
    w._on_any_change()

    keys = set(w._draft.parts.keys())
    assert "shelf_1" in keys
    assert "shelf_2" in keys

    # zmien na 1
    w.shelves.set_value(1)
    w._on_any_change()

    keys2 = set(w._draft.parts.keys())
    assert "shelf_1" in keys2
    assert "shelf_2" not in keys2