from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class CollapsibleSection(QtWidgets.QWidget):
    """
    Robust collapsible widget:
    - .content (QWidget)
    - .contentLayout (QVBoxLayout)
    - click triangle/title -> hides content (no "empty but visible" bug)
    """
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)

        self._btn = QtWidgets.QToolButton()
        self._btn.setText(title)
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._btn.setArrowType(QtCore.Qt.DownArrow)
        self._btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn.clicked.connect(self._toggle)

        self.content = QtWidgets.QWidget()
        self.contentLayout = QtWidgets.QVBoxLayout(self.content)
        self.contentLayout.setContentsMargins(8, 8, 8, 8)
        self.contentLayout.setSpacing(8)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addWidget(self._btn)
        root.addWidget(self.content)

    def _toggle(self):
        on = self._btn.isChecked()
        self.content.setVisible(on)
        self._btn.setArrowType(QtCore.Qt.DownArrow if on else QtCore.Qt.RightArrow)

    def setCollapsed(self, collapsed: bool):
        self._btn.setChecked(not collapsed)
        self._toggle()