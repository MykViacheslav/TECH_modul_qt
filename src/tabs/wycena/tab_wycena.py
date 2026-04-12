from __future__ import annotations

import base64
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QFileDialog,
    QMessageBox,
)

from src.app.app_settings import load_drawing_settings, load_ui_theme_settings
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.domain.project_model import ProjectModel
from src.domain.work_time_costing import WorkTimeCostBreakdown, compute_work_time_cost
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.data_paths import data_dir
from src.storage.order_store_json import OrderStoreJson
from src.storage.producer_library_store_json import ProducerLibraryStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.quote_pricing_store_json import QuotePricingStoreJson
from src.storage.quote_pricing_preset_store_json import QuotePricingPresetStoreJson
from src.storage.receptura_store_json import RecepturaStoreJson
from src.storage.safe_json_io import write_json_atomic
from src.services.quote_pricing_service import QuotePricingService
from src.services.receptura_bridge_service import build_quick_quote_entry_from_receptura
from src.services.project_model_assembly_adapter import build_assembly_project_model
from src.services.project_model_quick_quote_adapter import build_quick_quote_project_model
from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
    quick_quote_archive_path,
    sanitize_quick_quote_entries,
)
from src.tabs.receptura.receptura_picker import pick_receptura_rows
from src.ui.ui_polish import mark_ui_card, set_ui_variant


