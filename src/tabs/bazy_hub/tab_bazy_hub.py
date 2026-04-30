from __future__ import annotations
import traceback
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget, QLabel

class TabBazyHub(QWidget):
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

        # Bazy (Przegląd/Hub)
        try:
            from src.tabs.bazy.tab_bazy import TabBazy
            self.tabs.addTab(TabBazy(), "PRZEGLĄD BAZ")
        except: self.tabs.addTab(QLabel("Błąd: Bazy"), "PRZEGLĄD BAZ")

        # Baza Modułów
        try:
            from src.tabs.baza_modul.tab_baza_modul import TabBazaModul
            self.tabs.addTab(TabBazaModul(), "BAZA MODUŁÓW")
        except: self.tabs.addTab(QLabel("Błąd: Baza Modułów"), "BAZA MODUŁÓW")

        # Baza Materiałów
        try:
            from src.tabs.baza_materialu.tab_baza_materialu import TabBazaMaterialu
            self.tabs.addTab(TabBazaMaterialu(), "BAZA MATERIAŁÓW")
        except: self.tabs.addTab(QLabel("Błąd: Baza Materiału"), "BAZA MATERIAŁÓW")

        # Cennik Szybkich Wycen
        try:
            from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen
            self.tabs.addTab(TabBazaSzybkichWycen(), "CENNIK WYCEN")
        except: self.tabs.addTab(QLabel("Błąd: Cennik Wycen"), "CENNIK WYCEN")

        # Baza Usług
        try:
            from src.tabs.baza_uslug.tab_baza_uslug import TabBazaUslug
            self.tabs.addTab(TabBazaUslug(), "CENNIK USŁUG")
        except: self.tabs.addTab(QLabel("Błąd: Baza Usług"), "CENNIK USŁUG")
