from __future__ import annotations

from datetime import date
import tempfile
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
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
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.maps_urls import build_google_maps_search_url, open_url
from src.core.mymaps_export import export_map_points_to_csv
from src.core.orders_map_service import MapOrderPoint, OrdersMapService, VISIT_STATUS_VALUES, VISIT_TYPE_VALUES
from src.core.operations_store import OperationsStore
from src.core.trip_card_export import export_trip_card_to_csv, export_trip_card_to_html
from src.core.visit_history_store import VisitHistoryRecord, VisitHistoryStore


class VisitHistoryEditDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, record: VisitHistoryRecord | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wpis historii wizyty")
        self.setModal(True)
        self.setMinimumWidth(620)
        self._record = record or VisitHistoryRecord()
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_date = QLineEdit(self)
        self.ed_date.setPlaceholderText("YYYY-MM-DD")
        self.ed_crew = QLineEdit(self)
        self.ed_workers = QLineEdit(self)
        self.cb_type = QComboBox(self)
        for val in sorted(VISIT_TYPE_VALUES):
            self.cb_type.addItem(val, val)
        self.ed_status_before = QLineEdit(self)
        self.ed_status_after = QLineEdit(self)
        self.ed_work_done = QTextEdit(self)
        self.ed_work_remaining = QTextEdit(self)
        self.ed_items_taken = QTextEdit(self)
        self.ed_issues = QTextEdit(self)
        self.ed_duration = QLineEdit(self)
        self.chk_closed = QCheckBox("Zamknieto temat", self)
        self.ed_notes = QTextEdit(self)

        form.addRow("Data wizyty", self.ed_date)
        form.addRow("Ekipa", self.ed_crew)
        form.addRow("Pracownicy (po przecinku)", self.ed_workers)
        form.addRow("Typ wizyty", self.cb_type)
        form.addRow("Status przed", self.ed_status_before)
        form.addRow("Status po", self.ed_status_after)
        form.addRow("Co zrobiono", self.ed_work_done)
        form.addRow("Co zostalo", self.ed_work_remaining)
        form.addRow("Co zabrano", self.ed_items_taken)
        form.addRow("Problemy znalezione", self.ed_issues)
        form.addRow("Czas [min]", self.ed_duration)
        form.addRow("", self.chk_closed)
        form.addRow("Notatki", self.ed_notes)
        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.set_record(self._record)

    def set_record(self, record: VisitHistoryRecord) -> None:
        self._record = record
        self.ed_date.setText(record.visit_date)
        self.ed_crew.setText(record.crew)
        self.ed_workers.setText(",".join(record.workers))
        idx = self.cb_type.findData(record.visit_type)
        if idx >= 0:
            self.cb_type.setCurrentIndex(idx)
        self.ed_status_before.setText(record.status_before)
        self.ed_status_after.setText(record.status_after)
        self.ed_work_done.setPlainText(record.work_done)
        self.ed_work_remaining.setPlainText(record.work_remaining)
        self.ed_items_taken.setPlainText(record.items_taken)
        self.ed_issues.setPlainText(record.issues_found)
        self.ed_duration.setText(str(record.duration_minutes or 0))
        self.chk_closed.setChecked(record.is_closed)
        self.ed_notes.setPlainText(record.notes)

    def get_record(self) -> VisitHistoryRecord:
        rec = self._record
        rec.visit_date = self.ed_date.text().strip()
        rec.crew = self.ed_crew.text().strip()
        rec.workers = [x.strip() for x in self.ed_workers.text().split(",") if x.strip()]
        rec.visit_type = str(self.cb_type.currentData() or "inne")
        rec.status_before = self.ed_status_before.text().strip()
        rec.status_after = self.ed_status_after.text().strip()
        rec.work_done = self.ed_work_done.toPlainText().strip()
        rec.work_remaining = self.ed_work_remaining.toPlainText().strip()
        rec.items_taken = self.ed_items_taken.toPlainText().strip()
        rec.issues_found = self.ed_issues.toPlainText().strip()
        try:
            rec.duration_minutes = int(self.ed_duration.text().strip() or 0)
        except Exception:
            rec.duration_minutes = 0
        rec.is_closed = self.chk_closed.isChecked()
        rec.notes = self.ed_notes.toPlainText().strip()
        return rec


