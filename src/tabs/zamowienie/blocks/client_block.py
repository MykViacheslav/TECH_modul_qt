"""
Client block for the order form.

Handles client selection and client data fields.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_ui_string_list
from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


class ClientFieldCell(QWidget):
    """Komórka pola klienta z etykietą i edytorem."""
    
    def __init__(
        self,
        field_key: str,
        label_text: str,
        editor: QWidget,
        parent: QWidget | None = None,
        drop_handler=None,
    ) -> None:
        super().__init__(parent)
        self.field_key = field_key
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel(label_text, self)
        label.setStyleSheet("color: #6b7280; font-size: 12px;")
        label.setMinimumWidth(60)
        layout.addWidget(label)
        layout.addWidget(editor, 1)


class ClientBlock(OrderFormBlock):
    """Blok klienta w formularzu zamówienia."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Klient")
        self._client_field_cells: dict[str, QWidget] = {}
        self._client_identity_defaults = ["id", "first_name", "last_name", "phone", "email"]
        self._client_address_defaults = ["street", "house_number", "apartment_number", "postal_code", "city"]
    
    def build(self) -> None:
        """Buduje zawartość bloku klienta."""
        layout = self.get_layout()
        content_parent = self.block
        
        # ComboBox wyboru klienta
        layout.addWidget(self.make_section_header("Wybór klienta", self.block))
        
        self.cb_client_name = QComboBox(self.block)
        self.cb_client_name.setEditable(True)
        self.cb_client_name.setMinimumWidth(280)
        if self.cb_client_name.lineEdit() is not None:
            self.cb_client_name.lineEdit().setPlaceholderText("[wybierz klienta albo wpisz nowego]")
        
        self.btn_pick_client = QPushButton("Wybierz z bazy", self.block)
        self.btn_save_client = QPushButton("Dodaj do bazy", self.block)
        self.btn_open_clients_base = QPushButton("Bazy", self.block)
        self.make_compact_button(self.btn_pick_client, min_width=120, max_width=150)
        self.make_compact_button(self.btn_save_client, min_width=120, max_width=150)
        self.make_compact_button(self.btn_open_clients_base, min_width=70, max_width=90)
        
        client_picker_row = QHBoxLayout()
        client_picker_row.setSpacing(8)
        client_picker_row.addWidget(QLabel("Klient:", self.block), 0)
        client_picker_row.addWidget(self.cb_client_name, 1)
        client_picker_row.addWidget(self.btn_pick_client, 0)
        client_picker_row.addWidget(self.btn_save_client, 0)
        client_picker_row.addWidget(self.btn_open_clients_base, 0)
        client_picker_row.addStretch(1)
        layout.addLayout(client_picker_row)
        
        # Separator
        layout.addWidget(self.make_section_separator(self.block))
        
        # Dane osobowe
        layout.addWidget(self.make_section_header("Dane osobowe", self.block))
        
        self.client_identity_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.client_identity_splitter.setChildrenCollapsible(False)
        self.client_identity_splitter.setHandleWidth(8)
        
        self.ed_client_id = QLineEdit(self.block)
        self.ed_client_id.setPlaceholderText("ID")
        self.ed_client_id.setMinimumWidth(52)
        
        self.ed_client_first_name = QLineEdit(self.block)
        self.ed_client_first_name.setPlaceholderText("Imie")
        self.ed_client_first_name.setMinimumWidth(90)
        
        self.ed_client_last_name = QLineEdit(self.block)
        self.ed_client_last_name.setPlaceholderText("Nazwisko")
        self.ed_client_last_name.setMinimumWidth(110)
        
        self.ed_client_phone = QLineEdit(self.block)
        self.ed_client_phone.setPlaceholderText("Telefon")
        self.ed_client_phone.setMinimumWidth(90)
        
        self.ed_client_email = QLineEdit(self.block)
        self.ed_client_email.setPlaceholderText("E-mail")
        self.ed_client_email.setMinimumWidth(120)
        
        self._create_field_cells()
        self._setup_identity_splitter()
        
        # Adres
        self.client_address_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.client_address_splitter.setChildrenCollapsible(False)
        self.client_address_splitter.setHandleWidth(8)
        
        self.ed_client_street = QLineEdit(self.block)
        self.ed_client_street.setPlaceholderText("Ulica")
        self.ed_client_street.setMinimumWidth(100)
        
        self.ed_client_house_number = QLineEdit(self.block)
        self.ed_client_house_number.setPlaceholderText("Dom")
        self.ed_client_house_number.setMinimumWidth(50)
        
        self.ed_client_apartment_number = QLineEdit(self.block)
        self.ed_client_apartment_number.setPlaceholderText("Mieszkanie")
        self.ed_client_apartment_number.setMinimumWidth(70)
        
        self.ed_client_postal_code = QLineEdit(self.block)
        self.ed_client_postal_code.setPlaceholderText("Kod")
        self.ed_client_postal_code.setMinimumWidth(70)
        
        self.ed_client_city = QLineEdit(self.block)
        self.ed_client_city.setPlaceholderText("Miasto")
        self.ed_client_city.setMinimumWidth(90)
        
        self._create_address_field_cells()
        self._setup_address_splitter()
        
        # Notatki
        layout.addWidget(self.make_section_separator(self.block))
        layout.addWidget(self.make_section_header("Notatki", self.block))
        
        form = QFormLayout()
        self.ed_client_notes = QTextEdit(self.block)
        self.ed_client_notes.setMaximumHeight(52)
        form.addRow("Notatki", self.ed_client_notes)
        layout.addLayout(form)
        
        note = QLabel("Wybierz klienta z bazy z listy u gory albo wpisz nowego i kliknij 'Dodaj do bazy'.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
    
    def _create_field_cells(self) -> None:
        """Tworzy komórki pól danych osobowych."""
        self._client_field_cells["id"] = ClientFieldCell("id", "ID", self.ed_client_id, self.block)
        self._client_field_cells["first_name"] = ClientFieldCell("first_name", "Imie", self.ed_client_first_name, self.block)
        self._client_field_cells["last_name"] = ClientFieldCell("last_name", "Nazwisko", self.ed_client_last_name, self.block)
        self._client_field_cells["phone"] = ClientFieldCell("phone", "Telefon", self.ed_client_phone, self.block)
        self._client_field_cells["email"] = ClientFieldCell("email", "E-mail", self.ed_client_email, self.block)
    
    def _create_address_field_cells(self) -> None:
        """Tworzy komórki pól adresowych."""
        self._client_field_cells["street"] = ClientFieldCell("street", "Ulica", self.ed_client_street, self.block)
        self._client_field_cells["house_number"] = ClientFieldCell("house_number", "Dom", self.ed_client_house_number, self.block)
        self._client_field_cells["apartment_number"] = ClientFieldCell("apartment_number", "Mieszkanie", self.ed_client_apartment_number, self.block)
        self._client_field_cells["postal_code"] = ClientFieldCell("postal_code", "Kod", self.ed_client_postal_code, self.block)
        self._client_field_cells["city"] = ClientFieldCell("city", "Miasto", self.ed_client_city, self.block)
    
    def _setup_identity_splitter(self) -> None:
        """Konfiguruje splitter danych osobowych."""
        for key in self._client_identity_defaults:
            if key in self._client_field_cells:
                self.client_identity_splitter.addWidget(self._client_field_cells[key])
        
        self.client_identity_splitter.setSizes([70, 130, 170, 130, 180])
        
        layout = self.get_layout()
        layout.addWidget(self.client_identity_splitter)
    
    def _setup_address_splitter(self) -> None:
        """Konfiguruje splitter adresowy."""
        for key in self._client_address_defaults:
            if key in self._client_field_cells:
                self.client_address_splitter.addWidget(self._client_field_cells[key])
        
        self.client_address_splitter.setSizes([210, 80, 100, 100, 140])
        
        layout = self.get_layout()
        layout.addWidget(self.client_address_splitter)
