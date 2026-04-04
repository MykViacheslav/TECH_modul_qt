"""
Actions block for the order form.

Handles action buttons like save, export, etc.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


class ActionsBlock(OrderFormBlock):
    """Blok akcji w formularzu zamówienia."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Akcje")
    
    def build(self) -> None:
        """Buduje zawartość bloku akcji."""
        layout = self.get_layout()
        
        # Przyciski główne
        btns = QHBoxLayout()
        btns.setSpacing(10)
        
        self.btn_save_order = QPushButton("Zapisz zamowienie", self.block)
        self.btn_save_order.setMinimumHeight(48)
        self.btn_save_order.setStyleSheet(
            "QPushButton {"
            "background: #2563eb;"
            "color: white;"
            "border: none;"
            "border-radius: 8px;"
            "font-weight: 700;"
            "padding: 0 20px;"
            "}"
            "QPushButton:hover {"
            "background: #1d4ed8;"
            "}"
        )
        btns.addWidget(self.btn_save_order)
        
        self.btn_clear_form = QPushButton("Wyczysc", self.block)
        self.make_compact_button(self.btn_clear_form, min_width=100, max_width=130)
        btns.addWidget(self.btn_clear_form)
        
        btns.addStretch(1)
        layout.addLayout(btns)
        
        # Przyciski eksportu
        layout.addWidget(self.make_section_separator(self.block))
        layout.addWidget(self.make_section_header("Eksport PDF", self.block))
        
        # Wiersz 1 - Podstawowe
        export_btns_row1 = QHBoxLayout()
        export_btns_row1.setSpacing(8)
        
        self.btn_export_summary_pdf = QPushButton("Podsumowanie", self.block)
        self.btn_export_summary_pdf.setToolTip("Eksportuj podsumowanie zamówienia z kosztami i płatnościami")
        self.make_compact_button(self.btn_export_summary_pdf, min_width=120, max_width=150)
        export_btns_row1.addWidget(self.btn_export_summary_pdf)
        
        self.btn_export_bom_pdf = QPushButton("BOM", self.block)
        self.btn_export_bom_pdf.setToolTip("Eksportuj Bill of Materials - listę elementów")
        self.make_compact_button(self.btn_export_bom_pdf, min_width=80, max_width=110)
        export_btns_row1.addWidget(self.btn_export_bom_pdf)
        
        export_btns_row1.addStretch(1)
        layout.addLayout(export_btns_row1)
        
        # Wiersz 2 - Oferta
        export_btns_row2 = QHBoxLayout()
        export_btns_row2.setSpacing(8)
        
        self.btn_export_offer_pdf = QPushButton("Oferta dla klienta", self.block)
        self.btn_export_offer_pdf.setToolTip("Eksportuj ofertę w formacie gotowym dla klienta")
        self.make_compact_button(self.btn_export_offer_pdf, min_width=150, max_width=180)
        export_btns_row2.addWidget(self.btn_export_offer_pdf)
        
        self.btn_export_offer = QPushButton("Oferta HTML", self.block)
        self.make_compact_button(self.btn_export_offer, min_width=110, max_width=140)
        export_btns_row2.addWidget(self.btn_export_offer)
        
        export_btns_row2.addStretch(1)
        layout.addLayout(export_btns_row2)
        
        # Info
        note = QLabel("Zapisz zamowienie przed eksportem. Pliki PDF zapisywane w katalogu export/pdf/.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#9ca3af; font-size: 11px;")
        layout.addWidget(note)