class VisitFinanceResultDialog(QDialog):
    _STATUS_OPTIONS = [
        ("Gotowe do fakturowania", "gotowe_do_fakturowania"),
        ("Wymaga rozliczenia", "wymaga_rozliczenia"),
        ("Czeka na potwierdzenie", "czeka_na_potwierdzenie"),
        ("Nie dotyczy", "nie_dotyczy"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rozliczenie po wizycie")
        self.setModal(True)
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.chk_blocks_payment = QCheckBox("Odblokowuje platnosc", self)
        self.sp_unlock_amount = QDoubleSpinBox(self)
        self.sp_unlock_amount.setRange(0.0, 1_000_000_000.0)
        self.sp_unlock_amount.setDecimals(2)
        self.cb_followup = QComboBox(self)
        for label, key in self._STATUS_OPTIONS:
            self.cb_followup.addItem(label, key)
        self.chk_ready_invoice = QCheckBox("Gotowe do fakturowania", self)
        self.chk_requires_settlement = QCheckBox("Wymaga rozliczenia", self)
        self.chk_requires_confirmation = QCheckBox("Czeka na potwierdzenie", self)
        self.txt_note = QTextEdit(self)
        self.txt_note.setMaximumHeight(120)

        form.addRow("", self.chk_blocks_payment)
        form.addRow("Szacowana kwota", self.sp_unlock_amount)
        form.addRow("Stan po wizycie", self.cb_followup)
        form.addRow("", self.chk_ready_invoice)
        form.addRow("", self.chk_requires_settlement)
        form.addRow("", self.chk_requires_confirmation)
        form.addRow("Notatka", self.txt_note)
        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_payload(self) -> dict[str, Any]:
        return {
            "blocks_payment": bool(self.chk_blocks_payment.isChecked()),
            "estimated_payment_unlock": float(self.sp_unlock_amount.value() or 0.0),
            "finance_followup_status": str(self.cb_followup.currentData() or "nie_dotyczy"),
            "ready_to_invoice": bool(self.chk_ready_invoice.isChecked()),
            "requires_settlement": bool(self.chk_requires_settlement.isChecked()),
            "requires_confirmation": bool(self.chk_requires_confirmation.isChecked()),
            "finance_followup_note": self.txt_note.toPlainText().strip(),
        }


class OrdersMapPanel(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        service: OrdersMapService | None = None,
        operations_store: OperationsStore | None = None,
        on_data_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._operations_store = operations_store or OperationsStore()
        self._service = service or OrdersMapService(operations_store=self._operations_store)
        self._history_store = getattr(self._service, "_history_store", VisitHistoryStore())
        self._on_data_changed_cb = on_data_changed
        self._role = "biuro"
        self._worker_name = ""
        self._points: list[MapOrderPoint] = []
        self._route_points: list[MapOrderPoint] = []
        self._history_records: list[VisitHistoryRecord] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        self.lbl_navigation_info = QLabel("", self)
        self.lbl_navigation_info.setWordWrap(True)
        self.lbl_navigation_info.setVisible(False)
        self.lbl_navigation_info.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:8px;"
            "padding:6px 8px;color:#475569;font-size:12px;font-weight:600;}"
        )
        root.addWidget(self.lbl_navigation_info, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(splitter, 1)

        left = QFrame(self)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(10)
        self._build_filters(left_l)
        self._build_points_table(left_l)
        splitter.addWidget(left)

        middle = QFrame(self)
        mid_l = QVBoxLayout(middle)
        mid_l.setContentsMargins(0, 0, 0, 0)
        mid_l.setSpacing(10)
        self._build_details(mid_l)
        self._build_history(mid_l)
        splitter.addWidget(middle)

        right = QFrame(self)
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(10)
        self._build_route_card(right_l)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 4)

        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()
        self.refresh_data()

    def _build_filters(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.f_text = QLineEdit(self)
        self.f_text.setPlaceholderText("Szukaj...")
        self.f_city = QLineEdit(self)
        self.f_city.setPlaceholderText("Miasto")
        self.f_crew = QLineEdit(self)
        self.f_crew.setPlaceholderText("Ekipa")
        self.f_type = QComboBox(self)
        self.f_type.addItem("Typ: wszystkie", "all")
        for value in sorted(VISIT_TYPE_VALUES):
            self.f_type.addItem(value, value)
        self.f_status = QComboBox(self)
        self.f_status.addItem("Status: wszystkie", "all")
        for value in sorted(VISIT_STATUS_VALUES):
            self.f_status.addItem(value, value)
        self.f_active = QCheckBox("Tylko aktywne", self)
        self.f_today = QCheckBox("Tylko dzis", self)
        self.f_with_phone = QCheckBox("Tylko z telefonem", self)
        self.f_only_blocks_payment = QCheckBox("Tylko odblokowujace platnosc", self)
        self.f_only_ready_invoice = QCheckBox("Tylko gotowe do fakturowania", self)
        self.f_only_settlement = QCheckBox("Tylko wymagajace rozliczenia", self)
        self.f_only_confirmation = QCheckBox("Tylko czekajace na potwierdzenie", self)
        for w in [
            self.f_text,
            self.f_city,
            self.f_crew,
            self.f_type,
            self.f_status,
            self.f_active,
            self.f_today,
            self.f_with_phone,
            self.f_only_blocks_payment,
            self.f_only_ready_invoice,
            self.f_only_settlement,
            self.f_only_confirmation,
        ]:
            row.addWidget(w)
        root.addLayout(row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_refresh = QPushButton("Odswiez", self)
        self.btn_open_selected = QPushButton("Otworz w Google Maps", self)
        self.btn_open_day_route = QPushButton("Otworz trase w Google Maps", self)
        self.btn_copy_phone_top = QPushButton("Skopiuj telefon", self)
        self.btn_copy_address_top = QPushButton("Skopiuj adres", self)
        self.btn_show_day_route = QPushButton("Pokaz trase dnia", self)
        self.btn_export_csv = QPushButton("Eksport My Maps CSV", self)
        for b in [
            self.btn_open_selected,
            self.btn_open_day_route,
            self.btn_copy_phone_top,
            self.btn_copy_address_top,
            self.btn_show_day_route,
            self.btn_export_csv,
            self.btn_refresh,
        ]:
            actions.addWidget(b)
        root.addLayout(actions)

        for w in [self.f_text, self.f_city, self.f_crew]:
            w.textChanged.connect(self.refresh_data)
        for w in [self.f_type, self.f_status]:
            w.currentIndexChanged.connect(self.refresh_data)
        for w in [
            self.f_active,
            self.f_today,
            self.f_with_phone,
            self.f_only_blocks_payment,
            self.f_only_ready_invoice,
            self.f_only_settlement,
            self.f_only_confirmation,
        ]:
            w.stateChanged.connect(self.refresh_data)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_show_day_route.clicked.connect(self._populate_route_panel)
        self.btn_open_selected.clicked.connect(self._on_open_selected_point_in_google_maps)
        self.btn_open_day_route.clicked.connect(self._on_open_day_route_in_google_maps)
        self.btn_copy_phone_top.clicked.connect(self._on_copy_phone)
        self.btn_copy_address_top.clicked.connect(self._on_copy_address)
        self.btn_export_csv.clicked.connect(self._on_export_mymaps_csv)

    def _build_points_table(self, root: QVBoxLayout) -> None:
        self.tbl_points = QTableWidget(0, 12, self)
        self.tbl_points.setHorizontalHeaderLabels(
            [
                "Projekt",
                "Klient",
                "Miasto",
                "Adres",
                "Telefon",
                "Typ wizyty",
                "Status",
                "Data wizyty",
                "Ekipa",
                "Platnosc",
                "Kwota",
                "Stan po wizycie",
            ]
        )
        self.tbl_points.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_points.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_points.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_points.verticalHeader().setVisible(False)
        h1 = self.tbl_points.horizontalHeader()
        for col in range(12):
            mode = QHeaderView.ResizeMode.ResizeToContents
            if col in {1, 3, 4}:
                mode = QHeaderView.ResizeMode.Stretch
            h1.setSectionResizeMode(col, mode)
        self._tbl_points_amount_col = 10
        root.addWidget(self.tbl_points, 1)
        self.lbl_points_empty = QLabel("Brak punktow do wyswietlenia", self)
        self.lbl_points_empty.setStyleSheet("color:#64748b;font-style:italic;padding:4px 2px;")
        root.addWidget(self.lbl_points_empty, 0)
        self.tbl_points.itemSelectionChanged.connect(self._show_point_details)

    def _build_details(self, root: QVBoxLayout) -> None:
        title = QLabel("Szczegoly punktu", self)
        title.setStyleSheet("font-weight:700;color:#0f172a;")
        root.addWidget(title)

        hero = QFrame(self)
        hero.setStyleSheet("QFrame{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;}")
        hero_l = QFormLayout(hero)
        hero_l.setContentsMargins(10, 8, 10, 8)
        hero_l.setVerticalSpacing(6)
        self.lab_client = QLabel("Brak danych", self)
        self.lab_client.setStyleSheet("font-size:14px;font-weight:700;color:#0f172a;")
        self.lab_address = QLabel("Brak adresu", self)
        self.lab_address.setStyleSheet("font-size:13px;font-weight:600;color:#1f2937;")
        self.lab_phone = QLabel("Brak danych kontaktowych", self)
        self.lab_phone.setStyleSheet("font-size:13px;font-weight:700;color:#0f172a;")
        self.lab_status_chip = QLabel("Status wizyty: do ustalenia", self)
        self.lab_status_chip.setStyleSheet(
            "QLabel{background:#eef2ff;color:#1e3a8a;border:1px solid #c7d2fe;border-radius:10px;padding:3px 8px;font-weight:700;}"
        )
        self.lab_project_order = QLabel("-", self)
        self.lab_type = QLabel("-", self)
        self.lab_crew = QLabel("-", self)
        hero_l.addRow("Klient", self.lab_client)
        hero_l.addRow("Adres", self.lab_address)
        hero_l.addRow("Telefon", self.lab_phone)
        hero_l.addRow("Status wizyty", self.lab_status_chip)
        hero_l.addRow("Projekt / zamowienie", self.lab_project_order)
        hero_l.addRow("Typ wizyty", self.lab_type)
        hero_l.addRow("Przypisana ekipa", self.lab_crew)
        root.addWidget(hero, 0)

        row = QHBoxLayout()
        self.btn_copy_phone = QPushButton("Skopiuj telefon", self)
        self.btn_copy_address = QPushButton("Skopiuj adres", self)
        self.btn_open_point = QPushButton("Otworz punkt w Google Maps", self)
        self.btn_add_to_route = QPushButton("Dodaj do trasy", self)
        self.btn_mark_done = QPushButton("Oznacz jako wykonane", self)
        self.btn_finance_result = QPushButton("Ustaw wynik rozliczenia", self)
        for b in [self.btn_copy_phone, self.btn_copy_address, self.btn_open_point, self.btn_add_to_route, self.btn_mark_done, self.btn_finance_result]:
            row.addWidget(b)
        root.addLayout(row)

        scope_wrap = QHBoxLayout()
        scope_wrap.setSpacing(8)
        scope_left = QFrame(self)
        scope_left.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:10px;}")
        scope_left_l = QVBoxLayout(scope_left)
        scope_left_l.setContentsMargins(8, 6, 8, 6)
        scope_left_l.addWidget(QLabel("Zakres robot", self))
        self.txt_scope = QTextEdit(self)
        self.txt_scope.setReadOnly(True)
        self.txt_scope.setMaximumHeight(90)
        scope_left_l.addWidget(self.txt_scope)
        scope_wrap.addWidget(scope_left, 1)

        scope_right = QFrame(self)
        scope_right.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:10px;}")
        scope_right_l = QVBoxLayout(scope_right)
        scope_right_l.setContentsMargins(8, 6, 8, 6)
        scope_right_l.addWidget(QLabel("Co zabrac", self))
        self.txt_items = QTextEdit(self)
        self.txt_items.setReadOnly(True)
        self.txt_items.setMaximumHeight(90)
        scope_right_l.addWidget(self.txt_items)
        scope_wrap.addWidget(scope_right, 1)
        root.addLayout(scope_wrap)

        self.txt_details = QTextEdit(self)
        self.txt_details.setReadOnly(True)
        self.txt_details.setMaximumHeight(140)
        root.addWidget(self.txt_details, 0)

        finance = QFrame(self)
        finance.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d7e1ef;border-radius:10px;}")
        fin_l = QFormLayout(finance)
        fin_l.setContentsMargins(8, 6, 8, 6)
        fin_l.addRow(QLabel("Rozliczenie po wizycie", self))
        self.lab_fin_blocks_payment = QLabel("NIE", self)
        self.lab_fin_unlock_amount = QLabel("0.00", self)
        self.lab_fin_followup = QLabel("brak", self)
        self.lab_fin_ready = QLabel("NIE", self)
        self.lab_fin_settlement = QLabel("NIE", self)
        self.lab_fin_confirmation = QLabel("NIE", self)
        self.lab_fin_last_result = QLabel("brak", self)
        self.lab_fin_note = QLabel("-", self)
        fin_l.addRow("Odblokowuje platnosc", self.lab_fin_blocks_payment)
        fin_l.addRow("Szacowana kwota", self.lab_fin_unlock_amount)
        fin_l.addRow("Stan po wizycie", self.lab_fin_followup)
        fin_l.addRow("Gotowe do fakturowania", self.lab_fin_ready)
        fin_l.addRow("Wymaga rozliczenia", self.lab_fin_settlement)
        fin_l.addRow("Czeka na potwierdzenie", self.lab_fin_confirmation)
        fin_l.addRow("Ostatni wynik finansowy", self.lab_fin_last_result)
        fin_l.addRow("Notatka", self.lab_fin_note)
        root.addWidget(finance, 0)

        self.btn_open_point.clicked.connect(self._on_open_selected_point_in_google_maps)
        self.btn_copy_address.clicked.connect(self._on_copy_address)
        self.btn_copy_phone.clicked.connect(self._on_copy_phone)
        self.btn_add_to_route.clicked.connect(self._on_add_selected_to_route)
        self.btn_mark_done.clicked.connect(self._on_mark_selected_done)
        self.btn_finance_result.clicked.connect(self._on_set_finance_result)

    def _build_history(self, root: QVBoxLayout) -> None:
        title = QLabel("Historia wizyt", self)
        title.setStyleSheet("font-weight:700;color:#0f172a;")
        root.addWidget(title)
        self.tbl_history = QTableWidget(0, 7, self)
        self.tbl_history.setHorizontalHeaderLabels(["Data", "Ekipa", "Typ wizyty", "Co zrobiono", "Co zostalo", "Status po", "Zamkniete"])
        self.tbl_history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_history.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_history.verticalHeader().setVisible(False)
        h = self.tbl_history.horizontalHeader()
        for col in range(7):
            mode = QHeaderView.ResizeMode.ResizeToContents
            if col in {3, 4}:
                mode = QHeaderView.ResizeMode.Stretch
            h.setSectionResizeMode(col, mode)
        root.addWidget(self.tbl_history, 1)
        self.lbl_history_empty = QLabel("Brak historii wizyt", self)
        self.lbl_history_empty.setStyleSheet("color:#64748b;font-style:italic;padding:2px 2px;")
        root.addWidget(self.lbl_history_empty, 0)

        row = QHBoxLayout()
        self.btn_hist_add = QPushButton("Dodaj wpis historii", self)
        self.btn_hist_edit = QPushButton("Edytuj wpis", self)
        self.btn_hist_delete = QPushButton("Usun wpis", self)
        for b in [self.btn_hist_add, self.btn_hist_edit, self.btn_hist_delete]:
            row.addWidget(b)
        root.addLayout(row)
        self.btn_hist_add.clicked.connect(self._on_add_history_record)
        self.btn_hist_edit.clicked.connect(self._on_edit_history_record)
        self.btn_hist_delete.clicked.connect(self._on_delete_history_record)

    def _build_route_card(self, root: QVBoxLayout) -> None:
        title = QLabel("Karta wyjazdu", self)
        title.setStyleSheet("font-weight:700;color:#0f172a;")
        root.addWidget(title)
        self.tbl_route = QTableWidget(0, 11, self)
        self.tbl_route.setHorizontalHeaderLabels(
            ["Lp.", "Klient", "Adres", "Telefon", "Zakres robot", "Co zabrac", "Czas", "Status", "Platnosc", "Kwota", "Po wizycie"]
        )
        self.tbl_route.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_route.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_route.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_route.verticalHeader().setVisible(False)
        h2 = self.tbl_route.horizontalHeader()
        for col in range(11):
            mode = QHeaderView.ResizeMode.ResizeToContents
            if col in {2, 4, 5}:
                mode = QHeaderView.ResizeMode.Stretch
            h2.setSectionResizeMode(col, mode)
        self._tbl_route_amount_col = 9
        root.addWidget(self.tbl_route, 1)
        self.lbl_route_empty = QLabel("Brak punktow w trasie", self)
        self.lbl_route_empty.setStyleSheet("color:#64748b;font-style:italic;padding:2px 2px;")
        root.addWidget(self.lbl_route_empty, 0)

        row1 = QHBoxLayout()
        self.btn_move_up = QPushButton("Przenies wyzej", self)
        self.btn_move_down = QPushButton("Przenies nizej", self)
        self.btn_save_order = QPushButton("Zapisz kolejnosc", self)
        for b in [self.btn_move_up, self.btn_move_down, self.btn_save_order]:
            row1.addWidget(b)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_route_preview = QPushButton("Otworz podglad karty", self)
        self.btn_route_export_html = QPushButton("Eksport karty HTML", self)
        self.btn_route_export_csv = QPushButton("Eksport karty CSV", self)
        self.btn_route_google = QPushButton("Otworz trase w Google Maps", self)
        for b in [self.btn_route_preview, self.btn_route_export_html, self.btn_route_export_csv, self.btn_route_google]:
            row2.addWidget(b)
        root.addLayout(row2)

        self.btn_route_google.clicked.connect(self._on_open_day_route_in_google_maps)
        self.btn_route_export_csv.clicked.connect(self._on_export_trip_card_csv)
        self.btn_route_export_html.clicked.connect(self._on_export_trip_card_html)
        self.btn_route_preview.clicked.connect(self._on_preview_trip_card)
        self.btn_move_up.clicked.connect(self._on_move_route_point_up)
        self.btn_move_down.clicked.connect(self._on_move_route_point_down)
        self.btn_save_order.clicked.connect(self._on_save_route_order)

    def _selected_point(self) -> MapOrderPoint | None:
        model = self.tbl_points.selectionModel()
        if model is None or not model.selectedRows():
            return None
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._points):
            return None
        return self._points[row]

    def _selected_history(self) -> VisitHistoryRecord | None:
        model = self.tbl_history.selectionModel()
        if model is None or not model.selectedRows():
            return None
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._history_records):
            return None
        return self._history_records[row]

    def refresh_data(self) -> None:
        self._clear_navigation_info()
        self._points = self._service.filter_map_points(**self._read_filters())
        self._populate_points_table()
        self._populate_route_panel()
        self._refresh_history_for_selected_point()

    def navigate_to_point(
        self,
        point_id: str | None = None,
        project_name: str = "",
        client_name: str = "",
    ) -> bool:
        wanted_id = str(point_id or "").strip()
        wanted_project = str(project_name or "").strip().lower()
        wanted_client = str(client_name or "").strip().lower()
        self.refresh_data()
        idx = -1
        found_exact = False
        if wanted_id:
            for i, point in enumerate(self._points):
                if str(point.id or "").strip() == wanted_id:
                    idx = i
                    found_exact = True
                    break
        if idx < 0 and (wanted_project or wanted_client):
            for i, point in enumerate(self._points):
                project_ok = (not wanted_project) or (wanted_project in str(point.project_name or "").lower())
                client_ok = (not wanted_client) or (wanted_client in str(point.client_name or "").lower())
                if project_ok and client_ok:
                    idx = i
                    break
        if idx < 0:
            self._show_navigation_info("Nie znaleziono dokladnego punktu. Otworzono Mape zlecen.")
            return False
        self.tbl_points.selectRow(idx)
        item = self.tbl_points.item(idx, 0)
        if item is not None:
            self.tbl_points.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self._show_point_details()
        if found_exact:
            self._clear_navigation_info()
        else:
            self._show_navigation_info("Nie znaleziono dokladnego punktu. Otworzono Mape zlecen.")
        return True

    def _show_navigation_info(self, text: str) -> None:
        msg = str(text or "").strip()
        if not msg:
            self._clear_navigation_info()
            return
        self.lbl_navigation_info.setText(msg)
        self.lbl_navigation_info.setVisible(True)

    def _clear_navigation_info(self) -> None:
        self.lbl_navigation_info.setText("")
        self.lbl_navigation_info.setVisible(False)

    def _read_filters(self) -> dict[str, Any]:
        return {
            "text": self.f_text.text().strip(),
            "city": self.f_city.text().strip(),
            "crew": self.f_crew.text().strip(),
            "visit_type": str(self.f_type.currentData() or "all"),
            "visit_status": str(self.f_status.currentData() or "all"),
            "active_only": self.f_active.isChecked(),
            "only_today": self.f_today.isChecked(),
            "with_phone_only": self.f_with_phone.isChecked(),
            "only_blocks_payment": self.f_only_blocks_payment.isChecked(),
            "only_ready_to_invoice": self.f_only_ready_invoice.isChecked(),
            "only_requires_settlement": self.f_only_settlement.isChecked(),
            "only_requires_confirmation": self.f_only_confirmation.isChecked(),
        }

    def _populate_points_table(self) -> None:
        self.tbl_points.setRowCount(0)
        hide_amount = self._role in {"produkcja", "magazyn", "montaz"}
        for p in self._points:
            row = self.tbl_points.rowCount()
            self.tbl_points.insertRow(row)
            vals = [
                p.project_name,
                p.client_name,
                p.city,
                p.full_address,
                p.contact_phone,
                p.visit_type,
                p.visit_status,
                p.next_visit_at,
                p.crew,
                "TAK" if p.blocks_payment else "NIE",
                f"{float(p.estimated_payment_unlock or 0.0):.2f}",
                str(p.finance_followup_status or "brak"),
            ]
            for col, val in enumerate(vals):
                self.tbl_points.setItem(row, col, QTableWidgetItem(str(val)))
        self.tbl_points.setColumnHidden(self._tbl_points_amount_col, hide_amount)
        if self.tbl_points.rowCount() > 0:
            self.tbl_points.selectRow(0)
            self.lbl_points_empty.setVisible(False)
        else:
            self.lbl_points_empty.setVisible(True)
            self.lab_client.setText("Brak danych")
            self.lab_address.setText("Brak adresu")
            self.lab_phone.setText("Brak danych kontaktowych")
            self.lab_status_chip.setText("Status wizyty: do ustalenia")
            self.lab_project_order.setText("-")
            self.lab_type.setText("-")
            self.lab_crew.setText("-")
            self.txt_scope.setPlainText("Brak danych")
            self.txt_items.setPlainText("Brak danych")
            self.lab_fin_blocks_payment.setText("NIE")
            self.lab_fin_unlock_amount.setText("0.00")
            self.lab_fin_followup.setText("brak")
            self.lab_fin_ready.setText("NIE")
            self.lab_fin_settlement.setText("NIE")
            self.lab_fin_confirmation.setText("NIE")
            self.lab_fin_last_result.setText("brak")
            self.lab_fin_note.setText("-")
            self.txt_details.clear()

    def _show_point_details(self) -> None:
        p = self._selected_point()
        if p is None:
            self.txt_details.clear()
            self._populate_history_table([])
            return
        txt = [
            f"Osoba kontaktowa: {p.contact_name or 'Brak danych'}",
            f"Telefon dodatkowy: {p.contact_phone_alt or 'Brak danych'}",
            f"Miasto: {p.city or 'Brak danych'}",
            f"Ostatnia wizyta: {p.last_visit_at or 'Brak danych'}",
            f"Nastepna wizyta: {p.next_visit_at or 'Brak danych'}",
            f"Grupa trasy: {p.route_group}",
            f"Kolejnosc: {p.trip_order}",
            f"Zrodlo: {p.source_kind}",
            f"Historia: {'TAK' if p.has_history else 'NIE'}",
            f"Ostatni wynik: {p.last_visit_result or 'Brak danych'}",
            f"Ostatnia notatka: {p.last_history_note or 'Brak danych'}",
            f"Notatki dla ekipy: {p.crew_notes or 'Brak danych'}",
        ]
        self.lab_client.setText(p.client_name or "Brak danych")
        self.lab_address.setText(p.full_address or "Brak adresu")
        self.lab_phone.setText(p.contact_phone or "Brak danych kontaktowych")
        self.lab_status_chip.setText(f"Status wizyty: {p.visit_status or 'do ustalenia'}")
        self.lab_project_order.setText(f"{p.project_name or '-'} / {p.order_id or '-'}")
        self.lab_type.setText(p.visit_type or "inne")
        self.lab_crew.setText(p.crew or "Brak danych")
        self.txt_scope.setPlainText(p.work_scope or "Brak danych")
        self.txt_items.setPlainText(p.items_to_take or "Brak danych")
        self.lab_fin_blocks_payment.setText("TAK" if p.blocks_payment else "NIE")
        if self._role in {"produkcja", "magazyn", "montaz"}:
            self.lab_fin_unlock_amount.setText("Ukryte")
        else:
            self.lab_fin_unlock_amount.setText(f"{float(p.estimated_payment_unlock or 0.0):.2f}")
        self.lab_fin_followup.setText(p.finance_followup_status or "brak")
        self.lab_fin_ready.setText("TAK" if p.ready_to_invoice else "NIE")
        self.lab_fin_settlement.setText("TAK" if p.requires_settlement else "NIE")
        self.lab_fin_confirmation.setText("TAK" if p.requires_confirmation else "NIE")
        self.lab_fin_last_result.setText(p.last_finance_result or "brak")
        self.lab_fin_note.setText(p.finance_followup_note or "Brak danych")
        self.txt_details.setPlainText("\n".join(txt))
        self._refresh_history_for_selected_point()

    def _populate_route_panel(self) -> None:
        day = date.today().strftime("%Y-%m-%d")
        crew = self.f_crew.text().strip()
        self._route_points = self._service.build_route_points_for_day(day, crew=crew)
        self.tbl_route.setRowCount(0)
        hide_amount = self._role in {"produkcja", "magazyn", "montaz"}
        for idx, p in enumerate(self._route_points, 1):
            row = self.tbl_route.rowCount()
            self.tbl_route.insertRow(row)
            vals = [
                str(idx),
                p.client_name,
                p.full_address,
                p.contact_phone,
                p.work_scope,
                p.items_to_take,
                str(p.next_visit_at or ""),
                p.visit_status,
                "TAK" if p.blocks_payment else "NIE",
                f"{float(p.estimated_payment_unlock or 0.0):.2f}",
                str(p.finance_followup_status or "brak"),
            ]
            for col, val in enumerate(vals):
                self.tbl_route.setItem(row, col, QTableWidgetItem(str(val)))
        self.tbl_route.setColumnHidden(self._tbl_route_amount_col, hide_amount)
        self.lbl_route_empty.setVisible(self.tbl_route.rowCount() == 0)

    def _refresh_history_for_selected_point(self) -> None:
        p = self._selected_point()
        if p is None:
            self._populate_history_table([])
            return
        records = self._history_store.list_for_point(p.id)
        self._populate_history_table(records)

    def _populate_history_table(self, records: list[VisitHistoryRecord]) -> None:
        self._history_records = list(records)
        self.tbl_history.setRowCount(0)
        for rec in self._history_records:
            row = self.tbl_history.rowCount()
            self.tbl_history.insertRow(row)
            vals = [
                rec.visit_date,
                rec.crew,
                rec.visit_type,
                rec.work_done,
                rec.work_remaining,
                rec.status_after,
                "TAK" if rec.is_closed else "NIE",
            ]
            for col, val in enumerate(vals):
                self.tbl_history.setItem(row, col, QTableWidgetItem(str(val)))
        self.lbl_history_empty.setVisible(self.tbl_history.rowCount() == 0)

    def _on_add_history_record(self) -> None:
        p = self._selected_point()
        if p is None:
            QMessageBox.information(self, "Mapa zlecen", "Wybierz punkt.")
            return
        rec = VisitHistoryRecord(
            point_id=p.id,
            order_id=p.order_id,
            project_id=p.project_id,
            project_name=p.project_name,
            client_id=p.client_id,
            client_name=p.client_name,
            visit_date=date.today().strftime("%Y-%m-%d"),
            crew=p.crew,
            visit_type=p.visit_type,
            status_before=p.visit_status,
            status_after=p.visit_status,
            client_contact_name=p.contact_name,
            client_contact_phone=p.contact_phone,
            address=p.full_address,
            city=p.city,
        )
        dlg = VisitHistoryEditDialog(self, rec)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._history_store.add_record(dlg.get_record())
        self._refresh_history_for_selected_point()
        self.refresh_data()

    def _on_edit_history_record(self) -> None:
        rec = self._selected_history()
        if rec is None:
            QMessageBox.information(self, "Mapa zlecen", "Wybierz wpis historii.")
            return
        dlg = VisitHistoryEditDialog(self, rec)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._history_store.update_record(dlg.get_record())
        self._refresh_history_for_selected_point()
        self.refresh_data()

    def _on_delete_history_record(self) -> None:
        rec = self._selected_history()
        if rec is None:
            return
        self._history_store.delete_record(rec.id)
        self._refresh_history_for_selected_point()
        self.refresh_data()

    def _on_open_selected_point_in_google_maps(self) -> None:
        p = self._selected_point()
        if p is None:
            QMessageBox.information(self, "Mapa zlecen", "Wybierz punkt.")
            return
        if not str(p.full_address or "").strip():
            QMessageBox.information(self, "Mapa zlecen", "Brak adresu dla punktu.")
            return
        open_url(build_google_maps_search_url(p.full_address))

    def _on_open_day_route_in_google_maps(self) -> None:
        day = date.today().strftime("%Y-%m-%d")
        crew = self.f_crew.text().strip()
        url = self._service.build_google_maps_route_for_day(day, crew=crew)
        if not url:
            QMessageBox.information(self, "Mapa zlecen", "Brak punktow trasy dnia.")
            return
        open_url(url)

    def _on_copy_address(self) -> None:
        p = self._selected_point()
        if p is not None:
            QApplication.clipboard().setText(str(p.full_address or ""))

    def _on_copy_phone(self) -> None:
        p = self._selected_point()
        if p is not None:
            QApplication.clipboard().setText(str(p.contact_phone or ""))

    def _on_add_selected_to_route(self) -> None:
        p = self._selected_point()
        if p is None:
            QMessageBox.information(self, "Mapa zlecen", "Wybierz punkt.")
            return
        day = date.today().strftime("%Y-%m-%d")
        crew = self.f_crew.text().strip() or p.crew
        group = f"{day}-{crew or 'ekipa'}"
        self._service.append_point_to_route(p.id, day, crew, group)
        self.refresh_data()
        if callable(self._on_data_changed_cb):
            self._on_data_changed_cb()

    def _on_mark_selected_done(self) -> None:
        p = self._selected_point()
        if p is None:
            return
        self._service.mark_point_done(p.id, date.today().strftime("%Y-%m-%d"), crew=self.f_crew.text().strip())
        if p.id.startswith("route::"):
            dlg = VisitFinanceResultDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                payload = dlg.get_payload()
                self._service.mark_point_finance_result(
                    point_id=p.id,
                    finance_followup_status=str(payload["finance_followup_status"]),
                    estimated_payment_unlock=float(payload["estimated_payment_unlock"]),
                    ready_to_invoice=bool(payload["ready_to_invoice"]),
                    requires_settlement=bool(payload["requires_settlement"]),
                    requires_confirmation=bool(payload["requires_confirmation"]),
                    finance_followup_note=str(payload["finance_followup_note"]),
                )
        self.refresh_data()
        if callable(self._on_data_changed_cb):
            self._on_data_changed_cb()

    def _on_set_finance_result(self) -> None:
        p = self._selected_point()
        if p is None:
            QMessageBox.information(self, "Mapa zlecen", "Wybierz punkt.")
            return
        if not p.id.startswith("route::"):
            QMessageBox.information(self, "Mapa zlecen", "Wynik rozliczenia mozna ustawic dla punktow trasy.")
            return
        dlg = VisitFinanceResultDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dlg.get_payload()
        self._service.mark_point_finance_result(
            point_id=p.id,
            finance_followup_status=str(payload["finance_followup_status"]),
            estimated_payment_unlock=float(payload["estimated_payment_unlock"]),
            ready_to_invoice=bool(payload["ready_to_invoice"]),
            requires_settlement=bool(payload["requires_settlement"]),
            requires_confirmation=bool(payload["requires_confirmation"]),
            finance_followup_note=str(payload["finance_followup_note"]),
        )
        self.refresh_data()

    def _on_export_mymaps_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Eksport My Maps CSV", "mapa_zlecen.csv", "CSV (*.csv)")
        if not path:
            return
        export_map_points_to_csv(self._points, path)
        QMessageBox.information(self, "Mapa zlecen", "Eksport CSV zapisany.")

    def _route_selected_index(self) -> int:
        model = self.tbl_route.selectionModel()
        if model is None or not model.selectedRows():
            return -1
        return int(model.selectedRows()[0].row())

    def _swap_route_rows(self, a: int, b: int) -> None:
        if a < 0 or b < 0 or a >= len(self._route_points) or b >= len(self._route_points):
            return
        self._route_points[a], self._route_points[b] = self._route_points[b], self._route_points[a]
        self.tbl_route.setRowCount(0)
        for idx, p in enumerate(self._route_points, 1):
            row = self.tbl_route.rowCount()
            self.tbl_route.insertRow(row)
            vals = [str(idx), p.client_name, p.full_address, p.contact_phone, p.work_scope, p.items_to_take, str(p.next_visit_at or ""), p.visit_status]
            for col, val in enumerate(vals):
                self.tbl_route.setItem(row, col, QTableWidgetItem(str(val)))

    def _on_move_route_point_up(self) -> None:
        idx = self._route_selected_index()
        if idx <= 0:
            return
        self._swap_route_rows(idx, idx - 1)
        self.tbl_route.selectRow(idx - 1)

    def _on_move_route_point_down(self) -> None:
        idx = self._route_selected_index()
        if idx < 0 or idx >= len(self._route_points) - 1:
            return
        self._swap_route_rows(idx, idx + 1)
        self.tbl_route.selectRow(idx + 1)

    def _get_selected_route_point_ids_in_ui_order(self) -> list[str]:
        return [p.id for p in self._route_points]

    def _on_save_route_order(self) -> None:
        if not self._route_points:
            return
        group = str(self._route_points[0].route_group or "").strip()
        if not group:
            QMessageBox.information(self, "Mapa zlecen", "Brak grupy trasy do zapisu kolejnosci.")
            return
        self._service.reorder_route_points(group, self._get_selected_route_point_ids_in_ui_order())
        self.refresh_data()
        QMessageBox.information(self, "Mapa zlecen", "Kolejnosc trasy zapisana.")

    def _trip_meta(self) -> dict[str, str]:
        return {
            "title": "Karta wyjazdu",
            "date": date.today().strftime("%Y-%m-%d"),
            "crew": self.f_crew.text().strip(),
        }

    def _on_export_trip_card_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Eksport karty CSV", "karta_wyjazdu.csv", "CSV (*.csv)")
        if not path:
            return
        export_trip_card_to_csv(self._route_points, path, trip_meta=self._trip_meta())
        QMessageBox.information(self, "Mapa zlecen", "Karta wyjazdu CSV zapisana.")

    def _on_export_trip_card_html(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Eksport karty HTML", "karta_wyjazdu.html", "HTML (*.html)")
        if not path:
            return
        export_trip_card_to_html(self._route_points, path, trip_meta=self._trip_meta())
        QMessageBox.information(self, "Mapa zlecen", "Karta wyjazdu HTML zapisana.")

    def _on_preview_trip_card(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="trip_card_", suffix=".html", delete=False) as fh:
            preview_path = fh.name
        export_trip_card_to_html(self._route_points, preview_path, trip_meta=self._trip_meta())
        QDesktopServices.openUrl(QUrl.fromLocalFile(preview_path))
