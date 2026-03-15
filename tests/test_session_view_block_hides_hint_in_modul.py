from PyQt6.QtWidgets import QApplication


def test_session_view_block_hides_hint_label(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import SessionAndViewBlock

    w = SessionAndViewBlock()

    assert hasattr(w, "lab_hint")
    assert w.lab_hint.isHidden() is True


def test_tab_modul_keeps_hidden_session_hint_label(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "sessview")
    assert hasattr(w.sessview, "lab_hint")
    assert w.sessview.lab_hint.isHidden() is True