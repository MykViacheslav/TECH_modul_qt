from __future__ import annotations
from PySide6 import QtWidgets

class BazaModuluTab(QtWidgets.QWidget):
    """TOP TAB: BAZA modułu (library/database)."""

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        title = QtWidgets.QLabel("BAZA modułu")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        lay.addWidget(title)

        info = QtWidgets.QLabel(
            "Tu będzie biblioteka zapisanych modułów + wyszukiwanie + podgląd.\n"
            "Zakładka niezależna (osobny plik)."
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        lay.addStretch(1)
