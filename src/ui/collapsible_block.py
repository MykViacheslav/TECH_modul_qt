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
        self._content.setObjectName("contentPanel")
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(14, 12, 14, 14)
        self._content_lay.setSpacing(10)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._btn)
        root.addWidget(self._content)

        self._btn.toggled.connect(self._on_toggled)

        self.setStyleSheet("""
            QToolButton {
                padding: 12px 16px;
                font-size: 13px;
                font-weight: 800;
                text-align: left;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: white;
                color: #374151;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            QToolButton:hover {
                background: #f9fafb;
                border-color: #d1d5db;
                color: #005596;
            }
            QToolButton:checked {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                background: #f8fafc;
                border-color: #e2e8f0;
            }
            QFrame#contentPanel {
                border: 1px solid #e2e8f0;
                border-top: 0px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                background: white;
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
