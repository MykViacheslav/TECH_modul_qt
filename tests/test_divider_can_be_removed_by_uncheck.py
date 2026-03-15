from PyQt6.QtWidgets import QApplication


def test_divider_is_removed_when_unchecked(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # 1) wlacz piony + ustaw 2
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "divider"]))
    w.dividers.set_values(2, "right")
    w._on_any_change()

    assert w._draft.divider_count == 2
    assert "divider_1" in (w._draft.parts or {})
    assert "divider_2" in (w._draft.parts or {})

    # 2) odznacz "Pion"
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom"]))
    w._on_any_change()

    assert w._draft.divider_count == 0
    keys = set((w._draft.parts or {}).keys())
    assert "divider_1" not in keys
    assert "divider_2" not in keys