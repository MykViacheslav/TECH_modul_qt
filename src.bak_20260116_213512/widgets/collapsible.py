from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class CollapsibleSection(QtWidgets.QWidget):
    """
    Sekcja: nagłówek + treść (może być wiele otwartych jednocześnie).
    """
    toggled = QtCore.Signal(bool)

    def __init__(self, title: str, content: QtWidgets.QWidget | None = None, opened: bool = True, parent=None):
        super().__init__(parent)

        self._opened = bool(opened)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.btn = QtWidgets.QToolButton()
        self.btn.setText(title)
        self.btn.setCheckable(True)
        self.btn.setChecked(self._opened)
        self.btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if self._opened else QtCore.Qt.ArrowType.RightArrow)
        self.btn.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn.clicked.connect(self._on_clicked)

        self.frame = QtWidgets.QFrame()
        self.frame.setObjectName("CollapsibleFrame")
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame.setVisible(self._opened)

        frameL = QtWidgets.QVBoxLayout(self.frame)
        frameL.setContentsMargins(10, 8, 10, 8)
        frameL.setSpacing(8)

        if content is None:
            content = QtWidgets.QWidget()
            content.setLayout(QtWidgets.QVBoxLayout())

        frameL.addWidget(content)

        root.addWidget(self.btn)
        root.addWidget(self.frame)

    def set_title(self, title: str) -> None:
        self.btn.setText(title)

    def is_open(self) -> bool:
        return self._opened

    def set_open(self, value: bool) -> None:
        value = bool(value)
        if self._opened == value:
            return
        self._opened = value
        self.btn.setChecked(value)
        self.btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if value else QtCore.Qt.ArrowType.RightArrow)
        self.frame.setVisible(value)
        self.toggled.emit(value)

    def _on_clicked(self) -> None:
        self.set_open(self.btn.isChecked())
