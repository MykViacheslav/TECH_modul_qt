from __future__ import annotations

from PySide6 import QtWidgets
from tabs.registry import build_tabs


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, ctx) -> None:
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("TECH — Kalkulator (GUI)")

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        for title, widget in build_tabs(ctx):
            self.tabs.addTab(widget, title)

        self.resize(1280, 820)
