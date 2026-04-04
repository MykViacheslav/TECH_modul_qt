from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_avatar_startup_ui_availability(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    mw = MainWindow()
    mw.show()
    app.processEvents()

    assert "Avatar" in mw._tabs_by_title
    group_idx = mw._tab_title_to_group.get("Avatar")
    assert group_idx is not None
    gtw = mw._group_tabwidgets[group_idx]
    local_idx = mw._tab_title_to_local_idx.get("Avatar")
    assert local_idx is not None
    tab_container = gtw.widget(local_idx)
    assert tab_container is not None

    inner = tab_container.widget()
    assert inner is not None
    avatar_widget = getattr(inner, "avatar", None)
    assert avatar_widget is not None

    avatar_widget._store.add_note("startup UI test note")
    avatar_widget._load_notes()
    text = avatar_widget.notes_view.toPlainText()
    assert "startup UI test note" in text

    mw.close()
    app.processEvents()
