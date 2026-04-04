"""
Walls block for the order form.

Handles the list of walls attached to the order.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


class WallsBlock(OrderFormBlock):
    """Blok ścian zamówienia."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Projekty")
        self.block.set_expanded(False)  # Domyślnie zwinięty
    
    def build(self) -> None:
        """Buduje zawartość bloku ścian."""
        layout = self.get_layout()
        
        note = QLabel("Lista scian przypietych do tego zamowienia.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        # Przyciski
        btns = QHBoxLayout()
        self.btn_new_wall = QPushButton("Dodaj nowa sciane", self.block)
        self.btn_open_wall = QPushButton("Otworz zaznaczona", self.block)
        self.btn_refresh_walls = QPushButton("Odswiez sciany", self.block)
        
        for button in (self.btn_new_wall, self.btn_open_wall, self.btn_refresh_walls):
            self.make_compact_button(button, min_width=140, max_width=170)
            btns.addWidget(button, 0)
        btns.addStretch(1)
        layout.addLayout(btns)
        
        # Tabela ścian
        self.tbl_walls = QTableWidget(0, 4, self.block)
        self.tbl_walls.setHorizontalHeaderLabels(["Sciana", "Typ", "Przeszkody", "Widok"])
        self.tbl_walls.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_walls.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_walls.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_walls.verticalHeader().setVisible(False)
        self.tbl_walls.horizontalHeader().setStretchLastSection(True)
        self.tbl_walls.setAlternatingRowColors(True)
        self.tbl_walls.setMinimumHeight(170)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tbl_walls)
