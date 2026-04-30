from __future__ import annotations

from calendar import monthrange
from dataclasses import replace
from datetime import date

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor
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
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.work_time_costing import compute_work_time_cost
from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef, new_entry_id, new_sheet_id
from src.domain.worker_models import WorkerDef
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.worker_store_json import WorkerStoreJson

TABLE_TEXT_STYLE = ""


MONTH_ITEMS: tuple[tuple[int, str], ...] = (
    (1,  "StyczeĹ„"),
    (2,  "Luty"),
    (3,  "Marzec"),
    (4,  "KwiecieĹ„"),
    (5,  "Maj"),
    (6,  "Czerwiec"),
    (7,  "Lipiec"),
    (8,  "SierpieĹ„"),
    (9,  "WrzesieĹ„"),
    (10, "PaĹşdziernik"),
    (11, "Listopad"),
    (12, "GrudzieĹ„"),
)

PAY_MODE_ITEMS: tuple[str, ...] = ("Godzinowa", "Dniowka")

WORK_TYPE_ITEMS: tuple[str, ...] = (
    "",
    "Projekt / wycena",
    "Produkcja",
    "MontaĹĽ",
    "Praca na miejscu",
    "Lakiernia",
    "Delegacja / wyjazd",
    "Zakup materiaĹ‚Ăłw",
    "BHP / szkolenie",
    "Urlop",
    "Inne",
)

_DAY_NAMES = ("Pn", "Wt", "Ĺšr", "Cz", "Pt", "So", "Nd")

_COLOR_WEEKEND   = QColor("#f0f4ff")   # sobota / niedziela â€“ jasnoniebieski
_COLOR_SATURDAY  = QColor("#e8f0fe")
_COLOR_SUNDAY    = QColor("#fdecea")   # niedziela â€“ delikatny rĂłĹĽowy
_COLOR_FILLED    = QColor("#f0fdf4")   # wiersz z wpisanym rodzajem â€“ zielonkawy

# â”€â”€ Kolumny tabeli â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
COL_DAY    = 0
COL_DATE   = 1
COL_TYPE   = 2
COL_FROM   = 3
COL_TO     = 4
COL_HOURS  = 5
COL_OT     = 6
COL_EXTRA  = 7
COL_PROJ   = 8
COL_NOTE   = 9


# ---------------------------------------------------------------------------
# Delegate â€“ ComboBox w kolumnie "Rodzaj"
# ---------------------------------------------------------------------------

class _WorkTypeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index: QModelIndex):  # type: ignore[override]
        cb = QComboBox(parent)
        for item in WORK_TYPE_ITEMS:
            cb.addItem(item)
        return cb

    def setEditorData(self, editor, index: QModelIndex) -> None:  # type: ignore[override]
        value = str(index.data(Qt.ItemDataRole.EditRole) or "")
        idx = editor.findText(value)
        editor.setCurrentIndex(idx if idx >= 0 else 0)

    def setModelData(self, editor, model, index: QModelIndex) -> None:  # type: ignore[override]
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index: QModelIndex) -> None:  # type: ignore[override]
        editor.setGeometry(option.rect)


# ---------------------------------------------------------------------------
# Pomocnicze parsowanie czasu
# ---------------------------------------------------------------------------

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


def _format_pln(value: float) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    return f"{amount:.2f} PLN"


