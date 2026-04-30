from __future__ import annotations

import traceback
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.app.app_settings import load_ui_theme_settings

# Explicit global definition to fix potential namespace shadowing issues
from PyQt6 import QtWidgets as _qw
QHeaderView = _qw.QHeaderView
QDialog = _qw.QDialog
QMessageBox = _qw.QMessageBox

from src.domain.permissions import Permission, has_permission, normalize_role
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.tabs.finanse_hub.panel_operations_finance_ready import OperationsFinanceReadyPanel
from src.tabs.baza_faktur.tab_baza_faktur import TabBazaFaktur


TABLE_TEXT_STYLE = "font-size: 12px;"


def _fmt_pln(value: float) -> str:
    """Formatuje kwote jako PLN z separatorem tysiecy."""
    val = float(value or 0.0)
    return f"{val:,.2f} zl".replace(",", " ")


def _safe_sub_tab(title: str, factory) -> QWidget:
    try:
        return factory()
    except Exception as exc:
        traceback.print_exc()
        placeholder = QLabel(
            f"[{title}]\\n\\nNie udalo sie zaladowac widoku.\\n\\n{type(exc).__name__}: {exc}"
        )
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        placeholder.setStyleSheet("color:#b91c1c; padding:24px; font-size:12px;")
        return placeholder


def _make_placeholder(title: str, description: str, next_step: str) -> QWidget:
    box = QFrame(); box.setProperty("uiCard", True)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(18, 18, 18, 18)
    lay.setSpacing(8)

    theme = load_ui_theme_settings()
    is_tech_night = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
    c_text = "#e8efff" if is_tech_night else "#0f172a"

    lab_title = QLabel(title, box)
    lab_title.setStyleSheet(f"font-size:18px; font-weight:800; color:{c_text};")
    lay.addWidget(lab_title, 0)

    lab_desc = QLabel(description, box)
    lab_desc.setWordWrap(True)
    lab_desc.setStyleSheet("color:#94a3b8; font-size:12px;")
    lay.addWidget(lab_desc, 0)

    hint = QLabel(f"Co dalej: {next_step}", box)
    hint.setWordWrap(True)
    hint.setStyleSheet(
        "QLabel{background:rgba(59, 130, 246, 0.1); border:1px solid rgba(59, 130, 246, 0.2); border-radius:10px;"
        "padding:10px 12px; color:#60a5fa; font-size:12px; font-weight:600;}"
    )
    lay.addWidget(hint, 0)
    lay.addStretch(1)
    return box


# --- KPI CARD CLASS (STOLEN FROM DASHBOARD) ---

class FinancialKpiCard(QFrame):
    def __init__(self, title: str, accent: str, icon: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = accent
        self._target = 0.0
        self._displayed = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self.setFixedHeight(110)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("uiCard", True)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Top Accent Line
        self.accent_line = QFrame(self)
        self.accent_line.setFixedHeight(3)
        self.accent_line.setStyleSheet(f"background: {accent}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        main_lay.addWidget(self.accent_line)

        content = QVBoxLayout()
        content.setContentsMargins(16, 12, 16, 12)
        content.setSpacing(4)

        top = QHBoxLayout()
        lab_title = QLabel(title.upper())
        lab_title.setStyleSheet("font-size:10px; font-weight:800; color:#64748b; letter-spacing:1.2px;")
        top.addWidget(lab_title)
        top.addStretch()
        if icon:
            lab_icon = QLabel(icon)
            lab_icon.setStyleSheet(f"font-size:16px; color:{accent}; background:{accent}15; border-radius:8px; padding:4px 6px;")
            top.addWidget(lab_icon)
        content.addLayout(top)

        self._lab_value = QLabel("0.00 zl")
        self._lab_value.setStyleSheet("font-size:24px; font-weight:900; color:#1e293b; margin-top:2px;")
        content.addWidget(self._lab_value)

        self._lab_sub = QLabel("")
        self._lab_sub.setStyleSheet("font-size:11px; font-weight:600; color:#94a3b8;")
        content.addWidget(self._lab_sub)
        
        main_lay.addLayout(content)

    def set_value(self, value: float, sub: str = "", animate: bool = True) -> None:
        self._target = value
        self._lab_sub.setText(sub)
        if not animate or abs(value - self._displayed) < 1:
            self._displayed = value
            self._lab_value.setText(_fmt_pln(value))
            return
        self._timer.start()

    def _tick(self) -> None:
        diff = self._target - self._displayed
        if abs(diff) < 0.1:
            self._displayed = self._target
            self._lab_value.setText(_fmt_pln(self._displayed))
            self._timer.stop()
            return
        self._displayed += diff * 0.2
        self._lab_value.setText(_fmt_pln(self._displayed))

# --- PAYROLL PANEL ---

class PayrollPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker_store = WorkerStoreJson()
        self._work_time_store = WorkTimeStoreJson()
        
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        
        hdr = QHBoxLayout()
        title = QLabel("WYNAGRODZENIA I CZAS PRACY")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #60a5fa;")
        hdr.addWidget(title)
        hdr.addStretch()
        self.btn_refresh = QPushButton("Odswiez")
        hdr.addWidget(self.btn_refresh)
        root.addLayout(hdr)
        
        info = QLabel("Aktualne naliczenia pracownikow na podstawie zarejestrowanego czasu pracy i stawek godzinowych.")
        info.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(info)
        
        self.tbl = QTableWidget(0, 7, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels([
            "Pracownik", "Rola", "Stawka [zl/h]", "Godziny", "Nadgodziny", "Bonusy", "KWOTA BRUTTO"
        ])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.tbl)
        
        self.btn_refresh.clicked.connect(self.refresh)
        self.refresh()
        
    def refresh(self) -> None:
        import datetime
        now = datetime.datetime.now()
        year, month = now.year, now.month
        
        workers = self._worker_store.list_workers()
        self.tbl.setRowCount(0)
        
        for w in workers:
            sheet = self._work_time_store.get_sheet(w.name, year, month)
            total_h = 0.0
            total_ot = 0.0
            total_extra = 0.0
            for e in sheet.entries:
                total_h += float(getattr(e, "hours", 0.0) or 0.0)
                total_ot += float(getattr(e, "overtime_hours", 0.0) or 0.0)
                total_extra += float(getattr(e, "extra_pay", 0.0) or 0.0)
            
            rate = float(w.hourly_rate or 0.0)
            mult = float(w.overtime_multiplier or 1.0)
            brutto = (total_h * rate) + (total_ot * rate * mult) + total_extra
            
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(w.name)))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(w.role)))
            self.tbl.setItem(row, 2, QTableWidgetItem(f"{rate:.2f}"))
            self.tbl.setItem(row, 3, QTableWidgetItem(f"{total_h:.2f}"))
            self.tbl.setItem(row, 4, QTableWidgetItem(f"{total_ot:.2f}"))
            self.tbl.setItem(row, 5, QTableWidgetItem(f"{total_extra:.2f}"))
            
            item_brutto = QTableWidgetItem(_fmt_pln(brutto))
            item_brutto.setFont(QFont("", -1, QFont.Weight.Bold))
            item_brutto.setForeground(QColor("#34d399"))
            self.tbl.setItem(row, 6, item_brutto)


