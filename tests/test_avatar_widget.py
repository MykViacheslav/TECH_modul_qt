from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.avatar.avatar_widget import AvatarWidget


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_avatar_widget_instantiation(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = _app()
    aw = AvatarWidget(data_dir=str(tmp_path))
    assert aw is not None

    aw._store.add_note("test note")
    aw._load_notes()
    assert "test note" in aw.notes_view.toPlainText()

    aw.close()
    app.processEvents()
