from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow
from src.tabs.avatar.tab_avatar import AvatarTab


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_avatar_in_ui_integration(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    mw = MainWindow()
    mw.show()
    app.processEvents()

    avatar_tab = mw._tabs_by_title.get("Avatar")
    assert avatar_tab is not None
    assert isinstance(avatar_tab, AvatarTab)

    avatar_widget = avatar_tab.avatar
    avatar_widget._store.add_note("integration test note (UI)")
    avatar_widget._load_notes()
    text = avatar_widget.notes_view.toPlainText()
    assert "integration test note (UI)" in text

    mw.close()
    app.processEvents()
