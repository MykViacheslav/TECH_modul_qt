"""
Finance block for the order form.

Handles customer payments and order summary.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDateEdit,
    QDoubleSpinBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.ui.theme_utils import get_muted_color

if TYPE_CHECKING:
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


# Etapy płatności
CUSTOMER_PAYMENT_STAGE_ITEMS: tuple[str, ...] = (
    "Rezerwacja terminu",
    "Start pracy / 60%",
    "Przed montazem / 30%",
    "Koniec / 10%",
    "Inne",
)


class FinanceBlock(OrderFormBlock):
    """Blok finansów (kasa klienta + podsumowanie)."""
    
    def __init__(self, parent: "TabNoweZamowienie") -> None:
        super().__init__(parent, "Finanse")
        self.block.set_expanded(False)  # Domyślnie zwinięty
    
    def build(self) -> None:
        """Buduje zawartość bloku finansów."""
        layout = self.get_layout()
        
        # Kasa klienta
        layout.addWidget(self.make_section_header("Kasa klienta", self.block))
        self._build_customer_payments(layout)
        
        # Separator
        layout.addWidget(self.make_section_separator(self.block))
        
        # Podsumowanie
        layout.addWidget(self.make_section_header("Podsumowanie", self.block))
        self._build_summary(layout)
    
    def _build_customer_payments(self, layout: QVBoxLayout) -> None:
        """Buduje sekcję płatności klienta."""
        note = QLabel(
            "Tutaj zapisujesz harmonogram wplat klienta: rezerwacja terminu, start pracy, przed montazem i rozliczenie koncowe."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        # Pola formularza
        self.cb_customer_payment_stage = QComboBox(self.block)
        self.cb_customer_payment_stage.addItems(list(CUSTOMER_PAYMENT_STAGE_ITEMS))
        self.cb_customer_payment_stage.setMaximumWidth(220)
        
        self.sp_customer_payment_amount = QDoubleSpinBox(self.block)
        self.sp_customer_payment_amount.setRange(0.0, 9_999_999.99)
        self.sp_customer_payment_amount.setDecimals(2)
        self.sp_customer_payment_amount.setSuffix(" zl")
        self.sp_customer_payment_amount.setMaximumWidth(160)
        
        self.chk_customer_payment_paid = QCheckBox("Oplacone", self.block)
        
        self.ed_customer_payment_date = QDateEdit(self.block)
        self.ed_customer_payment_date.setCalendarPopup(True)
        self.ed_customer_payment_date.setDisplayFormat("yyyy-MM-dd")
        self.ed_customer_payment_date.setDate(QDate.currentDate())
        self.ed_customer_payment_date.setMaximumWidth(130)
        
        self.ed_customer_payment_id = QLineEdit(self.block)
        self.ed_customer_payment_id.setPlaceholderText("ID platnosci")
        self.ed_customer_payment_id.setMaximumWidth(100)
        
        self.ed_customer_payment_note = QLineEdit(self.block)
        self.ed_customer_payment_note.setPlaceholderText(
            "Uwagi, np. zadatek na rezerwacje terminu / 60% po akceptacji projektu"
        )
        
        # Przyciski
        self.btn_customer_payment_prefill = QPushButton("Wstaw etapy", self.block)
        self.btn_add_customer_payment = QPushButton("Dodaj / zapisz", self.block)
        self.btn_remove_customer_payment = QPushButton("Usun zaznaczony", self.block)
        self.make_compact_button(self.btn_customer_payment_prefill, min_width=110, max_width=130)
        self.make_compact_button(self.btn_add_customer_payment, min_width=120, max_width=150)
        self.make_compact_button(self.btn_remove_customer_payment, min_width=140, max_width=170)
        
        # Tabela płatności
        self.tbl_customer_payments = QTableWidget(0, 6, self.block)
        self.tbl_customer_payments.setHorizontalHeaderLabels(["Etap", "Kwota", "Oplacone", "Data", "ID", "Uwagi"])
        self.tbl_customer_payments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_customer_payments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_customer_payments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_customer_payments.verticalHeader().setVisible(False)
        self.tbl_customer_payments.horizontalHeader().setStretchLastSection(True)
        self.tbl_customer_payments.setAlternatingRowColors(True)
        self.tbl_customer_payments.setMinimumHeight(150)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Formularz
        entry_box, entry_layout = self.make_work_panel(
            "Nowa wplata klienta",
            "Tutaj wpisujesz etap, kwote i status pojedynczej wplaty albo szybko wstawiasz standardowy podzial.",
        )
        
        row_meta = QHBoxLayout()
        row_meta.addWidget(self.cb_customer_payment_stage, 0)
        row_meta.addWidget(self.sp_customer_payment_amount, 0)
        row_meta.addWidget(self.chk_customer_payment_paid, 0)
        row_meta.addWidget(self.ed_customer_payment_date, 0)
        row_meta.addWidget(self.ed_customer_payment_id, 0)
        row_meta.addStretch(1)
        entry_layout.addLayout(row_meta)
        
        entry_layout.addWidget(self.ed_customer_payment_note)
        
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addWidget(self.btn_customer_payment_prefill, 0)
        btns.addWidget(self.btn_add_customer_payment, 0)
        btns.addWidget(self.btn_remove_customer_payment, 0)
        btns.addStretch(1)
        entry_layout.addLayout(btns)
        
        layout.addWidget(entry_box)
        
        # Tabela historii
        history_box, history_layout = self.make_work_panel(
            "Harmonogram wplat",
            "Pelna lista zaplanowanych i zrealizowanych wplat klienta.",
        )
        history_layout.addWidget(self.tbl_customer_payments)
        layout.addWidget(history_box)
        
        # Podsumowanie płatności
        self.lab_customer_cash_detail = QLabel("")
        self.lab_customer_cash_detail.setWordWrap(True)
        self.lab_customer_cash_detail.setStyleSheet(
            "color:#1f2937; background:#f8fafc; border:1px solid #dbeafe; border-radius:6px; padding:8px;"
        )
        layout.addWidget(self.lab_customer_cash_detail)
    
    def _build_summary(self, layout: QVBoxLayout) -> None:
        """Buduje sekcję podsumowania."""
        note = QLabel(
            "Szybki podglad calego zamowienia: sciany, komplety, koszt laczny i materialy."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{get_muted_color()};")
        layout.addWidget(note)
        
        self.lab_summary = QLabel("")
        self.lab_summary.setWordWrap(True)
        self.lab_summary.setStyleSheet("color:#444444; background:#fafafa; border:1px solid #e9e9e9; border-radius:6px; padding:8px;")
        layout.addWidget(self.lab_summary)
        
        self.lab_cost_summary = QLabel("")
        self.lab_cost_summary.setWordWrap(True)
        self.lab_cost_summary.setStyleSheet("color:#1f1f1f; font-weight:600; background:#f7fbff; border:1px solid #dbeafe; border-radius:6px; padding:8px;")
        layout.addWidget(self.lab_cost_summary)
        
        self.lab_offer_summary = QLabel("")
        self.lab_offer_summary.setWordWrap(True)
        self.lab_offer_summary.setStyleSheet("color:#444444; background:#fefce8; border:1px solid #fde68a; border-radius:6px; padding:8px;")
        layout.addWidget(self.lab_offer_summary)
