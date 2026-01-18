from __future__ import annotations

from PySide6 import QtWidgets
from .base import BaseTab

class PlaceholderTab(BaseTab):
    tab_id: str = "placeholder"
    TAB_TITLE_PL: str = "Placeholder"
    tab_title: str = "Placeholder"

    # registry.py often calls: PlaceholderTab(ctx, "Moduł")
    # so 2nd arg is title (str), not QWidget parent.
    def __init__(self, ctx=None, title: str = "Placeholder", parent=None):
        # if someone passes (ctx, parentWidget) by mistake, tolerate it
        if parent is None and isinstance(title, QtWidgets.QWidget):
            parent = title
            title = "Placeholder"

        super().__init__(ctx=ctx, parent=parent)

        lay = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel(f"Placeholder: {title}")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)