from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson


CALENDAR_STAGE_ITEMS: tuple[str, ...] = (
    "Pomiar",
    "Wycena",
    "Zakup materialow",
    "Produkcja",
    "Lakiernia",
    "Montaz",
    "Poprawki",
    "Inne",
)

CALENDAR_STATUS_ITEMS: tuple[str, ...] = (
    "Nowe",
    "Wycena",
    "Wycena gotowa",
    "Zaakceptowane",
    "Zakup materialow",
    "Produkcja",
    "Lakiernia",
    "Montaz",
    "Poprawki",
    "Zakonczone",
)

CALENDAR_STAGE_SUMMARY_ITEMS: tuple[str, ...] = (
    "Wycena",
    "Zakup materialow",
    "Produkcja",
    "Montaz",
    "Poprawki",
)


def _parse_iso_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _matches_stage_bucket(order, calendar_stage: str, bucket: str) -> bool:
    stage = str(calendar_stage or "").strip().lower()
    status = str(getattr(order, "status", "") or "").strip().lower()
    bucket_norm = bucket.strip().lower()
    if bucket_norm == "wycena":
        return stage == "wycena" or status.startswith("wycena")
    return stage == bucket_norm or status == bucket_norm


class TabKalendarz(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        order_store: OrderStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._rows: list[dict[str, object]] = []
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("KALENDARZ PRAC")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.5px;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Widok projektow do prowadzenia pracy firmy: status, zaawansowanie, etap i planowany termin."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555555;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.lab_metric_total = self._make_metric_card("Projekty", "0")
        self.lab_metric_scheduled = self._make_metric_card("Zaplanowane", "0")
        self.lab_metric_overdue = self._make_metric_card("Po terminie", "0")
        self.lab_metric_montage = self._make_metric_card("Montaz", "0")
        for widget in (
            self.lab_metric_total,
            self.lab_metric_scheduled,
            self.lab_metric_overdue,
            self.lab_metric_montage,
        ):
            stats_row.addWidget(widget)
        stats_row.addStretch(1)
        root.addLayout(stats_row)

        stage_stats_row = QHBoxLayout()
        stage_stats_row.setSpacing(12)
        self.stage_metric_cards: dict[str, QFrame] = {}
        for stage_name in CALENDAR_STAGE_SUMMARY_ITEMS:
            frame = self._make_metric_card(stage_name, "0")
            self.stage_metric_cards[stage_name] = frame
            stage_stats_row.addWidget(frame)
        stage_stats_row.addStretch(1)
        root.addLayout(stage_stats_row)

        self._stage_bucket_filter = ""
        stage_filter_row = QHBoxLayout()
        stage_filter_row.setSpacing(8)
        stage_filter_row.addWidget(QLabel("Szybki filtr etapow:", self))
        self.stage_filter_group = QButtonGroup(self)
        self.stage_filter_group.setExclusive(True)
        self.stage_filter_buttons: dict[str, QPushButton] = {}
        for label, bucket in (("Wszystkie", ""), *[(name, name) for name in CALENDAR_STAGE_SUMMARY_ITEMS]):
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { padding: 4px 10px; border: 1px solid #cbd5e1; border-radius: 12px; background:#ffffff; }"
                "QPushButton:checked { background:#e2ecff; border-color:#7c9cff; font-weight:700; }"
            )
            button.clicked.connect(lambda checked=False, value=bucket: self._set_stage_bucket_filter(value))
            self.stage_filter_group.addButton(button)
            self.stage_filter_buttons[bucket] = button
            stage_filter_row.addWidget(button)
        self.stage_filter_buttons[""].setChecked(True)
        stage_filter_row.addStretch(1)
        root.addLayout(stage_filter_row)

        filters_box, filters_layout = self._make_panel(
            "Pulpit filtrowania",
            "Tutaj szybko zawezasz projekty po etapie, pracowniku, terminie i statusie.",
        )
        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po zamowieniu, kliencie lub pracowniku...")
        self.cb_status_filter = QComboBox(self)
        self.cb_status_filter.addItem("Wszystkie statusy")
        self.cb_stage_filter = QComboBox(self)
        self.cb_stage_filter.addItem("Wszystkie etapy")
        for stage in CALENDAR_STAGE_ITEMS:
            self.cb_stage_filter.addItem(stage)
        self.cb_worker_filter = QComboBox(self)
        self.cb_worker_filter.addItem("Wszyscy pracownicy")
        self.cb_time_filter = QComboBox(self)
        self.cb_time_filter.addItems(
            [
                "Wszystkie terminy",
                "Dzis",
                "Ten tydzien",
                "Po terminie",
                "Bez terminu",
            ]
        )
        self.btn_refresh = QPushButton("Odswiez", self)
        filters.addWidget(QLabel("Szukaj:", self))
        filters.addWidget(self.ed_search, 1)
        filters.addWidget(QLabel("Pracownik:", self))
        filters.addWidget(self.cb_worker_filter, 0)
        filters.addWidget(QLabel("Termin:", self))
        filters.addWidget(self.cb_time_filter, 0)
        filters.addWidget(QLabel("Status:", self))
        filters.addWidget(self.cb_status_filter, 0)
        filters.addWidget(QLabel("Etap:", self))
        filters.addWidget(self.cb_stage_filter, 0)
        filters.addWidget(self.btn_refresh, 0)
        filters_layout.addLayout(filters)
        filters_hint = QLabel(
            "Najwygodniej pracuje sie tu jak wchodzisz np. tylko w wyceny, tylko montaze albo tylko rzeczy po terminie."
        )
        filters_hint.setWordWrap(True)
        filters_hint.setStyleSheet("color:#6b7280;")
        filters_layout.addWidget(filters_hint)
        root.addWidget(filters_box, 0)

        self.tbl_orders = QTableWidget(0, 8, self)
        self.tbl_orders.setHorizontalHeaderLabels(
            ["Termin", "Etap", "Zamowienie", "Klient", "Status", "%", "Pracownik", "Notatka"]
        )
        self.tbl_orders.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_orders.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_orders.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_orders.setAlternatingRowColors(True)
        self.tbl_orders.verticalHeader().setVisible(False)
        header = self.tbl_orders.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl_orders, 1)

        editor, editor_layout = self._make_panel(
            "Plan etapu",
            "Tutaj zapisujesz, kto prowadzi zamowienie, na jakim jest etapie i jaki ma termin.",
        )

        self.lab_selected = QLabel("Wybierz zamowienie z listy.", editor)
        self.lab_selected.setWordWrap(True)
        editor_layout.addWidget(self.lab_selected)

        form = QFormLayout()
        self.cb_calendar_status = QComboBox(editor)
        self.cb_calendar_stage = QComboBox(editor)
        self.cb_calendar_status.addItem("")
        self.cb_calendar_stage.addItem("")
        for stage in CALENDAR_STAGE_ITEMS:
            self.cb_calendar_stage.addItem(stage)
        self.sp_calendar_progress = QSpinBox(editor)
        self.sp_calendar_progress.setRange(0, 100)
        self.sp_calendar_progress.setSuffix(" %")

        self.chk_no_date = QCheckBox("Bez terminu", editor)
        self.de_calendar_date = QDateEdit(editor)
        self.de_calendar_date.setCalendarPopup(True)
        self.de_calendar_date.setDisplayFormat("yyyy-MM-dd")
        self.de_calendar_date.setDate(QDate.currentDate())
        self.cb_calendar_worker = QComboBox(editor)
        self.cb_calendar_worker.setEditable(True)
        self.ed_calendar_note = QLineEdit(editor)
        self.ed_calendar_note.setPlaceholderText("Krotka notatka do etapu...")

        form.addRow("Status", self.cb_calendar_status)
        form.addRow("Postep", self.sp_calendar_progress)
        form.addRow("Etap", self.cb_calendar_stage)
        form.addRow("Termin", self.de_calendar_date)
        form.addRow("", self.chk_no_date)
        form.addRow("Pracownik", self.cb_calendar_worker)
        form.addRow("Notatka", self.ed_calendar_note)
        editor_layout.addLayout(form)

        actions = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz etap", editor)
        self.btn_clear = QPushButton("Wyczysc etap", editor)
        actions.addWidget(self.btn_save, 0)
        actions.addWidget(self.btn_clear, 0)
        actions.addStretch(1)
        editor_layout.addLayout(actions)

        self.lab_status = QLabel("", editor)
        self.lab_status.setWordWrap(True)
        editor_layout.addWidget(self.lab_status)
        root.addWidget(editor, 0)

        lower_panels = QHBoxLayout()
        lower_panels.setSpacing(12)

        workload_box, workload_layout = self._make_panel(
            "Obciazenie pracownikow",
            "Szybki widok: kto ma ile projektow, montazy i rzeczy po terminie.",
        )
        self.tbl_workload = QTableWidget(0, 4, workload_box)
        self.tbl_workload.setHorizontalHeaderLabels(["Pracownik", "Projekty", "Montaz", "Po terminie"])
        self.tbl_workload.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_workload.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_workload.setAlternatingRowColors(True)
        self.tbl_workload.verticalHeader().setVisible(False)
        workload_header = self.tbl_workload.horizontalHeader()
        workload_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        workload_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        workload_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        workload_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        workload_layout.addWidget(self.tbl_workload, 1)
        lower_panels.addWidget(workload_box, 1)

        history_box, history_layout = self._make_panel(
            "Historia statusu",
            "Tu wraca chronologia decyzji: z jakiego statusu na jaki, kiedy i przez kogo.",
        )
        self.tbl_status_history = QTableWidget(0, 4, history_box)
        self.tbl_status_history.setHorizontalHeaderLabels(["Data", "Z", "Na", "Kto"])
        self.tbl_status_history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_status_history.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_status_history.setAlternatingRowColors(True)
        self.tbl_status_history.verticalHeader().setVisible(False)
        history_header = self.tbl_status_history.horizontalHeader()
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.tbl_status_history, 1)
        self.lab_history_note = QLabel("Wybierz zamowienie z listy.", history_box)
        self.lab_history_note.setWordWrap(True)
        self.lab_history_note.setStyleSheet("color:#4b5563;")
        history_layout.addWidget(self.lab_history_note)
        lower_panels.addWidget(history_box, 1)

        root.addLayout(lower_panels, 0)

        self.ed_search.textChanged.connect(self._refresh_table)
        self.cb_worker_filter.currentTextChanged.connect(self._refresh_table)
        self.cb_time_filter.currentTextChanged.connect(self._refresh_table)
        self.cb_status_filter.currentTextChanged.connect(self._refresh_table)
        self.cb_stage_filter.currentTextChanged.connect(self._refresh_table)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.tbl_orders.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_clear.clicked.connect(self._on_clear)
        self.chk_no_date.toggled.connect(self.de_calendar_date.setDisabled)

        self._reload_worker_choices()
        self.refresh_data()

    def _make_panel(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(self)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #d8e2ec; border-radius: 12px; background: #fdfdfd; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        head = QLabel(title, frame)
        head.setStyleSheet("font-size:16px; font-weight:800; color:#122033;")
        layout.addWidget(head)
        if subtitle:
            sub = QLabel(subtitle, frame)
            sub.setWordWrap(True)
            sub.setStyleSheet("color:#64748b;")
            layout.addWidget(sub)
        return frame, layout

    def _make_metric_card(self, title: str, value: str) -> QFrame:
        frame = QFrame(self)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #d8e2ec; border-radius: 14px; background: #ffffff; min-width: 124px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet("color:#64748b; font-weight:700;")
        lab_value = QLabel(value, frame)
        lab_value.setStyleSheet("font-size: 28px; font-weight: 800; color:#0f172a;")
        lab_value.setObjectName("metricValue")
        layout.addWidget(lab_title)
        layout.addWidget(lab_value)
        frame.metric_value = lab_value  # type: ignore[attr-defined]
        return frame

    def _set_metric(self, frame: QFrame, value: int) -> None:
        label = getattr(frame, "metric_value", None)
        if isinstance(label, QLabel):
            label.setText(str(int(value)))

    def _reload_worker_choices(self) -> None:
        current = self.cb_calendar_worker.currentText().strip()
        current_filter = self.cb_worker_filter.currentText().strip()
        self.cb_calendar_worker.clear()
        self.cb_calendar_worker.addItem("")
        self.cb_worker_filter.clear()
        self.cb_worker_filter.addItem("Wszyscy pracownicy")
        for name in self._worker_store.list_names():
            self.cb_calendar_worker.addItem(name)
            self.cb_worker_filter.addItem(name)
        self.cb_calendar_worker.setCurrentText(current)
        if current_filter:
            self.cb_worker_filter.setCurrentText(current_filter)

    def refresh_data(self) -> None:
        orders = self._order_store.list_orders()
        statuses = sorted(
            {
                *CALENDAR_STATUS_ITEMS,
                *(str(order.status or "").strip() for order in orders if str(order.status or "").strip()),
            }
        )
        current_status = self.cb_status_filter.currentText()
        self.cb_status_filter.blockSignals(True)
        try:
            self.cb_status_filter.clear()
            self.cb_status_filter.addItem("Wszystkie statusy")
            for status in statuses:
                self.cb_status_filter.addItem(status)
            self.cb_status_filter.setCurrentText(current_status if current_status else "Wszystkie statusy")
        finally:
            self.cb_status_filter.blockSignals(False)
        current_editor_status = self.cb_calendar_status.currentText()
        self.cb_calendar_status.blockSignals(True)
        try:
            self.cb_calendar_status.clear()
            self.cb_calendar_status.addItem("")
            for status in statuses:
                self.cb_calendar_status.addItem(status)
            if current_editor_status:
                self.cb_calendar_status.setCurrentText(current_editor_status)
        finally:
            self.cb_calendar_status.blockSignals(False)
        self._refresh_table()

    def _filtered_orders(self) -> list[dict[str, object]]:
        search = self.ed_search.text().strip().lower()
        status_filter = self.cb_status_filter.currentText().strip()
        stage_filter = self.cb_stage_filter.currentText().strip()
        worker_filter = self.cb_worker_filter.currentText().strip()
        time_filter = self.cb_time_filter.currentText().strip()
        stage_bucket_filter = self._stage_bucket_filter
        today = date.today()
        week_start = today.fromordinal(today.toordinal() - today.weekday())
        week_end = today.fromordinal(week_start.toordinal() + 6)
        rows: list[dict[str, object]] = []
        for order in self._order_store.list_orders():
            order_status = str(order.status or "").strip()
            calendar_stage = str(getattr(order, "calendar_stage", "") or "").strip()
            worker_name = str(getattr(order, "worker_name", "") or "").strip()
            if status_filter and status_filter != "Wszystkie statusy" and order_status != status_filter:
                continue
            if stage_filter and stage_filter != "Wszystkie etapy" and calendar_stage != stage_filter:
                continue
            if worker_filter and worker_filter != "Wszyscy pracownicy" and worker_name != worker_filter:
                continue
            if stage_bucket_filter and not _matches_stage_bucket(order, calendar_stage, stage_bucket_filter):
                continue
            haystack = " ".join(
                [
                    str(order.code or ""),
                    str(order.client_name or ""),
                    str(order.worker_name or ""),
                    str(order.notes or ""),
                    str(getattr(order, "calendar_note", "") or ""),
                ]
            ).lower()
            if search and search not in haystack:
                continue
            calendar_date = str(getattr(order, "calendar_date", "") or "").strip()
            parsed_date = _parse_iso_date(calendar_date)
            if time_filter == "Dzis" and parsed_date != today:
                continue
            if time_filter == "Ten tydzien" and (parsed_date is None or parsed_date < week_start or parsed_date > week_end):
                continue
            if time_filter == "Po terminie" and (
                parsed_date is None
                or parsed_date >= today
                or str(getattr(order, "status", "") or "").strip().lower() == "zakonczone"
            ):
                continue
            if time_filter == "Bez terminu" and parsed_date is not None:
                continue
            rows.append(
                {
                    "order": order,
                    "calendar_date": calendar_date,
                    "calendar_stage": calendar_stage,
                    "calendar_note": str(getattr(order, "calendar_note", "") or "").strip(),
                    "parsed_date": parsed_date,
                }
            )
        rows.sort(
            key=lambda row: (
                row["parsed_date"] is None,
                row["parsed_date"] or date.max,
                str(getattr(row["order"], "code", "") or "").lower(),
            )
        )
        return rows

    def _refresh_metrics(self, rows: list[dict[str, object]]) -> None:
        today = date.today()
        scheduled = 0
        overdue = 0
        montage = 0
        stage_counts = {stage_name: 0 for stage_name in CALENDAR_STAGE_SUMMARY_ITEMS}
        for row in rows:
            order = row["order"]
            parsed_date = row["parsed_date"]
            calendar_stage = str(row["calendar_stage"] or "")
            if calendar_stage or parsed_date is not None:
                scheduled += 1
            if parsed_date is not None and parsed_date < today and str(getattr(order, "status", "") or "").strip().lower() != "zakonczone":
                overdue += 1
            if "montaz" in str(getattr(order, "status", "") or "").lower() or calendar_stage == "Montaz":
                montage += 1
            for stage_name in CALENDAR_STAGE_SUMMARY_ITEMS:
                if _matches_stage_bucket(order, calendar_stage, stage_name):
                    stage_counts[stage_name] += 1
        self._set_metric(self.lab_metric_total, len(rows))
        self._set_metric(self.lab_metric_scheduled, scheduled)
        self._set_metric(self.lab_metric_overdue, overdue)
        self._set_metric(self.lab_metric_montage, montage)
        for stage_name, count in stage_counts.items():
            self._set_metric(self.stage_metric_cards[stage_name], count)

    def _refresh_workload(self, rows: list[dict[str, object]]) -> None:
        today = date.today()
        worker_rows: dict[str, dict[str, int]] = {}
        for row in rows:
            order = row["order"]
            worker_name = str(getattr(order, "worker_name", "") or "").strip() or "[brak]"
            metrics = worker_rows.setdefault(worker_name, {"projects": 0, "montage": 0, "overdue": 0})
            metrics["projects"] += 1
            if "montaz" in str(getattr(order, "status", "") or "").lower() or str(row["calendar_stage"] or "") == "Montaz":
                metrics["montage"] += 1
            parsed_date = row["parsed_date"]
            if parsed_date is not None and parsed_date < today and str(getattr(order, "status", "") or "").strip().lower() != "zakonczone":
                metrics["overdue"] += 1

        ordered_workers = sorted(worker_rows.items(), key=lambda item: (item[0] == "[brak]", item[0].lower()))
        self.tbl_workload.setRowCount(0)
        for row_idx, (worker_name, metrics) in enumerate(ordered_workers):
            self.tbl_workload.insertRow(row_idx)
            values = [
                worker_name,
                str(metrics["projects"]),
                str(metrics["montage"]),
                str(metrics["overdue"]),
            ]
            for col, value in enumerate(values):
                self.tbl_workload.setItem(row_idx, col, QTableWidgetItem(value))

    def _refresh_table(self) -> None:
        self._rows = self._filtered_orders()
        self._refresh_metrics(self._rows)
        self._refresh_workload(self._rows)
        current_code = self._selected_order_code()
        self.tbl_orders.setRowCount(0)
        for row_idx, row in enumerate(self._rows):
            order = row["order"]
            self.tbl_orders.insertRow(row_idx)
            values = [
                str(row["calendar_date"] or "-"),
                str(row["calendar_stage"] or "-"),
                str(order.code or "-"),
                str(order.client_name or "-"),
                str(order.status or "-"),
                f'{int(round(float(getattr(order, "progress_percent", 0.0) or 0.0)))}%',
                str(order.worker_name or "-"),
                str(row["calendar_note"] or "-"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 2:
                    item.setData(Qt.ItemDataRole.UserRole, str(order.code or ""))
                self.tbl_orders.setItem(row_idx, col, item)
        if current_code:
            for row in range(self.tbl_orders.rowCount()):
                item = self.tbl_orders.item(row, 2)
                if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == current_code:
                    self.tbl_orders.selectRow(row)
                    break
        self._on_selection_changed()

    def _set_stage_bucket_filter(self, bucket: str) -> None:
        self._stage_bucket_filter = str(bucket or "")
        button = self.stage_filter_buttons.get(self._stage_bucket_filter)
        if button is not None:
            button.setChecked(True)
        self._refresh_table()

    def _selected_order_code(self) -> str:
        rows = self.tbl_orders.selectionModel().selectedRows() if self.tbl_orders.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_orders.item(int(rows[0].row()), 2)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _selected_order(self):
        code = self._selected_order_code()
        return self._order_store.get(code) if code else None

    def _on_selection_changed(self) -> None:
        order = self._selected_order()
        self._is_loading = True
        try:
            if order is None:
                self.lab_selected.setText("Wybierz zamowienie z listy.")
                self.cb_calendar_status.setCurrentIndex(0)
                self.sp_calendar_progress.setValue(0)
                self.cb_calendar_stage.setCurrentIndex(0)
                self.chk_no_date.setChecked(True)
                self.cb_calendar_worker.setCurrentText("")
                self.ed_calendar_note.clear()
                self.tbl_status_history.setRowCount(0)
                self.lab_history_note.setText("Wybierz zamowienie z listy.")
                return
            self.lab_selected.setText(
                f'Zamowienie: {order.code} | Klient: {order.client_name or "-"} | Status: {order.status or "-"} | {int(round(float(getattr(order, "progress_percent", 0.0) or 0.0)))}%'
            )
            status = str(getattr(order, "status", "") or "")
            idx_status = self.cb_calendar_status.findText(status)
            self.cb_calendar_status.setCurrentIndex(idx_status if idx_status >= 0 else 0)
            self.sp_calendar_progress.setValue(int(round(float(getattr(order, "progress_percent", 0.0) or 0.0))))
            stage = str(getattr(order, "calendar_stage", "") or "")
            idx = self.cb_calendar_stage.findText(stage)
            self.cb_calendar_stage.setCurrentIndex(idx if idx >= 0 else 0)
            raw_date = str(getattr(order, "calendar_date", "") or "").strip()
            parsed = _parse_iso_date(raw_date)
            self.chk_no_date.setChecked(parsed is None)
            if parsed is not None:
                self.de_calendar_date.setDate(QDate(parsed.year, parsed.month, parsed.day))
            self.cb_calendar_worker.setCurrentText(str(order.worker_name or ""))
            self.ed_calendar_note.setText(str(getattr(order, "calendar_note", "") or ""))
            self._refresh_status_history(order)
        finally:
            self._is_loading = False

    def _refresh_status_history(self, order) -> None:
        history = list(getattr(order, "status_history", []) or [])
        self.tbl_status_history.setRowCount(0)
        if not history:
            self.lab_history_note.setText("Brak zapisanej historii zmian statusu.")
            return
        for row_idx, entry in enumerate(reversed(history)):
            self.tbl_status_history.insertRow(row_idx)
            values = [
                str(entry.get("changed_at", "") or "-"),
                str(entry.get("from_status", "") or "-"),
                str(entry.get("to_status", "") or "-"),
                str(entry.get("changed_by", "") or "-"),
            ]
            for col, value in enumerate(values):
                self.tbl_status_history.setItem(row_idx, col, QTableWidgetItem(value))
        latest = history[-1]
        note = str(latest.get("note", "") or "").strip()
        self.lab_history_note.setText(note if note else "Ostatnia zmiana bez dodatkowej notatki.")

    def _on_save(self) -> None:
        if self._is_loading:
            return
        order = self._selected_order()
        if order is None:
            self._set_status("Wybierz zamowienie z listy.", ok=False)
            return
        new_status = str(self.cb_calendar_status.currentText().strip())
        new_progress = float(self.sp_calendar_progress.value())
        calendar_date = ""
        if not self.chk_no_date.isChecked():
            calendar_date = self.de_calendar_date.date().toString("yyyy-MM-dd")
        history = list(getattr(order, "status_history", []) or [])
        old_status = str(getattr(order, "status", "") or "").strip()
        if new_status and new_status != old_status:
            changed_by = str(self.cb_calendar_worker.currentText().strip() or getattr(order, "worker_name", "") or "Kalendarz")
            history.append(
                {
                    "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "from_status": old_status,
                    "to_status": new_status,
                    "changed_by": changed_by,
                    "note": str(self.ed_calendar_note.text().strip()),
                }
            )
        updated = replace(
            order,
            status=new_status or old_status,
            progress_percent=new_progress,
            worker_name=str(self.cb_calendar_worker.currentText().strip()),
            calendar_stage=str(self.cb_calendar_stage.currentText().strip()),
            calendar_date=calendar_date,
            calendar_note=str(self.ed_calendar_note.text().strip()),
            status_history=history,
        )
        result = self._order_store.overwrite(updated)
        self._refresh_table()
        self._set_status(result.message_pl, ok=result.ok)

    def _on_clear(self) -> None:
        order = self._selected_order()
        if order is None:
            self._set_status("Wybierz zamowienie z listy.", ok=False)
            return
        updated = replace(order, calendar_stage="", calendar_date="", calendar_note="")
        result = self._order_store.overwrite(updated)
        self._refresh_table()
        self._set_status("Wyczyszczono etap kalendarza." if result.ok else result.message_pl, ok=result.ok)

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
