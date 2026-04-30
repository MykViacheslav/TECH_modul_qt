from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from src.domain.project_model import ProjectModel
from src.services.project_model_quick_quote_adapter import (
    build_quick_quote_project_model,
)
from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
    quick_quote_archive_path,
    quick_quote_export_dir,
    sanitize_quick_quote_entries,
)
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.client_store_json import ClientStoreJson

TABLE_TEXT_STYLE = ""


SECTION_SCOPE_ITEMS: tuple[str, ...] = (
    "Gorne szafki",
    "Dolne szafki",
    "Slupki",
    "Wysoka zabudowa",
    "Inne",
)

MATERIAL_FALLBACK_ITEMS: tuple[str, ...] = ("[wybierz]",)
AUTO_PRICE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
MANUAL_PRICE_ROLE = int(Qt.ItemDataRole.UserRole) + 2


class _NumericSortItem(QTableWidgetItem):
    def __init__(self, value: float, text: str, editable: bool = False) -> None:
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, float(value))
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if not editable:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(Qt.ItemDataRole.UserRole)
        right = other.data(Qt.ItemDataRole.UserRole) if isinstance(other, QTableWidgetItem) else None
        if left is not None and right is not None:
            try:
                return float(left) < float(right)
            except Exception:
                pass
        return super().__lt__(other)


def _slugify_filename(value: str, fallback: str = "oferta") -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def _next_unique_export_path(directory: Path, stem: str, suffix: str) -> Path:
    first = directory / f"{stem}{suffix}"
    if not first.exists():
        return first
    index = 2
    while True:
        candidate = directory / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _create_simple_pdf(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    payload = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        f"4 0 obj << /Length {len(escaped) + 40} >> stream\n"
        "BT /F1 12 Tf 36 760 Td\n"
        f"({escaped}) Tj\n"
        "ET\n"
        "endstream endobj\n"
        "xref\n0 5\n0000000000 65535 f \n"
        "0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n0000000205 00000 n \n"
        "trailer << /Root 1 0 R /Size 5 >>\nstartxref\n320\n%%EOF\n"
    )
    path.write_bytes(payload.encode("utf-8", errors="ignore"))


def _default_data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[3]
    return root / "data"


