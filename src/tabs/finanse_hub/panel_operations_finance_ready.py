from __future__ import annotations

import html
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor

from src.core.finance_operations_daily_report import build_daily_report, build_daily_summary_text
from src.core.finance_operations_followup_store import (
    NEXT_ACTION_TYPE_VALUES,
    OFFICE_STATUS_VALUES,
    FinanceOperationsFollowupStore,
)
from src.core.operations_finance_adapter import get_finance_kpis, list_operations_ready_for_finance


def _fmt_pln(value: float) -> str:
    return f"{float(value or 0.0):.2f} zl"


def _bool_pl(value: bool) -> str:
    return "Tak" if bool(value) else "Nie"


def _prio_pl(priority: str) -> str:
    mapping = {
        "krytyczny": "Krytyczny",
        "wysoki": "Wysoki",
        "normalny": "Normalny",
        "niski": "Niski",
    }
    p = str(priority or "normalny").strip().lower()
    return mapping.get(p, p.capitalize() if p else "Normalny")


def _next_action_pl(action_type: str) -> str:
    key = str(action_type or "brak").strip().lower()
    return NEXT_ACTION_TYPE_VALUES.get(key, key.capitalize() if key else "Brak")


class MarkInvoicedDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Oznacz jako zafakturowane")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.ed_invoice_number = QLineEdit(self)
        self.ed_invoice_date = QLineEdit(self)
        self.ed_invoice_date.setPlaceholderText("YYYY-MM-DD")
        self.ed_linked_invoice_id = QLineEdit(self)
        self.ed_linked_invoice_source = QLineEdit(self)
        self.ed_linked_invoice_source.setText("manual")
        self.ed_note = QTextEdit(self)
        self.ed_note.setMaximumHeight(80)
        form.addRow("Numer faktury", self.ed_invoice_number)
        form.addRow("Data faktury", self.ed_invoice_date)
        form.addRow("Powiazany dokument ID", self.ed_linked_invoice_id)
        form.addRow("Zrodlo", self.ed_linked_invoice_source)
        form.addRow("Notatka", self.ed_note)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def payload(self) -> dict[str, str]:
        return {
            "invoice_number": self.ed_invoice_number.text().strip(),
            "invoice_date": self.ed_invoice_date.text().strip(),
            "linked_invoice_id": self.ed_linked_invoice_id.text().strip(),
            "linked_invoice_source": self.ed_linked_invoice_source.text().strip() or "manual",
            "note": self.ed_note.toPlainText().strip(),
        }


class MarkPaidDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Oznacz jako oplacone")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.sp_paid_amount = QDoubleSpinBox(self)
        self.sp_paid_amount.setRange(0.0, 1_000_000_000.0)
        self.sp_paid_amount.setDecimals(2)
        self.ed_payment_date = QLineEdit(self)
        self.ed_payment_date.setPlaceholderText("YYYY-MM-DD")
        self.cb_payment_method = QComboBox(self)
        for val in ["przelew", "gotowka", "karta", "inne"]:
            self.cb_payment_method.addItem(val, val)
        self.ed_note = QTextEdit(self)
        self.ed_note.setMaximumHeight(80)
        form.addRow("Kwota zaplacona", self.sp_paid_amount)
        form.addRow("Data platnosci", self.ed_payment_date)
        form.addRow("Sposob platnosci", self.cb_payment_method)
        form.addRow("Notatka", self.ed_note)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def payload(self) -> dict[str, Any]:
        return {
            "paid_amount": float(self.sp_paid_amount.value() or 0.0),
            "payment_date": self.ed_payment_date.text().strip(),
            "payment_method": str(self.cb_payment_method.currentData() or "inne"),
            "note": self.ed_note.toPlainText().strip(),
        }


class NextActionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustaw nastepna akcje")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_action_type = QComboBox(self)
        for key, label in NEXT_ACTION_TYPE_VALUES.items():
            self.cb_action_type.addItem(label, key)
        self.ed_action_date = QLineEdit(self)
        self.ed_action_date.setPlaceholderText("YYYY-MM-DD")
        self.ed_action_note = QTextEdit(self)
        self.ed_action_note.setMaximumHeight(80)
        self.chk_needs_contact = QCheckBox("Wymaga kontaktu", self)
        self.chk_needs_check = QCheckBox("Wymaga sprawdzenia", self)
        form.addRow("Typ akcji", self.cb_action_type)
        form.addRow("Termin", self.ed_action_date)
        form.addRow("Notatka", self.ed_action_note)
        form.addRow("", self.chk_needs_contact)
        form.addRow("", self.chk_needs_check)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def payload(self) -> dict[str, Any]:
        return {
            "next_action_type": str(self.cb_action_type.currentData() or "brak"),
            "next_action_date": self.ed_action_date.text().strip(),
            "next_action_note": self.ed_action_note.toPlainText().strip(),
            "needs_contact": self.chk_needs_contact.isChecked(),
            "needs_check": self.chk_needs_check.isChecked(),
        }


class SnoozeRecordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Odloz temat")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.ed_snoozed_until = QLineEdit(self)
        self.ed_snoozed_until.setPlaceholderText("YYYY-MM-DD")
        self.ed_note = QTextEdit(self)
        self.ed_note.setMaximumHeight(80)
        form.addRow("Odlozyc do", self.ed_snoozed_until)
        form.addRow("Notatka", self.ed_note)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def payload(self) -> dict[str, str]:
        return {
            "snoozed_until": self.ed_snoozed_until.text().strip(),
            "note": self.ed_note.toPlainText().strip(),
        }


