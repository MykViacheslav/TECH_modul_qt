"""
Order details block for the order form.

Handles order code, name, status, dates, and site address.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


# Status zamówienia
ORDER_STATUS_ITEMS: tuple[str, ...] = (
    "Nowe",
    "Wycena",
    "Wycena gotowa",
    "Zaakceptowane",
    "Zakup materialow",
    "W produkcji",
    "Lakiernia",
    "Montaz",
    "Poprawki",
    "Zakonczone",
)


class OrderBlock(OrderFormBlock):
    """Blok zamówienia w formularzu."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Zamówienie")
        self._order_field_cells: dict[str, QWidget] = {}
        self._order_primary_defaults = ["order_id", "code", "order_name", "status"]
        self._order_address_defaults = ["site_street", "site_house_number", "site_apartment_number", "site_postal_code", "site_city"]
    
    def build(self) -> None:
        """Buduje zawartość bloku zamówienia."""
        layout = self.get_layout()
        content_parent = self.block
        
        # Przyciski akcji
        self.btn_pick_order = QPushButton("Wczytaj z bazy", self.block)
        self.btn_save_order = QPushButton("Zapisz zamowienie", self.block)
        self.btn_open_orders_base = QPushButton("Bazy", self.block)
        self.make_compact_button(self.btn_pick_order, min_width=120, max_width=150)
        self.make_compact_button(self.btn_save_order, min_width=130, max_width=160)
        self.make_compact_button(self.btn_open_orders_base, min_width=70, max_width=90)
        self.btn_pick_order.hide()
        self.btn_save_order.hide()
        self.btn_open_orders_base.hide()
        
        # Pola podstawowe
        layout.addWidget(self.make_section_header("Dane zamówienia", self.block))
        
        self.ed_order_id = QLineEdit(self.block)
        self.ed_order_id.setPlaceholderText("ID")
        self.ed_order_id.setMinimumWidth(70)
        self.ed_order_id.setReadOnly(True)
        self.ed_order_id.setToolTip("ID nadaje sie automatycznie.")
        
        self.ed_order_code = QLineEdit(self.block)
        self.ed_order_code.setPlaceholderText("Kod")
        self.ed_order_code.setMinimumWidth(130)
        
        self.ed_order_name = QLineEdit(self.block)
        self.ed_order_name.setPlaceholderText("Nazwa zamowienia")
        self.ed_order_name.setMinimumWidth(200)
        
        self.cb_order_status = QComboBox(self.block)
        for item in ORDER_STATUS_ITEMS:
            self.cb_order_status.addItem(item)
        self.cb_order_status.setMinimumWidth(140)
        
        self.sp_order_progress = QSpinBox(self.block)
        self.sp_order_progress.setRange(0, 100)
        self.sp_order_progress.setSingleStep(5)
        self.sp_order_progress.setSuffix(" %")
        self.sp_order_progress.setMinimumWidth(100)
        
        # Splitter dla pól głównych
        self.order_primary_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.order_primary_splitter.setChildrenCollapsible(False)
        self.order_primary_splitter.setHandleWidth(8)
        
        self._create_order_field_cells()
        self._setup_primary_splitter()
        
        # Adres realizacji
        layout.addWidget(self.make_section_separator(self.block))
        layout.addWidget(self.make_section_header("Adres realizacji", self.block))
        
        self.ed_order_address = QLineEdit(self.block)
        self.ed_order_address.setPlaceholderText("Adres realizacji")
        self.ed_order_address.hide()
        
        self.ed_order_site_street = QLineEdit(self.block)
        self.ed_order_site_street.setPlaceholderText("Ulica")
        self.ed_order_site_street.setMinimumWidth(220)
        
        self.ed_order_site_house_number = QLineEdit(self.block)
        self.ed_order_site_house_number.setPlaceholderText("Dom")
        self.ed_order_site_house_number.setMinimumWidth(90)
        
        self.ed_order_site_apartment_number = QLineEdit(self.block)
        self.ed_order_site_apartment_number.setPlaceholderText("Mieszkanie")
        self.ed_order_site_apartment_number.setMinimumWidth(90)
        
        self.ed_order_site_postal_code = QLineEdit(self.block)
        self.ed_order_site_postal_code.setPlaceholderText("Kod")
        self.ed_order_site_postal_code.setMinimumWidth(110)
        
        self.ed_order_site_city = QLineEdit(self.block)
        self.ed_order_site_city.setPlaceholderText("Miasto")
        self.ed_order_site_city.setMinimumWidth(160)
        
        # Splitter adresowy
        self.order_address_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.order_address_splitter.setChildrenCollapsible(False)
        self.order_address_splitter.setHandleWidth(8)
        
        self._create_address_field_cells()
        self._setup_address_splitter()
        
        # Terminy
        layout.addWidget(self.make_section_separator(self.block))
        layout.addWidget(self.make_section_header("Terminy", self.block))
        
        terminy_label = QLabel("Terminy projektu (wybor z kalendarza):", self.block)
        layout.addWidget(terminy_label)
        
        self.ed_date_wycena = self._create_date_edit()
        self.ed_date_projekt = self._create_date_edit()
        self.ed_date_probki = self._create_date_edit()
        self.ed_date_zakup_mat = self._create_date_edit()
        self.ed_date_produkcja = self._create_date_edit()
        self.ed_date_montaz = self._create_date_edit()
        self.ed_date_poprawki = self._create_date_edit()
        
        dates_grid = QHBoxLayout()
        dates_grid.setSpacing(8)
        dates_grid.addWidget(QLabel("Wycena:", self.block), 0)
        dates_grid.addWidget(self.ed_date_wycena, 0)
        dates_grid.addWidget(QLabel("Projekt:", self.block), 0)
        dates_grid.addWidget(self.ed_date_projekt, 0)
        dates_grid.addWidget(QLabel("Probki:", self.block), 0)
        dates_grid.addWidget(self.ed_date_probki, 0)
        layout.addLayout(dates_grid)
        
        dates_grid2 = QHBoxLayout()
        dates_grid2.setSpacing(8)
        dates_grid2.addWidget(QLabel("Zakup:", self.block), 0)
        dates_grid2.addWidget(self.ed_date_zakup_mat, 0)
        dates_grid2.addWidget(QLabel("Produkcja:", self.block), 0)
        dates_grid2.addWidget(self.ed_date_produkcja, 0)
        dates_grid2.addWidget(QLabel("Montaz:", self.block), 0)
        dates_grid2.addWidget(self.ed_date_montaz, 0)
        dates_grid2.addWidget(QLabel("Poprawki:", self.block), 0)
        dates_grid2.addWidget(self.ed_date_poprawki, 0)
        dates_grid2.addStretch(1)
        layout.addLayout(dates_grid2)
        
        # Notatki
        layout.addWidget(self.make_section_separator(self.block))
        layout.addWidget(self.make_section_header("Notatki", self.block))
        
        self.ed_order_notes = QTextEdit(self.block)
        self.ed_order_notes.setMaximumHeight(110)
        layout.addWidget(self.ed_order_notes)
    
    def _create_date_edit(self) -> QDateEdit:
        """Tworzy pole edycji daty."""
        date_edit = QDateEdit(self.block)
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setDate(QDate.currentDate())
        date_edit.setMinimumWidth(110)
        return date_edit
    
    def _create_order_field_cells(self) -> None:
        """Tworzy komórki pól zamówienia."""
        from src.tabs.zamowienie.tab_nowe_zamowienie import ClientFieldCell
        
        self._order_field_cells["order_id"] = ClientFieldCell("order_id", "ID", self.ed_order_id, self.block)
        self._order_field_cells["code"] = ClientFieldCell("code", "Kod", self.ed_order_code, self.block)
        self._order_field_cells["order_name"] = ClientFieldCell("order_name", "Nazwa", self.ed_order_name, self.block)
        self._order_field_cells["status"] = ClientFieldCell("status", "Status", self.cb_order_status, self.block)
        self._order_field_cells["progress"] = ClientFieldCell("progress", "Postep", self.sp_order_progress, self.block)
    
    def _create_address_field_cells(self) -> None:
        """Tworzy komórki pól adresowych."""
        from src.tabs.zamowienie.tab_nowe_zamowienie import ClientFieldCell
        
        self._order_field_cells["site_street"] = ClientFieldCell("site_street", "Ulica", self.ed_order_site_street, self.block)
        self._order_field_cells["site_house_number"] = ClientFieldCell("site_house_number", "Dom", self.ed_order_site_house_number, self.block)
        self._order_field_cells["site_apartment_number"] = ClientFieldCell("site_apartment_number", "Mieszkanie", self.ed_order_site_apartment_number, self.block)
        self._order_field_cells["site_postal_code"] = ClientFieldCell("site_postal_code", "Kod", self.ed_order_site_postal_code, self.block)
        self._order_field_cells["site_city"] = ClientFieldCell("site_city", "Miasto", self.ed_order_site_city, self.block)
    
    def _setup_primary_splitter(self) -> None:
        """Konfiguruje splitter głównych pól."""
        for key in self._order_primary_defaults:
            if key in self._order_field_cells:
                self.order_primary_splitter.addWidget(self._order_field_cells[key])
        
        # Ukryj progress
        if "progress" in self._order_field_cells:
            self._order_field_cells["progress"].hide()
        
        self.order_primary_splitter.setSizes([90, 130, 200, 140])
        
        layout = self.get_layout()
        layout.addWidget(self.order_primary_splitter)
    
    def _setup_address_splitter(self) -> None:
        """Konfiguruje splitter adresowy."""
        for key in self._order_address_defaults:
            if key in self._order_field_cells:
                self.order_address_splitter.addWidget(self._order_field_cells[key])
        
        self.order_address_splitter.setSizes([220, 90, 90, 110, 160])
        
        layout = self.get_layout()
        layout.addWidget(self.order_address_splitter)
