from PyQt6.QtWidgets import QApplication


def test_dividers_count_rebuilds_parts(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    # wlacz piony i ustaw 2
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "divider"]))
    w.dividers.set_values(2, "right")
    w._on_any_change()

    keys = set(w._draft.parts.keys())
    assert "divider_1" in keys
    assert "divider_2" in keys

    # wylacz piony przez liczbe 0
    w.dividers.set_values(0, "right")
    w._on_any_change()

    keys2 = set(w._draft.parts.keys())
    assert "divider_1" not in keys2
    assert "divider_2" not in keys2