class SzybkaWycenaSection(QFrame):
    def __init__(
        self,
        section_title: str,
        section_id: str,
        module_templates: list[dict],
        hardware_options: list[tuple[str, str, float]],
        material_options_by_type: dict[str, list[tuple[str, str]]],
        mo_mm: float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._is_refreshing = False
        self._is_collapsed = False
        self._section_id = section_id
        self._section_title = section_title
        self._mo_mm = float(mo_mm or 18.0)

        self._module_templates: dict[str, dict] = {}
        self._hardware_options: list[tuple[str, str, float]] = []
        self._hardware_price_by_key: dict[str, float] = {}
        self._material_options_by_type: dict[str, list[tuple[str, str]]] = {}
        self._materials_total = 0.0

        self.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 10px; background:#fbfcfe; }")
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 10, 12, 10)
        box.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        self.btn_toggle = QToolButton(self)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle.setToolTip("Zwin / rozwin sekcje")
        header_row.addWidget(self.btn_toggle, 0)

        self.lab_title = QLabel(section_title, self)
        self.lab_title.setStyleSheet("font-size:15px; font-weight:800;")
        header_row.addWidget(self.lab_title, 0)
        header_row.addStretch(1)

        self.lab_total_inline = QLabel("Suma: 0.00 zl", self)
        self.lab_total_inline.setStyleSheet("font-weight:700; color:#334155;")
        header_row.addWidget(self.lab_total_inline, 0)

        self.lab_section_id = QLabel(f"ID: {section_id}", self)
        self.lab_section_id.setStyleSheet("font-weight:700; color:#334155;")
        header_row.addWidget(self.lab_section_id, 0)
        box.addLayout(header_row)

        self.body = QWidget(self)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        main_header = QHBoxLayout()
        main_header.setSpacing(6)
        self.btn_toggle_main = QToolButton(self)
        self.btn_toggle_main.setCheckable(True)
        self.btn_toggle_main.setChecked(True)
        self.btn_toggle_main.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle_main.setToolTip("Zwin / rozwin tabele sekcji")
        main_header.addWidget(self.btn_toggle_main, 0)
        self.lab_main_title = QLabel("Tabela sekcji", self)
        self.lab_main_title.setStyleSheet("font-weight:700;")
        main_header.addWidget(self.lab_main_title, 0)
        main_header.addStretch(1)
        body_layout.addLayout(main_header)

        self.scope_row_widget = QWidget(self)
        row_scope_material = QHBoxLayout(self.scope_row_widget)
        row_scope_material.setContentsMargins(0, 0, 0, 0)
        row_scope_material.setSpacing(8)
        row_scope_material.addWidget(QLabel("Sekcja:", self), 0)
        self.cb_scope = QComboBox(self)
        self.cb_scope.addItems(SECTION_SCOPE_ITEMS)
        self.cb_scope.setMinimumWidth(180)
        row_scope_material.addWidget(self.cb_scope, 0)
        row_scope_material.addWidget(QLabel("Material korpus:", self), 0)
        self.cb_material_korpus = QComboBox(self)
        self.cb_material_korpus.setMinimumWidth(200)
        row_scope_material.addWidget(self.cb_material_korpus, 0)
        row_scope_material.addWidget(QLabel("Material front:", self), 0)
        self.cb_material_front = QComboBox(self)
        self.cb_material_front.setMinimumWidth(200)
        row_scope_material.addWidget(self.cb_material_front, 0)
        row_scope_material.addSpacing(10)
        row_scope_material.addWidget(QLabel("Szafka z bazy modulow:", self), 0)
        self.cb_module_from_base = QComboBox(self)
        self.cb_module_from_base.setMinimumWidth(150)
        row_scope_material.addWidget(self.cb_module_from_base, 0)
        self.btn_insert_module = QPushButton("Wstaw z bazy", self)
        row_scope_material.addWidget(self.btn_insert_module, 0)
        row_scope_material.addStretch(1)
        body_layout.addWidget(self.scope_row_widget, 0)

        self.tbl = QTableWidget(0, 6, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels(["ID", "Szafka", "L", "W", "H", "Cena"])
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
            | QTableWidget.EditTrigger.SelectedClicked
        )
        self.tbl.verticalHeader().setVisible(True)
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl.setColumnWidth(0, 90)
        self.tbl.setColumnWidth(1, 360)
        self.tbl.setColumnWidth(2, 90)
        self.tbl.setColumnWidth(3, 90)
        self.tbl.setColumnWidth(4, 90)
        self.tbl.setColumnWidth(5, 130)
        body_layout.addWidget(self.tbl, 1)

        self.controls_widget = QWidget(self)
        controls = QHBoxLayout(self.controls_widget)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self.btn_add_row = QPushButton("Dodaj wiersz", self)
        self.btn_remove_row = QPushButton("Usun wiersz", self)
        self.btn_sum = QPushButton("Przelicz", self)
        controls.addWidget(self.btn_add_row, 0)
        controls.addWidget(self.btn_remove_row, 0)
        controls.addWidget(self.btn_sum, 0)
        controls.addStretch(1)
        controls.addWidget(QLabel("Suma sekcji:", self), 0)
        self.ed_total = QLineEdit(self)
        self.ed_total.setReadOnly(True)
        self.ed_total.setFixedWidth(150)
        controls.addWidget(self.ed_total, 0)
        body_layout.addWidget(self.controls_widget, 0)

        materials_frame = QFrame(self); materials_frame.setProperty("uiCard", True)
        materials_frame.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background:transparent; }")
        materials_layout = QVBoxLayout(materials_frame)
        materials_layout.setContentsMargins(8, 8, 8, 8)
        materials_layout.setSpacing(6)
        materials_header = QHBoxLayout()
        materials_header.setSpacing(6)
        self.btn_toggle_materials = QToolButton(self)
        self.btn_toggle_materials.setCheckable(True)
        self.btn_toggle_materials.setChecked(True)
        self.btn_toggle_materials.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle_materials.setToolTip("Zwin / rozwin podsumowanie materialow")
        materials_header.addWidget(self.btn_toggle_materials, 0)
        self.lab_materials = QLabel("Podsumowanie materialow (po nazwie i typie, m2):", self)
        self.lab_materials.setStyleSheet("font-weight:600;")
        materials_header.addWidget(self.lab_materials, 0)
        materials_header.addStretch(1)
        materials_layout.addLayout(materials_header)

        self.materials_body = QWidget(materials_frame)
        materials_body_layout = QVBoxLayout(self.materials_body)
        materials_body_layout.setContentsMargins(0, 0, 0, 0)
        materials_body_layout.setSpacing(4)
        self.tbl_materials = QTableWidget(0, 7, self)
        self.tbl_materials.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_materials.setHorizontalHeaderLabels(
            ["ID", "Nazwa", "Parametry", "Cena [zl]", "Typ", "m2", "Suma [zl]"]
        )
        self.tbl_materials.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_materials.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_materials.setSortingEnabled(True)
        self.tbl_materials.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tbl_materials.verticalHeader().setVisible(False)
        mh = self.tbl_materials.horizontalHeader()
        mh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        mh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        mh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        mh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        mh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        mh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        mh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        mh.setSortIndicator(6, Qt.SortOrder.DescendingOrder)
        materials_body_layout.addWidget(self.tbl_materials, 1)
        materials_layout.addWidget(self.materials_body, 1)
        body_layout.addWidget(materials_frame, 1)

        hardware_frame = QFrame(self); hardware_frame.setProperty("uiCard", True)
        hardware_frame.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background:transparent; }")
        hardware_layout = QVBoxLayout(hardware_frame)
        hardware_layout.setContentsMargins(8, 8, 8, 8)
        hardware_layout.setSpacing(6)
        hardware_header = QHBoxLayout()
        hardware_header.setSpacing(6)
        self.btn_toggle_hardware = QToolButton(self)
        self.btn_toggle_hardware.setCheckable(True)
        self.btn_toggle_hardware.setChecked(True)
        self.btn_toggle_hardware.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle_hardware.setToolTip("Zwin / rozwin okucie")
        hardware_header.addWidget(self.btn_toggle_hardware, 0)
        self.lab_hardware = QLabel("Okucie:", self)
        self.lab_hardware.setStyleSheet("font-weight:600;")
        hardware_header.addWidget(self.lab_hardware, 0)
        hardware_header.addStretch(1)
        hardware_layout.addLayout(hardware_header)

        self.hardware_body = QWidget(hardware_frame)
        hardware_body_layout = QVBoxLayout(self.hardware_body)
        hardware_body_layout.setContentsMargins(0, 0, 0, 0)
        hardware_body_layout.setSpacing(6)

        hw_controls = QHBoxLayout()
        hw_controls.setSpacing(8)
        self.btn_add_hw = QPushButton("+ Dodaj okucie", self)
        self.btn_remove_hw = QPushButton("Usun okucie", self)
        hw_controls.addWidget(self.btn_add_hw, 0)
        hw_controls.addWidget(self.btn_remove_hw, 0)
        hw_controls.addStretch(1)
        hardware_body_layout.addLayout(hw_controls)

        self.tbl_hardware = QTableWidget(0, 5, self)
        self.tbl_hardware.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_hardware.setHorizontalHeaderLabels(["ID", "Nazwa", "Cena [zl]", "Ilosc", "Suma [zl]"])
        self.tbl_hardware.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_hardware.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl_hardware.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
            | QTableWidget.EditTrigger.SelectedClicked
        )
        self.tbl_hardware.setSortingEnabled(True)
        self.tbl_hardware.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tbl_hardware.verticalHeader().setVisible(False)
        hh = self.tbl_hardware.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSortIndicator(4, Qt.SortOrder.DescendingOrder)
        hardware_body_layout.addWidget(self.tbl_hardware, 1)
        hardware_layout.addWidget(self.hardware_body, 1)
        body_layout.addWidget(hardware_frame, 1)

        box.addWidget(self.body, 1)

        self.btn_toggle.toggled.connect(self._on_toggle_section)
        self.btn_toggle_main.toggled.connect(self._on_toggle_main_block)
        self.btn_toggle_materials.toggled.connect(self._on_toggle_materials_block)
        self.btn_toggle_hardware.toggled.connect(self._on_toggle_hardware_block)
        self.btn_insert_module.clicked.connect(self._insert_module_from_base)
        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_remove_row.clicked.connect(self._remove_selected_rows)
        self.btn_sum.clicked.connect(self._recalculate_all)
        self.tbl.itemChanged.connect(self._on_table_item_changed)
        self.tbl.cellClicked.connect(self._on_table_cell_clicked)
        self.cb_material_korpus.currentIndexChanged.connect(lambda _idx: self._recalculate_all())
        self.cb_material_front.currentIndexChanged.connect(lambda _idx: self._recalculate_all())
        self.btn_add_hw.clicked.connect(self._add_hardware_row)
        self.btn_remove_hw.clicked.connect(self._remove_selected_hardware_rows)
        self.tbl_hardware.itemChanged.connect(self._on_hardware_item_changed)

        self.set_sources(
            module_templates,
            hardware_options,
            material_options_by_type,
            mo_mm=self._mo_mm,
        )
        self._recalculate_all()

    @property
    def section_id(self) -> str:
        return self._section_id

    @property
    def section_title(self) -> str:
        return self._section_title

    def set_section_title(self, title: str) -> None:
        cleaned = str(title or "").strip()
        if not cleaned:
            return
        self._section_title = cleaned
        self.lab_title.setText(cleaned)

    def set_sources(
        self,
        module_templates: list[dict],
        hardware_options: list[tuple[str, str, float]],
        material_options_by_type: dict[str, list[tuple[str, str]]],
        mo_mm: float,
    ) -> None:
        self._mo_mm = float(mo_mm or 18.0)
        self._module_templates = {}
        for row in module_templates:
            if not isinstance(row, dict):
                continue
            key = str(row.get("id", "") or "").strip()
            if not key:
                continue
            self._module_templates[key] = dict(row)
        self._hardware_options = list(hardware_options)
        self._hardware_price_by_key = {str(k): float(price) for k, _label, price in self._hardware_options}
        self._material_options_by_type = {
            str(k or "").strip().lower(): list(v or [])
            for k, v in (material_options_by_type or {}).items()
        }
        self._refresh_module_combo()
        self._refresh_material_combos()
        self._refresh_hardware_combos()
        self._recalculate_all()

    def _material_items_for_type(self, material_type: str) -> list[tuple[str, str]]:
        key = str(material_type or "").strip().lower()
        options = list(self._material_options_by_type.get(key, []))
        has_real_option = any(str(opt_key or "").strip() for opt_key, _label in options)
        if options and has_real_option:
            return options
        all_options = list(self._material_options_by_type.get("all", []))
        if all_options:
            return all_options
        return [("", MATERIAL_FALLBACK_ITEMS[0])]

    def _refresh_material_combo(self, combo: QComboBox, material_type: str) -> None:
        current_key = str(combo.currentData() or "")
        current_text = str(combo.currentText() or "").strip()
        options = self._material_items_for_type(material_type)
        combo.blockSignals(True)
        combo.clear()
        for key, label in options:
            combo.addItem(label, key)
        idx = combo.findData(current_key)
        if idx < 0 and current_text:
            for i in range(combo.count()):
                if str(combo.itemText(i)).strip() == current_text:
                    idx = i
                    break
        if idx < 0:
            idx = 0
        if combo.count() > 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _refresh_material_combos(self) -> None:
        self._refresh_material_combo(self.cb_material_korpus, "korpus")
        self._refresh_material_combo(self.cb_material_front, "front")

    def _refresh_module_combo(self) -> None:
        current_key = str(self.cb_module_from_base.currentData() or "")
        self.cb_module_from_base.blockSignals(True)
        self.cb_module_from_base.clear()
        self.cb_module_from_base.addItem("[wybierz]", "")
        for key, payload in sorted(self._module_templates.items(), key=lambda x: x[0]):
            name = str(payload.get("name", "") or "").strip()
            label = f"{key} | {name}" if name else key
            self.cb_module_from_base.addItem(label, key)
        idx = self.cb_module_from_base.findData(current_key)
        if idx < 0:
            idx = 0
        self.cb_module_from_base.setCurrentIndex(idx)
        self.cb_module_from_base.blockSignals(False)

    def _set_row_id(self, row: int, value: str) -> None:
        item = QTableWidgetItem(str(value or ""))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.tbl.setItem(row, 0, item)

    def _new_price_item(self, value: float = 0.0) -> QTableWidgetItem:
        item = QTableWidgetItem(f"{float(value):.2f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setData(AUTO_PRICE_ROLE, float(value))
        item.setData(MANUAL_PRICE_ROLE, False)
        return item

    def _new_manual_row_id(self) -> str:
        max_num = 0
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 0)
            raw = str(item.text() if item is not None else "").strip().upper()
            if not raw.startswith("R"):
                continue
            digits = "".join(ch for ch in raw[1:] if ch.isdigit())
            if not digits:
                continue
            try:
                max_num = max(max_num, int(digits))
            except ValueError:
                continue
        return f"R{max_num + 1:03d}"

    def _add_row(self) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self._is_refreshing = True
        try:
            self._set_row_id(row, self._new_manual_row_id())
            self.tbl.setItem(row, 1, QTableWidgetItem(""))
            self.tbl.setItem(row, 2, QTableWidgetItem(""))
            self.tbl.setItem(row, 3, QTableWidgetItem(""))
            self.tbl.setItem(row, 4, QTableWidgetItem(""))
            self.tbl.setItem(row, 5, self._new_price_item(0.0))
        finally:
            self._is_refreshing = False
        self._recalculate_all()

    def _insert_module_from_base(self) -> None:
        key = str(self.cb_module_from_base.currentData() or "").strip()
        if not key:
            return
        payload = dict(self._module_templates.get(key, {}))
        if not payload:
            return

        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self._is_refreshing = True
        try:
            self._set_row_id(row, key)
            name_item = QTableWidgetItem(str(payload.get("name", "") or ""))
            name_item.setData(Qt.ItemDataRole.UserRole, key)
            self.tbl.setItem(row, 1, name_item)
            self.tbl.setItem(row, 2, QTableWidgetItem(str(payload.get("l", "") or "")))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(payload.get("w", "") or "")))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(payload.get("h", "") or "")))
            self.tbl.setItem(row, 5, self._new_price_item(0.0))
        finally:
            self._is_refreshing = False
        self._append_hardware_from_template(payload)
        self._recalculate_all()

    def _remove_selected_rows(self) -> None:
        selected = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not selected:
            current = self.tbl.currentRow()
            if current >= 0:
                self.tbl.removeRow(current)
        else:
            for model_index in sorted(selected, key=lambda x: x.row(), reverse=True):
                self.tbl.removeRow(model_index.row())
        self._recalculate_all()

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_refreshing:
            return
        if item.column() == 0:
            return
        if item.column() == 5:
            current = self._parse_float(item.text())
            auto_value = self._parse_float(str(item.data(AUTO_PRICE_ROLE) or "0"))
            manual = abs(current - auto_value) > 0.0001
            if current <= 0.0:
                manual = False
            item.setData(MANUAL_PRICE_ROLE, manual)
        self._recalculate_all()

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        if col not in (2, 3, 4, 5):
            return
        item = self.tbl.item(row, col)
        if item is None:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            return
        self.tbl.editItem(item)

    def _fit_table_visible_rows(self, table: QTableWidget, min_rows: int, max_rows: int) -> None:
        visible_rows = max(min_rows, min(max_rows, max(1, table.rowCount())))
        header_h = table.horizontalHeader().height()
        row_h = table.verticalHeader().defaultSectionSize()
        height = header_h + (row_h * visible_rows) + (table.frameWidth() * 2) + 4
        table.setMinimumHeight(height)

    def _capture_sort_state(self, table: QTableWidget) -> tuple[bool, int, Qt.SortOrder]:
        header = table.horizontalHeader()
        return (
            bool(table.isSortingEnabled()),
            int(header.sortIndicatorSection()),
            header.sortIndicatorOrder(),
        )

    def _restore_sort_state(
        self,
        table: QTableWidget,
        sorting_enabled: bool,
        sort_col: int,
        sort_order: Qt.SortOrder,
    ) -> None:
        table.setSortingEnabled(sorting_enabled)
        if sorting_enabled and 0 <= sort_col < table.columnCount():
            table.sortItems(sort_col, sort_order)

    def _set_block_visible(self, expanded: bool, toggle: QToolButton, widgets: list[QWidget]) -> None:
        for widget in widgets:
            widget.setVisible(expanded)
        toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def _on_toggle_main_block(self, expanded: bool) -> None:
        self._set_block_visible(expanded, self.btn_toggle_main, [self.scope_row_widget, self.tbl, self.controls_widget])

    def _on_toggle_materials_block(self, expanded: bool) -> None:
        self._set_block_visible(expanded, self.btn_toggle_materials, [self.materials_body])

    def _on_toggle_hardware_block(self, expanded: bool) -> None:
        self._set_block_visible(expanded, self.btn_toggle_hardware, [self.hardware_body])

    def _on_toggle_section(self, expanded: bool) -> None:
        self._is_collapsed = not expanded
        self.body.setVisible(expanded)
        self.btn_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def set_collapsed(self, collapsed: bool) -> None:
        self.btn_toggle.setChecked(not collapsed)

    def _parse_float(self, text: str) -> float:
        value = str(text or "").strip()
        if not value:
            return 0.0
        value = value.replace("zl", "").replace("ZL", "").replace(",", ".").replace(" ", "")
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _row_template(self, row: int) -> dict | None:
        item = self.tbl.item(row, 1)
        if item is None:
            return None
        key = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not key:
            return None
        payload = self._module_templates.get(key)
        return dict(payload) if payload else None

    def _recalculate_price_total(self) -> None:
        total = 0.0
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 5)
            if item is None:
                continue
            total += self._parse_float(item.text())
        hardware_total = 0.0
        for row in range(self.tbl_hardware.rowCount()):
            item = self.tbl_hardware.item(row, 4)
            if item is None:
                continue
            hardware_total += self._parse_float(item.text())
        total += hardware_total
        self.ed_total.setText(f"{total:.2f} zl")
        self.lab_total_inline.setText(f"Suma: {total:.2f} zl")

    def _material_price_from_label(self, label: str) -> float:
        text = str(label or "").strip().lower()
        if not text:
            return 0.0
        matches = re.findall(r"([0-9]+(?:[.,][0-9]+)?)\s*zl", text)
        if not matches:
            return 0.0
        return self._parse_float(matches[-1])

    def _material_parts_from_label(self, label: str) -> tuple[str, str, str, float]:
        raw = str(label or "").strip()
        if not raw:
            return "", "", "", 0.0

        parts = [part.strip() for part in raw.split("|") if part.strip()]
        price = 0.0
        if parts and "zl" in parts[-1].lower():
            price = self._material_price_from_label(parts[-1])
            parts = parts[:-1]

        material_id = ""
        if parts and re.match(r"^[a-zA-Z]+[0-9]+$", parts[0]):
            material_id = parts[0]
            parts = parts[1:]

        name = parts[0] if parts else ""
        params = " | ".join(parts[1:]) if len(parts) > 1 else ""
        if not name:
            name = raw
        return material_id, name, params, price

    def _apply_auto_row_prices(self, row_totals: dict[int, float]) -> None:
        prev_refreshing = self._is_refreshing
        was_blocked = self.tbl.blockSignals(True)
        self._is_refreshing = True
        try:
            for row in range(self.tbl.rowCount()):
                computed = float(row_totals.get(row, 0.0))
                item = self.tbl.item(row, 5)
                if item is None:
                    item = self._new_price_item(0.0)
                    self.tbl.setItem(row, 5, item)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                manual = bool(item.data(MANUAL_PRICE_ROLE))
                current = self._parse_float(item.text())
                if manual and current <= 0.0:
                    manual = False
                    item.setData(MANUAL_PRICE_ROLE, False)
                if manual:
                    continue
                item.setText(f"{computed:.2f}")
                item.setData(AUTO_PRICE_ROLE, computed)
        finally:
            self._is_refreshing = prev_refreshing
            self.tbl.blockSignals(was_blocked)

    def _recalculate_material_summary(self) -> None:
        totals: dict[tuple[str, str], float] = {}
        row_totals: dict[int, float] = {}
        self._materials_total = 0.0
        mo = float(self._mo_mm)
        selected_korpus = self.cb_material_korpus.currentText().strip() or "[wybierz]"
        selected_front = self.cb_material_front.currentText().strip() or "[wybierz]"

        for row in range(self.tbl.rowCount()):
            l = self._parse_float(self.tbl.item(row, 2).text() if self.tbl.item(row, 2) else "")
            w = self._parse_float(self.tbl.item(row, 3).text() if self.tbl.item(row, 3) else "")
            h = self._parse_float(self.tbl.item(row, 4).text() if self.tbl.item(row, 4) else "")
            if l <= 0.0 or w <= 0.0 or h <= 0.0:
                continue

            tpl = self._row_template(row) or {}
            shelf_count = max(0, int(round(self._parse_float(str(tpl.get("shelf", "0") or "0")))))
            mat_c_raw = str(tpl.get("mat_carcass", "") or "").strip()
            mat_f_raw = str(tpl.get("mat_front", "") or "").strip()
            mat_b_raw = str(tpl.get("mat_back", "") or "").strip()

            mat_c = selected_korpus if mat_c_raw.lower() in {"", "korpus", "carcass"} else mat_c_raw
            mat_f = selected_front if mat_f_raw.lower() in {"", "front"} else mat_f_raw
            mat_b = selected_korpus if mat_b_raw.lower() in {"", "plecy", "back", "korpus"} else mat_b_raw

            internal_l = max(0.0, l - (2.0 * mo))
            m2_pion = (h * w) / 1_000_000.0
            m2_wieniec = (internal_l * w) / 1_000_000.0
            m2_back = (h * w) / 1_000_000.0
            m2_front = (h * l) / 1_000_000.0
            m2_carcass = m2_pion + m2_wieniec + (float(shelf_count) * m2_wieniec)

            totals[(mat_c, "korpus")] = totals.get((mat_c, "korpus"), 0.0) + m2_carcass
            totals[(mat_b, "plecy")] = totals.get((mat_b, "plecy"), 0.0) + m2_back
            totals[(mat_f, "front")] = totals.get((mat_f, "front"), 0.0) + m2_front
            row_totals[row] = (
                (m2_carcass * self._material_price_from_label(mat_c))
                + (m2_back * self._material_price_from_label(mat_b))
                + (m2_front * self._material_price_from_label(mat_f))
            )

        self._apply_auto_row_prices(row_totals)

        sorting_enabled, sort_col, sort_order = self._capture_sort_state(self.tbl_materials)
        self.tbl_materials.setSortingEnabled(False)
        self.tbl_materials.setRowCount(0)
        for (material, typ), value in sorted(totals.items(), key=lambda x: (x[0][1], x[0][0])):
            r = self.tbl_materials.rowCount()
            self.tbl_materials.insertRow(r)
            material_id, material_name, material_params, material_price = self._material_parts_from_label(material)
            row_sum = value * material_price
            self._materials_total += row_sum

            self.tbl_materials.setItem(r, 0, QTableWidgetItem(material_id))
            self.tbl_materials.setItem(r, 1, QTableWidgetItem(material_name))
            self.tbl_materials.setItem(r, 2, QTableWidgetItem(material_params))

            price_text = f"{material_price:.2f}" if material_price > 0 else ""
            self.tbl_materials.setItem(r, 3, _NumericSortItem(material_price, price_text))

            self.tbl_materials.setItem(r, 4, QTableWidgetItem(typ))

            self.tbl_materials.setItem(r, 5, _NumericSortItem(value, f"{value:.3f}"))

            sum_text = f"{row_sum:.2f}" if row_sum > 0 else ""
            self.tbl_materials.setItem(r, 6, _NumericSortItem(row_sum, sum_text))

        self._restore_sort_state(self.tbl_materials, sorting_enabled, sort_col, sort_order)

        self._fit_table_visible_rows(self.tbl_materials, min_rows=5, max_rows=12)

    def _make_hardware_combo(self) -> QComboBox:
        combo = QComboBox(self.tbl_hardware)
        combo.addItem("[wybierz]", "")
        if not self._hardware_options:
            return combo
        for key, label, _price in self._hardware_options:
            combo.addItem(label, key)
        combo.currentIndexChanged.connect(lambda _idx: self._recalculate_all())
        return combo

    def _set_hardware_row_id(self, row: int, hardware_id: str) -> None:
        item = self.tbl_hardware.item(row, 0)
        if item is None:
            item = QTableWidgetItem("")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setText(str(hardware_id or ""))
        self.tbl_hardware.setItem(row, 0, item)

    def _set_hardware_price(self, row: int, price: float) -> None:
        item = _NumericSortItem(float(price), f"{float(price):.2f}")
        self.tbl_hardware.setItem(row, 2, item)

    def _sync_hardware_row_details(self, row: int) -> None:
        combo = self.tbl_hardware.cellWidget(row, 1)
        key = str(combo.currentData() or "") if isinstance(combo, QComboBox) else ""
        price = float(self._hardware_price_by_key.get(key, 0.0))
        self._set_hardware_row_id(row, key)
        self._set_hardware_price(row, price)

    def _format_qty_text(self, qty: float) -> str:
        value = float(qty)
        if abs(value - round(value)) < 0.0001:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _upsert_hardware_line(self, hardware_key: str, qty_to_add: float) -> None:
        key = str(hardware_key or "").strip()
        qty_value = float(qty_to_add or 0.0)
        if not key or qty_value <= 0.0:
            return

        for row in range(self.tbl_hardware.rowCount()):
            current_key = str(self.tbl_hardware.item(row, 0).text() if self.tbl_hardware.item(row, 0) else "").strip()
            if current_key != key:
                continue
            qty_item = self.tbl_hardware.item(row, 3)
            if qty_item is None:
                qty_item = QTableWidgetItem("0")
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tbl_hardware.setItem(row, 3, qty_item)
            current_qty = self._parse_float(qty_item.text() if qty_item else "0")
            new_qty = current_qty + qty_value
            qty_item.setText(self._format_qty_text(new_qty))
            qty_item.setData(Qt.ItemDataRole.UserRole, new_qty)
            return

        row = self.tbl_hardware.rowCount()
        self.tbl_hardware.insertRow(row)
        self._set_hardware_row_id(row, "")
        combo = self._make_hardware_combo()
        idx = combo.findData(key)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.tbl_hardware.setCellWidget(row, 1, combo)
        self._set_hardware_price(row, 0.0)
        qty_item = QTableWidgetItem(self._format_qty_text(qty_value))
        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        qty_item.setData(Qt.ItemDataRole.UserRole, qty_value)
        self.tbl_hardware.setItem(row, 3, qty_item)
        sum_item = _NumericSortItem(0.0, "0.00")
        self.tbl_hardware.setItem(row, 4, sum_item)
        self._sync_hardware_row_details(row)

    def _append_hardware_from_template(self, payload: dict) -> None:
        rows = payload.get("hardware_items", [])
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "") or "").strip()
            qty = self._parse_float(str(row.get("qty", "0") or "0"))
            self._upsert_hardware_line(key, qty)

    def _add_hardware_row(self) -> None:
        row = self.tbl_hardware.rowCount()
        self.tbl_hardware.insertRow(row)
        self._set_hardware_row_id(row, "")
        self.tbl_hardware.setCellWidget(row, 1, self._make_hardware_combo())
        self._set_hardware_price(row, 0.0)
        qty_item = QTableWidgetItem("1")
        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        qty_item.setData(Qt.ItemDataRole.UserRole, 1.0)
        self.tbl_hardware.setItem(row, 3, qty_item)
        sum_item = _NumericSortItem(0.0, "0.00")
        self.tbl_hardware.setItem(row, 4, sum_item)
        self._sync_hardware_row_details(row)
        self._recalculate_all()

    def _remove_selected_hardware_rows(self) -> None:
        selected = self.tbl_hardware.selectionModel().selectedRows() if self.tbl_hardware.selectionModel() is not None else []
        if not selected:
            current = self.tbl_hardware.currentRow()
            if current >= 0:
                self.tbl_hardware.removeRow(current)
        else:
            for model_index in sorted(selected, key=lambda x: x.row(), reverse=True):
                self.tbl_hardware.removeRow(model_index.row())
        self._recalculate_all()

    def _refresh_hardware_combos(self) -> None:
        for row in range(self.tbl_hardware.rowCount()):
            combo = self.tbl_hardware.cellWidget(row, 1)
            old_key = str(combo.currentData() or "") if isinstance(combo, QComboBox) else ""
            new_combo = self._make_hardware_combo()
            idx = new_combo.findData(old_key)
            if idx >= 0:
                new_combo.setCurrentIndex(idx)
            self.tbl_hardware.setCellWidget(row, 1, new_combo)
            self._sync_hardware_row_details(row)
        self._recalculate_all()

    def _on_hardware_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 3:
            qty = self._parse_float(item.text() if item else "0")
            item.setData(Qt.ItemDataRole.UserRole, qty)
            self._recalculate_all()

    def _recalculate_hardware_summary(self) -> None:
        sorting_enabled, sort_col, sort_order = self._capture_sort_state(self.tbl_hardware)
        self.tbl_hardware.setSortingEnabled(False)
        for row in range(self.tbl_hardware.rowCount()):
            self._sync_hardware_row_details(row)
            price_item = self.tbl_hardware.item(row, 2)
            price = self._parse_float(price_item.text() if price_item else "0")
            qty_item = self.tbl_hardware.item(row, 3)
            qty = self._parse_float(qty_item.text() if qty_item else "0")
            if qty_item is not None:
                qty_item.setData(Qt.ItemDataRole.UserRole, qty)
            row_sum = price * qty
            self.tbl_hardware.setItem(row, 4, _NumericSortItem(row_sum, f"{row_sum:.2f}"))
        self._restore_sort_state(self.tbl_hardware, sorting_enabled, sort_col, sort_order)
        self._fit_table_visible_rows(self.tbl_hardware, min_rows=4, max_rows=10)

    def _recalculate_all(self) -> None:
        self._fit_table_visible_rows(self.tbl, min_rows=8, max_rows=16)
        self._recalculate_material_summary()
        self._recalculate_hardware_summary()
        self._recalculate_price_total()


