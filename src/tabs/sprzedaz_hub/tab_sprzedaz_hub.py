from __future__ import annotations
import traceback
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QLabel,
    QFrame
)
from src.app.app_settings import load_ui_theme_settings

class TabSprzedazHub(QWidget):
    """
    Główny hub sekcji Sprzedaż, łączący Start, Nowe Zamówienie i Wycenę
    w jednym poziomym widoku (oszczędność miejsca w Sidebarze).
    """
    # Sygnały przekazywane do MainWindow
    sig_open_calendar_requested = pyqtSignal()
    sig_open_work_time_requested = pyqtSignal()
    sig_open_time_kiosk_requested = pyqtSignal()
    sig_open_clients_requested = pyqtSignal()
    sig_new_wall_requested = pyqtSignal()
    sig_new_assembly_requested = pyqtSignal()
    sig_new_module_requested = pyqtSignal()
    sig_open_bazy_requested = pyqtSignal()
    sig_open_settings_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Nagłówek sekcji (opcjonalny, dla prestiżowego wyglądu)
        self.header = QFrame(self)
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("background: transparent; border-bottom: 1px solid rgba(0,0,0,0.05);")
        header_lay = QHBoxLayout(self.header)
        header_lay.setContentsMargins(15, 0, 15, 0)
        
        self.title = QLabel("DZIAŁ SPRZEDAŻY", self.header)
        self.title.setStyleSheet("font-weight: 800; font-size: 11px; letter-spacing: 1.5px; color: #64748b;")
        header_lay.addWidget(self.title)
        header_lay.addStretch(1)
        root.addWidget(self.header)

        # Główne zakładki poziome
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        # Stylizacja paska zakładek na "Pigułki"
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
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(59, 130, 246, 0.1);
                color: #3b82f6;
            }
            QTabWidget::pane { border: 0; }
        """)
        root.addWidget(self.tabs)

        # Ładowanie pod-zakładek
        self._setup_tabs()

    def _setup_tabs(self):
        # 1. Start (Pulpit sprzedaży)
        try:
            from src.tabs.start.tab_start import TabStart
            self.tab_start = TabStart()
            self.tabs.addTab(self.tab_start, "PULPIT / BAZA")
            
            # Naprawa przycisków "Szybki start" na pulpicie
            self.tab_start.sig_new_order_requested.connect(lambda: self.tabs.setCurrentIndex(1))
            self.tab_start.sig_open_quote_requested.connect(lambda: self.tabs.setCurrentIndex(2))
            
            # Przekazywanie sygnałów globalnych (przełączanie ikon w sidebarze)
            self.tab_start.sig_open_calendar_requested.connect(self.sig_open_calendar_requested.emit)
            self.tab_start.sig_open_work_time_requested.connect(self.sig_open_work_time_requested.emit)
            self.tab_start.sig_open_time_kiosk_requested.connect(self.sig_open_time_kiosk_requested.emit)
            self.tab_start.sig_open_clients_requested.connect(self.sig_open_clients_requested.emit)
            self.tab_start.sig_new_wall_requested.connect(self.sig_new_wall_requested.emit)
            self.tab_start.sig_new_assembly_requested.connect(self.sig_new_assembly_requested.emit)
            self.tab_start.sig_new_module_requested.connect(self.sig_new_module_requested.emit)
            self.tab_start.sig_open_bazy_requested.connect(self.sig_open_bazy_requested.emit)
            self.tab_start.sig_open_settings_requested.connect(self.sig_open_settings_requested.emit)
        except Exception:
            traceback.print_exc()
            self.tabs.addTab(QLabel("Błąd ładowania Pulpitu"), "PULPIT / BAZA")

        # 2. Nowe Zamówienie
        try:
            from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie
            self.tab_order = TabNoweZamowienie()
            self.tabs.addTab(self.tab_order, "KREATOR ZAMÓWIENIA")
        except Exception:
            traceback.print_exc()
            self.tabs.addTab(QLabel("Błąd ładowania Kreatora"), "KREATOR ZAMÓWIENIA")

        # 3. Wycena (Hub)
        try:
            from src.tabs.wycena_hub.tab_wycena_hub import TabWycenaHub
            self.tab_quote = TabWycenaHub()
            self.tabs.addTab(self.tab_quote, "CENTRUM WYCEN")
            
            # Obsługa przycisku "Wróć do zamówienia" z wnętrza wyceny
            if hasattr(self.tab_quote, "sig_open_order_requested"):
                self.tab_quote.sig_open_order_requested.connect(self.focus_new_order)
        except Exception:
            traceback.print_exc()
            self.tabs.addTab(QLabel("Błąd ładowania Wycen"), "CENTRUM WYCEN")

    def focus_new_order(self):
        """Metoda pomocnicza do szybkiego przełączania na kreator."""
        self.tabs.setCurrentIndex(1)