# ---------------------------------------------------------------------------
# GĹ‚Ăłwna zakĹ‚adka
# ---------------------------------------------------------------------------

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
            "MiesiÄ™czne zestawienie godzin pracy. Wybierz pracownika i miesiÄ…c â€” "
            "tabela pokazuje wszystkie dni z moĹĽliwoĹ›ciÄ… wpisania godzin, rodzaju pracy i projektu."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: palette(text);")
        root.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # â”€â”€ Panel lewĂ˝: Plan miesiÄ…ca â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        controls, controls_layout = self._make_panel(
            "Plan miesiÄ…ca",
            "Pracownik, okres i stawki rozliczeniowe.",
        )

        period_title = QLabel("Okres i pracownik", controls)
        period_title.setStyleSheet("font-weight:700; color:#0f172a;")
        controls_layout.addWidget(period_title)

        form = QFormLayout()
        self.cb_worker = QComboBox(self)
        self.cb_month = QComboBox(self)
        for month_value, month_label in MONTH_ITEMS:
            self.cb_month.addItem(month_label, month_value)
        self.sp_year = QSpinBox(self)
        self.sp_year.setRange(2020, 2100)
        self.sp_year.setValue(date.today().year)
        form.addRow("Pracownik", self.cb_worker)
        form.addRow("MiesiÄ…c", self.cb_month)
        form.addRow("Rok", self.sp_year)
        controls_layout.addLayout(form)

        buttons = QHBoxLayout()
        self.btn_refresh = QPushButton("Wczytaj miesiÄ…c", self)
        buttons.addWidget(self.btn_refresh)
        buttons.addStretch(1)
        controls_layout.addLayout(buttons)

        # Stawki
        rates_title = QLabel("Rozliczenie i dodatki", controls)
        rates_title.setStyleSheet("font-weight:700; color:#0f172a; margin-top:6px;")
        controls_layout.addWidget(rates_title)

        self.cb_pay_mode = QComboBox(self)
        for item in PAY_MODE_ITEMS:
            self.cb_pay_mode.addItem(item)
        self.sp_hourly_rate = QDoubleSpinBox(self)
        self.sp_hourly_rate.setRange(0.0, 1000.0)
        self.sp_hourly_rate.setDecimals(2)
        self.sp_hourly_rate.setSingleStep(1.0)
        self.sp_hourly_rate.setSuffix(" zĹ‚/h")
        self.sp_daily_rate = QDoubleSpinBox(self)
        self.sp_daily_rate.setRange(0.0, 5000.0)
        self.sp_daily_rate.setDecimals(2)
        self.sp_daily_rate.setSingleStep(10.0)
        self.sp_daily_rate.setSuffix(" zĹ‚/dzieĹ„")
        self.sp_overtime_multiplier = QDoubleSpinBox(self)
        self.sp_overtime_multiplier.setRange(0.0, 5.0)
        self.sp_overtime_multiplier.setDecimals(2)
        self.sp_overtime_multiplier.setSingleStep(0.1)
        self.sp_overtime_multiplier.setValue(1.0)
        self.sp_delegation_day_addon = QDoubleSpinBox(self)
        self.sp_delegation_day_addon.setRange(0.0, 5000.0)
        self.sp_delegation_day_addon.setDecimals(2)
        self.sp_delegation_day_addon.setSingleStep(10.0)
        self.sp_delegation_day_addon.setSuffix(" zĹ‚/dzieĹ„")
        self.sp_montage_hour_addon = QDoubleSpinBox(self)
        self.sp_montage_hour_addon.setRange(0.0, 1000.0)
        self.sp_montage_hour_addon.setDecimals(2)
        self.sp_montage_hour_addon.setSingleStep(1.0)
        self.sp_montage_hour_addon.setSuffix(" zĹ‚/h")
        self.sp_onsite_hour_addon = QDoubleSpinBox(self)
        self.sp_onsite_hour_addon.setRange(0.0, 1000.0)
        self.sp_onsite_hour_addon.setDecimals(2)
        self.sp_onsite_hour_addon.setSingleStep(1.0)
        self.sp_onsite_hour_addon.setSuffix(" zĹ‚/h")
        self.sp_lacquer_hour_addon = QDoubleSpinBox(self)
        self.sp_lacquer_hour_addon.setRange(0.0, 1000.0)
        self.sp_lacquer_hour_addon.setDecimals(2)
        self.sp_lacquer_hour_addon.setSingleStep(1.0)
        self.sp_lacquer_hour_addon.setSuffix(" zĹ‚/h")

        rates_form = QFormLayout()
        rates_form.addRow("Tryb rozlicz.", self.cb_pay_mode)
        rates_form.addRow("Stawka godz.", self.sp_hourly_rate)
        rates_form.addRow("DniĂłwka", self.sp_daily_rate)
        rates_form.addRow("Nadgodz. Ă—", self.sp_overtime_multiplier)
        rates_form.addRow("Delegacja / dzieĹ„", self.sp_delegation_day_addon)
        rates_form.addRow("MontaĹĽ / godz.", self.sp_montage_hour_addon)
        rates_form.addRow("Na miejscu / godz.", self.sp_onsite_hour_addon)
        rates_form.addRow("Lakiernia / godz.", self.sp_lacquer_hour_addon)
        controls_layout.addLayout(rates_form)

        action_title = QLabel("Zapis", controls)
        action_title.setStyleSheet("font-weight:700; color:#0f172a; margin-top:6px;")
        controls_layout.addWidget(action_title)

        action_buttons = QHBoxLayout()
        self.btn_save_rate = QPushButton("Zapisz stawkÄ™", self)
        self.btn_save_sheet = QPushButton("Zapisz godziny", self)
        action_buttons.addWidget(self.btn_save_rate)
        action_buttons.addWidget(self.btn_save_sheet)
        action_buttons.addStretch(1)
        controls_layout.addLayout(action_buttons)

        self.lab_status = QLabel("", self)
        self.lab_status.setWordWrap(True)
        controls_layout.addWidget(self.lab_status)
        controls_layout.addStretch(1)
        top_row.addWidget(controls, 1)

        # â”€â”€ Panel prawy: Podsumowanie miesiÄ…ca â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        summary, summary_layout = self._make_panel(
            "Podsumowanie miesiÄ…ca",
            "Koszt pracownika z wybranego miesiÄ…ca Ĺ‚Ä…cznie z nadgodzinami i dodatkami.",
        )
        summary_grid = QGridLayout()
        summary_grid.setSpacing(10)
        self.lab_days     = self._make_metric_card("Dni pracy",      "0")
        self.lab_hours    = self._make_metric_card("Godziny",        "0.0")
        self.lab_overtime = self._make_metric_card("Nadgodziny",     "0.0")
        self.lab_cost     = self._make_metric_card("Koszt miesiÄ…ca", _format_pln(0.0))
        summary_grid.addWidget(self.lab_days,     0, 0)
        summary_grid.addWidget(self.lab_hours,    0, 1)
        summary_grid.addWidget(self.lab_overtime, 1, 0)
        summary_grid.addWidget(self.lab_cost,     1, 1)
        summary_layout.addLayout(summary_grid)

        self.lab_breakdown = QLabel("", self)
        self.lab_breakdown.setWordWrap(True)
        self.lab_breakdown.setStyleSheet("color:#94a3b8; font-size: 12px;")
        summary_layout.addWidget(self.lab_breakdown)

        # legenda kolorĂłw
        legend_row = QHBoxLayout()
        legend_row.setSpacing(8)
        for color, label in (
            (_COLOR_FILLED,  "DzieĹ„ z pracÄ…"),
            (_COLOR_SATURDAY, "Sobota"),
            (_COLOR_SUNDAY,   "Niedziela"),
        ):
            dot = QLabel("â– ")
            dot.setStyleSheet(f"color: {color.name()}; font-size: 18px;")
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
            legend_row.addWidget(dot)
            legend_row.addWidget(lbl)
        legend_row.addStretch(1)
        summary_layout.addLayout(legend_row)
        summary_layout.addStretch(1)
        top_row.addWidget(summary, 1)

        root.addLayout(top_row)

        # â”€â”€ Tabela godzin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sheet_box, sheet_layout = self._make_panel(
            "Tabela miesiÄ…ca",
            "Kliknij komĂłrkÄ™ Rodzaj i wybierz typ pracy z listy. "
            "Wpisz Od/Do (np. 7:00 / 15:30) â€” godziny obliczÄ… siÄ™ automatycznie.",
        )

        self.tbl_hours = QTableWidget(0, 10, self)
        self.tbl_hours.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_hours.setHorizontalHeaderLabels(
            ["DzieĹ„", "Data", "Rodzaj pracy", "Od", "Do", "Godz.", "Nadg.", "Dodatek zĹ‚", "Projekt", "Notatka"]
        )
        self.tbl_hours.setAlternatingRowColors(False)
        self.tbl_hours.verticalHeader().setVisible(False)
        self.tbl_hours.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        header = self.tbl_hours.horizontalHeader()
        header.setSectionResizeMode(COL_DAY,   QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_DATE,  QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_TYPE,  QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_FROM,  QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_TO,    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_HOURS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_OT,    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_EXTRA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PROJ,  QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NOTE,  QHeaderView.ResizeMode.Stretch)
        header.resizeSection(COL_TYPE, 160)

        # Delegate dla kolumny Rodzaj
        self._type_delegate = _WorkTypeDelegate(self.tbl_hours)
        self.tbl_hours.setItemDelegateForColumn(COL_TYPE, self._type_delegate)

        # Auto-refresh godzin po zmianie Od/Do
        self.tbl_hours.cellChanged.connect(self._on_cell_changed)

        sheet_layout.addWidget(self.tbl_hours, 1)
        root.addWidget(sheet_box, 1)

        # â”€â”€ Zestawienie projektow: planowane vs realne â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        proj_box, proj_layout = self._make_panel(
            "Zestawienie projektow â€” planowane vs realne",
            "Godziny zarejestrowane w tym miesiacu z podzialem na kody projektow."
            " W kolumnie 'Plan h' wpisz planowane godziny â€” tabela policzy roznice.",
        )
        proj_hdr_row = QHBoxLayout()
        proj_hdr_row.setSpacing(8)
        self.btn_proj_refresh = QPushButton("Odswiez", self)
        self.btn_proj_refresh.setMaximumWidth(110)
        proj_hdr_row.addStretch(1)
        proj_hdr_row.addWidget(self.btn_proj_refresh)
        proj_layout.addLayout(proj_hdr_row)

        self.tbl_proj = QTableWidget(0, 6, self)
        self.tbl_proj.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_proj.setHorizontalHeaderLabels(
            ["Projekt / kod", "Typ pracy", "Realne h", "Plan h", "Roznica h", "Koszt zl"]
        )
        self.tbl_proj.setAlternatingRowColors(True)
        self.tbl_proj.verticalHeader().setVisible(False)
        self.tbl_proj.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        proj_hdr = self.tbl_proj.horizontalHeader()
        proj_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        proj_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        proj_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        proj_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        proj_hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        proj_hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_proj.setMinimumHeight(140)
        self.tbl_proj.setMaximumHeight(260)
        # kolumna Plan h jest edytowalna
        self.tbl_proj.cellChanged.connect(self._on_proj_plan_changed)
        proj_layout.addWidget(self.tbl_proj, 1)

        self.lab_proj_total = QLabel("Lacznie: 0.0 h  |  koszt: 0.00 zl", self)
        self.lab_proj_total.setStyleSheet("font-weight:700; color:#0f172a; font-size:12px;")
        proj_layout.addWidget(self.lab_proj_total)
        root.addWidget(proj_box)

        # â”€â”€ przechowuje plan [projekt][typ] -> float â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._proj_plan_hours: dict[str, float] = {}

        # PoĹ‚Ä…czenia sygnaĹ‚Ăłw
        self.cb_worker.currentTextChanged.connect(self._load_selected_month)
        self.cb_month.currentIndexChanged.connect(self._load_selected_month)
        self.sp_year.valueChanged.connect(self._load_selected_month)
        self.btn_refresh.clicked.connect(self._load_selected_month)
        self.btn_proj_refresh.clicked.connect(self._refresh_proj_table)
        self.btn_save_rate.clicked.connect(self._save_hourly_rate)
        self.btn_save_sheet.clicked.connect(self._save_sheet)
        self.cb_pay_mode.currentTextChanged.connect(lambda _: self._refresh_summary())
        self.sp_hourly_rate.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_daily_rate.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_overtime_multiplier.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_delegation_day_addon.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_montage_hour_addon.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_onsite_hour_addon.valueChanged.connect(lambda _: self._refresh_summary())
        self.sp_lacquer_hour_addon.valueChanged.connect(lambda _: self._refresh_summary())

        self._reload_workers()
        month_index = max(date.today().month - 1, 0)
        self.cb_month.setCurrentIndex(month_index)
        self._load_selected_month()

    # ------------------------------------------------------------------
    # Pomocnicze widgety
    # ------------------------------------------------------------------

    def _make_panel(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(self); frame.setProperty("uiCard", True)
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
            sub.setStyleSheet("color:#64748b; font-size: 12px;")
            layout.addWidget(sub)
        return frame, layout

    def _make_metric_card(self, title: str, value: str) -> QFrame:
        frame = QFrame(self); frame.setProperty("uiCard", True)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #d8e2ec; border-radius: 14px; background: transparent; min-width: 150px; }"
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

    def _set_metric(self, frame: QFrame, value: str) -> None:
        label = getattr(frame, "metric_value", None)
        if isinstance(label, QLabel):
            label.setText(value)

    # ------------------------------------------------------------------
    # Dane pracownikĂłw
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Ĺadowanie miesiÄ…ca
    # ------------------------------------------------------------------

    def _load_selected_month(self) -> None:
        if self._is_loading:
            return
        self._is_loading = True
        try:
            worker_name = self.cb_worker.currentText().strip()
            month = self._selected_month()
            year = self._selected_year()
            worker = self._worker_store.get(worker_name) if worker_name else None
            self.cb_pay_mode.setCurrentText(str(getattr(worker, "pay_mode", "Godzinowa") or "Godzinowa"))
            self.sp_hourly_rate.setValue(float(getattr(worker, "hourly_rate", 0.0) or 0.0))
            self.sp_daily_rate.setValue(float(getattr(worker, "daily_rate", 0.0) or 0.0))
            self.sp_overtime_multiplier.setValue(float(getattr(worker, "overtime_multiplier", 1.0) or 1.0))
            self.sp_delegation_day_addon.setValue(float(getattr(worker, "delegation_day_addon_pln", 0.0) or 0.0))
            self.sp_montage_hour_addon.setValue(float(getattr(worker, "montage_hour_addon_pln", 0.0) or 0.0))
            self.sp_onsite_hour_addon.setValue(float(getattr(worker, "onsite_hour_addon_pln", 0.0) or 0.0))
            self.sp_lacquer_hour_addon.setValue(float(getattr(worker, "lacquer_hour_addon_pln", 0.0) or 0.0))
            self._fill_table(worker_name, year, month)
        finally:
            self._is_loading = False

    # ------------------------------------------------------------------
    # Tabela
    # ------------------------------------------------------------------

    def _fill_table(self, worker_name: str, year: int, month: int) -> None:
        self.tbl_hours.blockSignals(True)
        try:
            sheet = (
                self._work_time_store.get_sheet(worker_name, year, month)
                if worker_name
                else WorkerMonthSheetDef(sheet_id=new_sheet_id(), worker_name="", year=year, month=month)
            )
            by_day = {int(entry.day): entry for entry in sheet.entries}
            days_in_month = monthrange(year, month)[1]
            self.tbl_hours.setRowCount(0)

            for day in range(1, days_in_month + 1):
                row = day - 1
                self.tbl_hours.insertRow(row)

                date_iso = f"{year:04d}-{month:02d}-{day:02d}"
                weekday = date(year, month, day).weekday()   # 0=Pn â€¦ 6=Nd
                day_name = _DAY_NAMES[weekday]
                entry = by_day.get(day, WorkTimeEntryDef(entry_id=new_entry_id(), day=day, date_iso=date_iso))

                # Kolumny tylko do odczytu
                day_item = QTableWidgetItem(f"{day_name} {day}")
                day_item.setFlags(day_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                day_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_hours.setItem(row, COL_DAY, day_item)

                date_item = QTableWidgetItem(date_iso)
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tbl_hours.setItem(row, COL_DATE, date_item)

                # Edytowalne kolumny
                self.tbl_hours.setItem(row, COL_TYPE,  QTableWidgetItem(entry.work_type))
                self.tbl_hours.setItem(row, COL_FROM,  QTableWidgetItem(entry.start_time))
                self.tbl_hours.setItem(row, COL_TO,    QTableWidgetItem(entry.end_time))
                hours = float(entry.hours or 0.0)
                self.tbl_hours.setItem(row, COL_HOURS, QTableWidgetItem(
                    f"{hours:.2f}" if hours else ""
                ))
                ot = float(entry.overtime_hours or 0.0)
                self.tbl_hours.setItem(row, COL_OT,   QTableWidgetItem(
                    f"{ot:.2f}" if ot else ""
                ))
                ex = float(entry.extra_pay or 0.0)
                self.tbl_hours.setItem(row, COL_EXTRA, QTableWidgetItem(
                    f"{ex:.2f}" if ex else ""
                ))
                self.tbl_hours.setItem(row, COL_PROJ,  QTableWidgetItem(entry.project_code))
                self.tbl_hours.setItem(row, COL_NOTE,  QTableWidgetItem(entry.note))

                # Kolorowanie wierszy
                self._color_row(row, weekday, bool(entry.work_type))

        finally:
            self.tbl_hours.blockSignals(False)
        self._refresh_summary()

    def _color_row(self, row: int, weekday: int, has_work: bool) -> None:
        """Koloruje wiersz zaleĹĽnie od dnia tygodnia i obecnoĹ›ci danych."""
        if weekday == 6:       # Niedziela
            bg = _COLOR_SUNDAY
        elif weekday == 5:     # Sobota
            bg = _COLOR_SATURDAY
        elif has_work:
            bg = _COLOR_FILLED
        else:
            bg = QColor("#ffffff")

        for col in range(self.tbl_hours.columnCount()):
            item = self.tbl_hours.item(row, col)
            if item is not None:
                item.setBackground(bg)

    def _on_cell_changed(self, row: int, col: int) -> None:
        """Po zmianie Od/Do przelicz godziny i odĹ›wieĹĽ kolory."""
        if self._is_loading:
            return
        if col in (COL_FROM, COL_TO):
            start = self._row_text(row, COL_FROM)
            end   = self._row_text(row, COL_TO)
            hours = _compute_hours(start, end, "")
            self.tbl_hours.blockSignals(True)
            try:
                item = self.tbl_hours.item(row, COL_HOURS)
                if item is not None:
                    item.setText(f"{hours:.2f}" if hours else "")
                else:
                    self.tbl_hours.setItem(row, COL_HOURS, QTableWidgetItem(f"{hours:.2f}" if hours else ""))
            finally:
                self.tbl_hours.blockSignals(False)

        # OdĹ›wieĹĽ kolor wiersza
        try:
            year  = self._selected_year()
            month = self._selected_month()
            day   = row + 1
            weekday = date(year, month, day).weekday()
        except Exception:
            weekday = 0

        has_work = bool(self._row_text(row, COL_TYPE))
        self._color_row(row, weekday, has_work)
        self._refresh_summary()

    # ------------------------------------------------------------------
    # Odczyt danych z tabeli
    # ------------------------------------------------------------------

    def _row_text(self, row: int, column: int) -> str:
        item = self.tbl_hours.item(row, column)
        return str(item.text()).strip() if item is not None else ""

    def _collect_entries(self) -> list[WorkTimeEntryDef]:
        entries: list[WorkTimeEntryDef] = []
        for row in range(self.tbl_hours.rowCount()):
            work_type   = self._row_text(row, COL_TYPE)
            start_time  = self._row_text(row, COL_FROM)
            end_time    = self._row_text(row, COL_TO)
            hours_text  = self._row_text(row, COL_HOURS)
            ot_text     = self._row_text(row, COL_OT).replace(",", ".")
            extra_text  = self._row_text(row, COL_EXTRA).replace(",", ".")
            project_code = self._row_text(row, COL_PROJ)
            note        = self._row_text(row, COL_NOTE)

            if not any([work_type, start_time, end_time, hours_text, ot_text, extra_text, project_code, note]):
                continue

            hours_value = _compute_hours(start_time, end_time, hours_text)
            try:
                ot_value = max(float(ot_text), 0.0) if ot_text else 0.0
            except ValueError:
                ot_value = 0.0
            try:
                extra_value = float(extra_text) if extra_text else 0.0
            except ValueError:
                extra_value = 0.0

            entries.append(WorkTimeEntryDef(
                entry_id=new_entry_id(),
                day=row + 1,
                date_iso=self._row_text(row, COL_DATE),
                work_type=work_type,
                start_time=start_time,
                end_time=end_time,
                hours=hours_value,
                overtime_hours=ot_value,
                extra_pay=extra_value,
                project_code=project_code,
                note=note,
            ))
        return entries

    # ------------------------------------------------------------------
    # Podsumowanie
    # ------------------------------------------------------------------

    def _refresh_summary(self) -> None:
        entries = self._collect_entries()
        worker_name = self.cb_worker.currentText().strip()
        sheet = WorkerMonthSheetDef(
            sheet_id=new_sheet_id(),
            worker_name=worker_name,
            year=self._selected_year(),
            month=self._selected_month(),
            entries=entries,
        )
        worker = WorkerDef(
            name=worker_name,
            pay_mode=self.cb_pay_mode.currentText().strip() or "Godzinowa",
            hourly_rate=float(self.sp_hourly_rate.value()),
            daily_rate=float(self.sp_daily_rate.value()),
            overtime_multiplier=float(self.sp_overtime_multiplier.value()),
            delegation_day_addon_pln=float(self.sp_delegation_day_addon.value()),
            montage_hour_addon_pln=float(self.sp_montage_hour_addon.value()),
            onsite_hour_addon_pln=float(self.sp_onsite_hour_addon.value()),
            lacquer_hour_addon_pln=float(self.sp_lacquer_hour_addon.value()),
        )
        breakdown = compute_work_time_cost([sheet], {worker_name: worker})
        self._set_metric(self.lab_days,     str(breakdown.tracked_days))
        self._set_metric(self.lab_hours,    f"{breakdown.total_hours:.2f}")
        self._set_metric(self.lab_overtime, f"{breakdown.overtime_hours:.2f}")
        self._set_metric(self.lab_cost, _format_pln(breakdown.total_cost))
        self.lab_breakdown.setText(
            f"Baza: {_format_pln(breakdown.base_total)}  |  "
            f"Nadgodziny: {_format_pln(breakdown.overtime_total)}  |  "
            f"Dodatki etapow: {_format_pln(breakdown.stage_extra_total)}  |  "
            f"Dodatki reczne: {_format_pln(breakdown.manual_extra_total)}"
        )
        self._refresh_proj_table()

    # ------------------------------------------------------------------
    # Zapis
    # ------------------------------------------------------------------

    def _save_hourly_rate(self) -> None:
        worker_name = self.cb_worker.currentText().strip()
        if not worker_name:
            self._set_status("Wybierz pracownika.", ok=False)
            return
        worker = self._worker_store.get(worker_name)
        if worker is None:
            self._set_status("Nie znaleziono pracownika w bazie.", ok=False)
            return
        updated = replace(
            worker,
            pay_mode=self.cb_pay_mode.currentText().strip() or "Godzinowa",
            hourly_rate=float(self.sp_hourly_rate.value()),
            daily_rate=float(self.sp_daily_rate.value()),
            overtime_multiplier=float(self.sp_overtime_multiplier.value()),
            delegation_day_addon_pln=float(self.sp_delegation_day_addon.value()),
            montage_hour_addon_pln=float(self.sp_montage_hour_addon.value()),
            onsite_hour_addon_pln=float(self.sp_onsite_hour_addon.value()),
            lacquer_hour_addon_pln=float(self.sp_lacquer_hour_addon.value()),
        )
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
            sheet_id=new_sheet_id(),
            worker_name=worker_name,
            year=self._selected_year(),
            month=self._selected_month(),
            entries=entries,
        )
        result = self._work_time_store.save_sheet(sheet)
        self._refresh_summary()
        self._set_status(result.message_pl, ok=result.ok)

    # ------------------------------------------------------------------
    # Zestawienie projektow: planowane vs realne
    # ------------------------------------------------------------------

    def _refresh_proj_table(self) -> None:
        """Grupuje wpisy z tabeli godzin po kodzie projektu + typie pracy."""
        if not hasattr(self, "tbl_proj"):
            return
        entries = self._collect_entries()

        # hourly cost for a single hour â€” simplified: use hourly_rate
        hourly = float(self.sp_hourly_rate.value()) if hasattr(self, "sp_hourly_rate") else 0.0

        # agreguj: (projekt, typ_pracy) -> realne_godziny
        agg: dict[tuple[str, str], float] = {}
        for e in entries:
            code = str(e.project_code or "").strip() or "(brak kodu)"
            wtype = str(e.work_type or "").strip() or "â€”"
            key = (code, wtype)
            agg[key] = agg.get(key, 0.0) + float(e.hours or 0.0)

        self.tbl_proj.blockSignals(True)
        self.tbl_proj.setRowCount(0)
        total_real = 0.0
        total_cost = 0.0
        for (code, wtype), real_h in sorted(agg.items()):
            r = self.tbl_proj.rowCount()
            self.tbl_proj.insertRow(r)
            plan_h = self._proj_plan_hours.get(f"{code}|{wtype}", 0.0)
            diff_h = real_h - plan_h
            cost = real_h * hourly
            total_real += real_h
            total_cost += cost

            self.tbl_proj.setItem(r, 0, QTableWidgetItem(code))
            self.tbl_proj.setItem(r, 1, QTableWidgetItem(wtype))

            item_real = QTableWidgetItem(f"{real_h:.2f}")
            item_real.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_real.setFlags(item_real.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_proj.setItem(r, 2, item_real)

            item_plan = QTableWidgetItem(f"{plan_h:.2f}" if plan_h else "")
            item_plan.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_proj.setItem(r, 3, item_plan)

            item_diff = QTableWidgetItem(f"{diff_h:+.2f}" if plan_h else "â€”")
            item_diff.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_diff.setFlags(item_diff.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if plan_h:
                color = QColor("#15803d") if diff_h <= 0 else QColor("#b91c1c")
                item_diff.setForeground(color)
            self.tbl_proj.setItem(r, 4, item_diff)

            item_cost = QTableWidgetItem(f"{cost:,.2f}")
            item_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_cost.setFlags(item_cost.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_proj.setItem(r, 5, item_cost)

        self.tbl_proj.blockSignals(False)
        self.lab_proj_total.setText(
            f"Lacznie: {total_real:.2f} h  |  koszt: {total_cost:,.2f} zl"
        )

    def _on_proj_plan_changed(self, row: int, col: int) -> None:
        """Zapisuje reczne wpisanie planowanych godzin i odswieza roznice."""
        if col != 3:
            return
        item_code = self.tbl_proj.item(row, 0)
        item_type = self.tbl_proj.item(row, 1)
        item_plan = self.tbl_proj.item(row, 3)
        if item_code is None or item_plan is None:
            return
        code = item_code.text().strip()
        wtype = (item_type.text().strip() if item_type else "")
        raw = item_plan.text().replace(",", ".").strip()
        try:
            plan_h = max(0.0, float(raw)) if raw else 0.0
        except ValueError:
            plan_h = 0.0
        self._proj_plan_hours[f"{code}|{wtype}"] = plan_h
        self._refresh_proj_table()

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color}; font-weight: 600;")
        self.lab_status.setText(str(message or ""))

