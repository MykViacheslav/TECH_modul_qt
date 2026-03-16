from __future__ import annotations

from calendar import monthrange
from dataclasses import replace
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.worker_store_json import WorkerStoreJson


MONTH_ITEMS: tuple[tuple[int, str], ...] = (
    (1, "Styczen"),
    (2, "Luty"),
    (3, "Marzec"),
    (4, "Kwiecien"),
    (5, "Maj"),
    (6, "Czerwiec"),
    (7, "Lipiec"),
    (8, "Sierpien"),
    (9, "Wrzesien"),
    (10, "Pazdziernik"),
    (11, "Listopad"),
    (12, "Grudzien"),
)


def _parse_clock_value(value: str) -> tuple[int, int] | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace(",", ".").replace(";", ":")
    if ":" in normalized:
        left, right = normalized.split(":", 1)
    elif "." in normalized:
        left, right = normalized.split(".", 1)
    else:
        left, right = normalized, "00"
    try:
        hour = int(left)
        minute = int(right.ljust(2, "0")[:2])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour, minute


def _compute_hours(start_time: str, end_time: str, explicit_hours: str) -> float:
    explicit = str(explicit_hours or "").strip().replace(",", ".")
    if explicit:
        try:
            return max(float(explicit), 0.0)
        except ValueError:
            pass
    parsed_start = _parse_clock_value(start_time)
    parsed_end = _parse_clock_value(end_time)
    if parsed_start is None or parsed_end is None:
        return 0.0
    start_minutes = parsed_start[0] * 60 + parsed_start[1]
    end_minutes = parsed_end[0] * 60 + parsed_end[1]
    if end_minutes <= start_minutes:
        return 0.0
    return round((end_minutes - start_minutes) / 60.0, 2)


