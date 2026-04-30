from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.storage.catalog_store_json import CatalogStoreJson
from src.app.app_settings import load_ui_theme_settings


def _default_data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[3]
    return root / "data"


class TabBazaModul(QWidget):
    TYPE_OPTIONS: tuple[str, ...] = ("gorne", "dolne", "slupek", "inne")

    COL_ID = 0
    COL_NAME = 1
    COL_TYPE = 2
    COL_L = 3
    COL_W = 4
    COL_H = 5
    COL_QTY = 6
    COL_RULE = 7
    COL_SHELF = 8
    COL_MAT_CARCASS = 9
    COL_MAT_FRONT = 10
    COL_FR = 11
    COL_MAT_BACK = 12
    COL_PC = 13
    COL_FMT_PION = 14
    COL_FMT_WIENIEC = 15
    COL_FMT_BACK = 16
    COL_FMT_FRONT = 17
    COL_EDGEBAND = 18
    COL_EDGE_L = 19
    COL_EDGE_P = 20
    COL_EDGE_G = 21
    COL_EDGE_D = 22
    COL_M2_PION = 23
    COL_M2_WIENIEC = 24
    COL_M2_BACK = 25
    COL_M2_FRONT = 26
    COL_M2_CARCASS = 27
    COL_M2_TOTAL = 28

    HEADER_LABELS = [
        "ID",
        "Nazwa",
        "Typ",
        "L",
        "W",
        "H",
        "Ilosc",
        "Pion",
        "Polka",
        "Mat. korpus",
        "Mat. front",
        "FR [mm]",
        "Mat. plecy",
        "PC [mm]",
        "Nazwa bok",
        "Nazwa wieniec",
        "Nazwa plecy",
        "Nazwa front",
        "Okleina",
        "L",
        "P",
        "G",
        "D",
        "m2 bok",
        "m2 wieniec",
        "m2 plecy",
        "m2 front",
        "m2 korpus",
        "m2 razem",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_refreshing = False
        self._catalog = CatalogStoreJson()
        self._edgeband_options: list[tuple[str, str]] = []
        self._hardware_options: list[tuple[str, str, float, str]] = []
        self._load_edgeband_options()
        self._load_hardware_options()
        self._store_path = _default_data_dir() / "quick_quote_baza_modul.json"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

        theme = load_ui_theme_settings()
        is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        
        # Color palette
        c_text = "#e8efff" if is_tech else "#0f172a"
        c_muted = "#9bb0cd" if is_tech else "#64748b"
        c_border = "#2a3b59" if is_tech else "#d1d5db"
        c_bg_card = "#111b30" if is_tech else "#ffffff"
        c_header_bg = "#1e293b" if is_tech else "#f8fafc"
        c_alternate_bg = "#162035" if is_tech else "#f9fafb"
        c_grid = "#1e293b" if is_tech else "#e2e8f0"

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("BAZA_modul", self)
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{c_text};")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Baza szafek do szybkiej wyceny: ID / nazwa / wymiary / materialy / okleina / automatyczne m2.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{c_muted}; font-size:12px;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        controls_frame = QFrame(self); controls_frame.setProperty("uiCard", True)
        controls_frame.setObjectName("bazaModulControls")
        controls_frame.setStyleSheet(
            f"""
            QFrame#bazaModulControls {{
                border: 1px solid {c_border};
                border-radius: 10px;
                background: {c_bg_card};
            }}
            QLabel {{
                color:{c_text};
            }}
            QDoubleSpinBox, QComboBox {{
                min-height: 30px;
                background: {'#0f172a' if is_tech else '#ffffff'};
                color: {c_text};
                border: 1px solid {c_border};
                border-radius: 4px;
            }}
            QPushButton {{
                min-height: 30px;
                padding: 0 10px;
            }}
            """
        )
        controls = QHBoxLayout(controls_frame)
        controls.setContentsMargins(10, 8, 10, 8)
        controls.setSpacing(8)

        controls.addWidget(QLabel("PLC [mm]:", self), 0)
        self.sp_pc = QDoubleSpinBox(self)
        self.sp_pc.setRange(0.0, 100.0)
        self.sp_pc.setDecimals(1)
        self.sp_pc.setValue(3.0)
        self.sp_pc.setSuffix(" mm")
        self.sp_pc.setFixedWidth(130)
        controls.addWidget(self.sp_pc, 0)

        controls.addSpacing(6)
        controls.addWidget(QLabel("MO [mm]:", self), 0)
        self.sp_mo = QDoubleSpinBox(self)
        self.sp_mo.setRange(0.0, 100.0)
        self.sp_mo.setDecimals(1)
        self.sp_mo.setValue(18.0)
        self.sp_mo.setSuffix(" mm")
        self.sp_mo.setFixedWidth(130)
        controls.addWidget(self.sp_mo, 0)

        controls.addSpacing(6)
        controls.addWidget(QLabel("FR [mm]:", self), 0)
        self.sp_fr = QDoubleSpinBox(self)
        self.sp_fr.setRange(0.0, 100.0)
        self.sp_fr.setDecimals(1)
        self.sp_fr.setValue(19.0)
        self.sp_fr.setSuffix(" mm")
        self.sp_fr.setFixedWidth(130)
        controls.addWidget(self.sp_fr, 0)

        controls.addSpacing(8)
        controls.addWidget(QLabel("Typ:", self), 0)
        self.cb_type_filter = QComboBox(self)
        self.cb_type_filter.addItem("[wszystkie]", "")
        for key in self.TYPE_OPTIONS:
            self.cb_type_filter.addItem(key, key)
        self.cb_type_filter.setFixedWidth(150)
        controls.addWidget(self.cb_type_filter, 0)

        controls.addSpacing(8)
        self.btn_add_row = QPushButton("+ Dodaj szafke", self)
        self.btn_add_edgeband = QPushButton("+ Dodaj okleine", self)
        self.btn_add_hardware = QPushButton("+ Dodaj okucie", self)
        self.btn_remove_hardware = QPushButton("- Usun okucie", self)
        self.btn_remove_row = QPushButton("Usun zaznaczone", self)
        self.btn_save = QPushButton("Zapisz baze", self)
        self.btn_reload = QPushButton("Wczytaj baze", self)
        controls.addWidget(self.btn_add_row, 0)
        controls.addWidget(self.btn_add_edgeband, 0)
        controls.addWidget(self.btn_add_hardware, 0)
        controls.addWidget(self.btn_remove_hardware, 0)
        controls.addWidget(self.btn_remove_row, 0)
        controls.addWidget(self.btn_save, 0)
        controls.addWidget(self.btn_reload, 0)
        controls.addStretch(1)

        root.addWidget(controls_frame, 0)

        info_expand = QLabel("Kliknij strzalke przy ID, aby rozwinac modul i zobaczyc rozpiske elementow.", self)
        info_expand.setStyleSheet(f"color:{c_muted}; font-size:12px; font-weight:600;")
        root.addWidget(info_expand, 0, Qt.AlignmentFlag.AlignLeft)

        self.tbl = QTreeWidget(self)
        self.tbl.setColumnCount(len(self.HEADER_LABELS))
        self.tbl.setHeaderLabels(self.HEADER_LABELS)
        self.tbl.setRootIsDecorated(True)
        self.tbl.setItemsExpandable(True)
        self.tbl.setUniformRowHeights(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl.setIndentation(18)
        self.tbl.setStyleSheet(
            f"""
            QTreeWidget {{
                border: 1px solid {c_border};
                border-radius: 10px;
                background: {c_bg_card};
                color: {c_text};
                gridline-color: {c_grid};
                alternate-background-color: {c_alternate_bg};
            }}
            QTreeWidget::item {{
                padding-top: 4px;
                padding-bottom: 4px;
            }}
            QTreeWidget::item:selected {{
                background: #3b82f6;
                color: #ffffff;
            }}
            QHeaderView::section {{
                background: {c_header_bg};
                color: {c_text};
                border: none;
                border-right: 1px solid {c_border};
                border-bottom: 1px solid {c_border};
                padding: 6px 8px;
                font-weight: 700;
            }}
            """
        )
        self.tbl.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        hdr = self.tbl.header()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(28)
        self._configure_tree_columns()
        root.addWidget(self.tbl, 1)

        summary_frame = QFrame(self); summary_frame.setProperty("uiCard", True)
        summary_frame.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {c_border};
                border-radius: 10px;
                background: {c_bg_card};
            }}
            """
        )
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 8, 10, 8)
        summary_layout.setSpacing(6)

        summary_title = QLabel("Podsumowanie materialow", self)
        summary_title.setStyleSheet(f"font-size:13px; font-weight:700; color:{c_text};")
        summary_layout.addWidget(summary_title, 0, Qt.AlignmentFlag.AlignLeft)

        self.tbl_summary = QTableWidget(0, 3, self)
        self.tbl_summary.setHorizontalHeaderLabels(["Material", "m2", "Zakres"])
        self.tbl_summary.verticalHeader().setVisible(False)
        self.tbl_summary.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_summary.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_summary.setAlternatingRowColors(True)
        self.tbl_summary.setMaximumHeight(160)
        self.tbl_summary.setStyleSheet(
            f"""
            QTableWidget {{
                border: 1px solid {c_border};
                border-radius: 8px;
                background: {c_bg_card};
                color: {c_text};
                gridline-color: {c_grid};
                alternate-background-color: {c_alternate_bg};
            }}
            QHeaderView::section {{
                background: {c_header_bg};
                color: {c_text};
                border: none;
                border-right: 1px solid {c_border};
                border-bottom: 1px solid {c_border};
                padding: 6px 8px;
                font-weight: 700;
            }}
            """
        )
        self.tbl_summary.horizontalHeader().setStretchLastSection(True)
        self.tbl_summary.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_summary.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_summary.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        summary_layout.addWidget(self.tbl_summary)

        self.lab_total = QLabel("RAZEM: 0.000 m2", self)
        self.lab_total.setStyleSheet(f"font-size:13px; font-weight:800; color:{c_text};")
        summary_layout.addWidget(self.lab_total, 0, Qt.AlignmentFlag.AlignRight)

        summary_frame.setVisible(False)
        root.addWidget(summary_frame, 0)

        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_add_edgeband.clicked.connect(self._add_edgeband_to_selected_module)
        self.btn_add_hardware.clicked.connect(self._add_hardware_to_selected_module)
        self.btn_remove_hardware.clicked.connect(self._remove_selected_hardware)
        self.btn_remove_row.clicked.connect(self._remove_selected_rows)
        self.btn_save.clicked.connect(self._save_store)
        self.btn_reload.clicked.connect(self._load_store)
        self.sp_mo.valueChanged.connect(self._recompute_all)
        self.sp_fr.valueChanged.connect(self._recompute_all)
        self.sp_pc.valueChanged.connect(self._recompute_all)
        self.cb_type_filter.currentIndexChanged.connect(self._apply_type_segregation)
        self.tbl.itemChanged.connect(self._on_item_changed)

        self._load_store()
        if self.tbl.topLevelItemCount() == 0:
            self._add_row()

    def _configure_tree_columns(self) -> None:
        self.tbl.setColumnWidth(self.COL_ID, 85)
        self.tbl.setColumnWidth(self.COL_NAME, 150)
        self.tbl.setColumnWidth(self.COL_TYPE, 70)
        self.tbl.setColumnWidth(self.COL_L, 58)
        self.tbl.setColumnWidth(self.COL_W, 58)
        self.tbl.setColumnWidth(self.COL_H, 58)
        self.tbl.setColumnWidth(self.COL_QTY, 52)
        self.tbl.setColumnWidth(self.COL_RULE, 52)
        self.tbl.setColumnWidth(self.COL_SHELF, 52)
        self.tbl.setColumnWidth(self.COL_MAT_CARCASS, 105)
        self.tbl.setColumnWidth(self.COL_MAT_FRONT, 95)
        self.tbl.setColumnWidth(self.COL_FR, 72)
        self.tbl.setColumnWidth(self.COL_MAT_BACK, 95)
        self.tbl.setColumnWidth(self.COL_PC, 72)
        self.tbl.setColumnWidth(self.COL_FMT_PION, 100)
        self.tbl.setColumnWidth(self.COL_FMT_WIENIEC, 110)
        self.tbl.setColumnWidth(self.COL_FMT_BACK, 100)
        self.tbl.setColumnWidth(self.COL_FMT_FRONT, 100)
        self.tbl.setColumnWidth(self.COL_EDGEBAND, 120)
        self.tbl.setColumnWidth(self.COL_EDGE_L, 34)
        self.tbl.setColumnWidth(self.COL_EDGE_P, 34)
        self.tbl.setColumnWidth(self.COL_EDGE_G, 34)
        self.tbl.setColumnWidth(self.COL_EDGE_D, 34)
        self.tbl.setColumnWidth(self.COL_M2_PION, 78)
        self.tbl.setColumnWidth(self.COL_M2_WIENIEC, 86)
        self.tbl.setColumnWidth(self.COL_M2_BACK, 72)
        self.tbl.setColumnWidth(self.COL_M2_FRONT, 72)
        self.tbl.setColumnWidth(self.COL_M2_CARCASS, 82)
        self.tbl.setColumnWidth(self.COL_M2_TOTAL, 82)

        self.tbl.setColumnHidden(self.COL_FR, True)
        self.tbl.setColumnHidden(self.COL_PC, True)
        self.tbl.setColumnHidden(self.COL_FMT_PION, True)
        self.tbl.setColumnHidden(self.COL_FMT_WIENIEC, True)
        self.tbl.setColumnHidden(self.COL_FMT_BACK, True)
        self.tbl.setColumnHidden(self.COL_FMT_FRONT, True)

    def _iter_modules(self):
        for i in range(self.tbl.topLevelItemCount()):
            item = self.tbl.topLevelItem(i)
            if item is not None:
                yield item

    def _top_item(self, item: QTreeWidgetItem | None) -> QTreeWidgetItem | None:
        current = item
        while current is not None and current.parent() is not None:
            current = current.parent()
        return current

    def _selected_top_item(self) -> QTreeWidgetItem | None:
        selected = self.tbl.selectedItems()
        for raw_item in selected:
            top = self._top_item(raw_item)
            if top is not None:
                return top
        current = self.tbl.currentItem()
        return self._top_item(current)

    def _parse_float(self, text: str, default: float = 0.0) -> float:
        raw = str(text or "").strip().replace(",", ".").replace(" ", "")
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def _parse_int(self, text: str, default: int = 0) -> int:
        return int(round(self._parse_float(text, float(default))))

    def _load_edgeband_options(self) -> None:
        options: list[tuple[str, str]] = [("", "[brak]")]
        try:
            for band in self._catalog.list_edgebands() or []:
                key = str(getattr(band, "key", "") or "").strip()
                name = str(getattr(band, "name_pl", "") or "").strip()
                if not key:
                    continue
                label = f"{key} | {name}" if name else key
                options.append((key, label))
        except Exception:
            pass
        self._edgeband_options = options

    def _load_hardware_options(self) -> None:
        options: list[tuple[str, str, float, str]] = []
        try:
            for hw in self._catalog.list_hardware() or []:
                key = str(getattr(hw, "key", "") or "").strip()
                name = str(getattr(hw, "name_pl", "") or "").strip()
                if not key:
                    continue
                label = f"{key} | {name}" if name else key
                price = float(getattr(hw, "price_pln", 0.0) or 0.0)
                unit = str(getattr(hw, "unit", "szt") or "szt").strip() or "szt"
                options.append((key, label, price, unit))
        except Exception:
            pass
        self._hardware_options = sorted(options, key=lambda row: row[1].lower())

    def _hardware_label(self, key: str) -> str:
        norm = str(key or "").strip()
        for hw_key, label, _price, _unit in self._hardware_options:
            if hw_key == norm:
                return label
        return norm

    def _hardware_unit_price(self, key: str) -> tuple[float, str]:
        norm = str(key or "").strip()
        for hw_key, _label, price, unit in self._hardware_options:
            if hw_key == norm:
                return float(price), str(unit or "szt")
        return 0.0, "szt"

    def _set_check(self, item: QTreeWidgetItem, col: int, checked: bool) -> None:
        item.setCheckState(col, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setText(col, "")
        item.setTextAlignment(col, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

    def _is_checked(self, item: QTreeWidgetItem, col: int) -> bool:
        return item.checkState(col) == Qt.CheckState.Checked

    def _edge_sides_text(self, item: QTreeWidgetItem) -> str:
        out: list[str] = []
        if self._is_checked(item, self.COL_EDGE_L):
            out.append("L")
        if self._is_checked(item, self.COL_EDGE_P):
            out.append("P")
        if self._is_checked(item, self.COL_EDGE_G):
            out.append("G")
        if self._is_checked(item, self.COL_EDGE_D):
            out.append("D")
        return "+".join(out)

    def _normalize_sides_text(self, sides: str) -> str:
        allowed = {"L", "P", "G", "D"}
        parts = [str(p).strip().upper() for p in str(sides or "").split("+")]
        unique = {p for p in parts if p in allowed}
        ordered = [k for k in ("L", "P", "G", "D") if k in unique]
        return "+".join(ordered)

    def _get_edge_parts_map(self, item: QTreeWidgetItem) -> dict[str, str]:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            raw = data.get("edge_parts")
            if isinstance(raw, dict):
                out: dict[str, str] = {}
                for key, value in raw.items():
                    norm_key = str(key or "").strip().lower()
                    if not norm_key:
                        continue
                    out[norm_key] = self._normalize_sides_text(str(value or ""))
                return out
        return {}

    def _set_edge_parts_map(self, item: QTreeWidgetItem, mapping: dict[str, str]) -> None:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        payload = dict(data) if isinstance(data, dict) else {}
        clean: dict[str, str] = {}
        for key, value in mapping.items():
            norm_key = str(key or "").strip().lower()
            if not norm_key:
                continue
            clean[norm_key] = self._normalize_sides_text(str(value or ""))
        payload["edge_parts"] = clean
        item.setData(self.COL_ID, Qt.ItemDataRole.UserRole, payload)

    def _get_edge_part_band_map(self, item: QTreeWidgetItem) -> dict[str, str]:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            raw = data.get("edge_part_band")
            if isinstance(raw, dict):
                out: dict[str, str] = {}
                for key, value in raw.items():
                    norm_key = str(key or "").strip().lower()
                    if not norm_key:
                        continue
                    out[norm_key] = str(value or "").strip()
                return out
        return {}

    def _set_edge_part_band_map(self, item: QTreeWidgetItem, mapping: dict[str, str]) -> None:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        payload = dict(data) if isinstance(data, dict) else {}
        clean: dict[str, str] = {}
        for key, value in mapping.items():
            norm_key = str(key or "").strip().lower()
            if not norm_key:
                continue
            clean[norm_key] = str(value or "").strip()
        payload["edge_part_band"] = clean
        item.setData(self.COL_ID, Qt.ItemDataRole.UserRole, payload)

    def _normalize_hardware_items(self, rows: object) -> list[dict[str, float | str]]:
        out: dict[str, float] = {}
        if not isinstance(rows, list):
            return []
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "") or "").strip()
            if not key:
                continue
            qty = self._parse_float(str(row.get("qty", "0") or "0"), 0.0)
            if qty <= 0.0:
                continue
            out[key] = out.get(key, 0.0) + qty
        normalized: list[dict[str, float | str]] = []
        for key in sorted(out.keys()):
            normalized.append({"key": key, "qty": out[key]})
        return normalized

    def _get_hardware_items(self, item: QTreeWidgetItem) -> list[dict[str, float | str]]:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return self._normalize_hardware_items(data.get("hardware_items"))
        return []

    def _set_hardware_items(self, item: QTreeWidgetItem, rows: list[dict[str, float | str]]) -> None:
        data = item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
        payload = dict(data) if isinstance(data, dict) else {}
        payload["hardware_items"] = self._normalize_hardware_items(rows)
        item.setData(self.COL_ID, Qt.ItemDataRole.UserRole, payload)

    def _safe_part_name(self, raw_name: str, default_name: str) -> str:
        value = str(raw_name or "").strip()
        if value in {"", ".", "..", "...", "-", "_"}:
            return default_name
        return value

    def _type_key_from_item(self, item: QTreeWidgetItem) -> str:
        combo = self.tbl.itemWidget(item, self.COL_TYPE)
        if isinstance(combo, QComboBox):
            value = combo.currentData()
            if value is not None:
                return str(value).strip().lower()
            return str(combo.currentText() or "").strip().lower()
        return str(item.text(self.COL_TYPE) or "").strip().lower()

    def _type_rank(self, type_key: str) -> int:
        order = {"gorne": 0, "dolne": 1, "slupek": 2, "inne": 3}
        return order.get(str(type_key or "").strip().lower(), 99)

    def _ensure_type_combo(self, item: QTreeWidgetItem) -> None:
        if item.parent() is not None:
            return
        combo = self.tbl.itemWidget(item, self.COL_TYPE)
        if not isinstance(combo, QComboBox):
            combo = QComboBox(self.tbl)
            combo.setEditable(False)
            for key in self.TYPE_OPTIONS:
                combo.addItem(key, key)
            combo.currentIndexChanged.connect(lambda _idx, it=item: self._on_type_combo_changed(it))
            self.tbl.setItemWidget(item, self.COL_TYPE, combo)

        key = str(item.text(self.COL_TYPE) or "").strip().lower()
        if key not in self.TYPE_OPTIONS:
            key = "gorne"
        idx = combo.findData(key)
        if idx < 0:
            idx = 0
        if combo.currentIndex() != idx:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        item.setToolTip(self.COL_TYPE, key)

    def _on_type_combo_changed(self, item: QTreeWidgetItem) -> None:
        if self._is_refreshing:
            return
        if item.parent() is not None:
            return
        type_key = self._type_key_from_item(item)
        if type_key not in self.TYPE_OPTIONS:
            type_key = "gorne"
        self._is_refreshing = True
        try:
            item.setText(self.COL_TYPE, type_key)
            item.setToolTip(self.COL_TYPE, type_key)
        finally:
            self._is_refreshing = False
        self._recompute_item(item)
        self._apply_type_segregation()
        self._rebuild_summary()

    def _apply_type_segregation(self) -> None:
        selected = ""
        if hasattr(self, "cb_type_filter") and isinstance(self.cb_type_filter, QComboBox):
            value = self.cb_type_filter.currentData()
            if value is not None:
                selected = str(value).strip().lower()

        modules = list(self._iter_modules())
        ordered = sorted(
            modules,
            key=lambda item: (
                self._type_rank(self._type_key_from_item(item)),
                str(item.text(self.COL_NAME) or "").strip().lower(),
                str(item.text(self.COL_ID) or "").strip().lower(),
            ),
        )
        if ordered != modules:
            self._is_refreshing = True
            try:
                while self.tbl.topLevelItemCount() > 0:
                    self.tbl.takeTopLevelItem(0)
                for item in ordered:
                    self.tbl.addTopLevelItem(item)
            finally:
                self._is_refreshing = False

        for item in self._iter_modules():
            type_key = self._type_key_from_item(item)
            visible = (not selected) or (type_key == selected)
            item.setHidden(not visible)

    def _ensure_edgeband_combo(self, item: QTreeWidgetItem) -> None:
        if item.parent() is not None:
            return
        combo = self.tbl.itemWidget(item, self.COL_EDGEBAND)
        if not isinstance(combo, QComboBox):
            combo = QComboBox(self.tbl)
            combo.setEditable(False)
            for key, label in self._edgeband_options:
                combo.addItem(label, key)
            combo.currentIndexChanged.connect(lambda _idx, it=item: self._on_edgeband_combo_changed(it))
            self.tbl.setItemWidget(item, self.COL_EDGEBAND, combo)

        key = str(item.text(self.COL_EDGEBAND)).strip()
        idx = combo.findData(key)
        if idx < 0 and key:
            combo.addItem(key, key)
            idx = combo.findData(key)
        if idx < 0:
            idx = 0

        if combo.currentIndex() != idx:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        item.setToolTip(self.COL_EDGEBAND, combo.currentText())

    def _edgeband_key_from_item(self, item: QTreeWidgetItem) -> str:
        combo = self.tbl.itemWidget(item, self.COL_EDGEBAND)
        if isinstance(combo, QComboBox):
            value = combo.currentData()
            if value is not None:
                return str(value).strip()
        return str(item.text(self.COL_EDGEBAND)).strip()

    def _on_edgeband_combo_changed(self, item: QTreeWidgetItem) -> None:
        if self._is_refreshing:
            return
        if item.parent() is not None:
            return
        key = self._edgeband_key_from_item(item)
        self._is_refreshing = True
        try:
            item.setText(self.COL_EDGEBAND, key)
            item.setToolTip(self.COL_EDGEBAND, key or "[brak]")
        finally:
            self._is_refreshing = False
        self._recompute_item(item)
        self._rebuild_summary()

    def _ensure_child_edgeband_combo(
        self,
        child: QTreeWidgetItem,
        top_item: QTreeWidgetItem,
        part_key: str,
        current_key: str,
    ) -> None:
        combo = self.tbl.itemWidget(child, self.COL_EDGEBAND)
        if not isinstance(combo, QComboBox):
            combo = QComboBox(self.tbl)
            combo.setEditable(False)
            for key, label in self._edgeband_options:
                combo.addItem(label, key)
            combo.currentIndexChanged.connect(
                lambda _idx, ch=child, top=top_item, pkey=part_key: self._on_child_edgeband_combo_changed(ch, top, pkey)
            )
            self.tbl.setItemWidget(child, self.COL_EDGEBAND, combo)

        idx = combo.findData(current_key)
        if idx < 0 and current_key:
            combo.addItem(current_key, current_key)
            idx = combo.findData(current_key)
        if idx < 0:
            idx = 0

        if combo.currentIndex() != idx:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        child.setToolTip(self.COL_EDGEBAND, combo.currentText())

    def _on_child_edgeband_combo_changed(
        self,
        child: QTreeWidgetItem,
        top_item: QTreeWidgetItem,
        part_key: str,
    ) -> None:
        if self._is_refreshing:
            return
        combo = self.tbl.itemWidget(child, self.COL_EDGEBAND)
        band_key = ""
        if isinstance(combo, QComboBox):
            value = combo.currentData()
            if value is not None:
                band_key = str(value).strip()

        edge_part_band = self._get_edge_part_band_map(top_item)
        edge_part_band[str(part_key).strip().lower()] = band_key
        self._set_edge_part_band_map(top_item, edge_part_band)

        self._is_refreshing = True
        try:
            child.setText(self.COL_EDGEBAND, band_key)
            child.setToolTip(self.COL_EDGEBAND, band_key or "[brak]")
        finally:
            self._is_refreshing = False

        self._recompute_item(top_item)
        self._rebuild_summary()

    def _add_edgeband_to_selected_module(self) -> None:
        self._load_edgeband_options()
        top = self._selected_top_item()
        if top is None:
            QMessageBox.information(self, "Brak modulu", "Najpierw zaznacz modul, do ktorego dodajesz okleine.")
            return

        choices: list[tuple[str, str]] = [(key, label) for key, label in self._edgeband_options if key.strip()]
        if not choices:
            QMessageBox.information(self, "Brak oklein", "W bazie oklein nie ma jeszcze zadnych wpisow.")
            return

        labels = [label for _key, label in choices]
        selected_label, ok = QInputDialog.getItem(
            self,
            "Dodaj okleine",
            "Wybierz okleine dla zaznaczonego modulu:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        selected_key = ""
        for key, label in choices:
            if label == selected_label:
                selected_key = key
                break
        if not selected_key:
            return

        combo = self.tbl.itemWidget(top, self.COL_EDGEBAND)
        if isinstance(combo, QComboBox):
            idx = combo.findData(selected_key)
            if idx < 0:
                combo.addItem(selected_key, selected_key)
                idx = combo.findData(selected_key)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        else:
            top.setText(self.COL_EDGEBAND, selected_key)
            self._recompute_item(top)
            self._rebuild_summary()

    def _add_hardware_to_selected_module(self) -> None:
        self._load_hardware_options()
        top = self._selected_top_item()
        if top is None:
            QMessageBox.information(self, "Brak modulu", "Najpierw zaznacz modul, do ktorego dodajesz okucie.")
            return

        if not self._hardware_options:
            QMessageBox.information(self, "Brak okuc", "Baza okuc jest pusta.")
            return

        labels = [label for _key, label, _price, _unit in self._hardware_options]
        selected_label, ok = QInputDialog.getItem(
            self,
            "Dodaj okucie",
            "Wybierz okucie z bazy:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        selected_key = ""
        for key, label, _price, _unit in self._hardware_options:
            if label == selected_label:
                selected_key = key
                break
        if not selected_key:
            return

        qty, qty_ok = QInputDialog.getDouble(
            self,
            "Ilosc okucia",
            "Podaj ilosc:",
            1.0,
            0.01,
            100000.0,
            2,
        )
        if not qty_ok:
            return

        hardware_rows = self._get_hardware_items(top)
        matched = False
        for row in hardware_rows:
            if str(row.get("key", "") or "").strip() == selected_key:
                prev_qty = self._parse_float(str(row.get("qty", "0") or "0"), 0.0)
                row["qty"] = prev_qty + float(qty)
                matched = True
                break
        if not matched:
            hardware_rows.append({"key": selected_key, "qty": float(qty)})
        self._set_hardware_items(top, hardware_rows)
        self._recompute_item(top)
        self._rebuild_summary()

    def _remove_selected_hardware(self) -> None:
        removals: dict[int, set[str]] = {}
        for raw_item in self.tbl.selectedItems():
            parent = raw_item.parent()
            if parent is None:
                continue
            marker = raw_item.data(self.COL_ID, Qt.ItemDataRole.UserRole)
            if not isinstance(marker, dict):
                continue
            if str(marker.get("kind", "") or "").strip().lower() != "hardware":
                continue
            key = str(marker.get("key", "") or "").strip()
            if not key:
                continue
            top_idx = self.tbl.indexOfTopLevelItem(parent)
            if top_idx < 0:
                continue
            removals.setdefault(top_idx, set()).add(key)

        if removals:
            for top_idx, keys in removals.items():
                top = self.tbl.topLevelItem(top_idx)
                if top is None:
                    continue
                hardware_rows = self._get_hardware_items(top)
                hardware_rows = [row for row in hardware_rows if str(row.get("key", "") or "").strip() not in keys]
                self._set_hardware_items(top, hardware_rows)
                self._recompute_item(top)
            self._rebuild_summary()
            return

        top = self._selected_top_item()
        if top is None:
            QMessageBox.information(self, "Brak okucia", "Zaznacz najpierw wiersz okucia albo modul.")
            return

        hardware_rows = self._get_hardware_items(top)
        if not hardware_rows:
            QMessageBox.information(self, "Brak okucia", "Wybrany modul nie ma jeszcze przypisanego okucia.")
            return

        choices: list[tuple[str, str]] = []
        for row in hardware_rows:
            key = str(row.get("key", "") or "").strip()
            qty = self._parse_float(str(row.get("qty", "0") or "0"), 0.0)
            if not key:
                continue
            choices.append((key, f"{self._hardware_label(key)} | ilosc: {qty:.2f}"))
        if not choices:
            return

        labels = [label for _key, label in choices]
        selected_label, ok = QInputDialog.getItem(
            self,
            "Usun okucie",
            "Wybierz okucie do usuniecia:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        remove_key = ""
        for key, label in choices:
            if label == selected_label:
                remove_key = key
                break
        if not remove_key:
            return

        new_rows = [row for row in hardware_rows if str(row.get("key", "") or "").strip() != remove_key]
        self._set_hardware_items(top, new_rows)
        self._recompute_item(top)
        self._rebuild_summary()

    def _next_id(self) -> str:
        max_num = 0
        for item in self._iter_modules():
            raw = str(item.text(self.COL_ID)).strip()
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                max_num = max(max_num, int(digits))
        return f"BM{max_num + 1:04d}"

    def _module_payload_from_item(self, item: QTreeWidgetItem) -> dict:
        return {
            "id": str(item.text(self.COL_ID)).strip(),
            "name": str(item.text(self.COL_NAME)).strip(),
            "type": self._type_key_from_item(item),
            "l": str(item.text(self.COL_L)).strip(),
            "w": str(item.text(self.COL_W)).strip(),
            "h": str(item.text(self.COL_H)).strip(),
            "qty": str(item.text(self.COL_QTY)).strip(),
            "pion": str(item.text(self.COL_RULE)).strip(),
            "shelf": str(item.text(self.COL_SHELF)).strip(),
            "mat_carcass": str(item.text(self.COL_MAT_CARCASS)).strip(),
            "mat_front": str(item.text(self.COL_MAT_FRONT)).strip(),
            "fr": str(item.text(self.COL_FR)).strip(),
            "mat_back": str(item.text(self.COL_MAT_BACK)).strip(),
            "pc": str(item.text(self.COL_PC)).strip(),
            "fmt_pion": str(item.text(self.COL_FMT_PION)).strip(),
            "fmt_wieniec": str(item.text(self.COL_FMT_WIENIEC)).strip(),
            "fmt_back": str(item.text(self.COL_FMT_BACK)).strip(),
            "fmt_front": str(item.text(self.COL_FMT_FRONT)).strip(),
            "edgeband": self._edgeband_key_from_item(item),
            "edge_l": bool(self._is_checked(item, self.COL_EDGE_L)),
            "edge_p": bool(self._is_checked(item, self.COL_EDGE_P)),
            "edge_g": bool(self._is_checked(item, self.COL_EDGE_G)),
            "edge_d": bool(self._is_checked(item, self.COL_EDGE_D)),
            "edge_parts": self._get_edge_parts_map(item),
            "edge_part_band": self._get_edge_part_band_map(item),
            "hardware_items": self._get_hardware_items(item),
        }

    def _set_module_payload(self, item: QTreeWidgetItem, payload: dict) -> None:
        item.setText(self.COL_ID, str(payload.get("id", "") or ""))
        item.setText(self.COL_NAME, str(payload.get("name", "") or ""))
        item.setText(self.COL_TYPE, str(payload.get("type", "") or ""))
        item.setText(self.COL_L, str(payload.get("l", "") or ""))
        item.setText(self.COL_W, str(payload.get("w", "") or ""))
        item.setText(self.COL_H, str(payload.get("h", "") or ""))
        item.setText(self.COL_QTY, str(payload.get("qty", "1") or "1"))
        item.setText(self.COL_RULE, str(payload.get("pion", payload.get("rule", "0")) or "0"))
        item.setText(self.COL_SHELF, str(payload.get("shelf", "") or ""))
        item.setText(self.COL_MAT_CARCASS, str(payload.get("mat_carcass", "") or ""))
        item.setText(self.COL_MAT_FRONT, str(payload.get("mat_front", "") or ""))
        item.setText(self.COL_FR, str(payload.get("fr", "") or ""))
        item.setText(self.COL_MAT_BACK, str(payload.get("mat_back", "") or ""))
        item.setText(self.COL_PC, str(payload.get("pc", "") or ""))
        item.setText(self.COL_FMT_PION, str(payload.get("fmt_pion", "") or ""))
        item.setText(self.COL_FMT_WIENIEC, str(payload.get("fmt_wieniec", "") or ""))
        item.setText(self.COL_FMT_BACK, str(payload.get("fmt_back", "") or ""))
        item.setText(self.COL_FMT_FRONT, str(payload.get("fmt_front", "") or ""))
        item.setText(self.COL_EDGEBAND, str(payload.get("edgeband", "") or ""))
        self._set_check(item, self.COL_EDGE_L, bool(payload.get("edge_l", False)))
        self._set_check(item, self.COL_EDGE_P, bool(payload.get("edge_p", False)))
        self._set_check(item, self.COL_EDGE_G, bool(payload.get("edge_g", False)))
        self._set_check(item, self.COL_EDGE_D, bool(payload.get("edge_d", False)))
        edge_parts = payload.get("edge_parts", {})
        if not isinstance(edge_parts, dict):
            edge_parts = {}
        self._set_edge_parts_map(item, edge_parts)
        edge_part_band = payload.get("edge_part_band", {})
        if not isinstance(edge_part_band, dict):
            edge_part_band = {}
        self._set_edge_part_band_map(item, edge_part_band)
        self._set_hardware_items(item, self._normalize_hardware_items(payload.get("hardware_items", [])))

    def _set_calc_cell(self, item: QTreeWidgetItem, col: int, value: float) -> None:
        item.setText(col, f"{value:.3f}")
        item.setTextAlignment(col, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _sync_children(
        self,
        item: QTreeWidgetItem,
        *,
        l: float,
        w: float,
        h: float,
        module_qty: int,
        pion_qty: int,
        shelf_qty: int,
        mo: float,
        m2_bok: float,
        m2_pion_extra: float,
        m2_polka: float,
        m2_wieniec: float,
        m2_back: float,
        m2_front: float,
        m2_carcass: float,
        m2_total: float,
        mat_c: str,
        mat_f: str,
        mat_b: str,
        fmt_pion: str,
        fmt_wieniec: str,
        fmt_back: str,
        fmt_front: str,
        edgeband_name: str,
        edge_sides: str,
    ) -> None:
        expanded = item.isExpanded()
        while item.childCount() > 0:
            item.takeChild(0)

        default_sides = self._normalize_sides_text(edge_sides)
        edge_parts = self._get_edge_parts_map(item)
        edge_part_band = self._get_edge_part_band_map(item)
        internal_l = max(0.0, l - (2.0 * mo))
        material_rollup: dict[str, float] = {}
        edge_rollup: dict[str, float] = {}
        default_edgeband_key = (edgeband_name or "").strip()

        def _edge_mb(dim_a_mm: float, dim_b_mm: float, sides: set[str]) -> float:
            total_mm = 0.0
            if "L" in sides:
                total_mm += dim_a_mm
            if "P" in sides:
                total_mm += dim_a_mm
            if "G" in sides:
                total_mm += dim_b_mm
            if "D" in sides:
                total_mm += dim_b_mm
            return total_mm / 1000.0

        details: list[tuple[str, str, str, int, float, int, str, int, float, float]] = [
            (
                "bok",
                self._safe_part_name(fmt_pion, "Bok"),
                "H * W",
                2 * module_qty,
                m2_bok,
                self.COL_M2_PION,
                mat_c,
                self.COL_MAT_CARCASS,
                h,
                w,
            ),
            (
                "wieniec",
                self._safe_part_name(fmt_wieniec, "Wieniec"),
                "(L - 2*MO) * W",
                2 * module_qty,
                m2_wieniec,
                self.COL_M2_WIENIEC,
                mat_c,
                self.COL_MAT_CARCASS,
                internal_l,
                w,
            ),
            (
                "plecy",
                self._safe_part_name(fmt_back, "Plecy"),
                "H * W",
                module_qty,
                m2_back,
                self.COL_M2_BACK,
                mat_b,
                self.COL_MAT_BACK,
                h,
                w,
            ),
            (
                "front",
                self._safe_part_name(fmt_front, "Front"),
                "H * L",
                module_qty,
                m2_front,
                self.COL_M2_FRONT,
                mat_f,
                self.COL_MAT_FRONT,
                h,
                l,
            ),
        ]
        if pion_qty > 0:
            details.insert(
                1,
                (
                    "pion",
                    "Pion",
                    "H * W",
                    pion_qty,
                    m2_pion_extra,
                    self.COL_M2_PION,
                    mat_c,
                    self.COL_MAT_CARCASS,
                    h,
                    w,
                ),
            )
        if shelf_qty > 0:
            details.insert(
                2,
                (
                    "polka",
                    "Polka",
                    "(L - 2*MO) * W",
                    shelf_qty,
                    m2_polka,
                    self.COL_M2_WIENIEC,
                    mat_c,
                    self.COL_MAT_CARCASS,
                    internal_l,
                    w,
                ),
            )

        for part_key, part_name, formula, part_qty, value, m2_col, material_name, mat_col, dim_a, dim_b in details:
            if part_qty <= 0:
                continue

            part_sides_text = self._normalize_sides_text(edge_parts.get(part_key, default_sides))
            part_sides = {s for s in part_sides_text.split("+") if s}
            part_band_key = str(edge_part_band.get(part_key, default_edgeband_key)).strip()
            part_edge_mb = _edge_mb(dim_a, dim_b, part_sides)
            part_edge_total_mb = part_edge_mb * float(part_qty)
            material_label = (material_name or "[brak]").strip() or "[brak]"
            material_rollup[material_label] = material_rollup.get(material_label, 0.0) + float(value)
            if part_edge_total_mb > 0.0:
                edge_label = part_band_key or "[brak]"
                edge_rollup[edge_label] = edge_rollup.get(edge_label, 0.0) + part_edge_total_mb

            child = QTreeWidgetItem(item)
            child.setText(self.COL_ID, "  -")
            child.setText(self.COL_NAME, part_name)
            child.setToolTip(self.COL_NAME, f"{formula} | {value:.3f} m2 | {part_edge_total_mb:.3f} mb")
            child.setText(self.COL_RULE, "")
            child.setText(self.COL_QTY, str(int(part_qty)))
            child.setTextAlignment(self.COL_QTY, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            child.setData(self.COL_ID, Qt.ItemDataRole.UserRole, part_key)
            child.setText(self.COL_L, "")
            child.setText(self.COL_W, "")
            child.setText(self.COL_H, "")

            if part_key == "pion":
                child.setText(self.COL_W, f"{w:.1f}")
                child.setText(self.COL_H, f"{h:.1f}")
            elif part_key in {"wieniec", "polka"}:
                child.setText(self.COL_L, f"{internal_l:.1f}")
                child.setText(self.COL_W, f"{w:.1f}")
            elif part_key == "plecy":
                child.setText(self.COL_W, f"{w:.1f}")
                child.setText(self.COL_H, f"{h:.1f}")
            elif part_key == "front":
                child.setText(self.COL_L, f"{l:.1f}")
                child.setText(self.COL_H, f"{h:.1f}")

            child.setText(mat_col, material_name or "[brak]")
            child.setText(self.COL_EDGEBAND, part_band_key)
            self._set_check(child, self.COL_EDGE_L, "L" in part_sides)
            self._set_check(child, self.COL_EDGE_P, "P" in part_sides)
            self._set_check(child, self.COL_EDGE_G, "G" in part_sides)
            self._set_check(child, self.COL_EDGE_D, "D" in part_sides)
            child.setText(m2_col, f"{value:.3f}")
            child.setTextAlignment(m2_col, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._ensure_child_edgeband_combo(child, item, part_key, part_band_key)

            combo_text = ""
            combo_widget = self.tbl.itemWidget(child, self.COL_EDGEBAND)
            if isinstance(combo_widget, QComboBox):
                combo_text = combo_widget.currentText()
            child.setToolTip(
                self.COL_EDGEBAND,
                f"{combo_text or (part_band_key or '[brak]')} | {part_edge_total_mb:.3f} mb",
            )

        if material_rollup or edge_rollup:
            for material_name, m2_value in sorted(material_rollup.items(), key=lambda kv: kv[0].lower()):
                row = QTreeWidgetItem(item)
                row.setText(self.COL_ID, "  *")
                row.setText(self.COL_NAME, f"Suma material: {material_name}")
                row.setText(self.COL_M2_TOTAL, f"{m2_value:.3f} m2")
                row.setTextAlignment(self.COL_M2_TOTAL, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEditable)

            for edge_name, edge_mb_value in sorted(edge_rollup.items(), key=lambda kv: kv[0].lower()):
                row = QTreeWidgetItem(item)
                row.setText(self.COL_ID, "  *")
                row.setText(self.COL_NAME, f"Suma okleina: {edge_name}")
                row.setText(self.COL_EDGEBAND, f"{edge_name} | {edge_mb_value:.3f} mb")
                row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEditable)

        hardware_items = self._get_hardware_items(item)
        hardware_total_pln = 0.0
        for hw_row in hardware_items:
            hw_key = str(hw_row.get("key", "") or "").strip()
            hw_qty = self._parse_float(str(hw_row.get("qty", "0") or "0"), 0.0)
            if not hw_key or hw_qty <= 0.0:
                continue

            unit_price, unit_name = self._hardware_unit_price(hw_key)
            line_total = hw_qty * unit_price
            hardware_total_pln += line_total

            hw_child = QTreeWidgetItem(item)
            hw_child.setText(self.COL_ID, "  +")
            hw_child.setData(self.COL_ID, Qt.ItemDataRole.UserRole, {"kind": "hardware", "key": hw_key})
            hw_child.setText(self.COL_NAME, f"Okucie: {self._hardware_label(hw_key)}")
            hw_child.setText(self.COL_QTY, f"{hw_qty:.2f}".rstrip("0").rstrip("."))
            hw_child.setTextAlignment(self.COL_QTY, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            hw_child.setText(self.COL_EDGEBAND, hw_key)
            hw_child.setText(self.COL_M2_TOTAL, f"{line_total:.2f} zl")
            hw_child.setTextAlignment(self.COL_M2_TOTAL, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            hw_child.setToolTip(
                self.COL_NAME,
                f"{self._hardware_label(hw_key)} | {hw_qty:.2f} {unit_name} | {unit_price:.2f} zl/{unit_name}",
            )
            hw_child.setFlags(hw_child.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if hardware_total_pln > 0.0:
            row = QTreeWidgetItem(item)
            row.setText(self.COL_ID, "  *")
            row.setText(self.COL_NAME, "Suma okuc")
            row.setText(self.COL_M2_TOTAL, f"{hardware_total_pln:.2f} zl")
            row.setTextAlignment(self.COL_M2_TOTAL, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEditable)

        item.setExpanded(expanded)

    def _recompute_item(self, item: QTreeWidgetItem) -> None:
        payload = self._module_payload_from_item(item)
        module_type = str(payload.get("type", "") or "").strip().lower()
        l = self._parse_float(payload["l"])
        w = self._parse_float(payload["w"])
        h = self._parse_float(payload["h"])
        module_qty = max(0, self._parse_int(payload.get("qty", "1"), 1))
        pion_count = max(0, self._parse_int(payload.get("pion", "0")))
        pion_qty = pion_count * module_qty
        shelf_count = max(0, self._parse_int(payload["shelf"]))
        shelf_qty = shelf_count * module_qty
        mo = float(self.sp_mo.value())
        fr_mm = self._parse_float(payload.get("fr", ""), float(self.sp_fr.value()))
        pc_mm = self._parse_float(payload.get("pc", ""), float(self.sp_pc.value()))
        if fr_mm <= 0.0:
            fr_mm = float(self.sp_fr.value())
        if pc_mm <= 0.0:
            pc_mm = float(self.sp_pc.value())
        mat_c = payload["mat_carcass"] or "korpus"
        mat_f = payload["mat_front"] or "front"
        mat_b = payload["mat_back"] or "plecy"
        fmt_pion = self._safe_part_name(str(payload.get("fmt_pion", "") or "").strip(), "Bok")
        fmt_wieniec = self._safe_part_name(str(payload.get("fmt_wieniec", "") or "").strip(), "Wieniec")
        fmt_back = self._safe_part_name(str(payload.get("fmt_back", "") or "").strip(), "Plecy")
        fmt_front = self._safe_part_name(str(payload.get("fmt_front", "") or "").strip(), "Front")
        edgeband_name = self._edgeband_key_from_item(item)
        edge_sides = self._edge_sides_text(item)

        if module_type not in {"gorne", "dolne", "slupek", "inne"}:
            module_type = "gorne"

        internal_l = max(0.0, l - (2.0 * mo))
        area_pion = (h * w) / 1_000_000.0
        area_wieniec = (internal_l * w) / 1_000_000.0
        area_back = (h * w) / 1_000_000.0
        area_front = (h * l) / 1_000_000.0

        m2_bok = area_pion * float(2 * module_qty)
        m2_pion_extra = area_pion * float(pion_qty)
        m2_pion = m2_bok + m2_pion_extra
        m2_wieniec = area_wieniec * float(2 * module_qty)
        m2_polka = area_wieniec * float(shelf_qty)
        m2_back = area_back * float(module_qty)
        m2_front = area_front * float(module_qty)
        m2_carcass = m2_pion + m2_wieniec + m2_polka
        m2_total = m2_carcass + m2_back + m2_front

        self._is_refreshing = True
        try:
            item.setText(self.COL_TYPE, module_type)
            self._ensure_type_combo(item)
            item.setText(self.COL_QTY, str(int(module_qty)))
            item.setText(self.COL_RULE, str(int(pion_count)))
            item.setText(self.COL_FR, f"{fr_mm:.1f}")
            item.setText(self.COL_PC, f"{pc_mm:.1f}")
            item.setText(self.COL_FMT_PION, fmt_pion)
            item.setText(self.COL_FMT_WIENIEC, fmt_wieniec)
            item.setText(self.COL_FMT_BACK, fmt_back)
            item.setText(self.COL_FMT_FRONT, fmt_front)
            item.setText(self.COL_EDGEBAND, edgeband_name)

            self._set_calc_cell(item, self.COL_M2_PION, m2_pion)
            self._set_calc_cell(item, self.COL_M2_WIENIEC, m2_wieniec)
            self._set_calc_cell(item, self.COL_M2_BACK, m2_back)
            self._set_calc_cell(item, self.COL_M2_FRONT, m2_front)
            self._set_calc_cell(item, self.COL_M2_CARCASS, m2_carcass)
            self._set_calc_cell(item, self.COL_M2_TOTAL, m2_total)

            self._sync_children(
                item,
                l=l,
                w=w,
                h=h,
                module_qty=module_qty,
                pion_qty=pion_qty,
                shelf_qty=shelf_qty,
                mo=mo,
                m2_bok=m2_bok,
                m2_pion_extra=m2_pion_extra,
                m2_polka=m2_polka,
                m2_wieniec=m2_wieniec,
                m2_back=m2_back,
                m2_front=m2_front,
                m2_carcass=m2_carcass,
                m2_total=m2_total,
                mat_c=mat_c,
                mat_f=mat_f,
                mat_b=mat_b,
                fmt_pion=fmt_pion,
                fmt_wieniec=fmt_wieniec,
                fmt_back=fmt_back,
                fmt_front=fmt_front,
                edgeband_name=edgeband_name,
                edge_sides=edge_sides,
            )
        finally:
            self._is_refreshing = False

    def _add_row(self) -> None:
        item = QTreeWidgetItem(self.tbl)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        payload = {
            "id": self._next_id(),
            "name": "",
            "type": "gorne",
            "l": "",
            "w": "",
            "h": "",
            "qty": "1",
            "pion": "0",
            "shelf": "0",
            "mat_carcass": "korpus",
            "mat_front": "front",
            "fr": f"{float(self.sp_fr.value()):.1f}",
            "mat_back": "plecy",
            "pc": f"{float(self.sp_pc.value()):.1f}",
            "fmt_pion": "Bok",
            "fmt_wieniec": "Wieniec",
            "fmt_back": "Plecy",
            "fmt_front": "Front",
            "edgeband": "",
            "edge_l": False,
            "edge_p": False,
            "edge_g": False,
            "edge_d": False,
            "edge_part_band": {},
            "hardware_items": [],
        }

        self._is_refreshing = True
        try:
            self._set_module_payload(item, payload)
            self._ensure_type_combo(item)
            self._ensure_edgeband_combo(item)
        finally:
            self._is_refreshing = False

        self._recompute_item(item)
        item.setExpanded(False)
        self._rebuild_summary()

    def _remove_selected_rows(self) -> None:
        selected = self.tbl.selectedItems()
        modules: list[QTreeWidgetItem] = []

        for item in selected:
            top = self._top_item(item)
            if top is not None and top not in modules:
                modules.append(top)

        if not modules:
            current = self.tbl.currentItem()
            top = self._top_item(current)
            if top is not None:
                modules.append(top)

        for module_item in modules:
            idx = self.tbl.indexOfTopLevelItem(module_item)
            if idx >= 0:
                self.tbl.takeTopLevelItem(idx)

        self._recompute_all()

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if self._is_refreshing:
            return

        top = self._top_item(item)
        if top is None:
            return

        if top is not item:
            if col in {self.COL_EDGE_L, self.COL_EDGE_P, self.COL_EDGE_G, self.COL_EDGE_D}:
                part_key = str(item.data(self.COL_ID, Qt.ItemDataRole.UserRole) or "").strip().lower()
                if part_key:
                    edge_parts = self._get_edge_parts_map(top)
                    edge_parts[part_key] = self._edge_sides_text(item)
                    self._set_edge_parts_map(top, edge_parts)
            self._recompute_item(top)
            self._rebuild_summary()
            return

        if col == self.COL_ID and not str(item.text(self.COL_ID)).strip():
            self._is_refreshing = True
            try:
                item.setText(self.COL_ID, self._next_id())
            finally:
                self._is_refreshing = False
        if col in {self.COL_EDGE_L, self.COL_EDGE_P, self.COL_EDGE_G, self.COL_EDGE_D}:
            self._set_edge_parts_map(item, {})

        self._recompute_item(item)
        self._rebuild_summary()

    def _recompute_all(self) -> None:
        for item in self._iter_modules():
            self._ensure_type_combo(item)
            self._ensure_edgeband_combo(item)
            self._recompute_item(item)
        self._apply_type_segregation()
        self._rebuild_summary()

    def _rebuild_summary(self) -> None:
        material_totals: dict[tuple[str, str], float] = {}
        total_all = 0.0

        for item in self._iter_modules():
            mat_c = str(item.text(self.COL_MAT_CARCASS)).strip() or "[brak]"
            mat_f = str(item.text(self.COL_MAT_FRONT)).strip() or "[brak]"
            mat_b = str(item.text(self.COL_MAT_BACK)).strip() or "[brak]"

            m2_c = self._parse_float(item.text(self.COL_M2_CARCASS), 0.0)
            m2_f = self._parse_float(item.text(self.COL_M2_FRONT), 0.0)
            m2_b = self._parse_float(item.text(self.COL_M2_BACK), 0.0)

            material_totals[(mat_c, "korpus")] = material_totals.get((mat_c, "korpus"), 0.0) + m2_c
            material_totals[(mat_f, "front")] = material_totals.get((mat_f, "front"), 0.0) + m2_f
            material_totals[(mat_b, "plecy")] = material_totals.get((mat_b, "plecy"), 0.0) + m2_b

            total_all += m2_c + m2_f + m2_b

        self.tbl_summary.setRowCount(0)
        for (material_name, scope), value in sorted(material_totals.items(), key=lambda x: (x[0][1], x[0][0])):
            row = self.tbl_summary.rowCount()
            self.tbl_summary.insertRow(row)
            self.tbl_summary.setItem(row, 0, QTableWidgetItem(material_name))
            it_m2 = QTableWidgetItem(f"{value:.3f}")
            it_m2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_summary.setItem(row, 1, it_m2)
            self.tbl_summary.setItem(row, 2, QTableWidgetItem(scope))

        self.lab_total.setText(f"RAZEM: {total_all:.3f} m2")

    def _save_store(self) -> None:
        rows = [self._module_payload_from_item(item) for item in self._iter_modules()]
        payload = {
            "mo_mm": float(self.sp_mo.value()),
            "rows": rows,
        }
        self._store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_store(self) -> None:
        raw = {}
        try:
            text = self._store_path.read_text(encoding="utf-8")
            raw = json.loads(text) if text.strip() else {}
            if not isinstance(raw, dict):
                raw = {}
        except Exception:
            raw = {}

        mo_value = self._parse_float(str(raw.get("mo_mm", "18.0")), 18.0)
        rows = raw.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        self._is_refreshing = True
        try:
            self.sp_mo.setValue(mo_value)
            self.tbl.clear()
            self.tbl.setColumnCount(len(self.HEADER_LABELS))
            self.tbl.setHeaderLabels(self.HEADER_LABELS)
            self._configure_tree_columns()

            for row_payload in rows:
                if not isinstance(row_payload, dict):
                    continue
                item = QTreeWidgetItem(self.tbl)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                fixed_payload = dict(row_payload)
                if not str(fixed_payload.get("id", "")).strip():
                    fixed_payload["id"] = self._next_id()
                self._set_module_payload(item, fixed_payload)
                self._ensure_type_combo(item)
                self._ensure_edgeband_combo(item)
        finally:
            self._is_refreshing = False

        self._recompute_all()
        self.tbl.collapseAll()
