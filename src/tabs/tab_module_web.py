from __future__ import annotations

import os
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from .base import BaseTab

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None

class Tab(BaseTab):
    TAB_TITLE_PL = "Moduł"
    tab_title = "Moduł"
    tab_id = "module_web"

    def __init__(self, ctx=None, parent=None):
        super().__init__(ctx=ctx, parent=parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        if QWebEngineView is None:
            box = QtWidgets.QTextEdit(self)
            box.setReadOnly(True)
            box.setPlainText(
                "QtWebEngine is not available.\n"
                "Install/repair PySide6 QtWebEngine (PySide6-Addons) and restart.\n\n"
                "Meanwhile: web prototype cannot be embedded."
            )
            lay.addWidget(box)
            return

        view = QWebEngineView(self)
        # tabs/ is src/tabs/, so parent is src/
        src_dir = Path(__file__).resolve().parents[1]
        index_html = src_dir / "webui" / "index.html"
        url = QtCore.QUrl.fromLocalFile(str(index_html))
        view.load(url)
        lay.addWidget(view)