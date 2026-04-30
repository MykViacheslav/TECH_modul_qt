from __future__ import annotations
import traceback
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget, QLabel

class TabUstawieniaHub(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 20px;
                margin: 4px 2px;
                border-radius: 15px;
                font-weight: 700;
                font-size: 11px;
                background: rgba(0,0,0,0.05);
                color: #64748b;
            }
            QTabBar::tab:selected { background: #3b82f6; color: white; }
            QTabWidget::pane { border: 0; }
        """)
        root.addWidget(self.tabs)

        # Ustawienia Rysunku
        try:
            from src.tabs.rysunek.tab_rysunek import TabRysunek
            self.tabs.addTab(TabRysunek(), "DOKUMENTACJA")
        except: self.tabs.addTab(QLabel("Błąd: Ustawienia"), "DOKUMENTACJA")

        # Ekrany
        try:
            from src.tabs.ekrany.tab_ekrany import TabEkrany
            self.tabs.addTab(TabEkrany(), "EKRANY")
        except: self.tabs.addTab(QLabel("Błąd: Ekrany"), "EKRANY")

        # Stanowiska
        try:
            from src.tabs.stanowiska.tab_stanowiska import TabStanowiska
            self.tabs.addTab(TabStanowiska(), "STANOWISKA")
        except: self.tabs.addTab(QLabel("Błąd: Stanowiska"), "STANOWISKA")

        # QR Telefon
        try:
            from src.tabs.qr_telefon.tab_qr_telefon import TabQrTelefon
            self.tabs.addTab(TabQrTelefon(), "QR TELEFON")
        except: self.tabs.addTab(QLabel("Błąd: QR"), "QR")

        # Struktura
        try:
            from src.tabs.struktura.tab_struktura import TabStruktura
            self.tabs.addTab(TabStruktura(), "STRUKTURA")
        except: self.tabs.addTab(QLabel("Błąd: Struktura"), "STRUKTURA")