def _text_to_float(raw: str) -> float:
    text = str(raw or "").strip().lower()
    text = text.replace("zl", "").replace("%", "").replace(",", ".").replace(" ", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _make_pill(text: str, bg: str, fg: str, border: str | None = None) -> QLabel:
    pill = QLabel(text)
    pill.setStyleSheet(
        f"QLabel{{background:{bg};color:{fg};border:1px solid {border or bg};"
        "border-radius:999px;padding:4px 10px;font-size:10px;font-weight:800;}}"
    )
    return pill


def _ask_preset_name(parent: QWidget) -> tuple[str, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nowy szablon")
    layout = QVBoxLayout(dlg)
    layout.setSpacing(10)
    layout.addWidget(QLabel("Nazwa szablonu:"))
    ed = QLineEdit(dlg)
    ed.setPlaceholderText("np. Kuchnia standard")
    layout.addWidget(ed)
    btn_row = QHBoxLayout()
    btn_ok = QPushButton("Zapisz", dlg)
    btn_cancel = QPushButton("Anuluj", dlg)
    set_ui_variant(btn_ok, "primary")
    btn_ok.setMinimumHeight(32)
    btn_cancel.setMinimumHeight(32)
    btn_row.addWidget(btn_ok)
    btn_row.addWidget(btn_cancel)
    layout.addLayout(btn_row)
    btn_ok.clicked.connect(dlg.accept)
    btn_cancel.clicked.connect(dlg.reject)
    ed.returnPressed.connect(dlg.accept)
    result = dlg.exec()
    return ed.text(), result == QDialog.DialogCode.Accepted


class _FastSpinBox(QDoubleSpinBox):
    def focusInEvent(self, event) -> None:  # type: ignore[override]
        super().focusInEvent(event)
        self.selectAll()


class TabWycena(QWidget):
    DEFAULT_QUOTE_MODE = "quick"

    def __init__(
        self,
        parent: QWidget | None = None,
        assembly_store: AssemblyStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        wall_store: WallStoreJson | None = None,
        catalog: CatalogStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
        work_time_store: WorkTimeStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._client_store = ClientStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._expenses_store = CompanyExpensesStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._work_time_store = work_time_store if work_time_store is not None else WorkTimeStoreJson()
        self._pricing_store = QuotePricingStoreJson()
        self._preset_store = QuotePricingPresetStoreJson()
        self._pricing_service = QuotePricingService()
        self._library_store = ProducerLibraryStoreJson()
        self._receptura_store = RecepturaStoreJson()
        self._last_project_model: ProjectModel | None = None
        self._rows: list[dict[str, object]] = []
        self._is_loading = False
        self._is_table_refresh = False
        self._is_quick_adjustment_refresh = False
        self._quick_adjustments: dict[str, dict[str, object]] = {}
        self._worker_hourly_rates: dict[str, float] = {}
        pricing_data = self._pricing_store.load()
        self._active_policy = str(pricing_data.get("active_policy", "base") or "base")
        self._policy_multipliers = dict(pricing_data.get("policy_multipliers", {}) or {})
        self._pricing_rules = dict(pricing_data.get("rules", {}) or {})
        self._active_role = str(pricing_data.get("active_role", "owner") or "owner")
        theme = load_ui_theme_settings()
        self._is_tech = str(theme.motif).strip().lower() == "tech" and str(theme.mode).strip().lower() == "night"
        self._colors = (
            {
                "title": "#e8efff",
                "subtitle": "#9cb7dc",
                "hero_bg_0": "#111b30",
                "hero_bg_1": "#15253f",
                "hero_border": "#2e4b78",
                "hero_title": "#f2f7ff",
                "hero_desc": "#9cb7dc",
                "hero_chip_bg": "#1f3a8a",
                "hero_chip_border": "#3b82f6",
                "hero_chip_text": "#eaf1ff",
                "stats_bg": "rgba(18,30,52,0.98)",
                "stats_border": "#2e4b78",
                "metric_bg_0": "#15253f",
                "metric_bg_1": "#1c3154",
                "metric_border": "#2e4b78",
                "metric_accent": "#3b82f6",
                "metric_title": "#9cb7dc",
                "metric_value": "#f2f7ff",
                "client_box_bg": "#102947",
                "client_box_border": "#2f5f96",
                "client_box_accent": "#4f8ce8",
                "client_hdr": "#cfe2ff",
                "client_text": "#dbe9ff",
                "payments_box_bg": "#163428",
                "payments_box_border": "#2f7d65",
                "payments_box_accent": "#2f9c7f",
                "payments_hdr": "#c9f5e6",
                "payments_text": "#dbf5e9",
                "dates_box_bg": "#3a2b18",
                "dates_box_border": "#8c6333",
                "dates_box_accent": "#d08b3f",
                "dates_hdr": "#ffe0ba",
                "dates_text": "#fde6cc",
            }
            if self._is_tech
            else {
                "title": "#0f172a",
                "subtitle": "#526174",
                "hero_bg_0": "#ffffff",
                "hero_bg_1": "#eef4ff",
                "hero_border": "#d7e1ef",
                "hero_title": "#10263d",
                "hero_desc": "#526174",
                "hero_chip_bg": "#0f172a",
                "hero_chip_border": "#0f172a",
                "hero_chip_text": "#ffffff",
                "stats_bg": "rgba(255,255,255,0.96)",
                "stats_border": "#d7e1ef",
                "metric_bg_0": "#ffffff",
                "metric_bg_1": "#f7fbff",
                "metric_border": "#dbe4ef",
                "metric_accent": "#2563eb",
                "metric_title": "#64748b",
                "metric_value": "#0f172a",
                "client_box_bg": "#eff6ff",
                "client_box_border": "#bfdbfe",
                "client_box_accent": "#2563eb",
                "client_hdr": "#1e40af",
                "client_text": "#1f2937",
                "payments_box_bg": "#f0fdf4",
                "payments_box_border": "#d1fae5",
                "payments_box_accent": "#16a34a",
                "payments_hdr": "#14532d",
                "payments_text": "#1f2937",
                "dates_box_bg": "#fffbeb",
                "dates_box_border": "#fde68a",
                "dates_box_accent": "#d97706",
                "dates_hdr": "#92400e",
                "dates_text": "#1f2937",
            }
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title = QLabel("WYCENA")
        title.setStyleSheet(
            f"font-size:24px; font-weight:900; letter-spacing:0.2px; color:{self._colors['title']};"
        )
        title_row.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)
        title_row.addStretch(1)

        self.lab_mode = QLabel("Tryb wyceny:", self)
        self.cb_quote_mode = QComboBox(self)
        self.cb_quote_mode.addItem("Komplety", "assemblies")
        self.cb_quote_mode.addItem("Wycena wstępna", "quick")
        self.cb_quote_mode.setMinimumWidth(180)
        title_row.addWidget(self.lab_mode, 0)
        title_row.addWidget(self.cb_quote_mode, 0)

        self.lab_policy = QLabel("Polityka cen:", self)
        self.cb_policy = QComboBox(self)
        self.cb_policy.addItem("Bazowa", "base")
        self.cb_policy.addItem("Dealer", "dealer")
        self.cb_policy.addItem("Promocja", "promo")
        self.cb_policy.addItem("Wewnetrzna", "internal")
        self.cb_policy.setMinimumWidth(140)
        title_row.addWidget(self.lab_policy, 0)
        title_row.addWidget(self.cb_policy, 0)

        self.lab_role = QLabel("Rola:", self)
        self.cb_role = QComboBox(self)
        self.cb_role.addItem("Wlasciciel", "owner")
        self.cb_role.addItem("Handlowiec", "sales")
        self.cb_role.addItem("Produkcja", "production")
        self.cb_role.setMinimumWidth(140)
        title_row.addWidget(self.lab_role, 0)
        title_row.addWidget(self.cb_role, 0)
        # Desktop-first: keep pricing controls visible in header.
        self._show_header_pricing_controls = True
        if not self._show_header_pricing_controls:
            for widget in (
                self.lab_mode,
                self.cb_quote_mode,
                self.lab_policy,
                self.cb_policy,
                self.lab_role,
                self.cb_role,
            ):
                widget.setVisible(False)

        root.addLayout(title_row)

        hero = QFrame(self)
        hero.setStyleSheet(
            "QFrame{"
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {self._colors['hero_bg_0']},"
            f"stop:1 {self._colors['hero_bg_1']});"
            f"border:1px solid {self._colors['hero_border']};border-radius:20px;"
            "}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(12)
        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)
        self.hero_title = QLabel("", self)
        self.hero_title.setStyleSheet(f"font-size:14px;font-weight:900;color:{self._colors['hero_title']};")
        self.hero_desc = QLabel("", self)
        self.hero_desc.setWordWrap(True)
        self.hero_desc.setStyleSheet(f"font-size:12px;color:{self._colors['hero_desc']};")
        hero_text.addWidget(self.hero_title)
        hero_text.addWidget(self.hero_desc)
        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        if self._is_tech:
            pill_row.addWidget(_make_pill("Desktop", "#1c335c", "#dbe9ff", "#31588e"))
            pill_row.addWidget(_make_pill("Szybka decyzja", "#2c2752", "#dbd4ff", "#504486"))
            pill_row.addWidget(_make_pill("Spojny widok", "#173a31", "#c7f5e5", "#2f7d65"))
        else:
            pill_row.addWidget(_make_pill("Desktop", "#dbeafe", "#1d4ed8", "#bfdbfe"))
            pill_row.addWidget(_make_pill("Szybka decyzja", "#eef2ff", "#4338ca", "#c7d2fe"))
            pill_row.addWidget(_make_pill("Spojny widok", "#ecfdf5", "#047857", "#a7f3d0"))
        pill_row.addStretch(1)
        hero_text.addLayout(pill_row)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addWidget(
            _make_pill(
                "Tryb wyceny: " + self.cb_quote_mode.currentText(),
                self._colors["hero_chip_bg"],
                self._colors["hero_chip_text"],
                self._colors["hero_chip_border"],
            )
        )
        root.addWidget(hero)

        self.subtitle = QLabel("", self)
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"color:{self._colors['subtitle']};font-size:12px;")
        root.addWidget(self.subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.lab_mode_hint = QLabel("", self)
        self.lab_mode_hint.setWordWrap(True)
        self.lab_mode_hint.setStyleSheet("color:#334155; font-size:12px; font-weight:600;")
        root.addWidget(self.lab_mode_hint, 0, Qt.AlignmentFlag.AlignLeft)

        self.stats_widget = QWidget(self)
        mark_ui_card(self.stats_widget, elevated=True)
        self.stats_widget.setStyleSheet(
            f"QWidget{{background:{self._colors['stats_bg']};"
            f"border:1px solid {self._colors['stats_border']};border-radius:18px;}}"
        )
        stats_row = QHBoxLayout(self.stats_widget)
        stats_row.setContentsMargins(12, 10, 12, 10)
        stats_row.setSpacing(10)
        self.card_count = self._make_metric_card("Komplety", "0")
        self.card_tech = self._make_metric_card("Koszt techniczny", "0.00 zl")
        self.card_sale = self._make_metric_card("Cena handlowa", "0.00 zl")
        self.card_profit = self._make_metric_card("Marża", "0.00 zl")
        for widget in (self.card_count, self.card_tech, self.card_sale, self.card_profit):
            stats_row.addWidget(widget)
        stats_row.addStretch(1)
        root.addWidget(self.stats_widget, 0)

        self.toolbar_toggle = QPushButton("Pasek narzędzi ▼", self)
        set_ui_variant(self.toolbar_toggle, "ghost")
        self.toolbar_toggle.clicked.connect(self._toggle_toolbar)
        root.addWidget(self.toolbar_toggle, 0)

        self.toolbar_container = QWidget(self)
        mark_ui_card(self.toolbar_container, elevated=False)
        toolbar_layout = QHBoxLayout(self.toolbar_container)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)
        self.lab_search = QLabel("Szukaj:", self)
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po komplecie, kliencie albo zamówieniu...")
        self.cb_order = QComboBox(self)
        self.cb_order.addItem("Wszystkie zamówienia", "")
        self.btn_refresh = QPushButton("Odswiez", self)
        toolbar_layout.addWidget(self.lab_search)
        toolbar_layout.addWidget(self.ed_search, 1)
        self.lab_scope = QLabel("Zamówienie:", self)
        toolbar_layout.addWidget(self.lab_scope)
        toolbar_layout.addWidget(self.cb_order, 0)
        self.lab_quick_pick = QLabel("Wpis:", self)
        self.cb_quick_pick = QComboBox(self)
        self.cb_quick_pick.setMinimumWidth(300)
        self.btn_quick_add = QPushButton("+ Dodaj", self)
        self.btn_quick_from_receptura = QPushButton("Dodaj z Receptury", self)
        self.btn_quick_remove = QPushButton("- Usun", self)
        self.btn_quick_export_pdf = QPushButton("Eksport PDF", self)
        self.btn_quick_preview = QPushButton("Podglad", self)
        self.lab_quick_pick.setVisible(False)
        self.cb_quick_pick.setVisible(False)
        self.btn_quick_add.setVisible(False)
        self.btn_quick_from_receptura.setVisible(False)
        self.btn_quick_remove.setVisible(False)
        self.btn_quick_export_pdf.setVisible(False)
        self.btn_quick_preview.setVisible(False)
        toolbar_layout.addWidget(self.lab_quick_pick, 0)
        toolbar_layout.addWidget(self.cb_quick_pick, 0)
        toolbar_layout.addWidget(self.btn_quick_add, 0)
        toolbar_layout.addWidget(self.btn_quick_from_receptura, 0)
        toolbar_layout.addWidget(self.btn_quick_remove, 0)
        toolbar_layout.addWidget(self.btn_quick_preview, 0)
        toolbar_layout.addWidget(self.btn_quick_export_pdf, 0)
        toolbar_layout.addWidget(self.btn_refresh, 0)
        set_ui_variant(self.btn_refresh, "ghost")
        set_ui_variant(self.btn_quick_add, "primary")
        set_ui_variant(self.btn_quick_from_receptura, "success")
        set_ui_variant(self.btn_quick_remove, "danger")
        set_ui_variant(self.btn_quick_export_pdf, "ghost")
        set_ui_variant(self.btn_quick_preview, "ghost")
        for button in (
            self.btn_refresh,
            self.btn_quick_add,
            self.btn_quick_from_receptura,
            self.btn_quick_remove,
            self.btn_quick_export_pdf,
            self.btn_quick_preview,
        ):
            button.setMinimumHeight(32)
        root.addWidget(self.toolbar_container, 0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(self.main_splitter, 1)

        left = QWidget(self.main_splitter)
        self.left_panel = left
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        self.tbl_assemblies = QTableWidget(0, 7, left)
        self.tbl_assemblies.setHorizontalHeaderLabels(
            ["Komplet", "Zamówienie", "Klient", "Techn.", "Robocizna", "Marża %", "Handlowa"]
        )
        self.tbl_assemblies.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_assemblies.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_assemblies.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_assemblies.setAlternatingRowColors(True)
        self.tbl_assemblies.verticalHeader().setVisible(False)
        header = self.tbl_assemblies.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        left_layout.addWidget(self.tbl_assemblies, 1)

        self.quick_calc_frame = QFrame(left)
        mark_ui_card(self.quick_calc_frame, elevated=False)
        quick_form = QFormLayout(self.quick_calc_frame)
        quick_form.setContentsMargins(10, 10, 10, 10)
        quick_form.setSpacing(6)
        self.sp_quick_transport = _FastSpinBox(self.quick_calc_frame)
        self.sp_quick_transport.setRange(0.0, 1000000.0)
        self.sp_quick_transport.setDecimals(2)
        self.sp_quick_transport.setSuffix(" zl")
        self.sp_quick_hours = _FastSpinBox(self.quick_calc_frame)
        self.sp_quick_hours.setRange(0.0, 10000.0)
        self.sp_quick_hours.setDecimals(2)
        self.sp_quick_hours.setSuffix(" h")
        self.cb_quick_worker = QComboBox(self.quick_calc_frame)
        self.sp_quick_montage = _FastSpinBox(self.quick_calc_frame)
        self.sp_quick_montage.setRange(0.0, 1000000.0)
        self.sp_quick_montage.setDecimals(2)
        self.sp_quick_montage.setSuffix(" zl")
        for spin in (self.sp_quick_transport, self.sp_quick_hours, self.sp_quick_montage):
            self._configure_spinbox_for_fast_entry(spin)
        self.lab_quick_material = QLabel("0.00 zl", self.quick_calc_frame)
        self.lab_quick_rate = QLabel("0.00 zl/h", self.quick_calc_frame)
        self.lab_quick_rate_source = QLabel("wg wydatkow firmy", self.quick_calc_frame)
        self.lab_quick_labor_cost = QLabel("0.00 zl", self.quick_calc_frame)
        self.lab_quick_base = QLabel("0.00 zl", self.quick_calc_frame)
        self.lab_quick_netto = QLabel("0.00 zl", self.quick_calc_frame)
        self.lab_quick_brutto = QLabel("0.00 zl", self.quick_calc_frame)
        self.lab_quick_rate_source.setStyleSheet("color:#64748b;")
        self.lab_quick_base.setStyleSheet("font-weight:600; color:#374151;")
        self.lab_quick_netto.setStyleSheet("font-weight:600; color:#1f2937;")
        self.lab_quick_brutto.setStyleSheet("font-weight:700; color:#0f172a;")
        quick_form.addRow("Wartość materiałów", self.lab_quick_material)
        quick_form.addRow("Transport", self.sp_quick_transport)
        quick_form.addRow("Roboczogodziny", self.sp_quick_hours)
        quick_form.addRow("Pracownik", self.cb_quick_worker)
        quick_form.addRow("Montaż", self.sp_quick_montage)

        # ── USLUGI DODATKOWE ──────────────────────────────────────
        extras_widget = QWidget(self.quick_calc_frame)
        extras_vbox = QVBoxLayout(extras_widget)
        extras_vbox.setContentsMargins(0, 0, 0, 0)
        extras_vbox.setSpacing(2)
        self.tbl_quick_extras = QTableWidget(0, 2, extras_widget)
        self.tbl_quick_extras.setHorizontalHeaderLabels(["Opis usługi", "Kwota [zl]"])
        self.tbl_quick_extras.verticalHeader().setVisible(False)
        self.tbl_quick_extras.setMinimumHeight(60)
        self.tbl_quick_extras.setMaximumHeight(160)
        extras_hdr = self.tbl_quick_extras.horizontalHeader()
        extras_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        extras_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        extras_vbox.addWidget(self.tbl_quick_extras)
        extras_btn_row = QHBoxLayout()
        self.btn_extra_add = QPushButton("+ Dodaj usługę", extras_widget)
        self.btn_extra_remove = QPushButton("- Usuń usługę", extras_widget)
        self.btn_extra_add.setFixedHeight(24)
        self.btn_extra_remove.setFixedHeight(24)
        extras_btn_row.addWidget(self.btn_extra_add)
        extras_btn_row.addWidget(self.btn_extra_remove)
        extras_btn_row.addStretch(1)
        extras_vbox.addLayout(extras_btn_row)
        quick_form.addRow("Usługi dodatkówe:", extras_widget)

        quick_form.addRow("Stawka rob.-godz.", self.lab_quick_rate)
        quick_form.addRow("Źródło stawki", self.lab_quick_rate_source)
        quick_form.addRow("Koszt robocizny", self.lab_quick_labor_cost)
        quick_form.addRow("Koszt bazowy", self.lab_quick_base)
        quick_form.addRow("Cena netto", self.lab_quick_netto)
        quick_form.addRow("Cena brutto", self.lab_quick_brutto)
        self.tbl_quick_breakdown = QTableWidget(0, 2, self.quick_calc_frame)
        self.tbl_quick_breakdown.setHorizontalHeaderLabels(["Opis", "Wartosc"])
        self.tbl_quick_breakdown.setAlternatingRowColors(True)
        self.tbl_quick_breakdown.verticalHeader().setVisible(False)
        self.tbl_quick_breakdown.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_quick_breakdown.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        quick_breakdown_header = self.tbl_quick_breakdown.horizontalHeader()
        quick_breakdown_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        quick_breakdown_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quick_breakdown.setMinimumHeight(180)
        quick_form.addRow("Podsumowanie", self.tbl_quick_breakdown)
        self.quick_calc_frame.setVisible(False)
        left_layout.addWidget(self.quick_calc_frame, 0)
        self.main_splitter.addWidget(left)

        right = QWidget(self.main_splitter)
        self.right_panel = right
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        editor = QFrame(right)
        mark_ui_card(editor, elevated=False)
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(10)

        editor_title = QLabel("Kalkulacja kompletu", editor)
        editor_title.setStyleSheet("font-weight: 700;")
        editor_layout.addWidget(editor_title)

        self.lab_selected = QLabel("Wybierz komplet z listy.", editor)
        self.lab_selected.setWordWrap(True)
        editor_layout.addWidget(self.lab_selected)

        form = QFormLayout()
        self.sp_labor = _FastSpinBox(editor)
        self.sp_labor.setRange(0.0, 1000000.0)
        self.sp_labor.setDecimals(2)
        self.sp_labor.setSuffix(" zl")
        self.sp_transport = _FastSpinBox(editor)
        self.sp_transport.setRange(0.0, 1000000.0)
        self.sp_transport.setDecimals(2)
        self.sp_transport.setSuffix(" zl")
        self.sp_montage = _FastSpinBox(editor)
        self.sp_montage.setRange(0.0, 1000000.0)
        self.sp_montage.setDecimals(2)
        self.sp_montage.setSuffix(" zl")
        self.sp_margin = _FastSpinBox(editor)
        self.sp_margin.setRange(0.0, 500.0)
        self.sp_margin.setDecimals(1)
        self.sp_margin.setSuffix(" %")
        self.sp_rule_processing = _FastSpinBox(editor)
        self.sp_rule_processing.setRange(0.0, 300.0)
        self.sp_rule_processing.setDecimals(2)
        self.sp_rule_processing.setSuffix(" %")
        self.sp_rule_assembly = _FastSpinBox(editor)
        self.sp_rule_assembly.setRange(0.0, 300.0)
        self.sp_rule_assembly.setDecimals(2)
        self.sp_rule_assembly.setSuffix(" %")
        self.sp_rule_transport = _FastSpinBox(editor)
        self.sp_rule_transport.setRange(0.0, 1000000.0)
        self.sp_rule_transport.setDecimals(2)
        self.sp_rule_transport.setSuffix(" zl")
        self.sp_policy_base = _FastSpinBox(editor)
        self.sp_policy_base.setRange(0.0, 5.0)
        self.sp_policy_base.setDecimals(3)
        self.sp_policy_dealer = _FastSpinBox(editor)
        self.sp_policy_dealer.setRange(0.0, 5.0)
        self.sp_policy_dealer.setDecimals(3)
        self.sp_policy_promo = _FastSpinBox(editor)
        self.sp_policy_promo.setRange(0.0, 5.0)
        self.sp_policy_promo.setDecimals(3)
        self.sp_policy_internal = _FastSpinBox(editor)
        self.sp_policy_internal.setRange(0.0, 5.0)
        self.sp_policy_internal.setDecimals(3)
        for spin in (
            self.sp_labor,
            self.sp_transport,
            self.sp_montage,
            self.sp_margin,
            self.sp_rule_processing,
            self.sp_rule_assembly,
            self.sp_rule_transport,
            self.sp_policy_base,
            self.sp_policy_dealer,
            self.sp_policy_promo,
            self.sp_policy_internal,
        ):
            self._configure_spinbox_for_fast_entry(spin)
        self.lab_base_total = QLabel("0.00 zl", editor)
        self.lab_base_total.setStyleSheet("font-weight:600; color:#374151;")
        self.lab_sale_total = QLabel("0.00 zl", editor)
        self.lab_sale_total.setStyleSheet("font-weight:700; color:#2f241b;")
        self.lab_profit_total = QLabel("0.00 zl", editor)
        self.lab_profit_total.setStyleSheet("font-weight:600; color:#6b5d4d;")
        self.lab_policy_info = QLabel("Polityka: bazowa x1.00", editor)
        self.lab_policy_info.setStyleSheet("color:#475569;")
        form.addRow("Robocizna", self.sp_labor)
        form.addRow("Transport", self.sp_transport)
        form.addRow("Montaż", self.sp_montage)
        form.addRow("Marża", self.sp_margin)
        form.addRow("Regula: obrobka", self.sp_rule_processing)
        form.addRow("Regula: skladanie", self.sp_rule_assembly)
        form.addRow("Regula: transport", self.sp_rule_transport)
        form.addRow("Mnoznik: bazowa", self.sp_policy_base)
        form.addRow("Mnoznik: dealer", self.sp_policy_dealer)
        form.addRow("Mnoznik: promocja", self.sp_policy_promo)
        form.addRow("Mnoznik: wewnetrzna", self.sp_policy_internal)
        form.addRow("Polityka", self.lab_policy_info)
        form.addRow("Koszt bazowy", self.lab_base_total)
        form.addRow("Cena handlowa", self.lab_sale_total)
        form.addRow("Narost", self.lab_profit_total)
        editor_layout.addLayout(form)

        # ── SZABLONY WYCENY ───────────────────────────────────────
        preset_frame = QFrame(editor)
        mark_ui_card(preset_frame, elevated=False)
        preset_layout = QVBoxLayout(preset_frame)
        preset_layout.setContentsMargins(10, 8, 10, 8)
        preset_layout.setSpacing(6)
        preset_title = QLabel("Szablony (transport + montaż + marża)", preset_frame)
        preset_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #374151;")
        preset_layout.addWidget(preset_title)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        self.cb_preset = QComboBox(preset_frame)
        self.cb_preset.setMinimumWidth(180)
        self.cb_preset.setPlaceholderText("Wybierz szablon...")
        self.btn_preset_load = QPushButton("Wczytaj", preset_frame)
        self.btn_preset_save = QPushButton("Zapisz nowy", preset_frame)
        self.btn_preset_delete = QPushButton("Usun", preset_frame)
        set_ui_variant(self.btn_preset_load, "primary")
        set_ui_variant(self.btn_preset_save, "success")
        set_ui_variant(self.btn_preset_delete, "danger")
        for _btn in (self.btn_preset_load, self.btn_preset_save, self.btn_preset_delete):
            _btn.setMinimumHeight(28)
        preset_row.addWidget(self.cb_preset, 1)
        preset_row.addWidget(self.btn_preset_load, 0)
        preset_row.addWidget(self.btn_preset_save, 0)
        preset_row.addWidget(self.btn_preset_delete, 0)
        preset_layout.addLayout(preset_row)
        editor_layout.addWidget(preset_frame)

        actions = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz wycene", editor)
        self.btn_clear = QPushButton("Wyczysc dodatki", editor)
        self.btn_export_purchase = QPushButton("Eksport zakupu CSV", editor)
        self.btn_export_report = QPushButton("Raport rentownosci", editor)
        self.btn_export_pdf = QPushButton("Eksport PDF", editor)
        set_ui_variant(self.btn_save, "primary")
        set_ui_variant(self.btn_clear, "danger")
        set_ui_variant(self.btn_export_purchase, "ghost")
        set_ui_variant(self.btn_export_report, "ghost")
        set_ui_variant(self.btn_export_pdf, "ghost")
        for button in (
            self.btn_save,
            self.btn_clear,
            self.btn_export_purchase,
            self.btn_export_report,
            self.btn_export_pdf,
        ):
            button.setMinimumHeight(32)
        actions.addWidget(self.btn_save, 0)
        actions.addWidget(self.btn_clear, 0)
        actions.addWidget(self.btn_export_purchase, 0)
        actions.addWidget(self.btn_export_report, 0)
        actions.addWidget(self.btn_export_pdf, 0)
        actions.addStretch(1)
        editor_layout.addLayout(actions)

        self.lab_status = QLabel("", editor)
        self.lab_status.setWordWrap(True)
        editor_layout.addWidget(self.lab_status)
        self.lab_profit_report = QLabel("", editor)
        self.lab_profit_report.setWordWrap(True)
        self.lab_profit_report.setStyleSheet("color:#334155;")
        editor_layout.addWidget(self.lab_profit_report)
        right_layout.addWidget(editor, 0)

        work_time_box = QFrame(right)
        mark_ui_card(work_time_box, elevated=False)
        work_time_layout = QFormLayout(work_time_box)
        work_time_layout.setContentsMargins(12, 12, 12, 12)
        self.lab_time_days = QLabel("0", work_time_box)
        self.lab_time_hours = QLabel("0.00 h", work_time_box)
        self.lab_time_overtime = QLabel("0.00 zl", work_time_box)
        self.lab_time_stage_extra = QLabel("0.00 zl", work_time_box)
        self.lab_time_extra = QLabel("0.00 zl", work_time_box)
        self.lab_time_cost = QLabel("0.00 zl", work_time_box)
        self.btn_load_labor_from_time = QPushButton("Pobierz do robocizny", work_time_box)
        set_ui_variant(self.btn_load_labor_from_time, "success")
        self.btn_load_labor_from_time.setMinimumHeight(32)
        work_time_layout.addRow("Dni z czasu pracy", self.lab_time_days)
        work_time_layout.addRow("Godziny z czasu pracy", self.lab_time_hours)
        work_time_layout.addRow("Nadgodziny", self.lab_time_overtime)
        work_time_layout.addRow("Dodatki etapow", self.lab_time_stage_extra)
        work_time_layout.addRow("Dodatki reczne", self.lab_time_extra)
        work_time_layout.addRow("Koszt robocizny", self.lab_time_cost)
        work_time_layout.addRow("", self.btn_load_labor_from_time)
        right_layout.addWidget(work_time_box, 0)

        order_box = QFrame(right)
        mark_ui_card(order_box, elevated=False)
        order_layout = QFormLayout(order_box)
        order_layout.setContentsMargins(12, 12, 12, 12)
        self.lab_order_tech = QLabel("0.00 zl", order_box)
        self.lab_order_sale = QLabel("0.00 zl", order_box)
        self.lab_order_profit = QLabel("0.00 zl", order_box)
        order_layout.addRow("Koszt techniczny", self.lab_order_tech)
        order_layout.addRow("Cena handlowa", self.lab_order_sale)
        order_layout.addRow("Marża kwotowo", self.lab_order_profit)
        right_layout.addWidget(order_box, 0)

        # --- Klient ---
        self.client_info_box = QFrame(right)
        self.client_info_box.setStyleSheet(
            f"QFrame {{ border: 1px solid {self._colors['client_box_border']};"
            f" border-left: 4px solid {self._colors['client_box_accent']}; border-radius: 8px;"
            f" background: {self._colors['client_box_bg']}; }}"
        )
        client_info_layout = QFormLayout(self.client_info_box)
        client_info_layout.setContentsMargins(12, 10, 12, 10)
        client_info_layout.setSpacing(4)
        _hdr_client = QLabel("Klient")
        _hdr_client.setStyleSheet(f"font-weight:800; font-size:13px; color:{self._colors['client_hdr']};")
        client_info_layout.addRow(_hdr_client)
        self.lab_client_name_val = QLabel("-")
        self.lab_client_name_val.setStyleSheet(f"font-weight:700; color:{self._colors['client_text']};")
        self.lab_client_name_val.setWordWrap(True)
        self.lab_client_phone_val = QLabel("-")
        self.lab_client_phone_val.setStyleSheet(f"color:{self._colors['client_text']};")
        self.lab_client_email_val = QLabel("-")
        self.lab_client_email_val.setStyleSheet(f"color:{self._colors['client_text']};")
        self.lab_order_code_val = QLabel("-")
        self.lab_order_code_val.setStyleSheet(f"font-family:monospace; color:{self._colors['client_text']};")
        client_info_layout.addRow("Zamówienie:", self.lab_order_code_val)
        client_info_layout.addRow("Klient:", self.lab_client_name_val)
        client_info_layout.addRow("Tel.:", self.lab_client_phone_val)
        client_info_layout.addRow("Email:", self.lab_client_email_val)
        self.client_info_box.hide()
        right_layout.addWidget(self.client_info_box, 0)

        # --- Płatności klienta ---
        self.payments_box = QFrame(right)
        self.payments_box.setStyleSheet(
            f"QFrame {{ border: 1px solid {self._colors['payments_box_border']};"
            f" border-left: 4px solid {self._colors['payments_box_accent']}; border-radius: 8px;"
            f" background: {self._colors['payments_box_bg']}; }}"
        )
        self.payments_layout = QVBoxLayout(self.payments_box)
        self.payments_layout.setContentsMargins(12, 10, 12, 10)
        self.payments_layout.setSpacing(4)
        _hdr_pay = QLabel("Płatności klienta")
        _hdr_pay.setStyleSheet(f"font-weight:800; font-size:13px; color:{self._colors['payments_hdr']};")
        self.payments_layout.addWidget(_hdr_pay)
        _pay_note = QLabel("Rezerwacja terminu: 5 000 zł  •  1 rata 60%  •  2 rata 30%  •  3 rata 10%")
        _pay_note.setStyleSheet(f"font-size:11px; color:{self._colors['payments_text']}; margin-bottom:4px;")
        _pay_note.setWordWrap(True)
        self.payments_layout.addWidget(_pay_note)
        self.lab_payments_rows = QLabel("")
        self.lab_payments_rows.setWordWrap(True)
        self.lab_payments_rows.setStyleSheet(f"font-size:12px; color:{self._colors['payments_text']};")
        self.payments_layout.addWidget(self.lab_payments_rows)
        self.payments_box.hide()
        right_layout.addWidget(self.payments_box, 0)

        # --- Terminy projektu ---
        self.dates_box = QFrame(right)
        self.dates_box.setStyleSheet(
            f"QFrame {{ border: 1px solid {self._colors['dates_box_border']};"
            f" border-left: 4px solid {self._colors['dates_box_accent']}; border-radius: 8px;"
            f" background: {self._colors['dates_box_bg']}; }}"
        )
        dates_layout = QFormLayout(self.dates_box)
        dates_layout.setContentsMargins(12, 10, 12, 10)
        dates_layout.setSpacing(4)
        _hdr_dates = QLabel("Terminy projektu")
        _hdr_dates.setStyleSheet(f"font-weight:800; font-size:13px; color:{self._colors['dates_hdr']};")
        dates_layout.addRow(_hdr_dates)
        self.lab_d_wycena = QLabel("-")
        self.lab_d_projekt = QLabel("-")
        self.lab_d_probki = QLabel("-")
        self.lab_d_zakup_mat = QLabel("-")
        self.lab_d_produkcja = QLabel("-")
        self.lab_d_montaz = QLabel("-")
        self.lab_d_poprawki = QLabel("-")
        _date_style = f"color:{self._colors['dates_text']}; font-weight:600;"
        for lbl in (
            self.lab_d_wycena, self.lab_d_projekt, self.lab_d_probki,
            self.lab_d_zakup_mat, self.lab_d_produkcja, self.lab_d_montaz, self.lab_d_poprawki,
        ):
            lbl.setStyleSheet(_date_style)
        dates_layout.addRow("Wycena:", self.lab_d_wycena)
        dates_layout.addRow("Projekt:", self.lab_d_projekt)
        dates_layout.addRow("Próbki mat.:", self.lab_d_probki)
        dates_layout.addRow("Zakup mat.:", self.lab_d_zakup_mat)
        dates_layout.addRow("Produkcja:", self.lab_d_produkcja)
        dates_layout.addRow("Montaż:", self.lab_d_montaz)
        dates_layout.addRow("Poprawki:", self.lab_d_poprawki)
        self.dates_box.hide()
        right_layout.addWidget(self.dates_box, 0)

        right_layout.addStretch(1)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([600, 400])

        self.ed_search.textChanged.connect(self._refresh_table)
        self.cb_order.currentIndexChanged.connect(self._refresh_table)
        self.cb_quick_pick.currentIndexChanged.connect(self._on_quick_pick_changed)
        self.cb_quote_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.btn_quick_add.clicked.connect(self._on_quick_add_clicked)
        self.btn_quick_from_receptura.clicked.connect(self._on_quick_add_from_receptura_clicked)
        self.btn_quick_remove.clicked.connect(self._on_quick_remove_clicked)
        self.btn_quick_export_pdf.clicked.connect(self._on_quick_export_pdf)
        self.btn_quick_preview.clicked.connect(self._on_quick_preview)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.tbl_assemblies.itemSelectionChanged.connect(self._on_selection_changed)
        self.tbl_assemblies.cellClicked.connect(self._on_table_cell_clicked)
        self.tbl_assemblies.itemChanged.connect(self._on_quick_table_item_changed)
        self.sp_quick_transport.valueChanged.connect(self._on_quick_adjustment_changed)
        self.sp_quick_hours.valueChanged.connect(self._on_quick_adjustment_changed)
        self.sp_quick_montage.valueChanged.connect(self._on_quick_adjustment_changed)
        self.cb_quick_worker.currentIndexChanged.connect(self._on_quick_adjustment_changed)
        self.tbl_quick_extras.itemChanged.connect(self._on_quick_extras_item_changed)
        self.btn_extra_add.clicked.connect(self._on_quick_extra_add)
        self.btn_extra_remove.clicked.connect(self._on_quick_extra_remove)
        self.btn_preset_save.clicked.connect(self._on_preset_save)
        self.btn_preset_load.clicked.connect(self._on_preset_load)
        self.btn_preset_delete.clicked.connect(self._on_preset_delete)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_export_purchase.clicked.connect(self._on_export_purchase_csv)
        self.btn_export_report.clicked.connect(self._on_export_profitability_report)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        self.btn_load_labor_from_time.clicked.connect(self._on_load_labor_from_time)
        self.sp_labor.valueChanged.connect(self._refresh_editor_totals)
        self.sp_transport.valueChanged.connect(self._refresh_editor_totals)
        self.sp_montage.valueChanged.connect(self._refresh_editor_totals)
        self.sp_margin.valueChanged.connect(self._refresh_editor_totals)
        self.sp_rule_processing.valueChanged.connect(self._on_rules_changed)
        self.sp_rule_assembly.valueChanged.connect(self._on_rules_changed)
        self.sp_rule_transport.valueChanged.connect(self._on_rules_changed)
        self.sp_policy_base.valueChanged.connect(self._on_policy_multipliers_changed)
        self.sp_policy_dealer.valueChanged.connect(self._on_policy_multipliers_changed)
        self.sp_policy_promo.valueChanged.connect(self._on_policy_multipliers_changed)
        self.sp_policy_internal.valueChanged.connect(self._on_policy_multipliers_changed)
        self.cb_policy.currentIndexChanged.connect(self._on_policy_changed)
        self.cb_role.currentIndexChanged.connect(self._on_role_changed)

        self._set_default_quote_mode()
        self._load_pricing_controls()
        self._apply_role_visibility()
        self._refresh_preset_combo()

        self._apply_mode_copy()
        self.refresh_data()

    def _make_metric_card(self, title: str, value: str) -> QFrame:
        frame = QFrame(self)
        mark_ui_card(frame, elevated=True)
        frame.setStyleSheet(
            "QFrame{"
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {self._colors['metric_bg_0']},"
            f"stop:1 {self._colors['metric_bg_1']});"
            f"border:1px solid {self._colors['metric_border']};"
            "border-radius:16px;"
            f"border-bottom:3px solid {self._colors['metric_accent']};"
            "}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet(f"color:{self._colors['metric_title']}; font-size:10px; font-weight:800;")
        lab_value = QLabel(value, frame)
        lab_value.setStyleSheet(f"font-size:18px; font-weight:900; color:{self._colors['metric_value']};")
        lab_value.setObjectName("metricValue")
        layout.addWidget(lab_title)
        layout.addWidget(lab_value)
        frame.metric_value = lab_value  # type: ignore[attr-defined]
        return frame

    def _set_metric(self, frame: QFrame, value: str) -> None:
        label = getattr(frame, "metric_value", None)
        if isinstance(label, QLabel):
            label.setText(value)

    def _policy_multiplier(self) -> float:
        key = str(self._active_policy or "base").strip()
        try:
            return float(self._policy_multipliers.get(key, 1.0) or 1.0)
        except Exception:
            return 1.0

    def _save_pricing_config(self) -> None:
        try:
            self._pricing_store.save(
                {
                    "active_policy": self._active_policy,
                    "policy_multipliers": self._policy_multipliers,
                    "rules": self._pricing_rules,
                    "active_role": self._active_role,
                }
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Blad zapisu danych",
                f"Nie udalo sie zapisac ustawien wyceny.\n\nSzczegoly: {exc}",
            )

    def _load_pricing_controls(self) -> None:
        idx_policy = self.cb_policy.findData(self._active_policy)
        self.cb_policy.setCurrentIndex(idx_policy if idx_policy >= 0 else 0)
        idx_role = self.cb_role.findData(self._active_role)
        self.cb_role.setCurrentIndex(idx_role if idx_role >= 0 else 0)
        self.sp_rule_processing.setValue(float(self._pricing_rules.get("processing_percent", 0.0) or 0.0))
        self.sp_rule_assembly.setValue(float(self._pricing_rules.get("assembly_percent", 0.0) or 0.0))
        self.sp_rule_transport.setValue(float(self._pricing_rules.get("transport_flat", 0.0) or 0.0))
        self.sp_policy_base.setValue(float(self._policy_multipliers.get("base", 1.0) or 1.0))
        self.sp_policy_dealer.setValue(float(self._policy_multipliers.get("dealer", 0.92) or 0.92))
        self.sp_policy_promo.setValue(float(self._policy_multipliers.get("promo", 0.88) or 0.88))
        self.sp_policy_internal.setValue(float(self._policy_multipliers.get("internal", 0.75) or 0.75))
        self.lab_policy_info.setText(f"Polityka: {self.cb_policy.currentText().lower()} x{self._policy_multiplier():.2f}")

    def _on_policy_changed(self) -> None:
        self._active_policy = str(self.cb_policy.currentData() or "base")
        self.lab_policy_info.setText(f"Polityka: {self.cb_policy.currentText().lower()} x{self._policy_multiplier():.2f}")
        self._save_pricing_config()
        self.refresh_data()

    def _on_rules_changed(self) -> None:
        self._pricing_rules = {
            "processing_percent": float(self.sp_rule_processing.value()),
            "assembly_percent": float(self.sp_rule_assembly.value()),
            "transport_flat": float(self.sp_rule_transport.value()),
        }
        self._save_pricing_config()
        self.refresh_data()

    def _on_policy_multipliers_changed(self) -> None:
        self._policy_multipliers = {
            "base": float(self.sp_policy_base.value()),
            "dealer": float(self.sp_policy_dealer.value()),
            "promo": float(self.sp_policy_promo.value()),
            "internal": float(self.sp_policy_internal.value()),
        }
        self.lab_policy_info.setText(f"Polityka: {self.cb_policy.currentText().lower()} x{self._policy_multiplier():.2f}")
        self._save_pricing_config()
        self.refresh_data()

    def _on_role_changed(self) -> None:
        self._active_role = str(self.cb_role.currentData() or "owner")
        self._save_pricing_config()
        self._apply_role_visibility()

    def _apply_role_visibility(self) -> None:
        role = str(self._active_role or "owner")
        show_costs = role in {"owner", "production"}
        show_profit = role in {"owner", "sales"}
        self.card_tech.setVisible(show_costs)
        self.card_profit.setVisible(show_profit)
        self.lab_order_tech.setVisible(show_costs)
        self.lab_order_profit.setVisible(show_profit)
        self.lab_time_cost.setVisible(show_costs)
        self.btn_load_labor_from_time.setVisible(show_costs)
        self.sp_rule_processing.setVisible(role == "owner")
        self.sp_rule_assembly.setVisible(role == "owner")
        self.sp_rule_transport.setVisible(role == "owner")
        self.sp_policy_base.setVisible(role == "owner")
        self.sp_policy_dealer.setVisible(role == "owner")
        self.sp_policy_promo.setVisible(role == "owner")
        self.sp_policy_internal.setVisible(role == "owner")
        if self._mode() != "quick":
            self.tbl_assemblies.setColumnHidden(3, role == "sales")
            self.tbl_assemblies.setColumnHidden(5, role == "production")
            self.tbl_assemblies.setColumnHidden(6, role == "production")

    def _configure_spinbox_for_fast_entry(self, spin: QDoubleSpinBox) -> None:
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAccelerated(True)
        spin.setKeyboardTracking(False)
        spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _mode(self) -> str:
        return str(self.cb_quote_mode.currentData() or "assemblies")

    def _apply_mode_copy(self) -> None:
        if self._mode() == "quick":
            self.hero_title.setText("Szybka wycena handlowa")
            self.hero_desc.setText(
                "Tryb do szybkiej oferty z sekcji, wymiarów i gotowych wpisów. Tu liczysz cenę bez wchodzenia w kompletową strukturę projektu."
            )
            self.subtitle.setText(
                "Tryb handlowy: szybka oferta z wymiarów, sekcji i gotowych pozycji. To najszybsza droga do ceny dla klienta."
            )
            self.lab_mode_hint.setText(
                "Ten ekran służy do szybkiej oferty. Widzisz listę wpisów, ich cenę i dodatki, bez pełnej struktury projektu."
            )
        else:
            self.hero_title.setText("Wycena projektu systemowego")
            self.hero_desc.setText(
                "Tryb pracy na module, komplecie albo ścianie. Tu wchodzisz w dane techniczne, robociznę i pełne rozbicie kosztu projektu."
            )
            self.subtitle.setText(
                "Tryb systemowy: wycena projektu z modułu, kompletu lub ściany. Tu pracujesz na danych technicznych i pełnym rozbiciu kosztów."
            )
            self.lab_mode_hint.setText(
                "Ten ekran prowadzi przez kompletną wycenę projektu. Najpierw widzisz strukturę techniczną, potem koszty i wynik handlowy."
            )

    def _set_default_quote_mode(self) -> None:
        idx = self.cb_quote_mode.findData(self.DEFAULT_QUOTE_MODE)
        if idx < 0:
            return
        self.cb_quote_mode.setCurrentIndex(idx)

    def _set_editor_enabled(self, enabled: bool) -> None:
        for widget in (self.sp_labor, self.sp_transport, self.sp_montage, self.sp_margin):
            widget.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        if not enabled:
            self.btn_load_labor_from_time.setEnabled(False)

    def _load_quick_quotes(self) -> list[dict[str, Any]]:
        path = quick_quote_archive_path()
        if not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text) if text.strip() else []
            if isinstance(payload, list):
                return sanitize_quick_quote_entries(payload)
        except Exception:
            return []
        return []

    def _write_quick_quotes(self, entries: list[dict[str, Any]]) -> bool:
        path = quick_quote_archive_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            write_json_atomic(path, entries, ensure_ascii=False, indent=2)
            return True
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Blad zapisu danych",
                f"Nie udalo sie zapisac bazy szybkich wycen.\n\nSzczegoly: {exc}",
            )
            return False

    def _next_quick_quote_id(self, entries: list[dict[str, Any]]) -> str:
        existing = {str(item.get("id", "") or "").strip() for item in entries if isinstance(item, dict)}
        while True:
            new_id = f"Q{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if new_id not in existing:
                return new_id

    def _quick_adjustment_defaults(self) -> dict[str, object]:
        return {"transport": 0.0, "hours": 0.0, "worker": "", "montage": 0.0, "extras": []}

    def _quick_adjustment_for(self, quick_id: str) -> dict[str, object]:
        key = str(quick_id or "").strip()
        if not key:
            return self._quick_adjustment_defaults()
        current = self._quick_adjustments.get(key)
        if not isinstance(current, dict):
            current = self._quick_adjustment_defaults()
            self._quick_adjustments[key] = current
        return current

    def _refresh_quick_workers(self) -> None:
        current = str(self.cb_quick_worker.currentData() or "").strip()
        workers = self._worker_store.list_workers()
        self._worker_hourly_rates = {
            str(worker.name or "").strip(): float(getattr(worker, "hourly_rate", 0.0) or 0.0)
            for worker in workers
            if str(worker.name or "").strip()
        }
        self.cb_quick_worker.blockSignals(True)
        try:
            self.cb_quick_worker.clear()
            self.cb_quick_worker.addItem("[brak]", "")
            for name in sorted(self._worker_hourly_rates):
                rate = float(self._worker_hourly_rates.get(name, 0.0))
                self.cb_quick_worker.addItem(f"{name} ({rate:.2f} zl/h)", name)
            idx = self.cb_quick_worker.findData(current)
            self.cb_quick_worker.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_quick_worker.blockSignals(False)

    def _select_quick_row_by_id(self, quick_id: str) -> bool:
        key = str(quick_id or "").strip()
        if not key:
            return False
        for row in range(self.tbl_assemblies.rowCount()):
            item = self.tbl_assemblies.item(row, 0)
            if item is None:
                continue
            item_key = str(item.data(Qt.ItemDataRole.UserRole) or item.text() or "").strip()
            if item_key != key:
                continue
            self.tbl_assemblies.selectRow(row)
            self.tbl_assemblies.scrollToItem(item)
            return True
        return False

    def _choose_quick_quote_id(self, entries: list[dict[str, Any]]) -> str:
        dialog = QDialog(self)
        dialog.setWindowTitle("Wybierz wycene z bazy szybkich wycen")
        dialog.resize(820, 420)
        layout = QVBoxLayout(dialog)
        tbl = QTableWidget(0, 4, dialog)
        tbl.setHorizontalHeaderLabels(["ID", "Klient", "Wartość materiałów", "VAT"])
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        header = tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        for entry in entries:
            quote_id = str(entry.get("id", "") or "").strip()
            if not quote_id:
                continue
            row_idx = tbl.rowCount()
            tbl.insertRow(row_idx)
            id_item = QTableWidgetItem(quote_id)
            id_item.setData(Qt.ItemDataRole.UserRole, quote_id)
            tbl.setItem(row_idx, 0, id_item)
            tbl.setItem(row_idx, 1, QTableWidgetItem(str(entry.get("client", "") or "")))
            tbl.setItem(row_idx, 2, QTableWidgetItem(str(entry.get("price", "") or "")))
            tbl.setItem(row_idx, 3, QTableWidgetItem(str(entry.get("vat", "") or "")))
        layout.addWidget(tbl, 1)
        buttons = QHBoxLayout()
        btn_cancel = QPushButton("Anuluj", dialog)
        btn_ok = QPushButton("Wybierz", dialog)
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel, 0)
        buttons.addWidget(btn_ok, 0)
        layout.addLayout(buttons)
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.clicked.connect(dialog.accept)
        if tbl.rowCount() > 0:
            tbl.selectRow(0)
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return ""
        rows = tbl.selectionModel().selectedRows() if tbl.selectionModel() is not None else []
        if not rows:
            return ""
        row = int(rows[0].row())
        item = tbl.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole) if item is not None else "").strip()

    def _real_hour_rate_from_expenses(self) -> float:
        metrics = self._expenses_store.real_hour_metrics(
            workers_fallback=max(1, len(self._worker_store.list_workers())),
            hours_fallback=160.0,
        )
        return float(metrics.get("real_hour_rate", 0.0) or 0.0)

    def _effective_quick_hour_rate(self, quick_id: str) -> tuple[float, str]:
        adj = self._quick_adjustment_for(quick_id)
        worker_name = str(adj.get("worker", "") or "").strip()
        worker_rate = float(self._worker_hourly_rates.get(worker_name, 0.0) or 0.0)
        if worker_name and worker_rate > 0.0:
            return worker_rate, worker_name
        return float(self._real_hour_rate_from_expenses()), "wydatki"

    def _compute_quick_totals(self, material_value: float, margin_percent: float, vat_percent: float, quick_id: str) -> dict[str, float | str]:
        adj = self._quick_adjustment_for(quick_id)
        transport = float(adj.get("transport", 0.0) or 0.0)
        hours = float(adj.get("hours", 0.0) or 0.0)
        montage = float(adj.get("montage", 0.0) or 0.0)
        extras_list = list(adj.get("extras", []) or [])
        extras_total = sum(
            float(e.get("amount", 0.0) or 0.0)
            for e in extras_list
            if isinstance(e, dict)
        )
        hour_rate, rate_source = self._effective_quick_hour_rate(quick_id)
        labor_cost = hours * hour_rate
        base = float(material_value) + transport + labor_cost + montage + extras_total
        adjusted_base = self._pricing_service.apply_rules(base, material_value, self._pricing_rules)
        netto = self._pricing_service.compute_sale(adjusted_base, margin_percent, self._policy_multiplier())
        brutto = netto * (1.0 + (float(vat_percent) / 100.0))
        return {
            "material_value": float(material_value),
            "transport": transport,
            "hours": hours,
            "montage": montage,
            "extras_total": extras_total,
            "hour_rate": float(hour_rate),
            "rate_source": rate_source,
            "labor_cost": labor_cost,
            "base_total": adjusted_base,
            "netto": netto,
            "brutto": brutto,
        }

    def _set_quick_breakdown_rows(self, values: dict[str, float | str]) -> None:
        source = str(values.get("rate_source", "") or "").strip()
        source_label = source if source and source != "wydatki" else "wg wydatkow firmy"
        rows: list[tuple[str, str]] = [
            ("Wartość materiałów", f"{float(values.get('material_value', 0.0) or 0.0):.2f} zl"),
            ("Transport", f"{float(values.get('transport', 0.0) or 0.0):.2f} zl"),
            ("Roboczogodziny", f"{float(values.get('hours', 0.0) or 0.0):.2f} h"),
            ("Stawka rob.-godz.", f"{float(values.get('hour_rate', 0.0) or 0.0):.2f} zl/h"),
            ("Pracownik / zrodlo", source_label),
            ("Koszt robocizny", f"{float(values.get('labor_cost', 0.0) or 0.0):.2f} zl"),
            ("Montaż", f"{float(values.get('montage', 0.0) or 0.0):.2f} zl"),
            ("Usługi dodatkówe", f"{float(values.get('extras_total', 0.0) or 0.0):.2f} zl"),
            ("Koszt bazowy", f"{float(values.get('base_total', 0.0) or 0.0):.2f} zl"),
            ("Cena netto", f"{float(values.get('netto', 0.0) or 0.0):.2f} zl"),
            ("Cena brutto", f"{float(values.get('brutto', 0.0) or 0.0):.2f} zl"),
        ]
        self.tbl_quick_breakdown.setRowCount(0)
        for label, value in rows:
            row = self.tbl_quick_breakdown.rowCount()
            self.tbl_quick_breakdown.insertRow(row)
            self.tbl_quick_breakdown.setItem(row, 0, QTableWidgetItem(label))
            value_item = QTableWidgetItem(value)
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_quick_breakdown.setItem(row, 1, value_item)

    def _selected_quick_id(self) -> str:
        return str(self.cb_quick_pick.currentData() or "").strip()

    def _refresh_quick_picker(self, entries: list[dict[str, Any]]) -> None:
        current_id = self._selected_quick_id()
        self.cb_quick_pick.blockSignals(True)
        try:
            self.cb_quick_pick.clear()
            self.cb_quick_pick.addItem("Wszystkie wpisy", "")
            for entry in entries:
                quote_id = str(entry.get("id", "") or "").strip()
                client = str(entry.get("client", "") or "").strip()
                price = str(entry.get("price", "") or "").strip()
                if not quote_id:
                    continue
                label_parts = [quote_id]
                if client:
                    label_parts.append(client)
                if price:
                    label_parts.append(price)
                self.cb_quick_pick.addItem(" | ".join(label_parts), quote_id)
            idx = self.cb_quick_pick.findData(current_id)
            self.cb_quick_pick.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_quick_pick.blockSignals(False)

    def _on_quick_pick_changed(self) -> None:
        if self._mode() == "quick":
            self._refresh_table()

    def _on_quick_add_clicked(self) -> None:
        if self._mode() != "quick":
            return
        entries = self._load_quick_quotes()
        if not entries:
            self._set_status("Baza szybkich wycen jest pusta.", ok=False)
            return
        selected_id = self._choose_quick_quote_id(entries)
        if not selected_id:
            return
        self.refresh_data()
        if self._select_quick_row_by_id(selected_id):
            self._set_status("Dodano wybor wyceny z bazy szybkich wycen.", ok=True)
        else:
            self._set_status("Nie znaleziono wybranej wyceny w tabeli.", ok=False)

    def _on_quick_add_from_receptura_clicked(self) -> None:
        if self._mode() != "quick":
            return
        source_rows = self._receptura_store.list_for_quote()
        if not source_rows:
            self._set_status("Brak pozycji receptury oznaczonych 'Do wyceny'.", ok=False)
            return
        picked_rows = pick_receptura_rows(
            self,
            source_rows,
            title="Wybierz pozycje z Receptury do szybkiej wyceny",
            subtitle="Wybrane pozycje zostana dodane jako nowe wpisy bazy szybkich wycen.",
            allow_multi=True,
        )
        if not picked_rows:
            return

        entries = self._load_quick_quotes()
        existing_ids = {str(item.get("id", "") or "").strip() for item in entries if isinstance(item, dict)}
        added_ids: list[str] = []
        for row in picked_rows:
            entry = build_quick_quote_entry_from_receptura(row, existing_ids=existing_ids)
            quick_id = str(entry.get("id", "") or "").strip()
            if not quick_id:
                continue
            existing_ids.add(quick_id)
            entries.append(entry)
            added_ids.append(quick_id)

        if not added_ids:
            self._set_status("Nie udalo sie przygotowac wpisow z Receptury.", ok=False)
            return
        if not self._write_quick_quotes(entries):
            return
        self.refresh_data()
        self._select_quick_row_by_id(added_ids[0])
        self._set_status(f"Dodano wpisy z Receptury: {len(added_ids)}.", ok=True)

    def _on_quick_remove_clicked(self) -> None:
        if self._mode() != "quick":
            return
        row = self._selected_quick_row()
        if row is None:
            self._set_status("Wybierz wpis z tabeli, aby usunac.", ok=False)
            return
        entry = dict(row.get("quick", {}))
        remove_id = str(entry.get("id", "") or "").strip()
        if not remove_id:
            self._set_status("Nie mozna usunac wpisu bez ID.", ok=False)
            return
        before = self._load_quick_quotes()
        after = [item for item in before if str(item.get("id", "") or "").strip() != remove_id]
        if len(after) == len(before):
            self._set_status("Nie znaleziono wpisu do usuniecia.", ok=False)
            return
        if not self._write_quick_quotes(after):
            return
        self.refresh_data()
        self._set_status("Usunieto wpis z bazy szybkich wycen.", ok=True)

    def _normalize_vat_text(self, raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return "23%"
        has_digit = any(ch.isdigit() for ch in text)
        has_alpha = any(ch.isalpha() for ch in text)
        if has_alpha and not has_digit:
            return text
        value = _text_to_float(text)
        if abs(value - round(value)) < 0.0001:
            return f"{int(round(value))}%"
        return f"{value:.2f}%"

    def _normalize_margin_text(self, raw: str) -> str:
        value = _text_to_float(raw)
        return f"{value:.2f}%"

    def _normalize_price_text(self, raw: str) -> str:
        value = _text_to_float(raw)
        return f"{value:.2f} zl"

    def _on_quick_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_table_refresh:
            return
        if self._mode() != "quick":
            return
        row = int(item.row())
        col = int(item.column())
        if col not in (2, 3):
            return
        id_item = self.tbl_assemblies.item(row, 0)
        quick_id = str(id_item.data(Qt.ItemDataRole.UserRole) if id_item is not None else "").strip()
        if not quick_id:
            quick_id = str(id_item.text() if id_item is not None else "").strip()
        if not quick_id:
            return

        entries = self._load_quick_quotes()
        target_index = -1
        for idx, entry in enumerate(entries):
            if str(entry.get("id", "") or "").strip() == quick_id:
                target_index = idx
                break
        if target_index < 0:
            return

        if col == 2:
            normalized = self._normalize_vat_text(item.text())
            entries[target_index]["vat"] = normalized
        else:
            normalized = self._normalize_margin_text(item.text())
            entries[target_index]["margin"] = normalized

        if not self._write_quick_quotes(entries):
            return

        was_blocked = self.tbl_assemblies.blockSignals(True)
        try:
            item.setText(normalized)
        finally:
            self.tbl_assemblies.blockSignals(was_blocked)
        self.refresh_data()

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        if self._mode() != "quick":
            return
        if col not in (2, 3):
            return
        item = self.tbl_assemblies.item(row, col)
        if item is None:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            return
        self.tbl_assemblies.editItem(item)

    def _on_mode_changed(self) -> None:
        if self._mode() == "quick":
            self.lab_scope.setText("Klient:")
            self.ed_search.setPlaceholderText("Szukaj po ID, kliencie lub nazwie szybkiej wyceny...")
            self.subtitle.setVisible(False)
            self.stats_widget.setVisible(False)
            self.right_panel.setVisible(False)
            self.main_splitter.setSizes([1, 0])
            self.quick_calc_frame.setVisible(True)
            self._refresh_quick_workers()
            self.lab_search.setVisible(False)
            self.ed_search.setVisible(False)
            self.lab_scope.setVisible(False)
            self.cb_order.setVisible(False)
            self.lab_quick_pick.setVisible(False)
            self.cb_quick_pick.setVisible(False)
            if self.cb_quick_pick.count() > 0:
                self.cb_quick_pick.setCurrentIndex(0)
            self.tbl_assemblies.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked
                | QTableWidget.EditTrigger.EditKeyPressed
                | QTableWidget.EditTrigger.AnyKeyPressed
                | QTableWidget.EditTrigger.SelectedClicked
            )
            self.btn_quick_add.setVisible(True)
            self.btn_quick_from_receptura.setVisible(True)
            self.btn_quick_remove.setVisible(True)
            self.btn_quick_export_pdf.setVisible(True)
            self.btn_quick_preview.setVisible(True)
            self._set_metric(self.card_count, "0")
            self._set_editor_enabled(False)
        else:
            self.lab_scope.setText("Zamówienie:")
            self.ed_search.setPlaceholderText("Szukaj po komplecie, kliencie, zamówieniu albo module...")
            self.subtitle.setVisible(True)
            self.stats_widget.setVisible(True)
            self.right_panel.setVisible(True)
            self.main_splitter.setSizes([3, 2])
            self.quick_calc_frame.setVisible(False)
            self.lab_search.setVisible(True)
            self.ed_search.setVisible(True)
            self.lab_scope.setVisible(True)
            self.cb_order.setVisible(True)
            self.lab_quick_pick.setVisible(False)
            self.cb_quick_pick.setVisible(False)
            self.tbl_assemblies.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.btn_quick_add.setVisible(False)
            self.btn_quick_from_receptura.setVisible(False)
            self.btn_quick_remove.setVisible(False)
            self.btn_quick_export_pdf.setVisible(False)
            self.btn_quick_preview.setVisible(False)
            self._set_editor_enabled(True)
        self._apply_mode_copy()
        self.refresh_data()

    def _selected_name(self) -> str:
        rows = self.tbl_assemblies.selectionModel().selectedRows() if self.tbl_assemblies.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_assemblies.item(int(rows[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _compute_totals(self, assembly) -> tuple[float, float, float, float]:
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)
        linked_wall = None
        wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
        if wall_name:
            linked_wall = self._wall_store.get(wall_name)
        resolved_items = resolve_assembly_items(
            assembly,
            self._catalog,
            auto_double_front_width_mm=auto_double_width,
            linked_wall=linked_wall,
        )
        technical_total = sum(item.cost_breakdown.grand_total_pln for item in resolved_items)
        base_total_raw = assembly.commercial_base_total(technical_total)
        base_total = self._pricing_service.apply_rules(base_total_raw, technical_total, self._pricing_rules)
        sale_total = self._pricing_service.compute_sale(base_total, float(getattr(assembly, "margin_percent", 0.0) or 0.0), self._policy_multiplier())
        profit_total = sale_total - base_total
        return technical_total, base_total, sale_total, profit_total

    def _compute_work_time_cost(self, assembly) -> WorkTimeCostBreakdown:
        project_codes = {
            str(getattr(assembly, "order_name", "") or "").strip(),
            str(getattr(assembly, "name", "") or "").strip(),
        }
        project_codes = {code for code in project_codes if code}
        if not project_codes:
            return WorkTimeCostBreakdown()
        workers_by_name = {
            str(worker.name or "").strip(): worker
            for worker in self._worker_store.list_workers()
            if str(worker.name or "").strip()
        }
        return compute_work_time_cost(self._work_time_store.list_sheets(), workers_by_name, project_codes)

    def open_assembly_for_pricing(self, assembly_name: str) -> None:
        """Przelacza na tryb 'Komplety' i zaznacza komplet o podanej nazwie."""
        target_name = str(assembly_name or "").strip()
        target_order = ""
        if target_name:
            assembly = self._assembly_store.get(target_name)
            if assembly is not None:
                target_order = str(getattr(assembly, "order_name", "") or "").strip()

        # upewnij sie ze jestesmy w trybie "assemblies"
        idx = self.cb_quote_mode.findData("assemblies")
        if idx >= 0:
            self.cb_quote_mode.setCurrentIndex(idx)
        self.refresh_data()

        # przy wejsciu z Kompletu automatycznie zawez filtr zamowienia
        if target_order:
            order_idx = self.cb_order.findData(target_order)
            if order_idx >= 0:
                self.cb_order.blockSignals(True)
                try:
                    self.cb_order.setCurrentIndex(order_idx)
                finally:
                    self.cb_order.blockSignals(False)
                self._refresh_table()

        # znajdz wiersz w tabeli i zaznacz
        for row in range(self.tbl_assemblies.rowCount()):
            item = self.tbl_assemblies.item(row, 0)
            if item is not None and item.text().strip() == target_name:
                self.tbl_assemblies.selectRow(row)
                self._on_selection_changed()
                break

    def refresh_data(self) -> None:
        if self._mode() == "quick":
            quotes = self._load_quick_quotes()
            self._refresh_quick_picker(quotes)
            values = sorted(
                {
                    str(item.get("client", "") or "").strip()
                    for item in quotes
                    if str(item.get("client", "") or "").strip()
                }
            )
            all_label = "Wszyscy klienci"
        else:
            assemblies = self._assembly_store.list_assemblies()
            values = sorted(
                {
                    str(getattr(item, "order_name", "") or "").strip()
                    for item in assemblies
                    if str(getattr(item, "order_name", "") or "").strip()
                }
            )
            all_label = "Wszystkie zamówienia"
        current_order = str(self.cb_order.currentData() or "").strip()
        self.cb_order.blockSignals(True)
        try:
            self.cb_order.clear()
            self.cb_order.addItem(all_label, "")
            for value in values:
                self.cb_order.addItem(value, value)
            idx = self.cb_order.findData(current_order)
            self.cb_order.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_order.blockSignals(False)
        self._refresh_table()

    def _filtered_rows(self) -> list[dict[str, object]]:
        search = self.ed_search.text().strip().lower()
        order_filter = str(self.cb_order.currentData() or "").strip()
        quick_filter = self._selected_quick_id()
        rows: list[dict[str, object]] = []
        if self._mode() == "quick":
            for entry in self._load_quick_quotes():
                quote_id = str(entry.get("id", "") or "").strip()
                if quick_filter and quote_id != quick_filter:
                    continue
                client_name = str(entry.get("client", "") or "").strip()
                if order_filter and client_name != order_filter:
                    continue
                sections = entry.get("sections", [])
                section_titles: list[str] = []
                if isinstance(sections, list):
                    for section in sections:
                        if not isinstance(section, dict):
                            continue
                        title = str(section.get("title", "") or "").strip()
                        if title:
                            section_titles.append(title)
                haystack = " ".join([quote_id, client_name, " ".join(section_titles)]).lower()
                if search and search not in haystack:
                    continue
                sale_total = _text_to_float(str(entry.get("price", "") or "0"))
                margin_percent = _text_to_float(str(entry.get("margin", "") or "0"))
                profit_total = sale_total * (margin_percent / 100.0)
                rows.append(
                    {
                        "quick": dict(entry),
                        "technical_total": 0.0,
                        "base_total": sale_total,
                        "sale_total": sale_total,
                        "profit_total": profit_total,
                        "margin_percent": margin_percent,
                        "section_count": len(section_titles),
                    }
                )
            return rows

        for assembly in self._assembly_store.list_assemblies():
            order_name = str(getattr(assembly, "order_name", "") or "").strip()
            if order_filter and order_name != order_filter:
                continue
            haystack = " ".join(
                [
                    str(getattr(assembly, "name", "") or ""),
                    str(getattr(assembly, "client_name", "") or ""),
                    order_name,
                    str(getattr(assembly, "worker_name", "") or ""),
                ]
            ).lower()
            if search and search not in haystack:
                continue
            technical_total, base_total, sale_total, profit_total = self._compute_totals(assembly)
            rows.append(
                {
                    "assembly": assembly,
                    "technical_total": technical_total,
                    "base_total": base_total,
                    "sale_total": sale_total,
                    "profit_total": profit_total,
                }
            )
        return rows

    def _refresh_table(self) -> None:
        current_name = self._selected_name()
        self._rows = self._filtered_rows()
        header = self.tbl_assemblies.horizontalHeader()
        self._is_table_refresh = True
        try:
            if self._mode() == "quick":
                self.tbl_assemblies.setColumnCount(7)
                self.tbl_assemblies.setHorizontalHeaderLabels(
                    ["ID", "Klient", "VAT", "Marża %", "Wartość materiałów", "Cena netto", "Cena brutto"]
                )
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
            else:
                self.tbl_assemblies.setColumnCount(7)
                self.tbl_assemblies.setHorizontalHeaderLabels(
                    ["Komplet", "Zamówienie", "Klient", "Techn.", "Robocizna", "Marża %", "Handlowa"]
                )
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
            self.tbl_assemblies.setRowCount(0)
            total_tech = 0.0
            total_sale = 0.0
            total_profit = 0.0
            for row_idx, row in enumerate(self._rows):
                technical_total = float(row["technical_total"])
                sale_total = float(row["sale_total"])
                profit_total = float(row["profit_total"])
                total_tech += technical_total
                total_sale += sale_total
                total_profit += profit_total
                self.tbl_assemblies.insertRow(row_idx)
                if self._mode() == "quick":
                    entry = dict(row.get("quick", {}))
                    quick_id = str(entry.get("id", "") or "")
                    vat_percent = _text_to_float(str(entry.get("vat", "") or "0"))
                    margin_percent = float(row.get("margin_percent", 0.0) or 0.0)
                    quick_totals = self._compute_quick_totals(
                        material_value=sale_total,
                        margin_percent=margin_percent,
                        vat_percent=vat_percent,
                        quick_id=quick_id,
                    )
                    values = [
                        str(entry.get("id", "") or "-"),
                        str(entry.get("client", "") or "-"),
                        str(entry.get("vat", "") or "-"),
                        f"{margin_percent:.2f} %",
                        f"{sale_total:.2f} zl",
                        f"{float(quick_totals.get('netto', 0.0) or 0.0):.2f} zl",
                        f"{float(quick_totals.get('brutto', 0.0) or 0.0):.2f} zl",
                    ]
                    user_key = quick_id
                else:
                    assembly = row["assembly"]
                    values = [
                        str(getattr(assembly, "name", "") or "-"),
                        str(getattr(assembly, "order_name", "") or "-"),
                        str(getattr(assembly, "client_name", "") or "-"),
                        f"{technical_total:.2f} zl",
                        f"{float(getattr(assembly, 'labor_cost_pln', 0.0) or 0.0):.2f} zl",
                        f"{float(getattr(assembly, 'margin_percent', 0.0) or 0.0):.1f} %",
                        f"{sale_total:.2f} zl",
                    ]
                    user_key = str(getattr(assembly, "name", "") or "")
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole, user_key)
                    if self._mode() == "quick":
                        editable = col in (2, 3)
                        if not editable:
                            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.tbl_assemblies.setItem(row_idx, col, item)
        finally:
            self._is_table_refresh = False
        self._set_metric(self.card_count, str(len(self._rows)))
        self._set_metric(self.card_tech, f"{total_tech:.2f} zl")
        self._set_metric(self.card_sale, f"{total_sale:.2f} zl")
        self._set_metric(self.card_profit, f"{total_profit:.2f} zl")
        self.lab_order_tech.setText(f"{total_tech:.2f} zl")
        self.lab_order_sale.setText(f"{total_sale:.2f} zl")
        self.lab_order_profit.setText(f"{total_profit:.2f} zl")
        if self._mode() != "quick":
            if self._active_role == "sales":
                self.tbl_assemblies.setColumnHidden(3, True)
                self.tbl_assemblies.setColumnHidden(4, False)
                self.tbl_assemblies.setColumnHidden(5, False)
                self.tbl_assemblies.setColumnHidden(6, False)
            elif self._active_role == "production":
                self.tbl_assemblies.setColumnHidden(3, False)
                self.tbl_assemblies.setColumnHidden(4, False)
                self.tbl_assemblies.setColumnHidden(5, True)
                self.tbl_assemblies.setColumnHidden(6, True)
            else:
                self.tbl_assemblies.setColumnHidden(3, False)
                self.tbl_assemblies.setColumnHidden(4, False)
                self.tbl_assemblies.setColumnHidden(5, False)
                self.tbl_assemblies.setColumnHidden(6, False)
        if current_name:
            for row in range(self.tbl_assemblies.rowCount()):
                item = self.tbl_assemblies.item(row, 0)
                if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == current_name:
                    self.tbl_assemblies.selectRow(row)
                    break
        self._on_selection_changed()

    def _selected_assembly(self):
        if self._mode() == "quick":
            return None
        name = self._selected_name()
        return self._assembly_store.get(name) if name else None

    def _selected_quick_row(self) -> dict[str, Any] | None:
        if self._mode() != "quick":
            return None
        key = self._selected_name()
        if not key:
            return None
        for row in self._rows:
            entry = row.get("quick")
            if not isinstance(entry, dict):
                continue
            if str(entry.get("id", "") or "").strip() == key:
                return dict(row)
        return None

    def _refresh_quick_adjustment_panel(self) -> None:
        row = self._selected_quick_row()
        self._is_quick_adjustment_refresh = True
        try:
            if row is None:
                self.quick_calc_frame.setEnabled(False)
                self.sp_quick_transport.setValue(0.0)
                self.sp_quick_hours.setValue(0.0)
                self.cb_quick_worker.setCurrentIndex(0)
                self.sp_quick_montage.setValue(0.0)
                self.tbl_quick_extras.blockSignals(True)
                self.tbl_quick_extras.setRowCount(0)
                self.tbl_quick_extras.blockSignals(False)
                self.lab_quick_material.setText("0.00 zl")
                self.lab_quick_rate.setText("0.00 zl/h")
                self.lab_quick_rate_source.setText("wg wydatkow firmy")
                self.lab_quick_labor_cost.setText("0.00 zl")
                self.lab_quick_base.setText("0.00 zl")
                self.lab_quick_netto.setText("0.00 zl")
                self.lab_quick_brutto.setText("0.00 zl")
                self._set_quick_breakdown_rows({})
                return
            self.quick_calc_frame.setEnabled(True)
            entry = dict(row.get("quick", {}))
            quick_id = str(entry.get("id", "") or "").strip()
            adj = self._quick_adjustment_for(quick_id)
            self.sp_quick_transport.setValue(float(adj.get("transport", 0.0) or 0.0))
            self.sp_quick_hours.setValue(float(adj.get("hours", 0.0) or 0.0))
            idx = self.cb_quick_worker.findData(str(adj.get("worker", "") or ""))
            self.cb_quick_worker.setCurrentIndex(idx if idx >= 0 else 0)
            self.sp_quick_montage.setValue(float(adj.get("montage", 0.0) or 0.0))
            self._load_quick_extras_to_table(list(adj.get("extras", []) or []))
            quick_totals = self._compute_quick_totals(
                material_value=float(row.get("sale_total", 0.0) or 0.0),
                margin_percent=float(row.get("margin_percent", 0.0) or 0.0),
                vat_percent=_text_to_float(str(entry.get("vat", "") or "0")),
                quick_id=quick_id,
            )
            self.lab_quick_material.setText(f"{float(quick_totals.get('material_value', 0.0) or 0.0):.2f} zl")
            self.lab_quick_rate.setText(f"{float(quick_totals.get('hour_rate', 0.0) or 0.0):.2f} zl/h")
            rate_source = str(quick_totals.get("rate_source", "") or "").strip()
            self.lab_quick_rate_source.setText(rate_source if rate_source and rate_source != "wydatki" else "wg wydatkow firmy")
            self.lab_quick_labor_cost.setText(f"{float(quick_totals.get('labor_cost', 0.0) or 0.0):.2f} zl")
            self.lab_quick_base.setText(f"{float(quick_totals.get('base_total', 0.0) or 0.0):.2f} zl")
            self.lab_quick_netto.setText(f"{float(quick_totals.get('netto', 0.0) or 0.0):.2f} zl")
            self.lab_quick_brutto.setText(f"{float(quick_totals.get('brutto', 0.0) or 0.0):.2f} zl")
            self._set_quick_breakdown_rows(quick_totals)
        finally:
            self._is_quick_adjustment_refresh = False

    def _on_quick_adjustment_changed(self) -> None:
        if self._is_quick_adjustment_refresh:
            return
        if self._mode() != "quick":
            return
        row = self._selected_quick_row()
        if row is None:
            return
        entry = dict(row.get("quick", {}))
        quick_id = str(entry.get("id", "") or "").strip()
        if not quick_id:
            return
        self._quick_adjustments[quick_id] = {
            "transport": float(self.sp_quick_transport.value()),
            "hours": float(self.sp_quick_hours.value()),
            "worker": str(self.cb_quick_worker.currentData() or ""),
            "montage": float(self.sp_quick_montage.value()),
            "extras": self._read_quick_extras_from_table(),
        }
        self._refresh_table()
        self._select_quick_row_by_id(quick_id)
        self._refresh_quick_adjustment_panel()

    # ── USLUGI DODATKOWE helpers ───────────────────────────────────────────

    def _read_quick_extras_from_table(self) -> list[dict[str, object]]:
        extras: list[dict[str, object]] = []
        for r in range(self.tbl_quick_extras.rowCount()):
            desc_item = self.tbl_quick_extras.item(r, 0)
            amt_item = self.tbl_quick_extras.item(r, 1)
            desc = str(desc_item.text() if desc_item else "").strip()
            try:
                amount = float(
                    (amt_item.text() if amt_item else "0")
                    .replace(",", ".")
                    .strip() or "0"
                )
            except Exception:
                amount = 0.0
            extras.append({"desc": desc, "amount": amount})
        return extras

    def _load_quick_extras_to_table(self, extras: list[dict]) -> None:
        self.tbl_quick_extras.blockSignals(True)
        try:
            self.tbl_quick_extras.setRowCount(0)
            for e in extras:
                if not isinstance(e, dict):
                    continue
                r = self.tbl_quick_extras.rowCount()
                self.tbl_quick_extras.insertRow(r)
                self.tbl_quick_extras.setItem(r, 0, QTableWidgetItem(str(e.get("desc", "") or "")))
                self.tbl_quick_extras.setItem(r, 1, QTableWidgetItem(f"{float(e.get('amount', 0.0) or 0.0):.2f}"))
        finally:
            self.tbl_quick_extras.blockSignals(False)

    def _on_quick_extras_item_changed(self) -> None:
        if not self._is_quick_adjustment_refresh:
            self._on_quick_adjustment_changed()

    def _on_quick_extra_add(self) -> None:
        r = self.tbl_quick_extras.rowCount()
        self.tbl_quick_extras.blockSignals(True)
        self.tbl_quick_extras.insertRow(r)
        self.tbl_quick_extras.setItem(r, 0, QTableWidgetItem(""))
        self.tbl_quick_extras.setItem(r, 1, QTableWidgetItem("0.00"))
        self.tbl_quick_extras.blockSignals(False)
        self.tbl_quick_extras.editItem(self.tbl_quick_extras.item(r, 0))
        self._on_quick_adjustment_changed()

    def _on_quick_extra_remove(self) -> None:
        selected = self.tbl_quick_extras.selectedItems()
        rows = sorted({i.row() for i in selected}, reverse=True)
        if not rows:
            last = self.tbl_quick_extras.rowCount() - 1
            if last < 0:
                return
            rows = [last]
        self.tbl_quick_extras.blockSignals(True)
        for r in rows:
            self.tbl_quick_extras.removeRow(r)
        self.tbl_quick_extras.blockSignals(False)
        self._on_quick_adjustment_changed()

    def _on_selection_changed(self) -> None:
        if self._mode() == "quick":
            self._on_selection_changed_quick()
            return
        assembly = self._selected_assembly()
        self._is_loading = True
        try:
            if assembly is None:
                self.lab_selected.setText("Wybierz komplet z listy.")
                self.sp_labor.setValue(0.0)
                self.sp_transport.setValue(0.0)
                self.sp_montage.setValue(0.0)
                self.sp_margin.setValue(0.0)
                self.lab_base_total.setText("0.00 zl")
                self.lab_sale_total.setText("0.00 zl")
                self.lab_profit_total.setText("0.00 zl")
                self.lab_time_days.setText("0")
                self.lab_time_hours.setText("0.00 h")
                self.lab_time_overtime.setText("0.00 zl")
                self.lab_time_stage_extra.setText("0.00 zl")
                self.lab_time_extra.setText("0.00 zl")
                self.lab_time_cost.setText("0.00 zl")
                self.btn_load_labor_from_time.setEnabled(False)
                self.lab_profit_report.setText("")
                self.client_info_box.hide()
                self.payments_box.hide()
                self.dates_box.hide()
                return
            self.lab_selected.setText(
                f'Komplet: {assembly.name} | Zamówienie: {assembly.order_name or "-"} | Klient: {assembly.client_name or "-"}'
            )
            self.sp_labor.setValue(float(getattr(assembly, "labor_cost_pln", 0.0) or 0.0))
            self.sp_transport.setValue(float(getattr(assembly, "transport_cost_pln", 0.0) or 0.0))
            self.sp_montage.setValue(float(getattr(assembly, "montage_cost_pln", 0.0) or 0.0))
            self.sp_margin.setValue(float(getattr(assembly, "margin_percent", 0.0) or 0.0))
            breakdown = self._compute_work_time_cost(assembly)
            self.lab_time_days.setText(str(breakdown.tracked_days))
            self.lab_time_hours.setText(f"{breakdown.total_hours:.2f} h")
            self.lab_time_overtime.setText(f"{breakdown.overtime_total:.2f} zl")
            self.lab_time_stage_extra.setText(f"{breakdown.stage_extra_total:.2f} zl")
            self.lab_time_extra.setText(f"{breakdown.manual_extra_total:.2f} zl")
            self.lab_time_cost.setText(f"{breakdown.total_cost:.2f} zl")
            self.btn_load_labor_from_time.setEnabled(breakdown.total_cost > 0.0)
            self._refresh_editor_totals()
            self._refresh_order_info_panels(assembly.order_name, assembly.client_name)
        finally:
            self._is_loading = False

    def _refresh_order_info_panels(self, order_name: str, assembly_client_name: str) -> None:
        """Odświeża panele z klientem, płatnościami i terminami na podstawie zamówienia."""
        order = self._order_store.get(order_name) if order_name else None

        # --- Klient ---
        client_name = (order.client_name if order else "") or assembly_client_name or "-"
        client = self._client_store.get(client_name) if client_name and client_name != "-" else None
        self.lab_order_code_val.setText(order_name or "-")
        self.lab_client_name_val.setText(client_name)
        self.lab_client_phone_val.setText((client.phone if client and client.phone else "-"))
        self.lab_client_email_val.setText((client.email if client and client.email else "-"))
        self.client_info_box.setVisible(bool(client_name and client_name != "-"))

        # --- Płatności ---
        if order and order.customer_payments:
            payments = order.customer_payments
            sale_total = 0.0
            # Policz sumę z ratami procentowymi (wyklucz "Rezerwacja terminu")
            for p in payments:
                stage = str(p.get("stage", "") or "")
                if "Rezerwacja" not in stage:
                    sale_total += float(p.get("amount", 0.0) or 0.0)

            lines: list[str] = []
            for p in payments:
                stage = str(p.get("stage", "") or "")
                amount = float(p.get("amount", 0.0) or 0.0)
                paid = bool(p.get("paid", False))
                status_icon = "✓" if paid else "○"
                lines.append(f"{status_icon}  {stage}: {amount:,.0f} zł")
            self.lab_payments_rows.setText("\n".join(lines))
            self.payments_box.show()
        else:
            # Brak zapisanych płatności — pokaż wzorcową strukturę
            self.lab_payments_rows.setText(
                "○  Rezerwacja terminu: 5 000 zł\n"
                "○  Start pracy / 60%: —\n"
                "○  Przed montażem / 30%: —\n"
                "○  Koniec / 10%: —"
            )
            self.payments_box.show()

        # --- Terminy ---
        def _d(val: str) -> str:
            return val.strip() if val and val.strip() else "—"

        if order:
            self.lab_d_wycena.setText(_d(order.date_wycena))
            self.lab_d_projekt.setText(_d(order.date_projekt))
            self.lab_d_probki.setText(_d(order.date_probki))
            self.lab_d_zakup_mat.setText(_d(order.date_zakup_mat))
            self.lab_d_produkcja.setText(_d(order.date_produkcja))
            self.lab_d_montaz.setText(_d(order.date_montaz))
            self.lab_d_poprawki.setText(_d(order.date_poprawki))
            self.dates_box.show()
        else:
            for lbl in (
                self.lab_d_wycena, self.lab_d_projekt, self.lab_d_probki,
                self.lab_d_zakup_mat, self.lab_d_produkcja, self.lab_d_montaz, self.lab_d_poprawki,
            ):
                lbl.setText("—")
            self.dates_box.show()

    def _on_selection_changed_quick(self) -> None:
        row = self._selected_quick_row()
        self._is_loading = True
        try:
            self.sp_labor.setValue(0.0)
            self.sp_transport.setValue(0.0)
            self.sp_montage.setValue(0.0)
            self.sp_margin.setValue(0.0)
            self.lab_time_days.setText("0")
            self.lab_time_hours.setText("0.00 h")
            self.lab_time_overtime.setText("0.00 zl")
            self.lab_time_stage_extra.setText("0.00 zl")
            self.lab_time_extra.setText("0.00 zl")
            self.lab_time_cost.setText("0.00 zl")
            self.btn_load_labor_from_time.setEnabled(False)
            self._set_editor_enabled(False)
            if row is None:
                self.lab_selected.setText("Wybierz wpis z bazy szybkich wycen.")
                self.lab_base_total.setText("0.00 zl")
                self.lab_sale_total.setText("0.00 zl")
                self.lab_profit_total.setText("0.00 zl")
                self._refresh_quick_adjustment_panel()
                return
            entry = dict(row.get("quick", {}))
            quote_id = str(entry.get("id", "") or "").strip()
            if quote_id and self.cb_quick_pick.isVisible():
                idx = self.cb_quick_pick.findData(quote_id)
                if idx >= 0 and self.cb_quick_pick.currentIndex() != idx:
                    self.cb_quick_pick.blockSignals(True)
                    self.cb_quick_pick.setCurrentIndex(idx)
                    self.cb_quick_pick.blockSignals(False)
            material_value = float(row.get("sale_total", 0.0) or 0.0)
            margin = float(row.get("margin_percent", 0.0) or 0.0)
            vat = str(entry.get("vat", "") or "").strip() or "-"
            quick_totals = self._compute_quick_totals(
                material_value=material_value,
                margin_percent=margin,
                vat_percent=_text_to_float(vat),
                quick_id=quote_id,
            )
            rate_source = str(quick_totals.get("rate_source", "") or "").strip()
            worker_label = "wydatki firmy" if not rate_source or rate_source == "wydatki" else rate_source
            self.lab_selected.setText(
                f'ID: {entry.get("id", "-")} | Klient: {entry.get("client", "-")} | VAT: {vat} | Marża: {margin:.2f}% | Pracownik: {worker_label}'
            )
            base_total = float(quick_totals.get("base_total", 0.0) or 0.0)
            netto = float(quick_totals.get("netto", 0.0) or 0.0)
            brutto = float(quick_totals.get("brutto", 0.0) or 0.0)
            self.lab_base_total.setText(f"{base_total:.2f} zl")
            self.lab_sale_total.setText(f"{netto:.2f} zl")
            self.lab_profit_total.setText(f"{(netto - base_total):.2f} zl")
            self._refresh_quick_adjustment_panel()
        finally:
            self._is_loading = False

    def _refresh_editor_totals(self) -> None:
        if self._is_loading:
            return
        if self._mode() == "quick":
            row = self._selected_quick_row()
            if not row:
                self.lab_base_total.setText("0.00 zl")
                self.lab_sale_total.setText("0.00 zl")
                self.lab_profit_total.setText("0.00 zl")
                return
            entry = dict(row.get("quick", {}))
            material_value = float(row.get("sale_total", 0.0) or 0.0)
            margin = float(row.get("margin_percent", 0.0) or 0.0)
            vat = _text_to_float(str(entry.get("vat", "") or "0"))
            quick_totals = self._compute_quick_totals(
                material_value,
                margin,
                vat,
                str(entry.get("id", "") or ""),
            )
            base_total = float(quick_totals.get("base_total", 0.0) or 0.0)
            netto = float(quick_totals.get("netto", 0.0) or 0.0)
            brutto = float(quick_totals.get("brutto", 0.0) or 0.0)
            self.lab_base_total.setText(f"{base_total:.2f} zl")
            self.lab_sale_total.setText(f"{netto:.2f} zl")
            self.lab_profit_total.setText(f"{(netto - base_total):.2f} zl")
            extras_total = float(quick_totals.get("extras_total", 0.0) or 0.0)
            self.lab_profit_report.setText(
                f"Rentowność (wstępna): netto {netto:.2f} zl | brutto {brutto:.2f} zl | "
                f"baza {base_total:.2f} zl | materiały {material_value:.2f} zl | usługi dodatkówe {extras_total:.2f} zl"
            )
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self.lab_base_total.setText("0.00 zl")
            self.lab_sale_total.setText("0.00 zl")
            self.lab_profit_total.setText("0.00 zl")
            self.lab_profit_report.setText("")
            return
        technical_total, _base_total, _sale_total, _profit_total = self._compute_totals(assembly)
        base_total_raw = technical_total + float(self.sp_labor.value()) + float(self.sp_transport.value()) + float(self.sp_montage.value())
        base_total = self._pricing_service.apply_rules(base_total_raw, technical_total, self._pricing_rules)
        sale_total = self._pricing_service.compute_sale(base_total, float(self.sp_margin.value()), self._policy_multiplier())
        profit_total = sale_total - base_total
        self.lab_base_total.setText(f"{base_total:.2f} zl")
        self.lab_sale_total.setText(f"{sale_total:.2f} zl")
        self.lab_profit_total.setText(f"{profit_total:.2f} zl")
        self.lab_profit_report.setText(self._build_profitability_text(base_total, sale_total, technical_total))

    def _build_profitability_text(self, base_total: float, sale_total: float, technical_total: float) -> str:
        fixed_total = float(self._expenses_store.sum_items("fixed"))
        variable_total = float(self._expenses_store.sum_items("variable"))
        monthly_overhead = fixed_total + variable_total
        assemblies_count = max(1, len(self._rows) or 1)
        allocated_overhead = monthly_overhead / assemblies_count
        operational_cost = float(base_total) + allocated_overhead
        operational_profit = float(sale_total) - operational_cost
        margin_percent = (operational_profit / sale_total * 100.0) if sale_total > 0 else 0.0
        return (
            f"Raport: techniczny {technical_total:.2f} zl | baza {base_total:.2f} zl | "
            f"koszt operacyjny {operational_cost:.2f} zl | zysk {operational_profit:.2f} zl ({margin_percent:.1f}%)"
        )

    def get_summary_snapshot(self) -> dict[str, float | str]:
        """
        Zwraca czytelny snapshot do zakladki Podsumowanie w hubie Wycena.

        Dla trybu szybkie wyceny pokazuje rowniez us?ugi dodatkówe jako jawny skladnik kosztu.
        """
        mode = self._mode()
        if mode == "quick":
            row = self._selected_quick_row()
            if row is None:
                self._last_project_model = None
                return {
                    "mode": "quick",
                    "title": "Szybka wycena",
                    "base_total": 0.0,
                    "sale_total": 0.0,
                    "profit_total": 0.0,
                    "material_value": 0.0,
                    "extras_total": 0.0,
                    "transport": 0.0,
                    "labor_cost": 0.0,
                    "montage": 0.0,
                    "vat": 0.0,
                    "report": "Brak wybranej wyceny z bazy szybkich wycen.",
                }
            entry = dict(row.get("quick", {}))
            material_value = float(row.get("sale_total", 0.0) or 0.0)
            margin = float(row.get("margin_percent", 0.0) or 0.0)
            vat = _text_to_float(str(entry.get("vat", "") or "0"))
            quick_totals = self._compute_quick_totals(
                material_value,
                margin,
                vat,
                str(entry.get("id", "") or ""),
            )
            netto = float(quick_totals.get("netto", 0.0) or 0.0)
            base_total = float(quick_totals.get("base_total", 0.0) or 0.0)
            labor_cost = float(quick_totals.get("labor_cost", 0.0) or 0.0)
            self._last_project_model = build_quick_quote_project_model(
                entry,
                quick_totals,
                quick_adjustment=self._quick_adjustment_for(str(entry.get("id", "") or "")),
                archive_path=str(data_dir() / "quick_quote_archive.json"),
                pricing_policy=self._active_policy,
                policy_multiplier=self._policy_multiplier(),
            )
            return {
                "mode": "quick",
                "title": "Szybka wycena",
                "client": str(entry.get("client", "") or ""),
                "quote_id": str(entry.get("id", "") or ""),
                "base_total": base_total,
                "sale_total": netto,
                "brutto_total": float(quick_totals.get("brutto", 0.0) or 0.0),
                "profit_total": netto - base_total,
                "material_value": float(quick_totals.get("material_value", 0.0) or 0.0),
                "extras_total": float(quick_totals.get("extras_total", 0.0) or 0.0),
                "transport": float(quick_totals.get("transport", 0.0) or 0.0),
                "labor_cost": labor_cost,
                "montage": float(quick_totals.get("montage", 0.0) or 0.0),
                "vat": vat,
                "report": self.lab_profit_report.text(),
            }

        assembly = self._selected_assembly()
        if assembly is None:
            self._last_project_model = None
            return {
                "mode": "assemblies",
                "title": "Wycena projektu",
                "base_total": 0.0,
                "sale_total": 0.0,
                "profit_total": 0.0,
                "technical_total": 0.0,
                "labor_cost": 0.0,
                "transport_cost": 0.0,
                "montage_cost": 0.0,
                "report": "Wybierz komplet z listy.",
            }
        technical_total, base_total, sale_total, profit_total = self._compute_totals(assembly)
        self._last_project_model = build_assembly_project_model(
            assembly,
            self._catalog,
            self._wall_store,
            technical_total=technical_total,
            base_total=base_total,
            sale_total=sale_total,
            profit_total=profit_total,
            labor_cost=float(self.sp_labor.value()),
            transport_cost=float(self.sp_transport.value()),
            montage_cost=float(self.sp_montage.value()),
            pricing_policy=self._active_policy,
            policy_multiplier=self._policy_multiplier(),
        )
        return {
            "mode": "assemblies",
            "title": "Wycena projektu",
            "assembly": str(getattr(assembly, "name", "") or ""),
            "order": str(getattr(assembly, "order_name", "") or ""),
            "client": str(getattr(assembly, "client_name", "") or ""),
            "base_total": float(base_total),
            "sale_total": float(sale_total),
            "profit_total": float(profit_total),
            "technical_total": float(technical_total),
            "labor_cost": float(self.sp_labor.value()),
            "transport_cost": float(self.sp_transport.value()),
            "montage_cost": float(self.sp_montage.value()),
            "margin_percent": float(self.sp_margin.value()),
            "report": self.lab_profit_report.text(),
        }

    def get_project_model(self) -> ProjectModel | None:
        return self._last_project_model

    def _on_save(self) -> None:
        if self._mode() == "quick":
            self._set_status("Tryb 'Wycena wstępna' jest podglądem z bazy szybkich wycen.", ok=True)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return
        assembly.labor_cost_pln = float(self.sp_labor.value())
        assembly.transport_cost_pln = float(self.sp_transport.value())
        assembly.montage_cost_pln = float(self.sp_montage.value())
        assembly.margin_percent = float(self.sp_margin.value())
        result = self._assembly_store.overwrite(assembly)
        self._refresh_table()
        self._set_status(result.message_pl, ok=result.ok)

    def _on_clear(self) -> None:
        if self._mode() == "quick":
            self._set_status("W trybie 'Wycena wstępna' nie ma dodatków do wyczyszczenia.", ok=True)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return
        assembly.labor_cost_pln = 0.0
        assembly.transport_cost_pln = 0.0
        assembly.montage_cost_pln = 0.0
        assembly.margin_percent = 0.0
        result = self._assembly_store.overwrite(assembly)
        self._refresh_table()
        self._set_status("Wyczyszczono kalkulacje handlowa." if result.ok else result.message_pl, ok=result.ok)

    # ── SZABLONY ─────────────────────────────────────────────────

    def _refresh_preset_combo(self) -> None:
        self.cb_preset.blockSignals(True)
        self.cb_preset.clear()
        for preset in self._preset_store.load():
            label = str(preset.get("name") or "")
            self.cb_preset.addItem(label, preset)
        self.cb_preset.blockSignals(False)

    def _on_preset_save(self) -> None:
        name, ok = _ask_preset_name(self)
        if not ok or not name.strip():
            return
        self._preset_store.save_preset(
            name=name.strip(),
            transport_flat=float(self.sp_transport.value()),
            montage_flat=float(self.sp_montage.value()),
            margin_percent=float(self.sp_margin.value()),
        )
        self._refresh_preset_combo()
        self._set_status(f"Zapisano szablon \"{name.strip()}\".", ok=True)

    def _on_preset_load(self) -> None:
        preset = self.cb_preset.currentData()
        if not isinstance(preset, dict):
            self._set_status("Wybierz szablon z listy.", ok=False)
            return
        self.sp_transport.setValue(float(preset.get("transport_flat", 0.0) or 0.0))
        self.sp_montage.setValue(float(preset.get("montage_flat", 0.0) or 0.0))
        self.sp_margin.setValue(float(preset.get("margin_percent", 0.0) or 0.0))
        self._set_status(f"Wczytano szablon \"{preset.get('name', '')}\".", ok=True)

    def _on_preset_delete(self) -> None:
        preset = self.cb_preset.currentData()
        if not isinstance(preset, dict):
            self._set_status("Wybierz szablon do usuniecia.", ok=False)
            return
        preset_id = str(preset.get("id") or "")
        name = str(preset.get("name") or "")
        reply = QMessageBox.question(
            self,
            "Usun szablon",
            f"Usunac szablon \"{name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._preset_store.delete_preset(preset_id)
        self._refresh_preset_combo()
        self._set_status(f"Usunieto szablon \"{name}\".", ok=True)

    def _on_load_labor_from_time(self) -> None:
        if self._mode() == "quick":
            self._set_status("Dla wyceny wstepnej robocizna nie jest pobierana z Czas pracy.", ok=False)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return
        breakdown = self._compute_work_time_cost(assembly)
        self.sp_labor.setValue(float(breakdown.total_cost))
        self._set_status("Przepisano robocizne z Czas pracy.", ok=True)

    def _on_export_purchase_csv(self) -> None:
        if self._mode() == "quick":
            self._set_status("Eksport zakupu dotyczy trybu 'Komplety'.", ok=False)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return

        linked_wall = self._wall_store.get(str(getattr(assembly, "wall_name", "") or "")) if str(getattr(assembly, "wall_name", "") or "").strip() else None
        resolved_items = resolve_assembly_items(
            assembly,
            self._catalog,
            auto_double_front_width_mm=float(load_drawing_settings().auto_double_front_width_mm or 600.0),
            linked_wall=linked_wall,
        )

        export_rows: list[list[str]] = [["Modul", "Typ", "Kod", "Nazwa", "Ilość", "Jednostka", "Koszt [zl]"]]
        for resolved in resolved_items:
            display = str(getattr(resolved, "display_name", "") or "Modul")
            breakdown = resolved.cost_breakdown
            for line in breakdown.material_lines:
                export_rows.append([display, "material", str(line.key), str(line.label), f"{line.area_m2:.3f}", "m2", f"{line.cost_pln:.2f}"])
            for line in breakdown.edgeband_lines:
                export_rows.append([display, "okleina", str(line.key), str(line.label), f"{line.length_m:.3f}", "m", f"{line.cost_pln:.2f}"])
            for line in breakdown.hardware_lines:
                label = f"{line.label} ({line.manufacturer})".strip()
                export_rows.append([display, "okucie", str(line.key), label, f"{line.quantity:.3f}", str(line.unit), f"{line.cost_pln:.2f}"])

        default_name = f"zakup_{str(assembly.name or 'komplet').replace(' ', '_')}.csv"
        target_path, _ = QFileDialog.getSaveFileName(self, "Zapisz eksport zakupu", default_name, "CSV (*.csv)")
        if not target_path:
            return
        with Path(target_path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerows(export_rows)
        self._set_status(f"Zapisano eksport zakupu: {target_path}", ok=True)

    def _on_export_profitability_report(self) -> None:
        if self._mode() == "quick":
            self._set_status("Raport rentownosci dotyczy trybu 'Komplety'.", ok=False)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return

        technical_total, _base, _sale, _profit = self._compute_totals(assembly)
        base_total_raw = technical_total + float(self.sp_labor.value()) + float(self.sp_transport.value()) + float(self.sp_montage.value())
        base_total = self._pricing_service.apply_rules(base_total_raw, technical_total, self._pricing_rules)
        sale_total = self._pricing_service.compute_sale(base_total, float(self.sp_margin.value()), self._policy_multiplier())
        report_line = self._build_profitability_text(base_total, sale_total, technical_total)

        report_text = (
            f"Raport rentownosci\n"
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Komplet: {assembly.name}\n"
            f"Zamówienie: {assembly.order_name or '-'}\n"
            f"Klient: {assembly.client_name or '-'}\n"
            f"Polityka cenowa: {self.cb_policy.currentText()} (x{self._policy_multiplier():.2f})\n"
            f"Rola: {self.cb_role.currentText()}\n"
            f"{report_line}\n"
        )

        default_name = f"rentownosc_{str(assembly.name or 'komplet').replace(' ', '_')}.txt"
        target_path, _ = QFileDialog.getSaveFileName(self, "Zapisz raport rentownosci", default_name, "TXT (*.txt)")
        if not target_path:
            self.lab_profit_report.setText(report_line)
            return
        try:
            Path(target_path).write_text(report_text, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Blad zapisu danych",
                f"Nie udalo sie zapisac raportu rentownosci.\n\nSzczegoly: {exc}",
            )
            return
        self.lab_profit_report.setText(report_line)
        self._set_status(f"Zapisano raport rentownosci: {target_path}", ok=True)

    def _on_quick_export_pdf(self) -> None:
        if self._mode() != "quick":
            self._set_status("Eksport PDF działa w trybie 'Szybka wycena'.", ok=False)
            return
        
        row = self._selected_quick_row()
        if row is None:
            self._set_status("Wybierz wpis z bazy szybkich wycen.", ok=False)
            return
        
        entry = dict(row.get("quick", {}))
        quick_id = str(entry.get("id", "") or "").strip()
        client_name = str(entry.get("client", "") or "-").strip()
        if not quick_id:
            self._set_status("Brak ID wyceny.", ok=False)
            return

        default_name = f"wycena_szybka_{quick_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport PDF szybkiej wyceny",
            default_name,
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))

        document = QTextDocument(self)
        document.setDocumentMargin(20.0)
        document.setHtml(self._build_quick_pdf_html(entry, row))
        document.print(printer)
        self._set_status(f'Wyeksportowano PDF szybkiej wyceny do "{output_path.name}".', ok=True)

    def _build_quick_pdf_html(self, entry: dict, row: dict) -> str:
        quick_id = str(entry.get("id", "") or "-").strip()
        client_name = str(entry.get("client", "") or "-").strip()
        description = str(entry.get("name", entry.get("description", "")) or "").strip()
        vat = str(entry.get("vat", "") or "23").strip()
        margin = float(row.get("margin_percent", 0.0) or 0.0)
        material_value = float(row.get("sale_total", 0.0) or 0.0)

        try:
            vat_percent = float(vat) if vat else 23.0
        except ValueError:
            vat_percent = 23.0

        totals = self._compute_quick_totals(
            material_value=material_value,
            margin_percent=margin,
            vat_percent=vat_percent,
            quick_id=quick_id,
        )
        adj = self._quick_adjustment_for(quick_id)
        transport = float(adj.get("transport", 0.0) or 0.0)
        hours = float(adj.get("hours", 0.0) or 0.0)
        montage = float(adj.get("montage", 0.0) or 0.0)
        extras_list = list(adj.get("extras", []) or [])
        extras_total = float(totals.get("extras_total", 0.0) or 0.0)
        labor_cost = float(totals.get("labor_cost", 0.0) or 0.0)
        hour_rate = float(totals.get("hour_rate", 0.0) or 0.0)
        base_total = float(totals.get("base_total", 0.0) or 0.0)
        netto = float(totals.get("netto", 0.0) or 0.0)
        brutto = float(totals.get("brutto", 0.0) or 0.0)

        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        # Us?ugi dodatkówe HTML
        extras_html = ""
        if extras_list:
            rows_html = "".join(
                f'<tr><td>{str(e.get("desc","") or "Usluga")}</td>'
                f'<td style="text-align:right">{float(e.get("amount",0) or 0):.2f} zl</td></tr>'
                for e in extras_list if isinstance(e, dict)
            )
            extras_html = f"""
            <h3 style="margin-top:16px;">Usługi dodatkówe</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
              <thead><tr style="background:#edf2f7;">
                <th style="text-align:left;padding:6px;">Opis</th>
                <th style="text-align:right;padding:6px;">Kwota</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>"""

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 30px; color: #1a202c; font-size: 14px; }}
  h1 {{ color: #1a365d; border-bottom: 3px solid #2b6cb0; padding-bottom: 8px; margin-bottom: 16px; font-size: 22px; }}
  h2 {{ color: #2d3748; font-size: 15px; margin: 18px 0 6px 0; }}
  h3 {{ color: #4a5568; font-size: 13px; margin: 12px 0 4px 0; }}
  .header-info {{ background: #edf2f7; padding: 12px 16px; border-radius: 6px; margin-bottom: 18px; line-height: 1.7; }}
  .kv {{ display: flex; gap: 8px; }}
  .kv b {{ min-width: 120px; }}
  .box {{ border: 1px solid #bee3f8; border-radius: 6px; padding: 12px 16px; margin: 12px 0; background: #ebf8ff; }}
  .row {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed #c3dafe; font-size: 13px; }}
  .row:last-child {{ border-bottom: none; }}
  .bold {{ font-weight: 700; }}
  .big {{ font-size: 16px; font-weight: 700; color: #1a365d; }}
  .green {{ color: #276749; font-weight: 700; }}
  .footer {{ margin-top: 28px; padding-top: 12px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 11px; }}
</style>
</head>
<body>
  <h1>WYCENA</h1>
  <div class="header-info">
    <div class="kv"><b>ID wyceny:</b> {quick_id}</div>
    <div class="kv"><b>Klient:</b> {client_name or "—"}</div>
    {"<div class='kv'><b>Opis:</b> " + description + "</div>" if description else ""}
    <div class="kv"><b>Data:</b> {now}</div>
    <div class="kv"><b>VAT:</b> {vat}%</div>
  </div>

  <h2>Kosztorys</h2>
  <div class="box">
    <div class="row"><span>Wartość materiałów</span><span>{material_value:,.2f} zł</span></div>
    <div class="row"><span>Transport</span><span>{transport:,.2f} zł</span></div>
    <div class="row"><span>Robocizna ({hours:.2f} h × {hour_rate:.2f} zł/h)</span><span>{labor_cost:,.2f} zł</span></div>
    <div class="row"><span>Montaż</span><span>{montage:,.2f} zł</span></div>
    {"<div class='row'><span>Usługi dodatkówe</span><span>" + f"{extras_total:,.2f} zł</span></div>" if extras_total else ""}
    <div class="row bold"><span>Koszt bazowy</span><span>{base_total:,.2f} zł</span></div>
  </div>

  {extras_html}

  <h2>Cena końcowa</h2>
  <div class="box">
    <div class="row"><span>Marża</span><span>{margin:.1f}%</span></div>
    <div class="row big"><span>NETTO</span><span>{netto:,.2f} zł</span></div>
    <div class="row big green"><span>BRUTTO ({vat}% VAT)</span><span>{brutto:,.2f} zł</span></div>
  </div>

  <div class="footer">
    Wygenerowano: {now} &nbsp;|&nbsp; TECH_modul
  </div>
</body>
</html>"""
        return html

    def _on_quick_preview(self) -> None:
        """Podglad wyceny w oknie przed eksportem PDF."""
        if self._mode() != "quick":
            return
        row = self._selected_quick_row()
        if row is None:
            self._set_status("Wybierz wpis z bazy szybkich wycen.", ok=False)
            return
        entry = dict(row.get("quick", {}))
        html = self._build_quick_pdf_html(entry, row)

        from PyQt6.QtWidgets import QTextBrowser
        dlg = QDialog(self)
        dlg.setWindowTitle("Podglad wyceny")
        dlg.resize(700, 600)
        lay = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setHtml(html)
        lay.addWidget(browser, 1)
        btn_row = QHBoxLayout()
        btn_pdf = QPushButton("Zapisz PDF...", dlg)
        btn_close = QPushButton("Zamknij", dlg)
        btn_row.addWidget(btn_pdf)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)
        btn_close.clicked.connect(dlg.reject)
        btn_pdf.clicked.connect(lambda: (dlg.accept(), self._on_quick_export_pdf()))
        dlg.exec()

    def _on_export_pdf(self) -> None:
        if self._mode() == "quick":
            self._set_status("Eksport PDF działa w trybie 'Komplety'.", ok=False)
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return

        default_name = f"wycena_{str(assembly.name or 'komplet').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport PDF wyceny",
            default_name,
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))

        document = QTextDocument(self)
        document.setDocumentMargin(20.0)
        document.setHtml(self._build_wycena_pdf_html(assembly))
        document.print(printer)
        self._set_status(f'Wyeksportowano PDF wyceny do "{output_path.name}".', ok=True)

    def _get_material_image_base64(self, material_key: str) -> str:
        """Get base64 encoded image for a material from the producer library."""
        lib_data = self._library_store.load()
        for row in lib_data.get("rows", []):
            kod = str(row.get("kod", "") or "").strip().upper()
            if kod == material_key.upper():
                img_path = str(row.get("image_path", "") or "").strip()
                if img_path and Path(img_path).exists():
                    try:
                        ext = Path(img_path).suffix.lower()
                        mime_types = {
                            ".png": "image/png",
                            ".jpg": "image/jpeg",
                            ".jpeg": "image/jpeg",
                            ".gif": "image/gif",
                            ".bmp": "image/bmp",
                        }
                        mime = mime_types.get(ext, "image/png")
                        with open(img_path, "rb") as f:
                            data = base64.b64encode(f.read()).decode("utf-8")
                        return f"data:{mime};base64,{data}"
                    except Exception:
                        return ""
        return ""

    def _get_module_image_html(self, resolved_item) -> str:
        """Get HTML img tag for module if image exists."""
        module = getattr(resolved_item, "module", None)
        if module is None:
            return ""
        
        materials = getattr(module, "materials", {}) or {}
        for key in materials.values():
            img_data = self._get_material_image_base64(str(key or ""))
            if img_data:
                return f'<img src="{img_data}" width="80" height="60" style="object-fit:contain; border:1px solid #ddd; border-radius:4px;" />'
        
        material_profile_key = str(getattr(module, "material_profile_key", "") or "").strip()
        if material_profile_key:
            img_data = self._get_material_image_base64(material_profile_key)
            if img_data:
                return f'<img src="{img_data}" width="80" height="60" style="object-fit:contain; border:1px solid #ddd; border-radius:4px;" />'
        
        return ""

    def _build_wycena_pdf_html(self, assembly) -> str:
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)
        wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
        linked_wall = self._wall_store.get(wall_name) if wall_name else None
        resolved_items = resolve_assembly_items(
            assembly,
            self._catalog,
            auto_double_front_width_mm=auto_double_width,
            linked_wall=linked_wall,
        )

        technical_total = sum(item.cost_breakdown.grand_total_pln for item in resolved_items)
        labor_cost = float(getattr(assembly, "labor_cost_pln", 0.0) or 0.0)
        transport_cost = float(getattr(assembly, "transport_cost_pln", 0.0) or 0.0)
        montage_cost = float(getattr(assembly, "montage_cost_pln", 0.0) or 0.0)
        margin_percent = float(getattr(assembly, "margin_percent", 0.0) or 0.0)
        base_total_raw = technical_total + labor_cost + transport_cost + montage_cost
        base_total = self._pricing_service.apply_rules(base_total_raw, technical_total, self._pricing_rules)
        sale_total = self._pricing_service.compute_sale(base_total, margin_percent, self._policy_multiplier())
        profit_total = sale_total - base_total

        material_total = sum(float(item.cost_breakdown.material_total_pln) for item in resolved_items)
        edgeband_total = sum(float(item.cost_breakdown.edgeband_total_pln) for item in resolved_items)
        hardware_total = sum(float(item.cost_breakdown.hardware_total_pln) for item in resolved_items)
        labor_total = labor_cost + transport_cost + montage_cost

        order_name = str(getattr(assembly, "order_name", "") or "-")
        client_name = str(getattr(assembly, "client_name", "") or "-")
        assembly_name = str(getattr(assembly, "name", "") or "-")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 30px; color: #333; }}
            h1 {{ color: #1a365d; border-bottom: 3px solid #2b6cb0; padding-bottom: 10px; margin-bottom: 20px; }}
            h2 {{ color: #2c5282; margin-top: 25px; border-bottom: 1px solid #cbd5e0; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background: #2b6cb0; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
            tr:nth-child(even) {{ background: #f7fafc; }}
            .header-info {{ background: #edf2f7; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .header-info p {{ margin: 5px 0; }}
            .summary-box {{ background: #ebf8ff; border: 2px solid #3182ce; border-radius: 8px; padding: 15px; margin: 20px 0; }}
            .summary-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #cbd5e0; }}
            .summary-row:last-child {{ border-bottom: none; }}
            .total-row {{ font-weight: bold; font-size: 1.1em; color: #1a365d; }}
            .profit {{ color: #276749; font-weight: bold; }}
            .material-section {{ background: #fffaf0; border-left: 4px solid #dd6b20; padding: 10px; margin: 10px 0; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 2px solid #e2e8f0; color: #718096; font-size: 12px; }}
        </style>
        </head>
        <body>
            <h1>WYCENA - {assembly_name}</h1>
            
            <div class="header-info">
                <p><strong>Komplet:</strong> {assembly_name}</p>
                <p><strong>Zamówienie:</strong> {order_name}</p>
                <p><strong>Klient:</strong> {client_name}</p>
                <p><strong>Data:</strong> {now}</p>
                <p><strong>Polityka:</strong> {self.cb_policy.currentText()} (x{self._policy_multiplier():.2f})</p>
            </div>

            <h2>📊 PODSUMOWANIE KOSZTÓW</h2>
            <div class="summary-box">
                <div class="summary-row">
                    <span>Materiały (płyta):</span>
                    <span>{material_total:,.2f} zł</span>
                </div>
                <div class="summary-row">
                    <span>Okleiny (brzegi):</span>
                    <span>{edgeband_total:,.2f} zł</span>
                </div>
                <div class="summary-row">
                    <span>Okucia (akcesoria):</span>
                    <span>{hardware_total:,.2f} zł</span>
                </div>
                <div class="summary-row total-row">
                    <span>SUMA MATERIAŁÓW:</span>
                    <span>{technical_total:,.2f} zł</span>
                </div>
            </div>

            <h2>⚙️ ROBOCIZNA I DODATKI</h2>
            <div class="summary-box">
                <div class="summary-row">
                    <span>Robocizna (montaż):</span>
                    <span>{labor_cost:,.2f} zł</span>
                </div>
                <div class="summary-row">
                    <span>Transport:</span>
                    <span>{transport_cost:,.2f} zł</span>
                </div>
                <div class="summary-row">
                    <span>Montaż u klienta:</span>
                    <span>{montage_cost:,.2f} zł</span>
                </div>
                <div class="summary-row total-row">
                    <span>SUMA ROBOCIZNA:</span>
                    <span>{labor_total:,.2f} zł</span>
                </div>
            </div>

            <h2>💰 PORÓWNANIE: MATERIAŁY vs ROBOCIZNA</h2>
            <div class="summary-box">
                <table>
                    <tr>
                        <th>Pozycja</th>
                        <th style="text-align:right;">Kwota</th>
                        <th style="text-align:right;">Udział %</th>
                    </tr>
                    <tr>
                        <td>📦 Materiały</td>
                        <td style="text-align:right;">{technical_total:,.2f} zł</td>
                        <td style="text-align:right;">{technical_total/base_total*100 if base_total > 0 else 0:.1f}%</td>
                    </tr>
                    <tr>
                        <td>👷 Robocizna</td>
                        <td style="text-align:right;">{labor_total:,.2f} zł</td>
                        <td style="text-align:right;">{labor_total/base_total*100 if base_total > 0 else 0:.1f}%</td>
                    </tr>
                    <tr style="background: #e2e8f0; font-weight: bold;">
                        <td>SUMA KOSZTÓW</td>
                        <td style="text-align:right;">{base_total:,.2f} zł</td>
                        <td style="text-align:right;">100%</td>
                    </tr>
                </table>
            </div>

            <h2>📈 MARŻA I ZYSK</h2>
            <div class="summary-box">
                <div class="summary-row">
                    <span>Koszt bazowy:</span>
                    <span>{base_total:,.2f} zł</span>
                </div>
                <div class="summary-row">
                    <span>Marża:</span>
                    <span>{margin_percent:.1f}%</span>
                </div>
                <div class="summary-row">
                    <span>Mnożnik polityki:</span>
                    <span>x{self._policy_multiplier():.2f}</span>
                </div>
                <div class="summary-row total-row">
                    <span>CENA HANDLOWA (netto):</span>
                    <span>{sale_total:,.2f} zł</span>
                </div>
                <div class="summary-row profit">
                    <span>ZYSK (marża kwotowa):</span>
                    <span>{profit_total:,.2f} zł ({(profit_total/sale_total*100) if sale_total > 0 else 0:.1f}%)</span>
                </div>
            </div>

            <h2>📋 SZCZEGӣY MODUŁÓW</h2>
            <table>
                <tr>
                    <th style="width:90px;">Zdjecie</th>
                    <th>Moduł</th>
                    <th style="text-align:right;">Materiał</th>
                    <th style="text-align:right;">Okleina</th>
                    <th style="text-align:right;">Okucia</th>
                    <th style="text-align:right;">SUMA</th>
                </tr>
        """
        for resolved in resolved_items:
            display = str(getattr(resolved, "display_name", "") or "Moduł")
            bd = resolved.cost_breakdown
            mat = float(bd.material_total_pln)
            edge = float(bd.edgeband_total_pln)
            hard = float(bd.hardware_total_pln)
            total = float(bd.grand_total_pln)
            img_html = self._get_module_image_html(resolved)
            if not img_html:
                img_html = "-"
            html += f"""
                <tr>
                    <td style="text-align:center;">{img_html}</td>
                    <td>{display}</td>
                    <td style="text-align:right;">{mat:,.2f} zł</td>
                    <td style="text-align:right;">{edge:,.2f} zł</td>
                    <td style="text-align:right;">{hard:,.2f} zł</td>
                    <td style="text-align:right; font-weight: bold;">{total:,.2f} zł</td>
                </tr>
            """

        html += f"""
            </table>

            <div class="footer">
                <p>Wygenerowano: {now} | TECH_modul - System zarządzania projektami meblowymi</p>
            </div>
        </body>
        </html>
        """
        return html

    def _toggle_toolbar(self) -> None:
        is_visible = self.toolbar_container.isVisible()
        self.toolbar_container.setVisible(not is_visible)
        if is_visible:
            self.toolbar_toggle.setText("Pasek narzędzi ▶")
        else:
            self.toolbar_toggle.setText("Pasek narzędzi ▼")

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
