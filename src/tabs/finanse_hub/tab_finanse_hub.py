from __future__ import annotations

import traceback
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.domain.permissions import Permission, has_permission, normalize_role
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.tabs.finanse_hub.panel_operations_finance_ready import OperationsFinanceReadyPanel


TABLE_TEXT_STYLE = """
QTableWidget {
    color: #1f2937;
    selection-color: #0f172a;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
"""


def _fmt_pln(value: float) -> str:
    return f"{float(value or 0.0):.2f} zl"


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
    box = QFrame()
    box.setStyleSheet(
        "QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:14px;}"
    )
    lay = QVBoxLayout(box)
    lay.setContentsMargins(18, 18, 18, 18)
    lay.setSpacing(8)

    lab_title = QLabel(title, box)
    lab_title.setStyleSheet("font-size:18px; font-weight:800; color:#10233f;")
    lay.addWidget(lab_title, 0)

    lab_desc = QLabel(description, box)
    lab_desc.setWordWrap(True)
    lab_desc.setStyleSheet("color:#475569; font-size:12px;")
    lay.addWidget(lab_desc, 0)

    hint = QLabel(f"Co dalej: {next_step}", box)
    hint.setWordWrap(True)
    hint.setStyleSheet(
        "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
        "padding:8px 10px;color:#334155;font-size:12px;font-weight:600;}"
    )
    lay.addWidget(hint, 0)
    lay.addStretch(1)
    return box


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
        info.setStyleSheet("color:#475569; font-size:12px;")
        root.addWidget(info, 0)

        self._kpi = QLabel(self)
        self._kpi.setWordWrap(True)
        self._kpi.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:8px 10px;color:#334155;font-size:12px;font-weight:700;}"
        )
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
        self.lab_order = QLabel("Platnosci klienta: wybierz zamowienie z listy.", self)
        self.lab_order.setWordWrap(True)
        self.lab_order.setStyleSheet("font-weight:700; color:#1f2937;")
        right.addWidget(self.lab_order, 0)

        self.tbl_payments = QTableWidget(0, 4, self)
        self.tbl_payments.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_payments.setHorizontalHeaderLabels(["Etap", "Kwota", "Oplacone", "Uwagi"])
        self.tbl_payments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_payments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_payments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_payments.verticalHeader().setVisible(False)
        self.tbl_payments.setAlternatingRowColors(True)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_payments.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.tbl_payments, 1)

        self.lab_invoice = QLabel("", self)
        self.lab_invoice.setWordWrap(True)
        self.lab_invoice.setStyleSheet("color:#475569; font-size:12px;")
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

        self._kpi.setText(
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
            paid = "Tak" if bool(item.get("paid", False)) else "Nie"
            note = str(item.get("note", "") or "").strip()
            self.tbl_payments.setItem(row, 0, QTableWidgetItem(stage))
            self.tbl_payments.setItem(row, 1, QTableWidgetItem(_fmt_pln(amount)))
            self.tbl_payments.setItem(row, 2, QTableWidgetItem(paid))
            self.tbl_payments.setItem(row, 3, QTableWidgetItem(note))
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
        stage, ok = QInputDialog.getText(self, "Nowa wplata", "Etap platnosci:")
        if not ok:
            return
        stage = str(stage or "").strip() or "Inne"
        amount, ok = QInputDialog.getDouble(
            self, "Nowa wplata", "Kwota [zl]:", 0.0, 0.0, 1_000_000_000.0, 2
        )
        if not ok:
            return
        note, _ = QInputDialog.getText(self, "Nowa wplata", "Uwagi (opcjonalnie):")
        paid_answer = QMessageBox.question(
            self,
            "Nowa wplata",
            "Czy ta wplata jest juz oplacona?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        payments = list(getattr(order, "customer_payments", []) or [])
        payments.append(
            {
                "stage": stage,
                "amount": float(amount or 0.0),
                "paid": paid_answer == QMessageBox.StandardButton.Yes,
                "note": str(note or "").strip(),
            }
        )
        order.customer_payments = payments
        if self._save_order(order):
            self.refresh()

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
        info.setStyleSheet("color:#475569; font-size:12px;")
        root.addWidget(info, 0)

        self.lab_summary = QLabel(self)
        self.lab_summary.setWordWrap(True)
        self.lab_summary.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:8px 10px;color:#334155;font-size:12px;font-weight:700;}"
        )
        root.addWidget(self.lab_summary, 0)

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

        self.tbl = QTableWidget(0, 6, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels(["Typ", "Zrodlo", "Projekt / koszt", "Kwota [zl]", "Status", "Opis"])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.cb_type.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        rows: list[dict[str, str | float]] = []
        income = 0.0
        receivable = 0.0
        costs = 0.0

        for order in self._order_store.list_orders():
            code = str(getattr(order, "code", "") or "").strip()
            client = str(getattr(order, "client_name", "") or "").strip()
            for item in list(getattr(order, "customer_payments", []) or []):
                if not isinstance(item, dict):
                    continue
                amount = float(item.get("amount", 0.0) or 0.0)
                stage = str(item.get("stage", "") or "").strip() or "Etap"
                note = str(item.get("note", "") or "").strip()
                paid = bool(item.get("paid", False))
                if paid:
                    income += amount
                    rows.append(
                        {
                            "flow": "income",
                            "typ": "Przychod",
                            "zrodlo": "Wplata klienta",
                            "projekt": f"{code} / {client}",
                            "kwota": amount,
                            "status": "Zaksiegowano",
                            "opis": stage if not note else f"{stage} | {note}",
                        }
                    )
                else:
                    receivable += amount
                    rows.append(
                        {
                            "flow": "receivable",
                            "typ": "Naleznosc",
                            "zrodlo": "Harmonogram klienta",
                            "projekt": f"{code} / {client}",
                            "kwota": amount,
                            "status": "Oczekuje",
                            "opis": stage if not note else f"{stage} | {note}",
                        }
                    )

        for item in self._expenses_store.list_items("fixed", []):
            name = str(item.get("name", "") or "").strip() or "Koszt staly"
            amount = float(item.get("amount", 0.0) or 0.0)
            costs += amount
            rows.append(
                {
                    "flow": "cost",
                    "typ": "Koszt",
                    "zrodlo": "Wydatki stale",
                    "projekt": "Koszt firmowy",
                    "kwota": amount,
                    "status": "Plan miesieczny",
                    "opis": name,
                }
            )

        for item in self._expenses_store.list_items("variable", []):
            name = str(item.get("name", "") or "").strip() or "Koszt zmienny"
            amount = float(item.get("amount", 0.0) or 0.0)
            costs += amount
            rows.append(
                {
                    "flow": "cost",
                    "typ": "Koszt",
                    "zrodlo": "Wydatki zmienne",
                    "projekt": "Koszt firmowy",
                    "kwota": amount,
                    "status": "Do kontroli",
                    "opis": name,
                }
            )

        saldo = income - costs
        self.lab_summary.setText(
            f"Wplaty klienta: {_fmt_pln(income)} | "
            f"Naleznosci: {_fmt_pln(receivable)} | "
            f"Koszty: {_fmt_pln(costs)} | "
            f"Saldo operacyjne: {_fmt_pln(saldo)}"
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
            self.tbl.setItem(row, 1, QTableWidgetItem(str(item.get("zrodlo", ""))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(item.get("projekt", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(_fmt_pln(float(item.get("kwota", 0.0) or 0.0))))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(item.get("status", ""))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(item.get("opis", ""))))


class FinancialSummaryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._order_store = OrderStoreJson()
        self._invoice_store = InvoiceStoreJson()
        self._expenses_store = CompanyExpensesStoreJson()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        intro = QLabel(
            "Podsumowanie finansowe: szybki obraz przychodow, naleznosci, kosztow i dokumentow.",
            self,
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#475569; font-size:12px;")
        root.addWidget(intro, 0)

        self.lab_kpi = QLabel(self)
        self.lab_kpi.setWordWrap(True)
        self.lab_kpi.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:8px 10px;color:#334155;font-size:12px;font-weight:700;}"
        )
        root.addWidget(self.lab_kpi, 0)

        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("Odswiez", self)
        actions.addStretch(1)
        actions.addWidget(self.btn_refresh, 0)
        root.addLayout(actions)

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
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_receivables.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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
        self.tbl_costs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_costs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_costs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.tbl_costs, 1)

        self.lab_info = QLabel("", self)
        self.lab_info.setWordWrap(True)
        self.lab_info.setStyleSheet("color:#475569; font-size:12px;")
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

        total_vat = sum(float(row.get("total_vat", 0.0) or 0.0) for row in invoices)
        pending_export = self._invoice_store.count_pending_export()

        self.lab_kpi.setText(
            f"Oplacone: {_fmt_pln(paid_total)} | Naleznosci: {_fmt_pln(receivable_total)} | "
            f"Plan wplat: {_fmt_pln(planned_total)} | Koszty: {_fmt_pln(costs_total)} | "
            f"Saldo operacyjne: {_fmt_pln(saldo_oper)} | VAT z dokumentow: {_fmt_pln(total_vat)}"
        )

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
        intro.setStyleSheet("color:#475569; font-size:12px;")
        root.addWidget(intro, 0)

        self.lab_kpi = QLabel(self)
        self.lab_kpi.setWordWrap(True)
        self.lab_kpi.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
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
        self.lab_info.setStyleSheet("color:#475569; font-size:12px;")
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
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:12px;"
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
        info.setStyleSheet("color:#475569; font-size:12px; padding:2px 2px;")
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

        self._tab_payroll = _make_placeholder(
            "Wynagrodzenia",
            "Naliczenia, wyplaty przelewem i gotowka, zaliczki oraz saldo pracownika.",
            "Uzupelnij naliczenia i wyplaty, aby kontrolowac saldo pracownikow.",
        )
        self._tabs.addTab(self._tab_payroll, "Wynagrodzenia")

        self._tab_taxes = TaxesSettlementsPanel(self)
        self._tabs.addTab(self._tab_taxes, "Podatki i rozrachunki")

        self._tab_reports = _make_placeholder(
            "Raporty",
            "Raporty finansowe i eksporty przekrojowe. Widok przygotowany pod dalszy etap wdrozenia.",
            "Wybierz okres i zakres raportu po uzupelnieniu danych finansowych.",
        )
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