# --- REPORTS PANEL ---

class ReportsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)
        
        hdr = QLabel("CENTRUM RAPORTOWE")
        hdr.setStyleSheet("font-size: 22px; font-weight: 900; color: #f8fafc;")
        root.addWidget(hdr)
        
        desc = QLabel("Wybierz rodzaj raportu i zakres dat, aby wygenerowac zestawienie analityczne.")
        desc.setStyleSheet("color:#94a3b8; font-size:13px;")
        root.addWidget(desc)
        
        # Grid of report types
        grid = QGridLayout()
        grid.setSpacing(15)
        
        reports = [
            ("Analiza Rentownosci", "Zestawienie przychodow i kosztow operacyjnych per miesiac.", "📈"),
            ("Rozliczenia Pracownikow", "Pelna historia wynagrodzen, zaliczek i premii.", "👥"),
            ("Rejestr Dokumentow VAT", "Lista faktur zakupowych z podzialem na stawki i status.", "🧾"),
            ("Zestawienie Naleznosci", "Szczegolowy raport zaleglych platnosci od klientow.", "⏳"),
        ]
        
        for i, (name, dsc, icon) in enumerate(reports):
            card = QFrame()
            card.setProperty("uiCard", True)
            card.setMinimumHeight(140)
            lay = QVBoxLayout(card)
            lay.setContentsMargins(15, 15, 15, 15)
            
            t_lay = QHBoxLayout()
            l_icon = QLabel(icon)
            l_icon.setStyleSheet("font-size: 24px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; padding: 5px;")
            t_lay.addWidget(l_icon)
            
            l_name = QLabel(name)
            l_name.setStyleSheet("font-size: 16px; font-weight: 700; color: #3b82f6;")
            t_lay.addWidget(l_name, 1)
            lay.addLayout(t_lay)
            
            l_desc = QLabel(dsc)
            l_desc.setWordWrap(True)
            l_desc.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 5px;")
            lay.addWidget(l_desc)
            
            btn = QPushButton("Generuj Raport")
            btn.setProperty("uiVariant", "secondary")
            lay.addWidget(btn)
            
            grid.addWidget(card, i // 2, i % 2)
            
        root.addLayout(grid)
        root.addStretch()



class AddPaymentDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dodaj wplate klienta")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.ed_stage = QLineEdit(self)
        self.ed_stage.setPlaceholderText("np. Zaliczka, Koncowa")
        self.sp_amount = QDoubleSpinBox(self)
        self.sp_amount.setRange(0.0, 1_000_000_000.0)
        self.sp_amount.setDecimals(2)
        self.cb_account = QComboBox(self)
        self.cb_account.addItem("🏦 Bank (Przelew / Faktura)", "bank")
        self.cb_account.addItem("💵 Gotowka (Do reki)", "cash")
        self.ed_note = QLineEdit(self)
        form.addRow("Etap platnosci", self.ed_stage)
        form.addRow("Kwota [zl]", self.sp_amount)
        form.addRow("Konto docelowe", self.cb_account)
        form.addRow("Notatka", self.ed_note)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def payload(self) -> dict[str, Any]:
        return {
            "stage": self.ed_stage.text().strip() or "Inne",
            "amount": float(self.sp_amount.value()),
            "account_type": str(self.cb_account.currentData() or "bank"),
            "note": self.ed_note.text().strip(),
            "paid": False,
        }


class SalesRevenuePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._order_store = OrderStoreJson()
        self._invoice_store = InvoiceStoreJson()
        self._order_codes: list[str] = []
        self._payment_indices: list[int] = []
        self._current_order_code = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        info = QLabel(
            "Sprzedaz / Przychody: zarzadzaj harmonogramem wplat klienta dla zamowien i kontroluj status naleznosci.",
            self,
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(info, 0)

        self._kpi = QFrame(self); self._kpi.setProperty("uiCard", True)
        kpi_lay = QHBoxLayout(self._kpi)
        kpi_lay.setContentsMargins(12, 10, 12, 10)
        self.lab_kpi_text = QLabel("Wczytywanie danych...", self._kpi)
        self.lab_kpi_text.setStyleSheet("color:#60a5fa; font-size:13px; font-weight:800;")
        kpi_lay.addWidget(self.lab_kpi_text)
        root.addWidget(self._kpi, 0)

        actions = QHBoxLayout()
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj zamowienia, klienta lub statusu...")
        self.btn_refresh = QPushButton("Odswiez", self)
        self.btn_add_payment = QPushButton("+ Dodaj wplate", self)
        self.btn_toggle_paid = QPushButton("Oznacz / cofnij oplacenie", self)
        self.btn_remove_payment = QPushButton("- Usun wplate", self)
        actions.addWidget(self.ed_search, 1)
        actions.addWidget(self.btn_refresh, 0)
        actions.addWidget(self.btn_add_payment, 0)
        actions.addWidget(self.btn_toggle_paid, 0)
        actions.addWidget(self.btn_remove_payment, 0)
        root.addLayout(actions)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.tbl_orders = QTableWidget(0, 8, self)
        self.tbl_orders.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_orders.setHorizontalHeaderLabels(
            [
                "Kod",
                "Klient",
                "Status",
                "Wplaty oplacone",
                "Naleznosc",
                "Plan",
                "Liczba etapow",
                "Pracownik",
            ]
        )
        self.tbl_orders.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_orders.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_orders.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_orders.verticalHeader().setVisible(False)
        self.tbl_orders.setAlternatingRowColors(True)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_orders.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        content.addWidget(self.tbl_orders, 3)

        right = QVBoxLayout()
        right.setSpacing(6)
        theme = load_ui_theme_settings()
        is_tech_night = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        c_text = "#e8efff" if is_tech_night else "#0f172a"

        self.lab_order = QLabel("Platnosci klienta: wybierz zamowienie z listy.", self)
        self.lab_order.setWordWrap(True)
        self.lab_order.setStyleSheet(f"font-weight:700; color:{c_text};")
        right.addWidget(self.lab_order, 0)

        self.tbl_payments = QTableWidget(0, 5, self)
        self.tbl_payments.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_payments.setHorizontalHeaderLabels(["Etap", "Kwota", "Konto", "Oplacone", "Uwagi"])
        self.tbl_payments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_payments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_payments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_payments.verticalHeader().setVisible(False)
        self.tbl_payments.setAlternatingRowColors(True)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.tbl_payments, 1)

        self.lab_invoice = QLabel("", self)
        self.lab_invoice.setWordWrap(True)
        self.lab_invoice.setStyleSheet("color:#94a3b8; font-size:12px;")
        right.addWidget(self.lab_invoice, 0)

        content.addLayout(right, 2)
        root.addLayout(content, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.ed_search.textChanged.connect(self.refresh)
        self.tbl_orders.itemSelectionChanged.connect(self._on_order_selection_changed)
        self.btn_add_payment.clicked.connect(self._on_add_payment)
        self.btn_toggle_paid.clicked.connect(self._on_toggle_paid)
        self.btn_remove_payment.clicked.connect(self._on_remove_payment)

        self.refresh()

    def _collect_order_totals(self, order) -> tuple[float, float, float, int]:
        paid = 0.0
        pending = 0.0
        total = 0.0
        count = 0
        for item in list(getattr(order, "customer_payments", []) or []):
            if not isinstance(item, dict):
                continue
            amount = float(item.get("amount", 0.0) or 0.0)
            count += 1
            total += amount
            if bool(item.get("paid", False)):
                paid += amount
            else:
                pending += amount
        return paid, pending, total, count

    def refresh(self) -> None:
        q = self.ed_search.text().strip().lower()
        rows = self._order_store.list_orders()
        self.tbl_orders.setRowCount(0)
        self._order_codes = []

        paid_sum = 0.0
        pending_sum = 0.0
        planned_sum = 0.0
        payments_count = 0

        for order in rows:
            code = str(getattr(order, "code", "") or "").strip()
            client = str(getattr(order, "client_name", "") or "").strip()
            status = str(getattr(order, "status", "") or "").strip()
            worker = str(getattr(order, "worker_name", "") or "").strip()
            hay = f"{code} {client} {status} {worker}".lower()
            if q and q not in hay:
                continue

            paid, pending, planned, count = self._collect_order_totals(order)
            paid_sum += paid
            pending_sum += pending
            planned_sum += planned
            payments_count += count

            row = self.tbl_orders.rowCount()
            self.tbl_orders.insertRow(row)
            vals = [
                code,
                client,
                status or "Nowe",
                _fmt_pln(paid),
                _fmt_pln(pending),
                _fmt_pln(planned),
                str(count),
                worker,
            ]
            for col, val in enumerate(vals):
                self.tbl_orders.setItem(row, col, QTableWidgetItem(val))
            self._order_codes.append(code)

        self.lab_kpi_text.setText(
            f"Zamowienia: {self.tbl_orders.rowCount()} | "
            f"Etapy platnosci: {payments_count} | "
            f"Oplacone: {_fmt_pln(paid_sum)} | Naleznosc: {_fmt_pln(pending_sum)} | Plan: {_fmt_pln(planned_sum)}"
        )

        invoices = self._invoice_store.list_invoices()
        pending_export = self._invoice_store.count_pending_export()
        self.lab_invoice.setText(
            f"Faktury w bazie: {len(invoices)} | Oczekuje eksportu do materialow: {pending_export}"
        )

        if self.tbl_orders.rowCount() > 0:
            self.tbl_orders.selectRow(0)
        else:
            self._current_order_code = ""
            self._refresh_payments_table(None)

    def _selected_order_code(self) -> str:
        model = self.tbl_orders.selectionModel()
        if model is None or not model.selectedRows():
            return ""
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._order_codes):
            return ""
        return str(self._order_codes[row] or "").strip()

    def _on_order_selection_changed(self) -> None:
        code = self._selected_order_code()
        self._current_order_code = code
        order = self._order_store.get(code) if code else None
        self._refresh_payments_table(order)

    def _refresh_payments_table(self, order) -> None:
        self.tbl_payments.setRowCount(0)
        self._payment_indices = []
        if order is None:
            self.lab_order.setText("Platnosci klienta: wybierz zamowienie z listy.")
            return
        code = str(getattr(order, "code", "") or "").strip()
        client = str(getattr(order, "client_name", "") or "").strip()
        self.lab_order.setText(f"Platnosci klienta: {code} / {client}")
        for idx, item in enumerate(list(getattr(order, "customer_payments", []) or [])):
            if not isinstance(item, dict):
                continue
            row = self.tbl_payments.rowCount()
            self.tbl_payments.insertRow(row)
            stage = str(item.get("stage", "") or "").strip() or "Inne"
            amount = float(item.get("amount", 0.0) or 0.0)
            account = str(item.get("account_type", "bank") or "bank").strip().lower()
            paid = "Tak" if bool(item.get("paid", False)) else "Nie"
            note = str(item.get("note", "") or "").strip()
            self.tbl_payments.setItem(row, 0, QTableWidgetItem(stage))
            self.tbl_payments.setItem(row, 1, QTableWidgetItem(_fmt_pln(amount)))
            acc_text = "🏦 Bank" if account == "bank" else "💵 Gotowka"
            self.tbl_payments.setItem(row, 2, QTableWidgetItem(acc_text))
            self.tbl_payments.setItem(row, 3, QTableWidgetItem(paid))
            self.tbl_payments.setItem(row, 4, QTableWidgetItem(note))
            self._payment_indices.append(idx)

    def _selected_payment_index(self) -> int:
        model = self.tbl_payments.selectionModel()
        if model is None or not model.selectedRows():
            return -1
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._payment_indices):
            return -1
        return int(self._payment_indices[row])

    def _load_selected_order_for_edit(self):
        code = self._current_order_code or self._selected_order_code()
        if not code:
            QMessageBox.information(self, "Sprzedaz / Przychody", "Najpierw wybierz zamowienie.")
            return None
        order = self._order_store.get(code)
        if order is None:
            QMessageBox.warning(self, "Sprzedaz / Przychody", "Nie mozna odczytac wybranego zamowienia.")
            return None
        return order

    def _save_order(self, order) -> bool:
        try:
            self._order_store.overwrite(order)
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Sprzedaz / Przychody", f"Blad zapisu: {exc}")
            return False

    def _on_add_payment(self) -> None:
        order = self._load_selected_order_for_edit()
        if order is None:
            return
        dlg = AddPaymentDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dlg.payload()
        if not hasattr(order, "customer_payments") or order.customer_payments is None:
            order.customer_payments = []
        
        plist = list(order.customer_payments)
        plist.append(payload)
        order.customer_payments = plist
        
        if self._save_order(order):
            self.refresh()
            self._refresh_payments_table(order)

    def _on_toggle_paid(self) -> None:
        order = self._load_selected_order_for_edit()
        if order is None:
            return
        idx = self._selected_payment_index()
        if idx < 0:
            QMessageBox.information(self, "Sprzedaz / Przychody", "Wybierz etap platnosci.")
            return
        payments = list(getattr(order, "customer_payments", []) or [])
        if idx >= len(payments) or not isinstance(payments[idx], dict):
            return
        current = bool(payments[idx].get("paid", False))
        payments[idx]["paid"] = not current
        order.customer_payments = payments
        if self._save_order(order):
            self.refresh()

    def _on_remove_payment(self) -> None:
        order = self._load_selected_order_for_edit()
        if order is None:
            return
        idx = self._selected_payment_index()
        if idx < 0:
            QMessageBox.information(self, "Sprzedaz / Przychody", "Wybierz etap platnosci do usuniecia.")
            return
        answer = QMessageBox.question(
            self,
            "Sprzedaz / Przychody",
            "Usunac wybrany etap platnosci?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        payments = list(getattr(order, "customer_payments", []) or [])
        if idx < len(payments):
            payments.pop(idx)
            order.customer_payments = payments
            if self._save_order(order):
                self.refresh()


class CashAndAccountsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._order_store = OrderStoreJson()
        self._expenses_store = CompanyExpensesStoreJson()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        info = QLabel(
            "Kasa i rachunki: rejestr przeplywow (wplaty klienta, naleznosci, koszty stale i zmienne) "
            "z podzialem na status i typ.",
            self,
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(info, 0)

        self._kpi = QFrame(self); self._kpi.setProperty("uiCard", True)
        kpi_lay = QHBoxLayout(self._kpi)
        kpi_lay.setContentsMargins(12, 10, 12, 10)
        self.lab_summary = QLabel("Wczytywanie...", self._kpi)
        self.lab_summary.setStyleSheet("color:#1e293b; font-size:13px; font-weight:800;")
        kpi_lay.addWidget(self.lab_summary)
        root.addWidget(self._kpi, 0)

        row = QHBoxLayout()
        self.cb_type = QComboBox(self)
        self.cb_type.addItem("Wszystkie ruchy", "all")
        self.cb_type.addItem("Przychody", "income")
        self.cb_type.addItem("Naleznosci", "receivable")
        self.cb_type.addItem("Koszty", "cost")
        self.btn_refresh = QPushButton("Odswiez", self)
        row.addWidget(QLabel("Filtr:", self), 0)
        row.addWidget(self.cb_type, 0)
        row.addStretch(1)
        row.addWidget(self.btn_refresh, 0)
        root.addLayout(row)

        self.tbl = QTableWidget(0, 7, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels(["Typ", "Konto", "Zrodlo", "Projekt / koszt", "Kwota [zl]", "Status", "Opis"])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.cb_type.currentIndexChanged.connect(self.refresh)
    def refresh(self) -> None:
        rows: list[dict[str, Any]] = []
        bank_income = 0.0
        bank_costs = 0.0
        cash_income = 0.0
        cash_costs = 0.0
        receivable = 0.0

        for order in self._order_store.list_orders():
            code = str(getattr(order, "code", "") or "").strip()
            client = str(getattr(order, "client_name", "") or "").strip()
            for item in list(getattr(order, "customer_payments", []) or []):
                if not isinstance(item, dict):
                    continue
                amount = float(item.get("amount", 0.0) or 0.0)
                stage = str(item.get("stage", "") or "").strip() or "Etap"
                account = str(item.get("account_type", "bank") or "bank").strip().lower()
                paid = bool(item.get("paid", False))
                note = str(item.get("note", "") or "").strip()

                if paid:
                    if account == "bank":
                        bank_income += amount
                    else:
                        cash_income += amount
                    
                    rows.append({
                        "flow": "income",
                        "typ": "Przychod",
                        "konto": "🏦 Bank" if account == "bank" else "💵 Gotowka",
                        "zrodlo": "Wplata klienta",
                        "projekt": f"{code} / {client}",
                        "kwota": amount,
                        "status": "Zaksiegowano",
                        "opis": stage if not note else f"{stage} | {note}",
                    })
                else:
                    receivable += amount
                    rows.append({
                        "flow": "receivable",
                        "typ": "Naleznosc",
                        "konto": "🏦 Bank" if account == "bank" else "💵 Gotowka",
                        "zrodlo": "Harmonogram",
                        "projekt": f"{code} / {client}",
                        "kwota": amount,
                        "status": "Oczekuje",
                        "opis": stage if not note else f"{stage} | {note}",
                    })

        for item in self._expenses_store.list_items("fixed", []):
            name = str(item.get("name", "") or "").strip() or "Koszt staly"
            amount = float(item.get("amount", 0.0) or 0.0)
            account = str(item.get("account_type", "bank") or "bank").strip().lower()
            if account == "bank":
                bank_costs += amount
            else:
                cash_costs += amount
                
            rows.append({
                "flow": "cost",
                "typ": "Koszt",
                "konto": "🏦 Bank" if account == "bank" else "💵 Gotowka",
                "zrodlo": "Wydatki stale",
                "projekt": "Koszt firmowy",
                "kwota": amount,
                "status": "Zaksiegowano",
                "opis": name,
            })

        for item in self._expenses_store.list_items("variable", []):
            name = str(item.get("name", "") or "").strip() or "Koszt zmienny"
            amount = float(item.get("amount", 0.0) or 0.0)
            account = str(item.get("account_type", "bank") or "bank").strip().lower()
            if account == "bank":
                bank_costs += amount
            else:
                cash_costs += amount

            rows.append({
                "flow": "cost",
                "typ": "Koszt",
                "konto": "🏦 Bank" if account == "bank" else "💵 Gotowka",
                "zrodlo": "Wydatki zmienne",
                "projekt": "Koszt firmowy",
                "kwota": amount,
                "status": "Zaksiegowano",
                "opis": name,
            })

        bank_saldo = bank_income - bank_costs
        cash_saldo = cash_income - cash_costs
        self.lab_summary.setText(
            f"🏦 RACHUNEK BANKOWY: {_fmt_pln(bank_saldo)} (In: {_fmt_pln(bank_income)} | Out: {_fmt_pln(bank_costs)})  |  "
            f"💵 KASA GOTÓWKOWA: {_fmt_pln(cash_saldo)} (In: {_fmt_pln(cash_income)} | Out: {_fmt_pln(cash_costs)})"
        )

        selected_flow = str(self.cb_type.currentData() or "all")
        self.tbl.setRowCount(0)
        for item in rows:
            flow = str(item.get("flow", "all"))
            if selected_flow != "all" and flow != selected_flow:
                continue
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(item.get("typ", ""))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(item.get("konto", ""))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(item.get("zrodlo", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(item.get("projekt", ""))))
            self.tbl.setItem(row, 4, QTableWidgetItem(_fmt_pln(float(item.get("kwota", 0.0) or 0.0))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(item.get("status", ""))))
            self.tbl.setItem(row, 6, QTableWidgetItem(str(item.get("opis", ""))))


class FinancialSummaryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._order_store = OrderStoreJson()
        self._invoice_store = InvoiceStoreJson()
        self._expenses_store = CompanyExpensesStoreJson()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # Title
        hdr = QHBoxLayout()
        title = QLabel("PODSUMOWANIE FINANSOWE")
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #3b82f6; letter-spacing: 0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()
        self.btn_refresh = QPushButton("⟳ Odswiez wszystko")
        self.btn_refresh.setProperty("uiVariant", "primary")
        self.btn_refresh.setMinimumWidth(160)
        hdr.addWidget(self.btn_refresh)
        root.addLayout(hdr)

        intro = QLabel(
            "Szybki obraz przychodow ze zlecen, kosztow operacyjnych oraz biezacego salda firmy.",
            self,
        )
        intro.setStyleSheet("color:#64748b; font-size:12px; margin-bottom: 4px;")
        root.addWidget(intro, 0)

        # KPI Cards Grid
        self._kpi_grid = QGridLayout()
        self._kpi_grid.setSpacing(12)
        
        self.card_paid = FinancialKpiCard("Oplacone klienta", "#16a34a", "💰")
        self.card_receivable = FinancialKpiCard("Naleznosci (do pobrania)", "#fbbf24", "⏳")
        self.card_planned = FinancialKpiCard("Plan laczny (zlecenia)", "#60a5fa", "📊")
        self.card_costs = FinancialKpiCard("Koszty miesieczne", "#f87171", "📉")
        self.card_saldo = FinancialKpiCard("Saldo operacyjne", "#a78bfa", "⚖️")
        self.card_vat = FinancialKpiCard("VAT z dokumentow", "#94a3b8", "🧾")

        self._kpi_grid.addWidget(self.card_paid, 0, 0)
        self._kpi_grid.addWidget(self.card_receivable, 0, 1)
        self._kpi_grid.addWidget(self.card_planned, 0, 2)
        self._kpi_grid.addWidget(self.card_costs, 1, 0)
        self._kpi_grid.addWidget(self.card_saldo, 1, 1)
        self._kpi_grid.addWidget(self.card_vat, 1, 2)
        
        root.addLayout(self._kpi_grid)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.tbl_receivables = QTableWidget(0, 5, self)
        self.tbl_receivables.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_receivables.setHorizontalHeaderLabels(
            ["Projekt", "Klient", "Naleznosc", "Plan", "Status"]
        )
        self.tbl_receivables.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_receivables.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_receivables.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_receivables.verticalHeader().setVisible(False)
        self.tbl_receivables.setAlternatingRowColors(True)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tbl_receivables.setColumnWidth(0, 140)
        self.tbl_receivables.setColumnWidth(2, 110)
        self.tbl_receivables.setColumnWidth(3, 110)
        self.tbl_receivables.setColumnWidth(4, 120)
        content.addWidget(self.tbl_receivables, 3)

        right = QVBoxLayout()
        right.setSpacing(6)
        self.tbl_costs = QTableWidget(0, 3, self)
        self.tbl_costs.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_costs.setHorizontalHeaderLabels(["Sekcja", "Kwota [zl]", "Uwagi"])
        self.tbl_costs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_costs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_costs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_costs.verticalHeader().setVisible(False)
        self.tbl_costs.setAlternatingRowColors(True)
        self.tbl_costs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_costs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_costs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_costs.setColumnWidth(0, 160)
        self.tbl_costs.setColumnWidth(1, 100)
        right.addWidget(self.tbl_costs, 1)

        self.lab_info = QLabel("", self)
        self.lab_info.setWordWrap(True)
        self.lab_info.setStyleSheet("color:#94a3b8; font-size:12px;")
        right.addWidget(self.lab_info, 0)
        content.addLayout(right, 2)

        root.addLayout(content, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        orders = self._order_store.list_orders()
        invoices = self._invoice_store.list_invoices()
        fixed_items = self._expenses_store.list_items("fixed", [])
        variable_items = self._expenses_store.list_items("variable", [])

        paid_total = 0.0
        receivable_total = 0.0
        planned_total = 0.0
        receivable_rows: list[tuple[str, str, float, float, str]] = []
        for order in orders:
            code = str(getattr(order, "code", "") or "").strip()
            client = str(getattr(order, "client_name", "") or "").strip()
            status = str(getattr(order, "status", "") or "").strip() or "Nowe"
            paid = 0.0
            receivable = 0.0
            planned = 0.0
            for payment in list(getattr(order, "customer_payments", []) or []):
                if not isinstance(payment, dict):
                    continue
                amount = float(payment.get("amount", 0.0) or 0.0)
                planned += amount
                if bool(payment.get("paid", False)):
                    paid += amount
                else:
                    receivable += amount
            paid_total += paid
            receivable_total += receivable
            planned_total += planned
            if receivable > 0.0 or planned > 0.0:
                receivable_rows.append((code, client, receivable, planned, status))

        fixed_total = sum(float(i.get("amount", 0.0) or 0.0) for i in fixed_items)
        variable_total = sum(float(i.get("amount", 0.0) or 0.0) for i in variable_items)
        costs_total = fixed_total + variable_total
        saldo_oper = paid_total - costs_total

        vat_in = sum(float(row.get("total_vat", 0.0) or 0.0) for row in invoices)
        vat_out = paid_total * 0.23 / 1.23  # Assuming 23% VAT included in gross payments
        vat_net = vat_out - vat_in

        pending_export = self._invoice_store.count_pending_export()

        self.card_paid.set_value(paid_total, sub=f"Przychod zrealizowany")
        self.card_receivable.set_value(receivable_total, sub=f"Czeka na wplate")
        self.card_planned.set_value(planned_total, sub=f"Wartosc aktywnych zlecen")
        self.card_costs.set_value(costs_total, sub=f"Stale: {_fmt_pln(fixed_total)}")
        self.card_saldo.set_value(saldo_oper, sub="Oplacone - Koszty")
        self.card_vat.set_value(vat_net, sub=f"Do zaplaty (Out:{_fmt_pln(vat_out)})")

        receivable_rows.sort(key=lambda x: x[2], reverse=True)
        self.tbl_receivables.setRowCount(0)
        for code, client, receivable, planned, status in receivable_rows[:50]:
            row = self.tbl_receivables.rowCount()
            self.tbl_receivables.insertRow(row)
            self.tbl_receivables.setItem(row, 0, QTableWidgetItem(code))
            self.tbl_receivables.setItem(row, 1, QTableWidgetItem(client))
            self.tbl_receivables.setItem(row, 2, QTableWidgetItem(_fmt_pln(receivable)))
            self.tbl_receivables.setItem(row, 3, QTableWidgetItem(_fmt_pln(planned)))
            self.tbl_receivables.setItem(row, 4, QTableWidgetItem(status))

        self.tbl_costs.setRowCount(0)
        for section, amount, note in (
            ("Wydatki stale", fixed_total, f"Pozycji: {len(fixed_items)}"),
            ("Wydatki zmienne", variable_total, f"Pozycji: {len(variable_items)}"),
            ("Koszt laczny", costs_total, "Stale + zmienne"),
            ("Saldo operacyjne", saldo_oper, "Oplacone - koszty"),
            ("Podatek VAT (est.)", vat_net, f"Nalezny: {_fmt_pln(vat_out)} | Naliczony: {_fmt_pln(vat_in)}"),
        ):
            row = self.tbl_costs.rowCount()
            self.tbl_costs.insertRow(row)
            self.tbl_costs.setItem(row, 0, QTableWidgetItem(section))
            self.tbl_costs.setItem(row, 1, QTableWidgetItem(_fmt_pln(amount)))
            self.tbl_costs.setItem(row, 2, QTableWidgetItem(note))

        self.lab_info.setText(
            f"Dokumenty zakupowe: {len(invoices)} | Oczekuje eksportu do materialow: {pending_export}"
        )


class TaxesSettlementsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._invoice_store = InvoiceStoreJson()
        self._invoice_ids: list[str] = []
        self._rows_by_id: dict[str, dict[str, Any]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        intro = QLabel(
            "Podatki i rozrachunki: tabela dokumentow z kontrola VAT oraz podgladem pozycji dokumentu.",
            self,
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(intro, 0)

        self.lab_kpi = QLabel(self)
        self.lab_kpi.setWordWrap(True)
        self.lab_kpi.setStyleSheet(
            "QLabel{background:transparent;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:8px 10px;color:#334155;font-size:12px;font-weight:700;}"
        )
        root.addWidget(self.lab_kpi, 0)

        actions = QHBoxLayout()
        self.cb_filter = QComboBox(self)
        self.cb_filter.addItem("Wszystkie", "all")
        self.cb_filter.addItem("VAT OK", "ok")
        self.cb_filter.addItem("Do weryfikacji", "review")
        self.cb_filter.addItem("Brak VAT", "no_vat")
        self.cb_filter.addItem("Brak pozycji", "no_items")
        self.btn_refresh = QPushButton("Odswiez", self)
        actions.addWidget(QLabel("Status VAT:", self), 0)
        actions.addWidget(self.cb_filter, 0)
        actions.addStretch(1)
        actions.addWidget(self.btn_refresh, 0)
        root.addLayout(actions)

        self.tbl_docs = QTableWidget(0, 9, self)
        self.tbl_docs.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_docs.setHorizontalHeaderLabels(
            [
                "ID",
                "Data",
                "Kontrahent",
                "Netto",
                "VAT",
                "Brutto",
                "Waluta",
                "Status VAT",
                "Rozrachunek",
            ]
        )
        self.tbl_docs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_docs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_docs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_docs.verticalHeader().setVisible(False)
        self.tbl_docs.setAlternatingRowColors(True)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.tbl_docs, 1)

        self.tbl_items = QTableWidget(0, 8, self)
        self.tbl_items.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_items.setHorizontalHeaderLabels(
            ["Lp", "Pozycja", "Ilosc", "Netto", "VAT %", "VAT", "Brutto", "Status"]
        )
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_items.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.tbl_items, 1)

        self.lab_info = QLabel("Wybierz dokument, aby zobaczyc pozycje i status VAT.", self)
        self.lab_info.setWordWrap(True)
        self.lab_info.setStyleSheet("color:#94a3b8; font-size:12px;")
        root.addWidget(self.lab_info, 0)

        self.btn_refresh.clicked.connect(self.refresh)
        self.cb_filter.currentIndexChanged.connect(self.refresh)
        self.tbl_docs.itemSelectionChanged.connect(self._on_doc_changed)

        self.refresh()

    def _vat_status(self, row: dict[str, Any]) -> tuple[str, str]:
        items = row.get("items", [])
        items_count = int(row.get("items_count", 0) or 0)
        total_vat = float(row.get("total_vat", 0.0) or 0.0)
        total_gross = float(row.get("total_gross", row.get("total_amount", 0.0)) or 0.0)
        needs_review = bool(row.get("needs_review", False))

        if needs_review:
            return ("Do weryfikacji", "review")
        if items_count <= 0 and not isinstance(items, list):
            return ("Brak pozycji", "no_items")
        if items_count <= 0 and isinstance(items, list) and len(items) == 0:
            return ("Brak pozycji", "no_items")
        if abs(total_vat) < 0.0001 and total_gross > 0:
            return ("Brak VAT", "no_vat")
        if total_vat > 0:
            return ("VAT OK", "ok")
        return ("Do weryfikacji", "review")

    def _settlement_status(self, row: dict[str, Any]) -> str:
        exported = bool(row.get("exported_to_material", False))
        amount_due = float(row.get("amount_due", 0.0) or 0.0)
        if exported and amount_due <= 0:
            return "Rozliczono"
        if exported:
            return "Po eksporcie"
        if amount_due > 0:
            return "Do zaplaty"
        return "W toku"

    def refresh(self) -> None:
        rows = self._invoice_store.list_invoices()
        self._invoice_ids = []
        self._rows_by_id = {}
        self.tbl_docs.setRowCount(0)
        self.tbl_items.setRowCount(0)

        total_vat = 0.0
        total_net = 0.0
        total_gross = 0.0
        review_count = 0

        wanted = str(self.cb_filter.currentData() or "all")
        for row in rows:
            invoice_id = str(row.get("invoice_id", "") or "").strip()
            supplier = str(row.get("supplier", row.get("sender", "")) or "").strip()
            inv_date = str(row.get("invoice_date", row.get("received_at", "")) or "").strip()[:10]
            net = float(row.get("total_net", 0.0) or 0.0)
            vat = float(row.get("total_vat", 0.0) or 0.0)
            gross = float(row.get("total_gross", row.get("total_amount", 0.0)) or 0.0)
            currency = str(row.get("currency", "PLN") or "PLN").strip()
            vat_label, vat_key = self._vat_status(row)
            settle = self._settlement_status(row)

            if wanted != "all" and vat_key != wanted:
                continue

            total_net += net
            total_vat += vat
            total_gross += gross
            if vat_key == "review":
                review_count += 1

            table_row = self.tbl_docs.rowCount()
            self.tbl_docs.insertRow(table_row)
            self.tbl_docs.setItem(table_row, 0, QTableWidgetItem(invoice_id[:12]))
            self.tbl_docs.setItem(table_row, 1, QTableWidgetItem(inv_date))
            self.tbl_docs.setItem(table_row, 2, QTableWidgetItem(supplier))
            self.tbl_docs.setItem(table_row, 3, QTableWidgetItem(_fmt_pln(net)))
            self.tbl_docs.setItem(table_row, 4, QTableWidgetItem(_fmt_pln(vat)))
            self.tbl_docs.setItem(table_row, 5, QTableWidgetItem(_fmt_pln(gross)))
            self.tbl_docs.setItem(table_row, 6, QTableWidgetItem(currency))
            self.tbl_docs.setItem(table_row, 7, QTableWidgetItem(vat_label))
            self.tbl_docs.setItem(table_row, 8, QTableWidgetItem(settle))

            self._invoice_ids.append(invoice_id)
            self._rows_by_id[invoice_id] = dict(row)

        self.lab_kpi.setText(
            f"Dokumenty: {self.tbl_docs.rowCount()} | Netto: {_fmt_pln(total_net)} | "
            f"VAT: {_fmt_pln(total_vat)} | Brutto: {_fmt_pln(total_gross)} | "
            f"Do weryfikacji: {review_count}"
        )
        if self.tbl_docs.rowCount() > 0:
            self.tbl_docs.selectRow(0)
        else:
            self.lab_info.setText("Brak dokumentow dla wybranego filtra VAT.")

    def _on_doc_changed(self) -> None:
        model = self.tbl_docs.selectionModel()
        if model is None or not model.selectedRows():
            return
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._invoice_ids):
            return
        invoice_id = self._invoice_ids[row]
        payload = self._rows_by_id.get(invoice_id, {})
        items = payload.get("items", [])
        if not isinstance(items, list):
            items = []

        self.tbl_items.setRowCount(0)
        if not items:
            self.lab_info.setText("Dokument nie ma pozycji - status VAT wymaga recznej kontroli.")
            return

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", item.get("description", "")) or "").strip() or "Pozycja"
            qty = float(item.get("quantity", item.get("qty", 0.0)) or 0.0)
            net = float(item.get("net_value", item.get("value_net", 0.0)) or 0.0)
            vat_rate = item.get("vat_rate", item.get("vat", ""))
            vat_value = float(item.get("vat_value", item.get("value_vat", 0.0)) or 0.0)
            gross = float(item.get("gross_value", item.get("value_gross", 0.0)) or 0.0)
            status = "OK" if vat_value > 0 or str(vat_rate).strip() in {"0", "0%", "zw"} else "Do weryfikacji"

            table_row = self.tbl_items.rowCount()
            self.tbl_items.insertRow(table_row)
            self.tbl_items.setItem(table_row, 0, QTableWidgetItem(str(idx)))
            self.tbl_items.setItem(table_row, 1, QTableWidgetItem(name))
            self.tbl_items.setItem(table_row, 2, QTableWidgetItem(f"{qty:.3f}".rstrip("0").rstrip(".")))
            self.tbl_items.setItem(table_row, 3, QTableWidgetItem(_fmt_pln(net)))
            self.tbl_items.setItem(table_row, 4, QTableWidgetItem(str(vat_rate)))
            self.tbl_items.setItem(table_row, 5, QTableWidgetItem(_fmt_pln(vat_value)))
            self.tbl_items.setItem(table_row, 6, QTableWidgetItem(_fmt_pln(gross)))
            self.tbl_items.setItem(table_row, 7, QTableWidgetItem(status))

        self.lab_info.setText(
            f"Pozycje dokumentu: {self.tbl_items.rowCount()} | "
            f"Nr: {str(payload.get('invoice_number', '') or '').strip() or '(brak numeru)'}"
        )


class TabFinanseHub(QWidget):
    """Lokalny hub finansowy bez przebudowy logiki danych."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_role = ""
        self._current_worker = ""
        self._navigate_to_operations_handler = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.lab_guide = QLabel(self)
        self.lab_guide.setWordWrap(True)
        self.lab_guide.setStyleSheet(
            "QLabel{background:transparent;border:1px solid #d7e1ef;border-radius:12px;"
            "padding:8px 12px;color:#334155;font-size:12px;font-weight:600;}"
        )
        root.addWidget(self.lab_guide, 0)

        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, 1)

        self._tab_summary = FinancialSummaryPanel(self)
        self._tabs.addTab(self._tab_summary, "Podsumowanie")

        self._tab_sales = SalesRevenuePanel(self)
        self._tabs.addTab(self._tab_sales, "Sprzedaz / Przychody")

        self._tab_ops_finance_ready = OperationsFinanceReadyPanel(
            on_navigate_to_operations=self._on_navigate_to_operations,
            parent=self,
        )
        self._tabs.addTab(self._tab_ops_finance_ready, "Do rozliczenia z OPERACJE")

        self._tab_costs = QWidget(self)
        costs_root = QVBoxLayout(self._tab_costs)
        costs_root.setContentsMargins(0, 0, 0, 0)
        costs_root.setSpacing(8)

        info_row = QHBoxLayout()
        info = QLabel(
            "Zakupy i koszty: jedna przestrzen robocza dla zakupow oraz kosztow stalych i zmiennych.",
            self._tab_costs,
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#94a3b8; font-size:12px; padding:2px 2px;")
        info_row.addWidget(info, 1)
        costs_root.addLayout(info_row)

        self._costs_sub_tabs = QTabWidget(self._tab_costs)
        self._costs_sub_tabs.setDocumentMode(True)
        self._costs_sub_tabs.addTab(
            _safe_sub_tab(
                "Zakupy",
                lambda: __import__("src.tabs.zakupy.tab_zakupy", fromlist=["TabZakupy"]).TabZakupy(),
            ),
            "Zakupy",
        )
        self._costs_sub_tabs.addTab(
            _safe_sub_tab(
                "Wydatki stale",
                lambda: __import__(
                    "src.tabs.wydatki_stale.tab_wydatki_stale", fromlist=["TabWydatkiStale"]
                ).TabWydatkiStale(),
            ),
            "Wydatki stale",
        )
        self._costs_sub_tabs.addTab(
            _safe_sub_tab(
                "Wydatki zmienne",
                lambda: __import__(
                    "src.tabs.wydatki_zmienne.tab_wydatki_zmienne", fromlist=["TabWydatkiZmienne"]
                ).TabWydatkiZmienne(),
            ),
            "Wydatki zmienne",
        )
        costs_root.addWidget(self._costs_sub_tabs, 1)
        self._tabs.addTab(self._tab_costs, "Zakupy i koszty")

        self._tab_cash = CashAndAccountsPanel(self)
        self._tabs.addTab(self._tab_cash, "Kasa i rachunki")

        self._tab_payroll = PayrollPanel(self)
        self._tabs.addTab(self._tab_payroll, "Wynagrodzenia")

        self._tab_taxes = TabBazaFaktur(self)
        self._tabs.addTab(self._tab_taxes, "Faktury i rozrachunki (Baza)")

        self._tab_reports = ReportsPanel(self)
        self._tabs.addTab(self._tab_reports, "Raporty")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._update_guide_text()

    def set_navigate_to_operations_handler(self, handler) -> None:
        self._navigate_to_operations_handler = handler

    def _on_navigate_to_operations(self, payload: dict[str, Any]) -> None:
        if callable(self._navigate_to_operations_handler):
            self._navigate_to_operations_handler(payload)
            return
        top = self.window()
        if top is not None and hasattr(top, "navigate_to_operations"):
            top.navigate_to_operations(payload)

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._current_worker = str(worker_name or "").strip()
        self._current_role = normalize_role(str(role or ""))
        if hasattr(self._tab_ops_finance_ready, "set_current_user"):
            self._tab_ops_finance_ready.set_current_user(self._current_worker, self._current_role)
        self._apply_permissions()

    def _can_view_cash(self) -> bool:
        return has_permission(self._current_role, Permission.VIEW_FINANCE_CASH)

    def _can_view_ops_finance_ready(self) -> bool:
        if not has_permission(self._current_role, Permission.VIEW_FINANCE):
            return False
        return self._current_role in {"wlasciciel", "biuro"}

    def _can_view_payroll(self) -> bool:
        return has_permission(self._current_role, Permission.VIEW_FINANCE_PAYROLL)

    def _can_view_taxes(self) -> bool:
        return has_permission(self._current_role, Permission.VIEW_FINANCE_TAXES)

    def _apply_permissions(self) -> None:
        ops_ready_idx = self._tabs.indexOf(self._tab_ops_finance_ready)
        if ops_ready_idx >= 0:
            can_ops_ready = self._can_view_ops_finance_ready()
            self._tabs.setTabVisible(ops_ready_idx, can_ops_ready)
            if not can_ops_ready and self._tabs.currentIndex() == ops_ready_idx:
                self._tabs.setCurrentIndex(0)

        cash_idx = self._tabs.indexOf(self._tab_cash)
        if cash_idx >= 0:
            can_cash = self._can_view_cash()
            self._tabs.setTabVisible(cash_idx, can_cash)
            if not can_cash and self._tabs.currentIndex() == cash_idx:
                self._tabs.setCurrentIndex(0)

        payroll_idx = self._tabs.indexOf(self._tab_payroll)
        if payroll_idx >= 0:
            can_payroll = self._can_view_payroll()
            self._tabs.setTabVisible(payroll_idx, can_payroll)
            if not can_payroll and self._tabs.currentIndex() == payroll_idx:
                self._tabs.setCurrentIndex(0)

        taxes_idx = self._tabs.indexOf(self._tab_taxes)
        if taxes_idx >= 0:
            can_taxes = self._can_view_taxes()
            self._tabs.setTabVisible(taxes_idx, can_taxes)
            if not can_taxes and self._tabs.currentIndex() == taxes_idx:
                self._tabs.setCurrentIndex(0)

    def _on_tab_changed(self, _: int) -> None:
        self._update_guide_text()

    def _update_guide_text(self) -> None:
        current = self._tabs.currentWidget()
        mapping = {
            self._tab_summary: "Podsumowanie: sprawdz aktualny stan finansow, a potem przejdz do brakujacej sekcji.",
            self._tab_sales: "Sprzedaz / Przychody: uzupelniaj etapy platnosci klienta i kontroluj naleznosci.",
            self._tab_ops_finance_ready: "Do rozliczenia z OPERACJE: sprawdz tematy terenowe gotowe na krok finansowy.",
            self._tab_costs: "Zakupy i koszty: aktualizuj koszty stale/zmienne i liste zakupow w jednym miejscu.",
            self._tab_cash: "Kasa i rachunki: kontroluj przeplywy i saldo operacyjne.",
            self._tab_payroll: "Wynagrodzenia: uzupelnij naliczenia, zaliczki i wyplaty pracownikow.",
            self._tab_taxes: "Podatki i rozrachunki: sprawdz, co wymaga decyzji i uzgodnienia.",
            self._tab_reports: "Raporty: wygeneruj przeglad finansowy po zamknieciu danych okresu.",
        }
        self.lab_guide.setText(mapping.get(current, "Finanse: wybierz sekcje i pracuj krok po kroku."))
