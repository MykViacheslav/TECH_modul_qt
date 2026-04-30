from __future__ import annotations
import traceback
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget, QLabel

class TabFirmaHub(QWidget):
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

        # Dashboard
        try:
            from src.tabs.dashboard.tab_dashboard import TabDashboard
            self.tabs.addTab(TabDashboard(), "DASHBOARD")
        except: self.tabs.addTab(QLabel("Błąd: Dashboard"), "DASHBOARD")

        # Alarmy
        try:
            from src.tabs.alarmy.tab_alarmy import TabAlarmy
            self.tabs.addTab(TabAlarmy(), "ALARM / LOGS")
        except: self.tabs.addTab(QLabel("Błąd: Alarmy"), "ALARM / LOGS")

        # Kalendarz
        try:
            from src.tabs.kalendarz.tab_kalendarz import TabKalendarz
            self.tabs.addTab(TabKalendarz(), "KALENDARZ")
        except: self.tabs.addTab(QLabel("Błąd: Kalendarz"), "KALENDARZ")

        # Czas Pracy
        try:
            from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy
            self.tabs.addTab(TabCzasPracy(), "CZAS PRACY")
        except: self.tabs.addTab(QLabel("Błąd: Czas Pracy"), "CZAS PRACY")

        # Pracownicy
        try:
            from src.tabs.pracownicy.tab_pracownicy import TabPracownicy
            self.tabs.addTab(TabPracownicy(), "PRACOWNICY")
        except: self.tabs.addTab(QLabel("Błąd: Pracownicy"), "PRACOWNICY")