class TabSzybkaWycena(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = CatalogStoreJson()
        self._client_store = ClientStoreJson()
        self._section_counter = 0
        self._sections: list[SzybkaWycenaSection] = []
        self._mo_mm = 18.0
        self._module_templates: list[dict] = []
        self._hardware_options: list[tuple[str, str, float]] = []
        self._material_options_by_type: dict[str, list[tuple[str, str]]] = {}
        self._load_sources()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("SZYBKA WYCENA", self)
        title.setStyleSheet("font-size:22px; font-weight:800;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Sekcje sa zwijane. Dodajesz pasek, wybierasz szafki z bazy modulow, a pod sekcja masz materialy i okucie.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: palette(text);")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)
        self.btn_add_section = QPushButton("➕ Dodaj pasek", self)
        self.btn_edit_section = QPushButton("✏️ Modyfikuj", self)
        self.btn_remove_section = QPushButton("🗑️ Usun", self)
        self.btn_save_to_base = QPushButton("💾 Zapisz w bazie", self)
        self.btn_export_pdf = QPushButton("📄 Eksport PDF", self)
        self.cb_client_selector = QComboBox(self)
        self.cb_client_selector.setMinimumWidth(220)
        self.ed_offer_title = QLineEdit(self)
        self.ed_offer_title.setPlaceholderText("Tytul oferty")
        self.ed_offer_title.setMinimumWidth(220)
        self.ed_discount_pct = QLineEdit(self)
        self.ed_discount_pct.setPlaceholderText("Rabat %")
        self.ed_discount_pct.setFixedWidth(90)
        self.cb_section_picker = QComboBox(self)
        row_actions.addWidget(self.btn_add_section, 0)
        row_actions.addWidget(self.btn_edit_section, 0)
        row_actions.addWidget(self.btn_remove_section, 0)
        row_actions.addWidget(self.btn_save_to_base, 0)

        for btn in (self.btn_add_section, self.btn_edit_section, self.btn_remove_section, self.btn_save_to_base, self.btn_export_pdf):
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self.btn_add_section.setFixedWidth(130)
        self.btn_edit_section.setFixedWidth(110)
        self.btn_remove_section.setFixedWidth(100)
        self.btn_save_to_base.setFixedWidth(150)
        self.btn_export_pdf.setFixedWidth(130)
        row_actions.addWidget(self.btn_export_pdf, 0)
        row_actions.addWidget(QLabel("Oferta:", self), 0)
        row_actions.addWidget(self.ed_offer_title, 0)
        row_actions.addWidget(QLabel("Klient:", self), 0)
        row_actions.addWidget(self.cb_client_selector, 0)
        row_actions.addWidget(QLabel("Rabat:", self), 0)
        row_actions.addWidget(self.ed_discount_pct, 0)
        row_actions.addStretch(1)
        row_actions.addWidget(QLabel("Aktywny pasek:", self), 0)
        row_actions.addWidget(self.cb_section_picker, 0)
        root.addLayout(row_actions)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        root.addWidget(scroll, 1)

        content = QWidget(scroll)
        self.sections_layout = QVBoxLayout(content)
        self.sections_layout.setContentsMargins(0, 0, 0, 0)
        self.sections_layout.setSpacing(10)
        self.sections_layout.addStretch(1)
        scroll.setWidget(content)

        self.btn_add_section.clicked.connect(self._add_section)
        self.btn_edit_section.clicked.connect(self._edit_selected_section)
        self.btn_remove_section.clicked.connect(self._remove_selected_section)
        self.btn_save_to_base.clicked.connect(self._save_quote_to_base)
        self.btn_export_pdf.clicked.connect(self._export_current_quote_pdf)

        self._refresh_clients()
        self.ed_discount_pct.setText("0")
        self._add_section()

    @staticmethod
    def _parse_percent(value: Any) -> float:
        raw = str(value or "").strip().replace(",", ".")
        if not raw:
            return 0.0
        try:
            parsed = float(raw)
        except Exception:
            return 0.0
        return max(0.0, min(95.0, parsed))

    @staticmethod
    def _apply_discount(total: float, discount_pct: float) -> float:
        base = max(0.0, float(total or 0.0))
        pct = max(0.0, min(95.0, float(discount_pct or 0.0)))
        return base * (1.0 - (pct / 100.0))

    @staticmethod
    def _build_quote_id(entries: list[dict[str, Any]], now_dt: datetime | None = None) -> str:
        now = now_dt or datetime.now()
        base = f"Q{now.strftime('%Y%m%d_%H%M%S')}"
        used = {str(row.get("id", "") or "").strip() for row in entries if isinstance(row, dict)}
        if base not in used:
            return base
        index = 2
        while True:
            candidate = f"{base}_{index:02d}"
            if candidate not in used:
                return candidate
            index += 1

    def _load_sources(self) -> None:
        self._mo_mm, self._module_templates = self._load_module_templates()
        self._hardware_options = self._load_hardware_options()
        self._material_options_by_type = self._load_material_options_by_type()

    def _load_module_templates(self) -> tuple[float, list[dict]]:
        path = _default_data_dir() / "quick_quote_baza_modul.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return 18.0, []
        except Exception:
            return 18.0, []
        mo = 18.0
        try:
            mo = float(payload.get("mo_mm", 18.0) or 18.0)
        except Exception:
            mo = 18.0
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []
        out: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if not str(row.get("id", "") or "").strip():
                continue
            out.append(dict(row))
        return mo, out

    def _load_hardware_options(self) -> list[tuple[str, str, float]]:
        options: list[tuple[str, str, float]] = []
        try:
            for hw in self._catalog.list_hardware():
                key = str(getattr(hw, "key", "") or "").strip()
                name = str(getattr(hw, "name_pl", "") or "").strip()
                if not key:
                    continue
                label = name if name else key
                price = float(getattr(hw, "price_pln", 0.0) or 0.0)
                options.append((key, label, price))
        except Exception:
            options = []
        return options

    def _load_material_options_by_type(self) -> dict[str, list[tuple[str, str]]]:
        path = _default_data_dir() / "baza_materialu.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        per_type: dict[str, list[tuple[str, str]]] = {}
        per_type["all"] = [("", "[wybierz]")]
        for key in ("korpus", "front", "plecy", "okleina"):
            per_type[key] = [("", "[wybierz]")]

        for row in rows:
            if not isinstance(row, dict):
                continue
            material_id = str(row.get("id", "") or "").strip()
            material_type = str(row.get("typ", "") or "").strip().lower()
            material_name = str(row.get("nazwa", "") or "").strip()
            material_params = str(row.get("parametry", "") or "").strip()
            material_price = str(row.get("cena_zl", "") or "").strip()
            if not material_name:
                continue

            label_parts = []
            if material_id:
                label_parts.append(material_id)
            label_parts.append(material_name)
            if material_params:
                label_parts.append(material_params)
            if material_price:
                label_parts.append(f"{material_price} zl")
            label = " | ".join(label_parts)
            key = material_id or material_name

            per_type["all"].append((key, label))
            if material_type in per_type:
                per_type[material_type].append((key, label))

        return per_type

    def _section_by_id(self, section_id: str) -> SzybkaWycenaSection | None:
        key = str(section_id or "").strip()
        if not key:
            return None
        for section in self._sections:
            if section.section_id == key:
                return section
        return None

    def _active_section(self) -> SzybkaWycenaSection | None:
        section_id = str(self.cb_section_picker.currentData() or "").strip()
        return self._section_by_id(section_id)

    def _sync_section_picker(self) -> None:
        current_id = str(self.cb_section_picker.currentData() or "")
        self.cb_section_picker.blockSignals(True)
        self.cb_section_picker.clear()
        for section in self._sections:
            self.cb_section_picker.addItem(f"{section.section_id} | {section.section_title}", section.section_id)
        idx = self.cb_section_picker.findData(current_id)
        if idx < 0 and self.cb_section_picker.count() > 0:
            idx = self.cb_section_picker.count() - 1
        if idx >= 0:
            self.cb_section_picker.setCurrentIndex(idx)
        self.cb_section_picker.blockSignals(False)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._load_sources()
        self._refresh_clients()
        for section in self._sections:
            section.set_sources(
                self._module_templates,
                self._hardware_options,
                self._material_options_by_type,
                mo_mm=self._mo_mm,
            )

    def _add_section(self) -> None:
        self._section_counter += 1
        section_id = f"SW{self._section_counter:03d}"
        section = SzybkaWycenaSection(
            section_title=f"Sekcja {self._section_counter}",
            section_id=section_id,
            module_templates=self._module_templates,
            hardware_options=self._hardware_options,
            material_options_by_type=self._material_options_by_type,
            mo_mm=self._mo_mm,
            parent=self,
        )
        section.set_collapsed(True)
        insert_at = max(0, self.sections_layout.count() - 1)
        self.sections_layout.insertWidget(insert_at, section, 0)
        self._sections.append(section)
        self._sync_section_picker()

    def _edit_selected_section(self) -> None:
        section = self._active_section()
        if section is None:
            return
        new_title, ok = QInputDialog.getText(self, "Modyfikuj pasek", "Nowa nazwa paska:", text=section.section_title)
        if not ok:
            return
        section.set_section_title(new_title)
        self._sync_section_picker()

    def _remove_selected_section(self) -> None:
        section = self._active_section()
        if section is None:
            return
        self.sections_layout.removeWidget(section)
        section.setParent(None)
        section.deleteLater()
        self._sections = [s for s in self._sections if s is not section]
        if not self._sections:
            self._section_counter = 0
        self._sync_section_picker()

    def _refresh_clients(self) -> None:
        current = str(self.cb_client_selector.currentData() or "")
        client_names = self._client_store.list_names()
        self.cb_client_selector.blockSignals(True)
        self.cb_client_selector.clear()
        if client_names:
            self.cb_client_selector.addItem("[wybierz klienta]", "")
            for name in client_names:
                self.cb_client_selector.addItem(name, name)
        else:
            self.cb_client_selector.addItem("[brak klientow]", "")
        idx = self.cb_client_selector.findData(current)
        if idx < 0:
            idx = 0
        if self.cb_client_selector.count() > 0:
            self.cb_client_selector.setCurrentIndex(idx)
        self.cb_client_selector.blockSignals(False)

    def _collect_sections_summary(self) -> tuple[list[dict[str, str]], float]:
        sections: list[dict[str, str]] = []
        total = 0.0
        for section in self._sections:
            section._recalculate_price_total()
            price_value = section._parse_float(section.ed_total.text())
            total += price_value
            price_text = f"{price_value:.2f} zl"
            sections.append(
                {"id": section.section_id, "title": section.section_title, "price": price_text}
            )
        return sections, total

    def _load_quote_archive(self) -> list[dict[str, Any]]:
        path = quick_quote_archive_path()
        if not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text) if text.strip() else []
            if isinstance(payload, list):
                return sanitize_quick_quote_entries(payload)
        except Exception:
            pass
        return []

    def _write_quote_archive(self, entries: list[dict[str, Any]]) -> None:
        path = quick_quote_archive_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_quote_to_base(self) -> None:
        client = str(self.cb_client_selector.currentData() or "").strip()
        if not client:
            QMessageBox.warning(
                self,
                "Wybierz klienta",
                "Wybierz klienta, dla ktĂłrego chcesz zapisaÄ‡ tÄ™ wycenÄ™.",
            )
            return
        sections, total = self._collect_sections_summary()
        if not sections:
            QMessageBox.warning(
                self,
                "Brak sekcji",
                "Dodaj przynajmniej jeden pasek z szafkami, aby zapisaÄ‡ wycenÄ™.",
            )
            return
        entries = self._load_quote_archive()
        quote_id = self._build_quote_id(entries)
        title = str(self.ed_offer_title.text() or "").strip() or "Oferta"
        discount_pct = self._parse_percent(self.ed_discount_pct.text())
        final_total = self._apply_discount(total, discount_pct)
        entry = {
            "id": quote_id,
            "title": title,
            "client": client,
            "base_price": f"{total:.2f} zl",
            "price": f"{final_total:.2f} zl",
            "discount_pct": f"{discount_pct:.2f}%",
            "vat": "23%",
            "margin": "0.00%",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "sections": sections,
        }
        entries.append(entry)
        self._write_quote_archive(entries)
        QMessageBox.information(
            self,
            "Zapisano wycenÄ™",
            "Szybka wycena zostaĹ‚a dopisana do bazy szybkich wycen.",
        )

    def _export_current_quote_pdf(self) -> None:
        client = str(self.cb_client_selector.currentData() or self.cb_client_selector.currentText() or "").strip()
        if not client:
            QMessageBox.warning(self, "Wybierz klienta", "Wybierz klienta przed eksportem PDF.")
            return

        sections, total = self._collect_sections_summary()
        if not sections:
            QMessageBox.warning(self, "Brak sekcji", "Dodaj przynajmniej jedna sekcje przed eksportem.")
            return

        entries = self._load_quote_archive()
        quote_id = self._build_quote_id(entries)
        title = str(self.ed_offer_title.text() or "").strip() or "Oferta"
        discount_pct = self._parse_percent(self.ed_discount_pct.text())
        final_total = self._apply_discount(total, discount_pct)

        lines = [
            f"ID oferty: {quote_id}",
            f"Oferta: {title}",
            f"Klient: {client}",
            f"Cena bazowa: {total:.2f} zl",
            f"Rabat: {discount_pct:.2f}%",
            f"Cena po rabacie: {final_total:.2f} zl",
        ]
        for section in sections:
            lines.append(
                f"Sekcja: {section.get('id', '')} | {section.get('title', '')} | {section.get('price', '')}"
            )

        stem = f"{quote_id}_{_slugify_filename(title, fallback='Oferta')}"
        out = _next_unique_export_path(quick_quote_export_dir(), stem, ".pdf")
        _create_simple_pdf(out, lines)
        QMessageBox.information(self, "Eksport PDF", f"Zapisano: {out.name}")

    def get_project_model(self) -> ProjectModel | None:
        """Builds ProjectModel from the active quick quote section."""
        section = self._active_section()
        if section is None:
            return None

        # Collect all data from the active section
        section._recalculate_price_total()
        total_price = section._parse_float(section.ed_total.text())

        # Build entry dict for the adapter
        entry = {
            "id": section.section_id,
            "title": section.section_title,
            "client": str(self.cb_client_selector.currentData() or self.cb_client_selector.currentText() or "").strip(),
            "order_code": "",
            "vat": 23.0,
            "margin": 0.0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Build quick_totals dict for the adapter
        quick_totals = {
            "material_value": total_price,
            "transport": 0.0,
            "hours": 0.0,
            "montage": 0.0,
            "extras_total": 0.0,
            "labor_cost": 0.0,
            "base_total": total_price,
            "netto": total_price,
            "brutto": total_price,
            "rate_source": "quick_quote",
        }

        try:
            return build_quick_quote_project_model(
                entry,
                quick_totals,
                archive_path=str(quick_quote_archive_path()),
            )
        except Exception:
            return None

