from __future__ import annotations

from PySide6.QtCore import QSettings, QByteArray
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
from PySide6.QtCore import QObject


ORG_NAME = "TECH_modul"
APP_NAME = "TECH_modul_qt"


def _settings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def restore_window_state(window: QMainWindow) -> None:
    s = _settings()

    geom = s.value("window/geometry", None)
    if isinstance(geom, (QByteArray, bytes)):
        window.restoreGeometry(geom)

    state = s.value("window/state", None)
    if isinstance(state, (QByteArray, bytes)):
        window.restoreState(state)

    # Restore any splitters by objectName
    # (only if splitters have objectName set)
    # keys: splitter/<name>
    for obj in window.findChildren(QSplitter):
        name = obj.objectName()
        if name:
            val = s.value(f"splitter/{name}", None)
            if isinstance(val, (QByteArray, bytes)):
                obj.restoreState(val)


def save_window_state(window: QMainWindow) -> None:
    s = _settings()
    s.setValue("window/geometry", window.saveGeometry())
    s.setValue("window/state", window.saveState())

    for obj in window.findChildren(QSplitter):
        name = obj.objectName()
        if name:
            s.setValue(f"splitter/{name}", obj.saveState())


def setup_autosave(app: QApplication, window: QMainWindow) -> None:
    # Save on quit
    def _on_quit():
        try:
            save_window_state(window)
        except Exception:
            pass

    app.aboutToQuit.connect(_on_quit)