class TabCzasPracy(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        worker_store: WorkerStoreJson | None = None,
        work_time_store: WorkTimeStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._work_time_store = work_time_store if work_time_store is not None else WorkTimeStoreJson()
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("CZAS PRACY")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.5px;")
        root.addWidget(title)

        subtitle = QLabel(
            "Osobna karta do prowadzenia czasu pracy pracownikow, stawki godzinowej i miesiecznej tabeli godzin."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555555;")
        root.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        controls = QFrame(self)
        controls.setFrameShape(QFrame.Shape.StyledPanel)
        controls.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background: #fbfcfe; }")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(10)

        form = QFormLayout()
        self.cb_worker = QComboBox(self)
        self.cb_month = QComboBox(self)
        for month_value, month_label in MONTH_ITEMS:
            self.cb_month.addItem(month_label, month_value)
        self.sp_year = QSpinBox(self)
        self.sp_year.setRange(2020, 2100)
        self.sp_year.setValue(date.today().year)
        self.sp_hourly_rate = QDoubleSpinBox(self)
        self.sp_hourly_rate.setRange(0.0, 1000.0)
        self.sp_hourly_rate.setDecimals(2)
        self.sp_hourly_rate.setSingleStep(1.0)
        self.sp_hourly_rate.setSuffix(" PLN/h")
        form.addRow("Pracownik", self.cb_worker)
        form.addRow("Miesiac", self.cb_month)
        form.addRow("Rok", self.sp_year)
        form.addRow("Stawka godz.", self.sp_hourly_rate)
        controls_layout.addLayout(form)

        buttons = QHBoxLayout()
        self.btn_refresh = QPushButton("Wczytaj miesiac", self)
        self.btn_save_rate = QPushButton("Zapisz stawke", self)
        self.btn_save_sheet = QPushButton("Zapisz godziny", self)
        buttons.addWidget(self.btn_refresh)
        buttons.addWidget(self.btn_save_rate)
        buttons.addWidget(self.btn_save_sheet)
        buttons.addStretch(1)
        controls_layout.addLayout(buttons)

        self.lab_status = QLabel("", self)
        self.lab_status.setWordWrap(True)
        controls_layout.addWidget(self.lab_status)
        top_row.addWidget(controls, 1)

        summary = QFrame(self)
        summary.setFrameShape(QFrame.Shape.StyledPanel)
        summary.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background: #ffffff; }")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(10)
        self.lab_days = self._make_metric_card("Dni pracy", "0")
        self.lab_hours = self._make_metric_card("Godziny", "0.0")
        self.lab_cost = self._make_metric_card("Koszt miesiaca", "0.00 PLN")
        summary_layout.addWidget(self.lab_days, 0, 0)
        summary_layout.addWidget(self.lab_hours, 0, 1)
        summary_layout.addWidget(self.lab_cost, 1, 0, 1, 2)
        top_row.addWidget(summary, 1)

        root.addLayout(top_row)

        self.tbl_hours = QTableWidget(0, 7, self)
        self.tbl_hours.setHorizontalHeaderLabels(
            ["Dzien", "Data", "Od", "Do", "Godz.", "Projekt", "Notatka"]
        )
        self.tbl_hours.setAlternatingRowColors(True)
        self.tbl_hours.verticalHeader().setVisible(False)
        header = self.tbl_hours.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl_hours, 1)

        self.cb_worker.currentTextChanged.connect(self._load_selected_month)
        self.cb_month.currentIndexChanged.connect(self._load_selected_month)
        self.sp_year.valueChanged.connect(self._load_selected_month)
        self.btn_refresh.clicked.connect(self._load_selected_month)
        self.btn_save_rate.clicked.connect(self._save_hourly_rate)
        self.btn_save_sheet.clicked.connect(self._save_sheet)

        self._reload_workers()
        month_index = max(date.today().month - 1, 0)
        self.cb_month.setCurrentIndex(month_index)
        self._load_selected_month()

    def _make_metric_card(self, title: str, value: str) -> QFrame:
        frame = QFrame(self)
        frame.setStyleSheet("QFrame { border: 1px solid #d8e2ec; border-radius: 10px; background: #ffffff; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet("color:#64748b; font-weight:600;")
        lab_value = QLabel(value, frame)
        lab_value.setStyleSheet("font-size: 20px; font-weight: 800; color:#0f172a;")
        lab_value.setObjectName("metricValue")
        layout.addWidget(lab_title)
        layout.addWidget(lab_value)
        frame.metric_value = lab_value  # type: ignore[attr-defined]
        return frame

    def _set_metric(self, frame: QFrame, value: str) -> None:
        label = getattr(frame, "metric_value", None)
        if isinstance(label, QLabel):
            label.setText(value)

    def _reload_workers(self) -> None:
        current = self.cb_worker.currentText().strip()
        self.cb_worker.clear()
        self.cb_worker.addItem("")
        for worker in self._worker_store.list_workers():
            self.cb_worker.addItem(worker.name)
        self.cb_worker.setCurrentText(current)
        if not self.cb_worker.currentText().strip() and self.cb_worker.count() > 1:
            self.cb_worker.setCurrentIndex(1)

    def _selected_month(self) -> int:
        return int(self.cb_month.currentData() or 1)

    def _selected_year(self) -> int:
        return int(self.sp_year.value())

    def _load_selected_month(self) -> None:
        if self._is_loading:
            return
        self._is_loading = True
        try:
            worker_name = self.cb_worker.currentText().strip()
            month = self._selected_month()
            year = self._selected_year()
            worker = self._worker_store.get(worker_name) if worker_name else None
            self.sp_hourly_rate.setValue(float(getattr(worker, "hourly_rate", 0.0) or 0.0))
            self._fill_table(worker_name, year, month)
        finally:
            self._is_loading = False

    def _fill_table(self, worker_name: str, year: int, month: int) -> None:
        sheet = self._work_time_store.get_sheet(worker_name, year, month) if worker_name else WorkerMonthSheetDef(worker_name="", year=year, month=month)
        by_day = {int(entry.day): entry for entry in sheet.entries}
        days_in_month = monthrange(year, month)[1]
        self.tbl_hours.setRowCount(0)
        for day in range(1, days_in_month + 1):
            self.tbl_hours.insertRow(day - 1)
            date_iso = f"{year:04d}-{month:02d}-{day:02d}"
            entry = by_day.get(day, WorkTimeEntryDef(day=day, date_iso=date_iso))
            fixed_values = [str(day), date_iso]
            for col, value in enumerate(fixed_values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tbl_hours.setItem(day - 1, col, item)
            self.tbl_hours.setItem(day - 1, 2, QTableWidgetItem(entry.start_time))
            self.tbl_hours.setItem(day - 1, 3, QTableWidgetItem(entry.end_time))
            self.tbl_hours.setItem(day - 1, 4, QTableWidgetItem(f"{float(entry.hours or 0.0):.2f}" if float(entry.hours or 0.0) else ""))
            self.tbl_hours.setItem(day - 1, 5, QTableWidgetItem(entry.project_code))
            self.tbl_hours.setItem(day - 1, 6, QTableWidgetItem(entry.note))
        self._refresh_summary()

    def _row_text(self, row: int, column: int) -> str:
        item = self.tbl_hours.item(row, column)
        return str(item.text()).strip() if item is not None else ""

    def _collect_entries(self) -> list[WorkTimeEntryDef]:
        entries: list[WorkTimeEntryDef] = []
        for row in range(self.tbl_hours.rowCount()):
            start_time = self._row_text(row, 2)
            end_time = self._row_text(row, 3)
            hours_text = self._row_text(row, 4)
            project_code = self._row_text(row, 5)
            note = self._row_text(row, 6)
            if not any([start_time, end_time, hours_text, project_code, note]):
                continue
            hours_value = _compute_hours(start_time, end_time, hours_text)
            entries.append(
                WorkTimeEntryDef(
                    day=row + 1,
                    date_iso=self._row_text(row, 1),
                    start_time=start_time,
                    end_time=end_time,
                    hours=hours_value,
                    project_code=project_code,
                    note=note,
                )
            )
        return entries

    def _refresh_summary(self) -> None:
        entries = self._collect_entries()
        total_hours = round(sum(float(entry.hours or 0.0) for entry in entries), 2)
        days_worked = len([entry for entry in entries if float(entry.hours or 0.0) > 0.0 or entry.start_time or entry.end_time])
        total_cost = round(total_hours * float(self.sp_hourly_rate.value()), 2)
        self._set_metric(self.lab_days, str(days_worked))
        self._set_metric(self.lab_hours, f"{total_hours:.2f}")
        self._set_metric(self.lab_cost, f"{total_cost:.2f} PLN")

    def _save_hourly_rate(self) -> None:
        worker_name = self.cb_worker.currentText().strip()
        if not worker_name:
            self._set_status("Wybierz pracownika.", ok=False)
            return
        worker = self._worker_store.get(worker_name)
        if worker is None:
            self._set_status("Nie znaleziono pracownika w bazie.", ok=False)
            return
        updated = replace(worker, hourly_rate=float(self.sp_hourly_rate.value()))
        result = self._worker_store.overwrite(updated)
        self._refresh_summary()
        self._set_status(result.message_pl, ok=result.ok)

    def _save_sheet(self) -> None:
        worker_name = self.cb_worker.currentText().strip()
        if not worker_name:
            self._set_status("Wybierz pracownika.", ok=False)
            return
        entries = self._collect_entries()
        sheet = WorkerMonthSheetDef(
            worker_name=worker_name,
            year=self._selected_year(),
            month=self._selected_month(),
            entries=entries,
        )
        result = self._work_time_store.save_sheet(sheet)
        self._refresh_summary()
        self._set_status(result.message_pl, ok=result.ok)

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
