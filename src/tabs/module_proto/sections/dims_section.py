from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from widgets.collapsible import CollapsibleSection


def _content_layout(sec: QtWidgets.QWidget) -> QtWidgets.QLayout:
    """
    CollapsibleSection implementations in our repo may differ.
    We support: contentLayout / content_layout / (content widget with its own layout).
    """
    lay = getattr(sec, "contentLayout", None) or getattr(sec, "content_layout", None)
    if lay is not None:
        return lay

    content = getattr(sec, "content", None) or getattr(sec, "body", None)
    if content is not None:
        lay2 = content.layout()
        if lay2 is None:
            lay2 = QtWidgets.QVBoxLayout(content)
            lay2.setContentsMargins(0, 0, 0, 0)
        return lay2

    # last resort: use section's own layout
    lay3 = sec.layout()
    if lay3 is None:
        lay3 = QtWidgets.QVBoxLayout(sec)
        lay3.setContentsMargins(0, 0, 0, 0)
    return lay3


class DimsSection(QtWidgets.QWidget):
    """
    Extracted section: Wymiary + Anchor
    Provides the same widgets as before: w, h, d, anchor.
    """
    changed = QtCore.Signal()

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.section = CollapsibleSection("Wymiary + Anchor")
        outer.addWidget(self.section)

        dims = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(dims)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)

        self.w = QtWidgets.QSpinBox(); self.w.setRange(50, 5000); self.w.setValue(600)
        self.h = QtWidgets.QSpinBox(); self.h.setRange(50, 5000); self.h.setValue(720)
        self.d = QtWidgets.QSpinBox(); self.d.setRange(50, 2000); self.d.setValue(560)

        self.anchor = QtWidgets.QComboBox()
        self.anchor.addItems(["NONE", "LT", "RT", "LB", "RB"])

        g.addWidget(QtWidgets.QLabel("W (mm)"), 0, 0); g.addWidget(self.w, 0, 1)
        g.addWidget(QtWidgets.QLabel("H (mm)"), 1, 0); g.addWidget(self.h, 1, 1)
        g.addWidget(QtWidgets.QLabel("D (mm)"), 2, 0); g.addWidget(self.d, 2, 1)
        g.addWidget(QtWidgets.QLabel("Anchor"), 3, 0); g.addWidget(self.anchor, 3, 1)

        _content_layout(self.section).addWidget(dims)

        # emit changed
        for sp in (self.w, self.h, self.d):
            sp.valueChanged.connect(self.changed.emit)
        self.anchor.currentIndexChanged.connect(self.changed.emit)