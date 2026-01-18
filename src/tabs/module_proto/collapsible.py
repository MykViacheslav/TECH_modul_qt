from __future__ import annotations

from PySide6 import QtCore, QtWidgets

class CollapsibleSection(QtWidgets.QWidget):
    """
    Stable collapsible section used by module_proto (doesn't depend on widgets.collapsible API).
    Provides .content (QWidget) and .contentLayout (QVBoxLayout) for convenience.
    """
    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)

        self._btn = QtWidgets.QToolButton(text=title, checkable=True, checked=expanded)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self._btn.clicked.connect(self._toggle)

        self.content = QtWidgets.QWidget()
        self.contentLayout = QtWidgets.QVBoxLayout(self.content)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(8)
        self.content.setVisible(expanded)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addWidget(self._btn)
        root.addWidget(self.content)

    def _toggle(self):
        on = self._btn.isChecked()
        self.content.setVisible(on)
        self._btn.setArrowType(QtCore.Qt.DownArrow if on else QtCore.Qt.RightArrow)

    def setExpanded(self, on: bool):
        self._btn.setChecked(bool(on))
        self._toggle()

    def isExpanded(self) -> bool:
        return self._btn.isChecked()