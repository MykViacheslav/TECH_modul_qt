from __future__ import annotations
import traceback
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QLabel, QFrame

class TabProjektHub(QWidget):
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

        # Moduł
        try:
            from src.tabs.modul.tab_modul import TabModul
            self.tabs.addTab(TabModul(), "MODUŁ")
        except: self.tabs.addTab(QLabel("Błąd: Moduł"), "MODUŁ")

        # Komplet
        try:
            from src.tabs.sciana.tab_sciana import TabSciana
            self.tabs.addTab(TabSciana(), "KOMPLET")
        except: self.tabs.addTab(QLabel("Błąd: Komplet"), "KOMPLET")

        # Ściana
        try:
            from src.tabs.sciana.tab_sciana_layout import TabScianaLayout
            self.tabs.addTab(TabScianaLayout(), "ŚCIANA")
        except: self.tabs.addTab(QLabel("Błąd: Ściana"), "ŚCIANA")
