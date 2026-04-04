"""
Quote block for the order form.

Handles quote items and material selections.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


# Typy pozycji wyceny
QUOTE_ITEM_TYPES: tuple[str, ...] = (
    "Kuchnia",
    "Szafa",
    "RTV",
    "Lazienka",
    "Garderoba",
    "Biuro",
    "Inne",
)

# Zakresy materiałów
MATERIAL_SCOPE_ITEMS: tuple[str, ...] = (
    "Korpus",
    "Front",
    "Blat",
    "Okleina",
    "Farba",
    "Uchwyt",
    "Szklo",
    "Inne",
)

# Status wyboru materiału
MATERIAL_CHOICE_STATUS_ITEMS: tuple[str, ...] = (
    "Probka pokazana",
    "Wariant",
    "Wybrane finalnie",
    "Odrzucone",
)


class QuoteBlock(OrderFormBlock):
    """Blok wyceny (pozycje + materiały)."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Wycena")
        self.block.set_expanded(False)  # Domyślnie zwinięty
    
    def build(self) -> None:
        """Buduje zawartość bloku wyceny."""
        layout = self.get_layout()
        
        # Pozycje do wyceny
        layout.addWidget(self.make_section_header("Pozycje do wyceny", self.block))
        self._build_quote_items(layout)
        
        # Separator
        layout.addWidget(self.make_section_separator(self.block))
        
        # Próbki i materiały
        layout.addWidget(self.make_section_header("Próbki i materiały", self.block))
        self._build_material_choices(layout)
    
    def _build_quote_items(self, layout: QVBoxLayout) -> None:
        """Buduje sekcję pozycji wyceny."""
        note = QLabel(
            "Tutaj rozbijasz zamowienie na szybkie pozycje handlowe, np. kuchnia, szafa, RTV albo lazienka."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        # Pola formularza
        self.ed_quote_item_name = QLineEdit(self.block)
        self.ed_quote_item_name.setPlaceholderText("Nazwa pozycji, np. Kuchnia salon")
        
        self.cb_quote_item_kind = QComboBox(self.block)
        self.cb_quote_item_kind.addItems(list(QUOTE_ITEM_TYPES))
        self.cb_quote_item_kind.setMaximumWidth(150)
        
        self.sp_quote_item_quantity = QSpinBox(self.block)
        self.sp_quote_item_quantity.setRange(1, 999)
        self.sp_quote_item_quantity.setValue(1)
        self.sp_quote_item_quantity.setPrefix("Ilosc ")
        self.sp_quote_item_quantity.setMaximumWidth(120)
        
        self.ed_quote_item_description = QLineEdit(self.block)
        self.ed_quote_item_description.setPlaceholderText(
            "Opis / uwagi do wyceny (np. front ryflowany, wyspa, lustro)."
        )
        
        self.ed_quote_item_id = QLineEdit(self.block)
        self.ed_quote_item_id.setPlaceholderText("ID pozycji")
        self.ed_quote_item_id.setMaximumWidth(100)
        
        # Przyciski
        self.btn_add_quote_item = QPushButton("Dodaj pozycje", self.block)
        self.btn_remove_quote_item = QPushButton("Usun zaznaczona", self.block)
        self.btn_quote_to_sciana = QPushButton("Otworz jako Sciana", self.block)
        self.btn_quote_to_komplet = QPushButton("Otworz jako Komplet", self.block)
        self.btn_quote_set_fragment_target = QPushButton("Ustaw jako cel fragmentu", self.block)
        
        self.make_compact_button(self.btn_add_quote_item, min_width=130, max_width=160)
        self.make_compact_button(self.btn_remove_quote_item, min_width=130, max_width=160)
        self.make_compact_button(self.btn_quote_to_sciana, min_width=150, max_width=180)
        self.make_compact_button(self.btn_quote_to_komplet, min_width=150, max_width=180)
        self.make_compact_button(self.btn_quote_set_fragment_target, min_width=180, max_width=220)
        
        # Tabela pozycji
        self.tbl_quote_items = self._create_quote_items_table()
        
        # Formularz
        entry_box, entry_layout = self.make_work_panel(
            "Nowa pozycja do wyceny",
            "Tutaj dodajesz pojedyncza pozycje do wyceny z opisem i iloscia.",
        )
        
        row1 = QHBoxLayout()
        row1.addWidget(self.ed_quote_item_name, 1)
        row1.addWidget(self.cb_quote_item_kind, 0)
        row1.addWidget(self.sp_quote_item_quantity, 0)
        row1.addWidget(self.ed_quote_item_id, 0)
        entry_layout.addLayout(row1)
        
        entry_layout.addWidget(self.ed_quote_item_description)
        
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addWidget(self.btn_add_quote_item, 0)
        btns.addWidget(self.btn_remove_quote_item, 0)
        btns.addStretch(1)
        entry_layout.addLayout(btns)
        
        layout.addWidget(entry_box)
        
        # Tabela pozycji
        history_box, history_layout = self.make_work_panel(
            "Lista pozycji do wyceny",
            "Tutaj widzisz wszystkie pozycje, ktore rozbiles z zamowienia.",
        )
        history_layout.addWidget(self.tbl_quote_items)
        
        # Przyciski akcji na tabeli
        action_btns = QHBoxLayout()
        action_btns.addWidget(self.btn_quote_to_sciana, 0)
        action_btns.addWidget(self.btn_quote_to_komplet, 0)
        action_btns.addWidget(self.btn_quote_set_fragment_target, 0)
        action_btns.addStretch(1)
        history_layout.addLayout(action_btns)
        
        layout.addWidget(history_box)
    
    def _build_material_choices(self, layout: QVBoxLayout) -> None:
        """Buduje sekcję wyborów materiałów."""
        note = QLabel(
            "Tutaj zapisujesz pokazane probki i finalne wybory klienta: korpus, front, blot, farba, uchwyt albo inny material z kolorem i kodem."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        # Pola formularza
        self.cb_material_scope = QComboBox(self.block)
        self.cb_material_scope.addItems(list(MATERIAL_SCOPE_ITEMS))
        self.cb_material_scope.setMaximumWidth(170)
        
        self.cb_material_choice_status = QComboBox(self.block)
        self.cb_material_choice_status.addItems(list(MATERIAL_CHOICE_STATUS_ITEMS))
        self.cb_material_choice_status.setMaximumWidth(180)
        
        self.ed_material_choice_material = QLineEdit(self.block)
        self.ed_material_choice_material.setPlaceholderText("Material / producent, np. Egger U702 albo lakier poliuretan")
        
        self.ed_material_choice_color = QLineEdit(self.block)
        self.ed_material_choice_color.setPlaceholderText("Kolor / dekor, np. Cashmere, dab naturalny")
        
        self.ed_material_choice_code = QLineEdit(self.block)
        self.ed_material_choice_code.setPlaceholderText("Kod, np. U702 ST9 / RAL 9016")
        
        self.ed_material_choice_notes = QLineEdit(self.block)
        self.ed_material_choice_notes.setPlaceholderText("Uwagi, np. klient wybral probke nr 2")
        
        self.ed_material_choice_date = QDateEdit(self.block)
        self.ed_material_choice_date.setCalendarPopup(True)
        self.ed_material_choice_date.setDisplayFormat("yyyy-MM-dd")
        self.ed_material_choice_date.setDate(QDate.currentDate())
        self.ed_material_choice_date.setMaximumWidth(130)
        
        # Przyciski
        self.btn_add_material_choice = QPushButton("Dodaj wpis", self.block)
        self.btn_remove_material_choice = QPushButton("Usun zaznaczony", self.block)
        self.make_compact_button(self.btn_add_material_choice, min_width=120, max_width=150)
        self.make_compact_button(self.btn_remove_material_choice, min_width=140, max_width=170)
        
        # Tabela materiałów
        self.tbl_material_choices = self._create_material_choices_table()
        
        # Formularz
        entry_box, entry_layout = self.make_work_panel(
            "Nowy wybor klienta",
            "Tutaj zapisujesz probke albo finalny wybor materialu z kolorem, kodem i uwaga.",
        )
        
        row_meta = QHBoxLayout()
        row_meta.addWidget(self.cb_material_scope, 0)
        row_meta.addWidget(self.cb_material_choice_status, 0)
        row_meta.addStretch(1)
        entry_layout.addLayout(row_meta)
        
        row_material = QHBoxLayout()
        row_material.addWidget(self.ed_material_choice_material, 1)
        row_material.addWidget(self.ed_material_choice_color, 1)
        entry_layout.addLayout(row_material)
        
        row_code = QHBoxLayout()
        row_code.addWidget(self.ed_material_choice_code, 1)
        row_code.addWidget(self.ed_material_choice_date, 0)
        row_code.addWidget(self.ed_material_choice_notes, 1)
        entry_layout.addLayout(row_code)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.btn_add_material_choice, 0)
        buttons.addWidget(self.btn_remove_material_choice, 0)
        buttons.addStretch(1)
        entry_layout.addLayout(buttons)
        
        layout.addWidget(entry_box)
        
        # Tabela historii
        history_box, history_layout = self.make_work_panel(
            "Historia probek i finalnych wyborow",
            "To jest pelna lista tego, co bylo pokazane klientowi i co zostalo wybrane.",
        )
        history_layout.addWidget(self.tbl_material_choices)
        layout.addWidget(history_box)
    
    def _create_quote_items_table(self) -> QTableWidget:
        """Tworzy tabelę pozycji wyceny."""
        tbl = QTableWidget(0, 5, self.block)
        tbl.setHorizontalHeaderLabels(["Pozycja", "Typ", "Opis", "Ilosc", "ID"])
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setAlternatingRowColors(True)
        tbl.setMinimumHeight(160)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        return tbl
    
    def _create_material_choices_table(self) -> QTableWidget:
        """Tworzy tabelę wyborów materiałów."""
        tbl = QTableWidget(0, 7, self.block)
        tbl.setHorizontalHeaderLabels(["Zakres", "Material", "Kolor", "Kod", "Status", "Data", "Uwagi"])
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setAlternatingRowColors(True)
        tbl.setMinimumHeight(170)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        return tbl
