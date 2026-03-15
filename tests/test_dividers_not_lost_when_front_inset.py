from PyQt6.QtWidgets import QApplication


def test_dividers_not_lost_when_front_layout_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # ustaw: 2 piony w bloku "Piony"
    w.dividers.set_values(2, "right")

    # UWAGA: nie zaznaczamy checkboxa "Pion" recznie
    # zmiana innego ustawienia (np. front_layout) ma nie wyzerowac pionow
    idx = w.fhw.cb_front_layout.findData("inset")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    w._on_any_change()

    assert w._draft.divider_count == 2
    assert "divider" in w._draft.visible_parts