class DailyReportPreviewDialog(QDialog):
    def __init__(self, html_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Podglad raportu dnia")
        root = QVBoxLayout(self)
        self.viewer = QTextEdit(self)
        self.viewer.setReadOnly(True)
        self.viewer.setHtml(html_text)
        root.addWidget(self.viewer)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        root.addWidget(btns)


class OperationsFinanceReadyPanel(QWidget):
    def __init__(
        self,
        adapter: Callable[[], list[dict]] | None = None,
        followup_store: FinanceOperationsFollowupStore | None = None,
        on_navigate_to_operations: Callable[[dict[str, Any]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter or list_operations_ready_for_finance
        self._followup_store = followup_store or FinanceOperationsFollowupStore()
        self._on_navigate_to_operations = on_navigate_to_operations
        self._rows_all: list[dict[str, Any]] = []
        self._rows_visible: list[dict[str, Any]] = []
        self._agenda_buckets: dict[str, list[dict[str, Any]]] = {}
        self._agenda_rows: dict[str, list[dict[str, Any]]] = {}
        self._daily_report: dict[str, Any] = {}
        self._agenda_tab_keys = ["today", "tomorrow", "overdue", "snoozed"]
        self._current_worker = ""
        self._history_store = self._followup_store.history_store
        self._build_ui()
        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._current_worker = str(worker_name or "").strip()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self._kpi_widgets: dict[str, QLabel] = {}
        kpi_wrap = QFrame(self); kpi_wrap.setProperty("uiCard", True)
        kpi_l = QGridLayout(kpi_wrap)
        kpi_l.setSpacing(8)
        kpi_l.setContentsMargins(8, 8, 8, 8)
        
        labels = [
            ("ready", "Gotowe", "#60a5fa"),
            ("settlement", "Rozliczenia", "#fbbf24"),
            ("confirm", "Potwierdzenia", "#a78bfa"),
            ("blocking", "Blokujace", "#f87171"),
            ("amount", "Suma PLN", "#34d399"),
            ("office_new", "Nowe", "#60a5fa"),
            ("office_sent", "Przekaz.", "#60a5fa"),
            ("office_invoiced", "Zafakt.", "#60a5fa"),
            ("office_paid", "Oplac.", "#60a5fa"),
            ("office_settled", "Rozlicz.", "#60a5fa"),
            ("office_closed", "Biur. Zamk.", "#60a5fa"),
            ("office_fin_closed", "Fin. Zamk.", "#60a5fa"),
            ("office_stale", "Zalegle", "#f87171"),
            ("office_high_prio", "Wys. Prio", "#f87171"),
            ("office_no_move_3d", "Stagnacja", "#f87171"),
            ("office_today", "Do reakcji", "#fbbf24"),
            ("action_due_today", "Na dzis", "#fbbf24"),
            ("action_tomorrow", "Jutro", "#fbbf24"),
            ("action_overdue", "Po term.", "#f87171"),
            ("action_snoozed", "Odl.", "#94a3b8"),
        ]
        
        for i, (k, t, color) in enumerate(labels):
            card = QFrame(kpi_wrap)
            card.setStyleSheet(f"QFrame {{ background: rgba(15, 23, 42, 0.4); border: 1px solid {color}33; border-radius: 8px; padding: 4px; }}")
            cl = QVBoxLayout(card)
            cl.setSpacing(2)
            title_lab = QLabel(t.upper(), card)
            title_lab.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; border: none; background:transparent;")
            cl.addWidget(title_lab)
            v = QLabel("0", card)
            v.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: 800; border: none; background:transparent;")
            cl.addWidget(v)
            self._kpi_widgets[k] = v
            kpi_l.addWidget(card, i // 4, i % 4)
        root.addWidget(kpi_wrap)

        fil = QHBoxLayout()
        self.view_mode = QComboBox(self)
        self.view_mode.addItem("Widok: Kolejka", "queue")
        self.view_mode.addItem("Widok: Agenda", "agenda")
        self.f_text = QLineEdit(self)
        self.f_project = QLineEdit(self)
        self.f_client = QLineEdit(self)
        self.f_office_status = QComboBox(self)
        self.f_office_status.addItem("Status biurowy: Wszystkie", "all")
        for key, label in OFFICE_STATUS_VALUES.items():
            self.f_office_status.addItem(f"Status biurowy: {label}", key)
        self.f_ready = QCheckBox("Tylko gotowe do fakturowania", self)
        self.f_settlement = QCheckBox("Tylko wymagajace rozliczenia", self)
        self.f_confirm = QCheckBox("Tylko czekajace na potwierdzenie", self)
        self.f_blocking = QCheckBox("Tylko odblokowujace platnosc", self)
        self.f_new_only = QCheckBox("Tylko nowe", self)
        self.f_stale_only = QCheckBox("Tylko zalegle", self)
        self.f_attention_today = QCheckBox("Tylko do reakcji dzis", self)
        self.f_priority = QComboBox(self)
        self.f_priority.addItem("Priorytet: Wszystkie", "all")
        self.f_priority.addItem("Priorytet: Krytyczny", "krytyczny")
        self.f_priority.addItem("Priorytet: Wysoki", "wysoki")
        self.f_priority.addItem("Priorytet: Normalny", "normalny")
        self.f_priority.addItem("Priorytet: Niski", "niski")
        self.f_action_type = QComboBox(self)
        self.f_action_type.addItem("Typ akcji: Wszystkie", "all")
        for key, label in NEXT_ACTION_TYPE_VALUES.items():
            self.f_action_type.addItem(f"Typ akcji: {label}", key)
        self.f_action_due_today = QCheckBox("Tylko akcja na dzis", self)
        self.f_action_overdue = QCheckBox("Tylko po terminie akcji", self)
        self.f_snoozed_only = QCheckBox("Tylko odlozone", self)
        self.f_needs_contact = QCheckBox("Tylko wymagajace kontaktu", self)
        self.f_needs_check = QCheckBox("Tylko wymagajace sprawdzenia", self)
        self.btn_refresh = QPushButton("Odswiez", self)
        for w in [
            self.view_mode,
            self.f_text,
            self.f_project,
            self.f_client,
            self.f_office_status,
            self.f_priority,
            self.f_action_type,
            self.f_ready,
            self.f_settlement,
            self.f_confirm,
            self.f_blocking,
            self.f_new_only,
            self.f_stale_only,
            self.f_attention_today,
            self.f_action_due_today,
            self.f_action_overdue,
            self.f_snoozed_only,
            self.f_needs_contact,
            self.f_needs_check,
            self.btn_refresh,
        ]:
            fil.addWidget(w)
        root.addLayout(fil)
        self.view_mode.currentIndexChanged.connect(self._on_view_mode_changed)
        self.f_text.textChanged.connect(self.refresh_data)
        self.f_project.textChanged.connect(self.refresh_data)
        self.f_client.textChanged.connect(self.refresh_data)
        self.f_office_status.currentIndexChanged.connect(self.refresh_data)
        self.f_priority.currentIndexChanged.connect(self.refresh_data)
        self.f_action_type.currentIndexChanged.connect(self.refresh_data)
        self.f_ready.stateChanged.connect(self.refresh_data)
        self.f_settlement.stateChanged.connect(self.refresh_data)
        self.f_confirm.stateChanged.connect(self.refresh_data)
        self.f_blocking.stateChanged.connect(self.refresh_data)
        self.f_new_only.stateChanged.connect(self.refresh_data)
        self.f_stale_only.stateChanged.connect(self.refresh_data)
        self.f_attention_today.stateChanged.connect(self.refresh_data)
        self.f_action_due_today.stateChanged.connect(self.refresh_data)
        self.f_action_overdue.stateChanged.connect(self.refresh_data)
        self.f_snoozed_only.stateChanged.connect(self.refresh_data)
        self.f_needs_contact.stateChanged.connect(self.refresh_data)
        self.f_needs_check.stateChanged.connect(self.refresh_data)
        self.btn_refresh.clicked.connect(self.refresh_data)

        report_frame = QFrame(self); report_frame.setProperty("uiCard", True)
        report_layout = QVBoxLayout(report_frame)
        report_top = QHBoxLayout()
        self.btn_report_refresh = QPushButton("Odswiez raport", self)
        self.btn_report_export_csv = QPushButton("Eksport CSV", self)
        self.btn_report_export_html = QPushButton("Eksport HTML", self)
        self.btn_report_preview = QPushButton("Otworz podglad", self)
        self.btn_report_copy = QPushButton("Kopiuj podsumowanie", self)
        for w in [
            self.btn_report_refresh,
            self.btn_report_export_csv,
            self.btn_report_export_html,
            self.btn_report_preview,
            self.btn_report_copy,
        ]:
            report_top.addWidget(w)
        report_layout.addLayout(report_top)
        self.txt_daily_summary = QTextEdit(self)
        self.txt_daily_summary.setReadOnly(True)
        self.txt_daily_summary.setMaximumHeight(120)
        report_layout.addWidget(self.txt_daily_summary)
        self.tbl_daily_top = QTableWidget(0, 7, self)
        self.tbl_daily_top.setHorizontalHeaderLabels(
            ["Projekt", "Klient", "Priorytet", "Nastepna akcja", "Termin", "Kwota", "Notatka"]
        )
        self.tbl_daily_top.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_daily_top.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_daily_top.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_daily_top.verticalHeader().setVisible(False)
        hh_daily = self.tbl_daily_top.horizontalHeader()
        for col in range(7):
            hh_daily.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        report_layout.addWidget(self.tbl_daily_top)
        root.addWidget(report_frame)

        self.btn_report_refresh.clicked.connect(self._refresh_daily_report)
        self.btn_report_export_csv.clicked.connect(self._on_export_daily_report_csv)
        self.btn_report_export_html.clicked.connect(self._on_export_daily_report_html)
        self.btn_report_preview.clicked.connect(self._on_preview_daily_report)
        self.btn_report_copy.clicked.connect(self._on_copy_daily_summary)
        self.tbl_daily_top.itemSelectionChanged.connect(self._on_daily_report_selection_changed)

        body = QHBoxLayout()
        self.left_views = QTabWidget(self)
        queue_page = QWidget(self)
        queue_layout = QVBoxLayout(queue_page)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        self.tbl = QTableWidget(0, 23, self)
        self.tbl.setHorizontalHeaderLabels([
            "Projekt", "Klient", "Adres", "Status wizyty", "Stan po wizycie", "Odblokowuje platnosc", "Kwota",
            "Status biurowy", "Priorytet biurowy", "Do reakcji", "Nastepna akcja", "Termin akcji", "Odlozone do", "Dni bez ruchu",
            "Dokument", "Data faktury", "Status platnosci", "Kwota zaplacona", "Data platnosci",
            "Ostatnia wizyta", "Ostatni wynik", "Notatka", "Notatka biurowa",
        ])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        for col in range(23):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        queue_layout.addWidget(self.tbl)
        self.left_views.addTab(queue_page, "Kolejka")

        self.agenda_tabs = QTabWidget(self)
        self._agenda_tables: dict[str, QTableWidget] = {}
        labels = [("today", "Na dzis"), ("tomorrow", "Na jutro"), ("overdue", "Po terminie"), ("snoozed", "Odlozone")]
        for key, label in labels:
            t = self._make_agenda_table()
            self._agenda_tables[key] = t
            self._agenda_rows[key] = []
            self.agenda_tabs.addTab(t, label)
            t.itemSelectionChanged.connect(self._on_selection_changed)
        self.left_views.addTab(self.agenda_tabs, "Agenda")
        self.left_views.currentChanged.connect(self._on_left_view_changed)
        body.addWidget(self.left_views, 3)

        right = QVBoxLayout()
        self.txt_details = QTextEdit(self)
        self.txt_details.setReadOnly(True)
        right.addWidget(self.txt_details, 1)
        self.txt_history = QTextEdit(self)
        self.txt_history.setReadOnly(True)
        self.txt_history.setPlaceholderText("Historia zmian dla wybranego rekordu.")
        self.txt_history.setMinimumHeight(160)
        right.addWidget(QLabel("Historia zmian", self))
        right.addWidget(self.txt_history, 1)
        box = QFrame(self); box.setProperty("uiCard", True)
        form = QFormLayout(box)
        self.cb_office_status = QComboBox(self)
        for key, label in OFFICE_STATUS_VALUES.items():
            self.cb_office_status.addItem(label, key)
        self.lab_invoice_status = QLabel("brak", self)
        self.ed_invoice_number = QLineEdit(self)
        self.ed_invoice_date = QLineEdit(self)
        self.ed_linked_invoice_id = QLineEdit(self)
        self.ed_linked_invoice_source = QLineEdit(self)
        self.lab_payment_status = QLabel("brak", self)
        self.sp_paid_amount = QDoubleSpinBox(self)
        self.sp_paid_amount.setRange(0.0, 1_000_000_000.0)
        self.sp_paid_amount.setDecimals(2)
        self.ed_payment_date = QLineEdit(self)
        self.cb_payment_method = QComboBox(self)
        for val in ["przelew", "gotowka", "karta", "inne"]:
            self.cb_payment_method.addItem(val, val)
        self.ed_payment_note = QTextEdit(self)
        self.ed_payment_note.setMaximumHeight(60)
        self.chk_financially_closed = QCheckBox("Domkniete finansowo", self)
        self.lab_queue_priority = QLabel("-", self)
        self.lab_queue_days = QLabel("0", self)
        self.lab_queue_attention = QLabel("Nie", self)
        self.lab_queue_last = QLabel("-", self)
        self.lab_queue_reason = QLabel("-", self)
        self.lab_queue_reason.setWordWrap(True)
        self.lab_next_action_type = QLabel("-", self)
        self.lab_next_action_date = QLabel("-", self)
        self.lab_next_action_note = QLabel("-", self)
        self.lab_next_action_note.setWordWrap(True)
        self.chk_needs_contact = QCheckBox("Wymaga kontaktu", self)
        self.chk_needs_contact.setEnabled(False)
        self.chk_needs_check = QCheckBox("Wymaga sprawdzenia", self)
        self.chk_needs_check.setEnabled(False)
        self.lab_snoozed_until = QLabel("-", self)
        self.ed_office_note = QTextEdit(self)
        self.ed_office_note.setMaximumHeight(60)
        self.lab_office_updated = QLabel("-", self)
        form.addRow("Status biurowy", self.cb_office_status)
        form.addRow("Status dokumentu", self.lab_invoice_status)
        form.addRow("Numer faktury", self.ed_invoice_number)
        form.addRow("Data faktury", self.ed_invoice_date)
        form.addRow("Powiazany dokument ID", self.ed_linked_invoice_id)
        form.addRow("Zrodlo dokumentu", self.ed_linked_invoice_source)
        form.addRow("Status platnosci", self.lab_payment_status)
        form.addRow("Kwota zaplacona", self.sp_paid_amount)
        form.addRow("Data platnosci", self.ed_payment_date)
        form.addRow("Sposob platnosci", self.cb_payment_method)
        form.addRow("Notatka platnosci", self.ed_payment_note)
        form.addRow("", self.chk_financially_closed)
        form.addRow("Priorytet biurowy", self.lab_queue_priority)
        form.addRow("Dni bez ruchu", self.lab_queue_days)
        form.addRow("Do reakcji dzis", self.lab_queue_attention)
        form.addRow("Ostatnia aktywnosc", self.lab_queue_last)
        form.addRow("Powod priorytetu", self.lab_queue_reason)
        form.addRow("Typ nastepnej akcji", self.lab_next_action_type)
        form.addRow("Termin akcji", self.lab_next_action_date)
        form.addRow("Notatka akcji", self.lab_next_action_note)
        form.addRow("", self.chk_needs_contact)
        form.addRow("", self.chk_needs_check)
        form.addRow("Odlozone do", self.lab_snoozed_until)
        form.addRow("Notatka biurowa", self.ed_office_note)
        form.addRow("Ostatnia aktualizacja", self.lab_office_updated)
        right.addWidget(box, 0)
        actions = QHBoxLayout()
        self.btn_sent = QPushButton("Przekaz do fakturowania", self)
        self.btn_invoiced = QPushButton("Oznacz jako zafakturowane", self)
        self.btn_paid = QPushButton("Oznacz jako oplacone", self)
        self.btn_settled = QPushButton("Oznacz jako rozliczone", self)
        self.btn_closed = QPushButton("Zamknij biurowo", self)
        self.btn_fin_closed = QPushButton("Domknij finansowo", self)
        self.btn_save_office_note = QPushButton("Zapisz notatke", self)
        self.btn_set_next_action = QPushButton("Ustaw nastepna akcje", self)
        self.btn_snooze = QPushButton("Odloz", self)
        self.btn_clear_snooze = QPushButton("Usun odlozenie", self)
        for b in [
            self.btn_sent,
            self.btn_invoiced,
            self.btn_paid,
            self.btn_settled,
            self.btn_closed,
            self.btn_fin_closed,
            self.btn_set_next_action,
            self.btn_snooze,
            self.btn_clear_snooze,
            self.btn_save_office_note,
        ]:
            actions.addWidget(b)
        right.addLayout(actions)
        nav = QHBoxLayout()
        self.btn_copy_note = QPushButton("Kopiuj notatke", self)
        self.btn_copy_address = QPushButton("Kopiuj adres", self)
        self.btn_go_ops = QPushButton("Przejdz do OPERACJE", self)
        nav.addWidget(self.btn_copy_note)
        nav.addWidget(self.btn_copy_address)
        nav.addWidget(self.btn_go_ops)
        right.addLayout(nav)
        body.addLayout(right, 2)
        root.addLayout(body, 1)

        self.tbl.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_copy_note.clicked.connect(self._on_copy_note)
        self.btn_copy_address.clicked.connect(self._on_copy_address)
        self.btn_go_ops.clicked.connect(self._on_go_ops)
        self.btn_sent.clicked.connect(self._on_mark_sent_to_invoicing)
        self.btn_invoiced.clicked.connect(self._on_mark_invoiced)
        self.btn_paid.clicked.connect(self._on_mark_paid)
        self.btn_settled.clicked.connect(self._on_mark_settled)
        self.btn_closed.clicked.connect(self._on_mark_office_closed)
        self.btn_fin_closed.clicked.connect(self._on_mark_financially_closed)
        self.btn_set_next_action.clicked.connect(self._on_set_next_action)
        self.btn_snooze.clicked.connect(self._on_snooze_record)
        self.btn_clear_snooze.clicked.connect(self._on_clear_snooze)
        self.btn_save_office_note.clicked.connect(self._on_save_office_note)

    def _make_agenda_table(self) -> QTableWidget:
        tbl = QTableWidget(0, 9, self)
        tbl.setHorizontalHeaderLabels(
            [
                "Projekt",
                "Klient",
                "Status",
                "Priorytet",
                "Nastepna akcja",
                "Termin",
                "Kwota",
                "Dni bez ruchu",
                "Notatka",
            ]
        )
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        hh = tbl.horizontalHeader()
        for col in range(9):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        return tbl

    def _on_view_mode_changed(self) -> None:
        mode = str(self.view_mode.currentData() or "queue")
        self.left_views.setCurrentIndex(0 if mode == "queue" else 1)

    def _on_left_view_changed(self, index: int) -> None:
        mode = "queue" if int(index) == 0 else "agenda"
        i = self.view_mode.findData(mode)
        if i >= 0 and i != self.view_mode.currentIndex():
            self.view_mode.blockSignals(True)
            self.view_mode.setCurrentIndex(i)
            self.view_mode.blockSignals(False)

    def _populate_agenda(self, buckets: dict[str, list[dict]]) -> None:
        for key in self._agenda_tab_keys:
            rows = list(buckets.get(key, []) or [])
            self._agenda_rows[key] = rows
            tbl = self._agenda_tables[key]
            tbl.setRowCount(0)
            for row in rows:
                r = tbl.rowCount()
                tbl.insertRow(r)
                vals = [
                    str(row.get("project_name", "") or ""),
                    str(row.get("client_name", "") or ""),
                    OFFICE_STATUS_VALUES.get(str(row.get("office_status", "nowe")), str(row.get("office_status", "nowe"))),
                    _prio_pl(str(row.get("office_priority", "normalny") or "normalny")),
                    str(row.get("next_action_label", "") or "Brak"),
                    str(row.get("next_action_date", "") or ""),
                    _fmt_pln(float(row.get("estimated_payment_unlock", 0.0) or 0.0)),
                    str(int(row.get("days_since_last_activity", 0) or 0)),
                    str(row.get("office_note", "") or row.get("finance_followup_note", "") or ""),
                ]
                for c, val in enumerate(vals):
                    tbl.setItem(r, c, QTableWidgetItem(val))
            if tbl.rowCount() > 0:
                tbl.selectRow(0)

    def _build_daily_report(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return build_daily_report(rows=rows)

    def _refresh_daily_report(self) -> None:
        self._daily_report = self._build_daily_report(self._rows_visible)
        self._populate_daily_report(self._daily_report)

    def _populate_daily_report(self, report: dict[str, Any]) -> None:
        self.txt_daily_summary.setPlainText(build_daily_summary_text(report))
        self.tbl_daily_top.setRowCount(0)
        for row in list(report.get("top_items", []) or []):
            r = self.tbl_daily_top.rowCount()
            self.tbl_daily_top.insertRow(r)
            vals = [
                str(row.get("project_name", "") or ""),
                str(row.get("client_name", "") or ""),
                _prio_pl(str(row.get("office_priority", "normalny") or "normalny")),
                str(row.get("next_action_label", "") or "Brak"),
                str(row.get("next_action_date", "") or ""),
                _fmt_pln(float(row.get("estimated_payment_unlock", 0.0) or 0.0)),
                str(row.get("office_note", "") or row.get("finance_followup_note", "") or ""),
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if c == 2: # Priority
                    p_low = val.lower()
                    if "krytyczny" in p_low: item.setForeground(QColor("#f87171"))
                    elif "wysoki" in p_low: item.setForeground(QColor("#fbbf24"))
                self.tbl_daily_top.setItem(r, c, item)

    def _report_row_by_index(self, idx: int) -> dict | None:
        rows = list(self._daily_report.get("top_items", []) or [])
        if idx < 0 or idx >= len(rows):
            return None
        return rows[idx]

    def _on_daily_report_selection_changed(self) -> None:
        model = self.tbl_daily_top.selectionModel()
        if model is None or not model.selectedRows():
            return
        idx = int(model.selectedRows()[0].row())
        row = self._report_row_by_index(idx)
        if row is None:
            return
        point_id = str(row.get("point_id", "") or "")
        if point_id:
            self._select_row_by_point_id(point_id)
            self._show_details(row)

    def _render_report_html(self, report: dict[str, Any]) -> str:
        s = dict(report.get("summary", {}) or {})
        top_rows = list(report.get("top_items", []) or [])
        contact_rows = list(report.get("contact_items", []) or [])
        check_rows = list(report.get("check_items", []) or [])
        html_rows = []
        for row in top_rows:
            html_rows.append(
                "<tr>"
                f"<td>{html.escape(str(row.get('project_name', '') or ''))}</td>"
                f"<td>{html.escape(str(row.get('client_name', '') or ''))}</td>"
                f"<td>{html.escape(_prio_pl(str(row.get('office_priority', 'normalny') or 'normalny')))}</td>"
                f"<td>{html.escape(str(row.get('next_action_label', '') or 'Brak'))}</td>"
                f"<td>{html.escape(str(row.get('next_action_date', '') or ''))}</td>"
                f"<td>{html.escape(_fmt_pln(float(row.get('estimated_payment_unlock', 0.0) or 0.0)))}</td>"
                "</tr>"
            )
        return (
            "<html><body>"
            f"<h2>Raport dnia: {html.escape(str(report.get('report_date', '') or ''))}</h2>"
            "<h3>Podsumowanie</h3>"
            "<ul>"
            f"<li>Na dzis: {int(s.get('today_count', 0) or 0)}</li>"
            f"<li>Na jutro: {int(s.get('tomorrow_count', 0) or 0)}</li>"
            f"<li>Po terminie: {int(s.get('overdue_count', 0) or 0)}</li>"
            f"<li>Odlozone: {int(s.get('snoozed_count', 0) or 0)}</li>"
            f"<li>Wysoki priorytet: {int(s.get('high_priority_count', 0) or 0)}</li>"
            f"<li>Odblokowuje platnosc: {int(s.get('blocks_payment_count', 0) or 0)}</li>"
            f"<li>Laczna kwota aktywna: {float(s.get('active_amount_total', 0.0) or 0.0):.2f} zl</li>"
            "</ul>"
            "<h3>Top tematy</h3>"
            "<table border='1' cellspacing='0' cellpadding='4'>"
            "<tr><th>Projekt</th><th>Klient</th><th>Priorytet</th><th>Nastepna akcja</th><th>Termin</th><th>Kwota</th></tr>"
            f"{''.join(html_rows)}"
            "</table>"
            f"<p>Do kontaktu: {len(contact_rows)} | Do sprawdzenia: {len(check_rows)}</p>"
            "</body></html>"
        )

    def _export_daily_report_csv(self, path: str) -> str:
        report = self._daily_report or self._build_daily_report(self._rows_visible)
        s = dict(report.get("summary", {}) or {})
        lines = [
            "Raport dnia",
            f"Data;{report.get('report_date', '')}",
            f"Na dzis;{int(s.get('today_count', 0) or 0)}",
            f"Na jutro;{int(s.get('tomorrow_count', 0) or 0)}",
            f"Po terminie;{int(s.get('overdue_count', 0) or 0)}",
            f"Odlozone;{int(s.get('snoozed_count', 0) or 0)}",
            f"Wysoki priorytet;{int(s.get('high_priority_count', 0) or 0)}",
            f"Odblokowuje platnosc;{int(s.get('blocks_payment_count', 0) or 0)}",
            f"Gotowe do fakturowania;{int(s.get('ready_to_invoice_count', 0) or 0)}",
            f"Wymaga rozliczenia;{int(s.get('requires_settlement_count', 0) or 0)}",
            f"Czeka na potwierdzenie;{int(s.get('requires_confirmation_count', 0) or 0)}",
            f"Laczna kwota aktywna;{float(s.get('active_amount_total', 0.0) or 0.0):.2f}",
            "",
            "Projekt;Klient;Priorytet;Nastepna akcja;Termin;Kwota;Notatka",
        ]
        for row in list(report.get("top_items", []) or []):
            lines.append(
                ";".join(
                    [
                        str(row.get("project_name", "") or ""),
                        str(row.get("client_name", "") or ""),
                        _prio_pl(str(row.get("office_priority", "normalny") or "normalny")),
                        str(row.get("next_action_label", "") or "Brak"),
                        str(row.get("next_action_date", "") or ""),
                        f"{float(row.get('estimated_payment_unlock', 0.0) or 0.0):.2f}",
                        str(row.get("office_note", "") or row.get("finance_followup_note", "") or "").replace(";", ","),
                    ]
                )
            )
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def _export_daily_report_html(self, path: str) -> str:
        report = self._daily_report or self._build_daily_report(self._rows_visible)
        html_text = self._render_report_html(report)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html_text)
        return path

    def _on_export_daily_report_csv(self) -> None:
        default = f"finance_operations_daily_report_{self._daily_report.get('report_date', '') or 'today'}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Eksport raportu CSV", default, "CSV (*.csv)")
        if not path:
            return
        self._export_daily_report_csv(path)

    def _on_export_daily_report_html(self) -> None:
        default = f"finance_operations_daily_report_{self._daily_report.get('report_date', '') or 'today'}.html"
        path, _ = QFileDialog.getSaveFileName(self, "Eksport raportu HTML", default, "HTML (*.html)")
        if not path:
            return
        self._export_daily_report_html(path)

    def _on_preview_daily_report(self) -> None:
        report = self._daily_report or self._build_daily_report(self._rows_visible)
        dlg = DailyReportPreviewDialog(self._render_report_html(report), self)
        dlg.exec()

    def _on_copy_daily_summary(self) -> None:
        report = self._daily_report or self._build_daily_report(self._rows_visible)
        QApplication.clipboard().setText(build_daily_summary_text(report))

    def refresh_data(self) -> None:
        merged = self._followup_store.merge_with_operations_rows(list(self._adapter() or []))
        self._rows_all = self._followup_store.build_office_queue(merged)
        self._rows_visible = self._apply_filters(self._rows_all)
        self._agenda_buckets = self._followup_store.get_agenda_buckets(self._rows_visible)
        self._populate_table(self._rows_visible)
        self._populate_agenda(self._agenda_buckets)
        self._refresh_kpis(self._rows_visible)
        self._refresh_daily_report()
        row = self._selected_row()
        self._refresh_history(str((row or {}).get("point_id", "") or ""))

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        q = self.f_text.text().strip().lower()
        proj = self.f_project.text().strip().lower()
        client = self.f_client.text().strip().lower()
        status = str(self.f_office_status.currentData() or "all")
        priority = str(self.f_priority.currentData() or "all")
        action_type = str(self.f_action_type.currentData() or "all")
        out = []
        for row in rows:
            hay = f"{row.get('project_name','')} {row.get('client_name','')} {row.get('full_address','')} {row.get('finance_followup_note','')} {row.get('office_note','')} {row.get('invoice_number','')}".lower()
            if q and q not in hay:
                continue
            if proj and proj not in str(row.get("project_name", "")).lower():
                continue
            if client and client not in str(row.get("client_name", "")).lower():
                continue
            if status != "all" and str(row.get("office_status", "nowe")) != status:
                continue
            if priority != "all" and str(row.get("office_priority", "normalny")) != priority:
                continue
            if action_type != "all" and str(row.get("next_action_type", "brak")) != action_type:
                continue
            if self.f_ready.isChecked() and not bool(row.get("ready_to_invoice", False)):
                continue
            if self.f_settlement.isChecked() and not bool(row.get("requires_settlement", False)):
                continue
            if self.f_confirm.isChecked() and not bool(row.get("requires_confirmation", False)):
                continue
            if self.f_blocking.isChecked() and not bool(row.get("blocks_payment", False)) and float(row.get("estimated_payment_unlock", 0.0) or 0.0) <= 0:
                continue
            if self.f_new_only.isChecked() and str(row.get("office_status", "nowe")) != "nowe":
                continue
            if self.f_stale_only.isChecked() and not bool(row.get("is_stale", False)):
                continue
            if self.f_attention_today.isChecked() and not bool(row.get("needs_attention_today", False)):
                continue
            if self.f_action_due_today.isChecked() and not bool(row.get("action_due_today", False)):
                continue
            if self.f_action_overdue.isChecked() and not bool(row.get("action_overdue", False)):
                continue
            if self.f_snoozed_only.isChecked() and not bool(row.get("is_snoozed", False)):
                continue
            if self.f_needs_contact.isChecked() and not bool(row.get("needs_contact", False)):
                continue
            if self.f_needs_check.isChecked() and not bool(row.get("needs_check", False)):
                continue
            out.append(row)
        return out

    def _populate_table(self, rows: list[dict]) -> None:
        self.tbl.setRowCount(0)
        for row in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            vals = [
                str(row.get("project_name", "") or ""),
                str(row.get("client_name", "") or ""),
                str(row.get("full_address", "") or ""),
                str(row.get("visit_status", "") or ""),
                str(row.get("finance_followup_status", "") or ""),
                _bool_pl(bool(row.get("blocks_payment", False)) or float(row.get("estimated_payment_unlock", 0.0) or 0.0) > 0),
                _fmt_pln(float(row.get("estimated_payment_unlock", 0.0) or 0.0)),
                OFFICE_STATUS_VALUES.get(str(row.get("office_status", "nowe")), str(row.get("office_status", "nowe"))),
                _prio_pl(str(row.get("office_priority", "normalny") or "normalny")),
                _bool_pl(bool(row.get("needs_attention_today", False))),
                str(row.get("next_action_label", "") or "Brak"),
                str(row.get("next_action_date", "") or ""),
                str(row.get("snoozed_until", "") or ""),
                str(int(row.get("days_since_last_activity", 0) or 0)),
                str(row.get("invoice_number", "") or ""),
                str(row.get("invoice_date", "") or ""),
                str(row.get("payment_status", "brak") or "brak"),
                _fmt_pln(float(row.get("paid_amount", 0.0) or 0.0)),
                str(row.get("payment_date", "") or ""),
                str(row.get("last_visit_at", "") or ""),
                str(row.get("last_finance_result", "") or ""),
                str(row.get("finance_followup_note", "") or ""),
                str(row.get("office_note", "") or ""),
            ]
            for c, v in enumerate(vals):
                self.tbl.setItem(r, c, QTableWidgetItem(v))
        if self.tbl.rowCount() > 0:
            self.tbl.selectRow(0)
        else:
            self._show_details(None)

    def _refresh_kpis(self, rows: list[dict]) -> None:
        k = get_finance_kpis(rows=rows)
        self._kpi_widgets["ready"].setText(str(int(k["ready_to_invoice_count"])))
        self._kpi_widgets["settlement"].setText(str(int(k["requires_settlement_count"])))
        self._kpi_widgets["confirm"].setText(str(int(k["requires_confirmation_count"])))
        self._kpi_widgets["blocking"].setText(str(int(k["blocks_payment_count"])))
        self._kpi_widgets["amount"].setText(_fmt_pln(k["estimated_payment_unlock_total"]))
        mapping = {
            "office_new": "nowe",
            "office_sent": "przekazane_do_fakturowania",
            "office_invoiced": "zafakturowane",
            "office_paid": "oplacone",
            "office_settled": "rozliczone",
            "office_closed": "zamkniete_biurowo",
            "office_fin_closed": "domkniete_finansowo",
        }
        for key, status in mapping.items():
            self._kpi_widgets[key].setText(str(sum(1 for x in rows if str(x.get("office_status", "nowe")) == status)))
        self._kpi_widgets["office_stale"].setText(str(sum(1 for x in rows if bool(x.get("is_stale", False)))))
        self._kpi_widgets["office_today"].setText(str(sum(1 for x in rows if bool(x.get("needs_attention_today", False)))))
        self._kpi_widgets["office_high_prio"].setText(
            str(sum(1 for x in rows if str(x.get("office_priority", "normalny")) in {"wysoki", "krytyczny"}))
        )
        self._kpi_widgets["office_no_move_3d"].setText(
            str(sum(1 for x in rows if int(x.get("days_since_last_activity", 0) or 0) > 3))
        )
        self._kpi_widgets["action_due_today"].setText(str(len(self._agenda_buckets.get("today", []))))
        self._kpi_widgets["action_tomorrow"].setText(str(len(self._agenda_buckets.get("tomorrow", []))))
        self._kpi_widgets["action_overdue"].setText(str(len(self._agenda_buckets.get("overdue", []))))
        self._kpi_widgets["action_snoozed"].setText(str(len(self._agenda_buckets.get("snoozed", []))))

    def _selected_row(self) -> dict | None:
        if self.left_views.currentIndex() == 0:
            model = self.tbl.selectionModel()
            if model is None or not model.selectedRows():
                return None
            idx = int(model.selectedRows()[0].row())
            if idx < 0 or idx >= len(self._rows_visible):
                return None
            return self._rows_visible[idx]
        key = self._agenda_tab_keys[self.agenda_tabs.currentIndex()]
        tbl = self._agenda_tables[key]
        model = tbl.selectionModel()
        if model is None or not model.selectedRows():
            return None
        idx = int(model.selectedRows()[0].row())
        rows = self._agenda_rows.get(key, [])
        if idx < 0 or idx >= len(rows):
            return None
        return rows[idx]

    def _select_row_by_point_id(self, point_id: str) -> None:
        for i, row in enumerate(self._rows_visible):
            if str(row.get("point_id", "")) == str(point_id):
                self.tbl.selectRow(i)
                break
        for k in self._agenda_tab_keys:
            rows = self._agenda_rows.get(k, [])
            for i, row in enumerate(rows):
                if str(row.get("point_id", "")) == str(point_id):
                    self._agenda_tables[k].selectRow(i)
                    break

    def _on_selection_changed(self) -> None:
        self._show_details(self._selected_row())

    def _show_details(self, row: dict | None) -> None:
        if not row:
            self.txt_details.setPlainText("Brak danych do wyswietlenia.")
            self.txt_history.setPlainText("Brak historii.")
            self.ed_office_note.clear()
            self.ed_invoice_number.clear()
            self.ed_invoice_date.clear()
            self.ed_linked_invoice_id.clear()
            self.ed_linked_invoice_source.clear()
            self.lab_invoice_status.setText("brak")
            self.lab_payment_status.setText("brak")
            self.sp_paid_amount.setValue(0.0)
            self.ed_payment_date.clear()
            self.ed_payment_note.clear()
            self.chk_financially_closed.setChecked(False)
            self.lab_queue_priority.setText("-")
            self.lab_queue_days.setText("0")
            self.lab_queue_attention.setText("Nie")
            self.lab_queue_last.setText("-")
            self.lab_queue_reason.setText("-")
            self.lab_next_action_type.setText("-")
            self.lab_next_action_date.setText("-")
            self.lab_next_action_note.setText("-")
            self.chk_needs_contact.setChecked(False)
            self.chk_needs_check.setChecked(False)
            self.lab_snoozed_until.setText("-")
            self.lab_office_updated.setText("-")
            return
        status = str(row.get("office_status", "nowe"))
        idx = self.cb_office_status.findData(status)
        self.cb_office_status.setCurrentIndex(idx if idx >= 0 else 0)
        self.ed_office_note.setPlainText(str(row.get("office_note", "") or ""))
        self.lab_invoice_status.setText(str(row.get("invoice_status", "brak") or "brak"))
        self.ed_invoice_number.setText(str(row.get("invoice_number", "") or ""))
        self.ed_invoice_date.setText(str(row.get("invoice_date", "") or ""))
        self.ed_linked_invoice_id.setText(str(row.get("linked_invoice_id", "") or ""))
        self.ed_linked_invoice_source.setText(str(row.get("linked_invoice_source", "") or ""))
        self.lab_payment_status.setText(str(row.get("payment_status", "brak") or "brak"))
        self.sp_paid_amount.setValue(float(row.get("paid_amount", 0.0) or 0.0))
        self.ed_payment_date.setText(str(row.get("payment_date", "") or ""))
        m = self.cb_payment_method.findData(str(row.get("payment_method", "inne") or "inne"))
        self.cb_payment_method.setCurrentIndex(m if m >= 0 else 0)
        self.ed_payment_note.setPlainText(str(row.get("payment_note", "") or ""))
        self.chk_financially_closed.setChecked(bool(row.get("financially_closed", False)))
        self.lab_queue_priority.setText(_prio_pl(str(row.get("office_priority", "normalny") or "normalny")))
        self.lab_queue_days.setText(str(int(row.get("days_since_last_activity", 0) or 0)))
        self.lab_queue_attention.setText(_bool_pl(bool(row.get("needs_attention_today", False))))
        self.lab_queue_last.setText(str(row.get("last_activity_at", "") or "-"))
        self.lab_queue_reason.setText(str(row.get("office_priority_reason", "") or "-"))
        self.lab_next_action_type.setText(_next_action_pl(str(row.get("next_action_type", "brak") or "brak")))
        self.lab_next_action_date.setText(str(row.get("next_action_date", "") or "-"))
        self.lab_next_action_note.setText(str(row.get("next_action_note", "") or "-"))
        self.chk_needs_contact.setChecked(bool(row.get("needs_contact", False)))
        self.chk_needs_check.setChecked(bool(row.get("needs_check", False)))
        self.lab_snoozed_until.setText(str(row.get("snoozed_until", "") or "-"))
        self.lab_office_updated.setText(str(row.get("office_updated_at", "") or "-"))
        self.txt_details.setPlainText(
            f"Point ID: {row.get('point_id','')}\n"
            f"Projekt: {row.get('project_name','')}\n"
            f"Klient: {row.get('client_name','')}\n"
            f"Status biurowy: {OFFICE_STATUS_VALUES.get(status, status)}\n"
            f"Numer faktury: {row.get('invoice_number','')}\n"
            f"Data faktury: {row.get('invoice_date','')}\n"
            f"Status platnosci: {row.get('payment_status','brak')}\n"
            f"Kwota zaplacona: {_fmt_pln(float(row.get('paid_amount',0.0) or 0.0))}\n"
            f"Data platnosci: {row.get('payment_date','')}\n"
            f"Sposob platnosci: {row.get('payment_method','')}\n"
            f"Domkniete finansowo: {_bool_pl(bool(row.get('financially_closed',False)))}\n"
            f"Priorytet biurowy: {_prio_pl(str(row.get('office_priority','normalny')))}\n"
            f"Dni bez ruchu: {int(row.get('days_since_last_activity',0) or 0)}\n"
            f"Do reakcji dzis: {_bool_pl(bool(row.get('needs_attention_today',False)))}\n"
            f"Ostatnia aktywnosc: {row.get('last_activity_at','')}\n"
            f"Powod priorytetu: {row.get('office_priority_reason','')}\n"
            f"Nastepna akcja: {row.get('next_action_label','Brak')}\n"
            f"Termin akcji: {row.get('next_action_date','')}\n"
            f"Odlozone do: {row.get('snoozed_until','')}\n"
            f"Notatka biurowa: {row.get('office_note','')}"
        )
        self._refresh_history(str(row.get("point_id", "") or ""))

    def _refresh_history(self, point_id: str) -> None:
        pid = str(point_id or "").strip()
        if not pid:
            self._populate_history([])
            return
        rows = self._history_store.list_for_point(pid)
        self._populate_history(rows)

    def _populate_history(self, records: list[dict]) -> None:
        if not records:
            self.txt_history.setPlainText("Brak historii.")
            return
        lines = [self._format_history_entry(rec) for rec in records]
        self.txt_history.setPlainText("\n".join(lines))

    def _format_history_entry(self, record: dict) -> str:
        action_map = {
            "mark_sent_to_invoicing": "Przekazane do fakturowania",
            "mark_invoiced": "Zafakturowane",
            "mark_paid": "Oplacone",
            "mark_settled": "Rozliczone",
            "mark_office_closed": "Zamkniete biurowo",
            "mark_financially_closed": "Domkniete finansowo",
            "save_office_note": "Zapisano notatke biurowa",
            "update_invoice_data": "Zapisano dane faktury",
            "update_payment_data": "Zapisano dane platnosci",
            "set_next_action": "Ustawiono nastepna akcje",
            "snooze_record": "Odlozono temat",
            "clear_snooze": "Usunieto odlozenie",
        }
        when = str(record.get("created_at", "") or "")
        who = str(record.get("created_by", "") or "-")
        action_key = str(record.get("action_type", "") or "")
        action_label = action_map.get(action_key, action_key or "Aktualizacja")
        old_status = str(record.get("old_office_status", "") or "")
        new_status = str(record.get("new_office_status", "") or "")
        status_part = ""
        if old_status or new_status:
            old_label = OFFICE_STATUS_VALUES.get(old_status, old_status or "-")
            new_label = OFFICE_STATUS_VALUES.get(new_status, new_status or "-")
            status_part = f" | {old_label} -> {new_label}"
        extras: list[str] = []
        invoice_number = str(record.get("invoice_number", "") or "")
        if invoice_number:
            extras.append(invoice_number)
        paid_amount = float(record.get("paid_amount", 0.0) or 0.0)
        if paid_amount > 0:
            extras.append(_fmt_pln(paid_amount))
        payment_date = str(record.get("payment_date", "") or "")
        if payment_date:
            extras.append(payment_date)
        note = str(record.get("note", "") or "")
        extra_part = f" | {' | '.join(extras)}" if extras else ""
        note_part = f" | {note}" if note else ""
        return f"{when} | {who} | {action_label}{status_part}{extra_part}{note_part}"

    def _on_mark_sent_to_invoicing(self) -> None:
        self._apply_office_status("przekazane_do_fakturowania")

    def _on_mark_invoiced(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        dlg = MarkInvoicedDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        p = dlg.payload()
        self._followup_store.mark_invoiced(
            point_id=pid,
            invoice_number=p.get("invoice_number", ""),
            invoice_date=p.get("invoice_date", ""),
            linked_invoice_id=p.get("linked_invoice_id", ""),
            linked_invoice_source=p.get("linked_invoice_source", "manual"),
            note=p.get("note", ""),
            updated_by=self._current_worker,
        )
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_mark_paid(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        dlg = MarkPaidDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        p = dlg.payload()
        self._followup_store.mark_paid(
            point_id=pid,
            paid_amount=float(p.get("paid_amount", 0.0) or 0.0),
            payment_date=str(p.get("payment_date", "") or ""),
            payment_method=str(p.get("payment_method", "") or ""),
            note=str(p.get("note", "") or ""),
            updated_by=self._current_worker,
        )
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_mark_settled(self) -> None:
        self._apply_office_status("rozliczone")

    def _on_mark_office_closed(self) -> None:
        self._apply_office_status("zamkniete_biurowo")

    def _on_mark_financially_closed(self) -> None:
        self._apply_office_status("domkniete_finansowo")

    def _on_set_next_action(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        dlg = NextActionDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        p = dlg.payload()
        self._followup_store.set_next_action(
            point_id=pid,
            next_action_date=str(p.get("next_action_date", "") or ""),
            next_action_type=str(p.get("next_action_type", "brak") or "brak"),
            next_action_note=str(p.get("next_action_note", "") or ""),
            needs_contact=bool(p.get("needs_contact", False)),
            needs_check=bool(p.get("needs_check", False)),
            updated_by=self._current_worker,
        )
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_snooze_record(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        dlg = SnoozeRecordDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        p = dlg.payload()
        self._followup_store.snooze_record(
            point_id=pid,
            snoozed_until=str(p.get("snoozed_until", "") or ""),
            note=str(p.get("note", "") or ""),
            updated_by=self._current_worker,
        )
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_clear_snooze(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        self._followup_store.clear_snooze(point_id=pid, updated_by=self._current_worker)
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _apply_office_status(self, status: str) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        note = self.ed_office_note.toPlainText().strip()
        if status == "przekazane_do_fakturowania":
            self._followup_store.mark_sent_to_invoicing(pid, note=note, updated_by=self._current_worker)
        elif status == "rozliczone":
            self._followup_store.mark_settled(pid, note=note, updated_by=self._current_worker)
        elif status == "zamkniete_biurowo":
            self._followup_store.mark_office_closed(pid, note=note, updated_by=self._current_worker)
        elif status == "domkniete_finansowo":
            self._followup_store.mark_financially_closed(pid, note=note, updated_by=self._current_worker)
        else:
            self._followup_store.upsert_record(pid, status, note, self._current_worker)
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_save_office_note(self) -> None:
        row = self._selected_row()
        if not row:
            return
        pid = str(row.get("point_id", "") or "")
        next_action_date = str(self.lab_next_action_date.text() or "").strip()
        next_action_note = str(self.lab_next_action_note.text() or "").strip()
        snoozed_until = str(self.lab_snoozed_until.text() or "").strip()
        if next_action_date == "-":
            next_action_date = ""
        if next_action_note == "-":
            next_action_note = ""
        if snoozed_until == "-":
            snoozed_until = ""
        self._followup_store.upsert_record(
            point_id=pid,
            office_status=str(self.cb_office_status.currentData() or "nowe"),
            office_note=self.ed_office_note.toPlainText().strip(),
            updated_by=self._current_worker,
            invoice_number=self.ed_invoice_number.text().strip(),
            invoice_date=self.ed_invoice_date.text().strip(),
            linked_invoice_id=self.ed_linked_invoice_id.text().strip(),
            linked_invoice_source=self.ed_linked_invoice_source.text().strip(),
            payment_status=str(self.lab_payment_status.text() or "brak"),
            paid_amount=float(self.sp_paid_amount.value() or 0.0),
            payment_date=self.ed_payment_date.text().strip(),
            payment_method=str(self.cb_payment_method.currentData() or "inne"),
            payment_note=self.ed_payment_note.toPlainText().strip(),
            next_action_date=next_action_date,
            next_action_type=str(row.get("next_action_type", "brak") or "brak"),
            next_action_note=next_action_note,
            snoozed_until=snoozed_until,
            needs_contact=self.chk_needs_contact.isChecked(),
            needs_check=self.chk_needs_check.isChecked(),
            financially_closed=self.chk_financially_closed.isChecked(),
        )
        self.refresh_data()
        self._select_row_by_point_id(pid)

    def _on_copy_note(self) -> None:
        row = self._selected_row()
        if not row:
            return
        QApplication.clipboard().setText(str(row.get("office_note", "") or row.get("finance_followup_note", "") or ""))

    def _on_copy_address(self) -> None:
        row = self._selected_row()
        if not row:
            return
        QApplication.clipboard().setText(str(row.get("full_address", "") or ""))

    def _on_go_ops(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "Do rozliczenia z OPERACJE", "Wybierz rekord z tabeli.")
            return
        payload = {
            "point_id": str(row.get("point_id", "") or ""),
            "project_name": str(row.get("project_name", "") or ""),
            "client_name": str(row.get("client_name", "") or ""),
            "target_tab": "mapa_zlecen",
        }
        if callable(self._on_navigate_to_operations):
            self._on_navigate_to_operations(payload)
            return
        QMessageBox.information(self, "Do rozliczenia z OPERACJE", "Nawigacja do OPERACJE jest niedostepna w tym widoku.")
