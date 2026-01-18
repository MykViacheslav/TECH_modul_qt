from __future__ import annotations

from PySide6 import QtWidgets

class BaseTab(QtWidgets.QWidget):
    """Minimal base class for tabs."""
    tab_id: str = "base"
    tab_title: str = "Base"

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx