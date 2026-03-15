from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QToolButton, QVBoxLayout, QSizePolicy, QFrame


class CollapsibleBlock(QWidget):
    """
    Zwijany blok UI (jak Scratch): naglowek + zawartosc.
    GUI: PL
    Identyfikatory wewnetrzne: EN (bez PL znakow).
    """
    toggled = pyqtSignal(bool)

    def __init__(self, title_pl: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._btn = QToolButton(self)
        self._btn.setText(title_pl)
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._btn.setArrowType(Qt.ArrowType.DownArrow)
        self._btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._content = QFrame(self)
        self._content.setFrameShape(QFrame.Shape.NoFrame)
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(10, 8, 10, 10)
        self._content_lay.setSpacing(8)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._btn)
        root.addWidget(self._content)

        self._btn.toggled.connect(self._on_toggled)

        self.setStyleSheet("""
            QToolButton {
                padding: 6px;
                font-weight: 600;
                border: 1px solid #cfcfcf;
                border-radius: 6px;
                background: #fafafa;
            }
            QFrame {
                border: 1px solid #e4e4e4;
                border-top: 0px;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                background: #ffffff;
            }
        """)

    def content_layout(self) -> QVBoxLayout:
        return self._content_lay

    def set_expanded(self, on: bool) -> None:
        self._btn.setChecked(bool(on))

    def is_expanded(self) -> bool:
        return bool(self._btn.isChecked())

    def _on_toggled(self, on: bool) -> None:
        self._btn.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)
        self._content.setVisible(on)
        self.toggled.emit(on)
