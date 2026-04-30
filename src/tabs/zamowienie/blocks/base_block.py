"""
Base class for order form blocks.

Each block represents a collapsible section in the order form.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.collapsible_block import CollapsibleBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


class OrderFormBlock:
    """
    Bazowa klasa dla bloków formularza zamówienia.
    
    Każdy blok (Klient, Zamówienie, Wycena, etc.) dziedziczy z tej klasy
    i implementuje metodę build().
    """
    
    def __init__(self, parent: "TabNoweZamowienie", title: str) -> None:
        self.parent_tab = parent
        self.title = title
        self.block = CollapsibleBlock(title, parent)
        self._setup_block()
    
    def _setup_block(self) -> None:
        """Konfiguruje podstawowe właściwości bloku."""
        self.block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._apply_visual_polish()
    
    def _apply_visual_polish(self) -> None:
        """Stosuje style wizualne do bloku."""
        self.block.setStyleSheet(
            "QToolButton {"
            "padding: 12px 14px;"
            "font-size: 15px;"
            "font-weight: 800;"
            "text-align: left;"
            "border: 1px solid #d9cfbe;"
            "border-radius: 12px;"
            "background: #fffdf9;"
            "color: #1f2a37;"
            "}"
            "QToolButton:hover {"
            "background: #f8f1e6;"
            "border-color: #cdbca0;"
            "}"
            "QToolButton:checked {"
            "background: #efe4d2;"
            "border-color: #beaa86;"
            "color: #1b2430;"
            "}"
            "QToolButton:checked:hover {"
            "background: #e9dcc8;"
            "border-color: #b4996f;"
            "}"
            "QFrame#contentPanel {"
            "border: 1px solid #e7dccd;"
            "border-top: 0px;"
            "border-bottom-left-radius: 12px;"
            "border-bottom-right-radius: 12px;"
            "background: #fefcf8;"
            "}"
        )
        content_layout = self.block.content_layout()
        content_layout.setContentsMargins(16, 13, 16, 15)
        content_layout.setSpacing(10)
    
    def get_layout(self) -> QVBoxLayout:
        """Zwraca layout zawartości bloku."""
        return self.block.content_layout()
    
    def build(self) -> None:
        """
        Buduje zawartość bloku.
        Należy nadpisać w klasach potomnych.
        """
        raise NotImplementedError
    
    @staticmethod
    def make_section_header(text: str, parent: QWidget) -> QLabel:
        """Tworzy nagłówek sekcji wewnątrz bloku."""
        label = QLabel(text, parent)
        muted = get_muted_color()
        label.setStyleSheet(
            "font-size: 12px;"
            "font-weight: 700;"
            f"color: {muted};"
            "padding: 4px 0px;"
            "border-bottom: 1px solid #e5e7eb;"
            "margin-top: 8px;"
        )
        return label
    
    @staticmethod
    def make_section_separator(parent: QWidget) -> QFrame:
        """Tworzy linię separującą między sekcjami."""
        line = QFrame(parent)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e5e7eb;")
        line.setFixedHeight(1)
        return line
    
    @staticmethod
    def make_compact_button(button: QPushButton, min_width: int = 120, max_width: int = 160) -> None:
        """Ustawia przycisk na kompaktowy rozmiar."""
        button.setMinimumWidth(min_width)
        button.setMaximumWidth(max_width)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    @staticmethod
    def make_work_panel(title: str, subtitle: str = "", parent: QWidget | None = None) -> tuple[QFrame, QVBoxLayout]:
        """Tworzy panel roboczy z tytułem."""
        panel = QFrame(parent); panel.setProperty("uiCard", True)
        panel.setStyleSheet(
            "QFrame {"
            "border: 1px solid #e5e7eb;"
            "border-radius: 8px;"
            "background: #fafafa;"
            "}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        if title:
            title_label = QLabel(title, panel)
            title_label.setStyleSheet("font-weight: 700; color: #374151;")
            layout.addWidget(title_label)
        
        if subtitle:
            subtitle_label = QLabel(subtitle, panel)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("color: #6b7280; font-size: 12px;")
            layout.addWidget(subtitle_label)
        
        return panel, layout
