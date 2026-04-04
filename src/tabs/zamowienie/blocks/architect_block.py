"""
Architect attachments block for the order form.

Handles PDF files, screenshots, and references from architect or ImageMeter.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


class ArchitectBlock(OrderFormBlock):
    """Blok załączników od architekta."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Załączniki architekta")
        self.block.set_expanded(False)  # Domyślnie zwinięty
    
    def build(self) -> None:
        """Buduje zawartość bloku załączników."""
        layout = self.get_layout()
        
        note = QLabel("PDF-y, zrzuty i referencje od architekta lub pomiarow z ImageMeter Pro do wyceny i oferty.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        # Ścieżka pliku
        self.ed_architect_file = QLineEdit(self.block)
        self.ed_architect_file.setPlaceholderText("Sciezka do PDF albo obrazu (architekt / ImageMeter Pro)...")
        self.btn_pick_architect_file = QPushButton("Wybierz plik", self.block)
        self.btn_import_imagemeter_files = QPushButton("Import z ImageMeter", self.block)
        self.make_compact_button(self.btn_pick_architect_file, min_width=110, max_width=130)
        self.make_compact_button(self.btn_import_imagemeter_files, min_width=160, max_width=190)
        
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.ed_architect_file, 1)
        path_row.addWidget(self.btn_pick_architect_file, 0)
        path_row.addWidget(self.btn_import_imagemeter_files, 0)
        layout.addLayout(path_row)
        
        # Meta dane
        self.cb_architect_kind = QComboBox(self.block)
        self.cb_architect_kind.addItems(["PDF", "Obraz", "Referencja"])
        self.cb_architect_kind.setMaximumWidth(140)
        
        self.ed_architect_description = QLineEdit(self.block)
        self.ed_architect_description.setPlaceholderText("Opis, np. Lazienka master / widok front / wizualizacja...")
        
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        meta_row.addWidget(self.cb_architect_kind, 0)
        meta_row.addWidget(self.ed_architect_description, 1)
        layout.addLayout(meta_row)
        
        # Przyciski
        self.btn_add_architect_attachment = QPushButton("Dodaj zalacznik", self.block)
        self.btn_remove_architect_attachment = QPushButton("Usun zaznaczony", self.block)
        self.make_compact_button(self.btn_add_architect_attachment, min_width=130, max_width=160)
        self.make_compact_button(self.btn_remove_architect_attachment, min_width=130, max_width=160)
        
        add_buttons = QHBoxLayout()
        add_buttons.setSpacing(8)
        add_buttons.addWidget(self.btn_add_architect_attachment, 0)
        add_buttons.addWidget(self.btn_remove_architect_attachment, 0)
        add_buttons.addStretch(1)
        layout.addLayout(add_buttons)
        
        # Tabela załączników
        self.tbl_architect_attachments = self._create_attachments_table()
        layout.addWidget(self.tbl_architect_attachments)
        
        # Podgląd
        preview_note = QLabel(
            "Po zaznaczeniu zalacznika PDF zobaczysz miniatury stron. To bedzie baza pod pozniejsze wycinanie fragmentow do Sciana, Komplet i oferty."
        )
        preview_note.setWordWrap(True)
        preview_note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(preview_note)
        
        self.lab_architect_preview_info = QLabel("Wybierz zalacznik, aby zobaczyc podglad.")
        self.lab_architect_preview_info.setWordWrap(True)
        self.lab_architect_preview_info.setStyleSheet("color:#444444; font-weight:600;")
        layout.addWidget(self.lab_architect_preview_info)
        
        self.btn_save_architect_fragment = QPushButton("Zapisz fragment", self.block)
        self.btn_save_architect_fragment.hide()
        self.make_compact_button(self.btn_save_architect_fragment, min_width=130, max_width=160)
        layout.addWidget(self.btn_save_architect_fragment, 0)
    
    def _create_attachments_table(self) -> "QTableWidget":
        """Tworzy tabelę załączników."""
        from PyQt6.QtWidgets import QAbstractItemView, QTableWidget
        
        tbl = QTableWidget(0, 3, self.block)
        tbl.setHorizontalHeaderLabels(["Plik", "Typ", "Opis"])
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setAlternatingRowColors(True)
        tbl.setMinimumHeight(150)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        return tbl
