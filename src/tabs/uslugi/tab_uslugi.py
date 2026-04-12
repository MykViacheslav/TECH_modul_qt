from __future__ import annotations

import csv
import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QDate, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyleOptionHeader,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.domain.client_models import ClientDef
from src.domain.service_models import ServiceDef, new_service_id
from src.domain.project_model import ProjectModel
from src.domain.alarm_models import AlarmDef, new_alarm_id
from src.domain.calendar_event import CalendarEvent
from src.app.app_settings import load_ui_theme_settings
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.data_paths import data_dir
from src.storage.service_store_json import ServiceStoreJson
from src.services.project_model_service_adapter import build_service_quote_project_model


def _to_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    raw = raw.replace("zl", "").replace("ZL", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    return txt in {"1", "true", "tak", "yes", "y", "x"}


def _txt(table: QTableWidget, row: int, col: int) -> str:
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def _set_readonly(table: QTableWidget, row: int, col: int, text: str) -> None:
    item = table.item(row, col) or QTableWidgetItem()
    item.setText(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    table.setItem(row, col, item)


def _set_money(table: QTableWidget, row: int, col: int, value: float, readonly: bool = True) -> None:
    item = table.item(row, col) or QTableWidgetItem()
    item.setText(f"{float(value):.2f}")
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if readonly:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    else:
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
    table.setItem(row, col, item)


def _next_client_id(existing_ids: set[str]) -> str:
    max_num = 0
    for raw in existing_ids:
        digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
        if digits:
            try:
                max_num = max(max_num, int(digits))
            except ValueError:
                pass
    value = max_num + 1
    while True:
        cid = f"K{value:04d}"
        if cid not in existing_ids:
            return cid
        value += 1


class _GroupedHeaderView(QHeaderView):
    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self._groups: list[tuple[int, int, str]] = []
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_groups(self, groups: list[tuple[int, int, str]]) -> None:
        self._groups = list(groups)
        self.viewport().update()

    def _group_for(self, logical_index: int) -> tuple[int, int, str] | None:
        for start, span, title in self._groups:
            if start <= logical_index < start + span:
                return start, span, title
        return None

    def sizeHint(self):  # type: ignore[override]
        hint = super().sizeHint()
        hint.setHeight(max(hint.height(), 48))
        return hint

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:  # type: ignore[override]
        if not rect.isValid():
            return
        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = logical_index
        self.style().drawControl(QStyle.ControlElement.CE_HeaderSection, opt, painter, self)
        text = str(self.model().headerData(logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole) or "")
        painter.save()
        painter.setPen(QPen(self.palette().color(self.foregroundRole())))
        grouped = self._group_for(logical_index) is not None
        if grouped:
            bottom_rect = QRect(rect.left() + 2, rect.top() + rect.height() // 2, rect.width() - 4, rect.height() // 2 - 1)
            painter.drawText(bottom_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
        else:
            full_rect = QRect(rect.left() + 2, rect.top(), rect.width() - 4, rect.height())
            painter.drawText(full_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
        painter.restore()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        if not self._groups:
            return
        painter = QPainter(self.viewport())
        split_y = self.height() // 2
        painter.setPen(QPen(QColor("#aeb8c5")))
        painter.drawLine(0, split_y, self.viewport().width(), split_y)
        painter.setPen(QPen(self.palette().color(self.foregroundRole())))
        for start, span, title in self._groups:
            x = self.sectionViewportPosition(start)
            if x < 0 and self.sectionSize(start) <= 0:
                continue
            width = 0
            for idx in range(start, start + span):
                if 0 <= idx < self.count() and not self.isSectionHidden(idx):
                    width += self.sectionSize(idx)
            if width <= 0:
                continue
            top_rect = QRect(x + 2, 1, width - 4, max(1, split_y - 2))
            painter.drawText(top_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, title)
        painter.end()


class _FormatkiDialog(QDialog):
    COL_ID = 0
    COL_NAME = 1
    COL_L = 2
    COL_B = 3
    COL_QTY = 4
    COL_M2 = 5
    COL_OKL_L = 6
    COL_OKL_P = 7
    COL_OKL_G = 8
    COL_OKL_D = 9
    COL_OKL_MB = 10
    COL_NOTES = 11
    COL_LAK_1 = 12
    COL_LAK_2 = 13
    COL_PROM_L = 14
    COL_PROM_P = 15
    COL_PROM_G = 16
    COL_PROM_D = 17
    COL_ZAK_L = 18
    COL_ZAK_P = 19
    COL_ZAK_G = 20
    COL_ZAK_D = 21

    _BOOL_COLS = {
        COL_OKL_L,
        COL_OKL_P,
        COL_OKL_G,
        COL_OKL_D,
        COL_LAK_1,
        COL_LAK_2,
        COL_PROM_L,
        COL_PROM_P,
        COL_PROM_G,
        COL_PROM_D,
        COL_ZAK_L,
        COL_ZAK_P,
        COL_ZAK_G,
        COL_ZAK_D,
    }

    def __init__(self, rows: list[dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Formatki pozycji")
        self.resize(1500, 520)
        self._is_sync = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.btn_add = QPushButton("+ Dodaj formatke", self)
        self.btn_remove = QPushButton("- Usuń formatke", self)
        top.addWidget(self.btn_add, 0)
        top.addWidget(self.btn_remove, 0)
        top.addStretch(1)
        root.addLayout(top)

        self.tbl = QTableWidget(0, 22, self)
        self.tbl.setHorizontalHeaderLabels(
            [
                "ID",
                "Nazwa",
                "L",
                "B",
                "Sztuki",
                "m.kw",
                "L",
                "P",
                "G",
                "D",
                "M.B",
                "Uwagi",
                "1 str",
                "2 str",
                "L",
                "P",
                "G",
                "D",
                "L",
                "P",
                "G",
                "D",
            ]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        header = _GroupedHeaderView(Qt.Orientation.Horizontal, self.tbl)
        header.set_groups(
            [
                (self.COL_OKL_L, 4, "Okleina"),
                (self.COL_LAK_1, 2, "Lakier"),
                (self.COL_PROM_L, 4, "Promyk"),
                (self.COL_ZAK_L, 4, "Zakladka"),
            ]
        )
        self.tbl.setHorizontalHeader(header)
        h = self.tbl.horizontalHeader()
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        h.setFixedHeight(50)
        h.setSectionResizeMode(self.COL_ID, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.COL_L, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_B, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_QTY, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_M2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OKL_MB, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_NOTES, QHeaderView.ResizeMode.Stretch)
        for col in self._BOOL_COLS:
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            self.tbl.setColumnWidth(col, 62)
        self.tbl.setColumnWidth(self.COL_NAME, 240)
        self.tbl.setColumnWidth(self.COL_NOTES, 240)
        self.tbl.setColumnWidth(self.COL_OKL_MB, 72)
        self.tbl.setColumnWidth(self.COL_M2, 72)
        root.addWidget(self.tbl, 1)

        self.lab_summary = QLabel("Suma okleina: 0.000 mb | Suma lakier: 0.000 m.kw", self)
        _theme = load_ui_theme_settings()
        _is_tech = str(_theme.motif or "").strip().lower() == "tech" and str(_theme.mode or "").strip().lower() == "night"
        self.lab_summary.setStyleSheet(f"font-weight:600; color:{'#dbe9ff' if _is_tech else '#23344f'};")
        root.addWidget(self.lab_summary, 0, Qt.AlignmentFlag.AlignRight)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_cancel = QPushButton("Anuluj", self)
        self.btn_ok = QPushButton("OK", self)
        bottom.addWidget(self.btn_cancel, 0)
        bottom.addWidget(self.btn_ok, 0)
        root.addLayout(bottom)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        self.tbl.itemChanged.connect(self._on_item_changed)

        loaded = rows or []
        if loaded:
            for row_data in loaded:
                if isinstance(row_data, dict):
                    self._add_row(row_data)
        else:
            self._add_row()
        self._update_summary()

    def _next_id(self) -> str:
        max_num = 0
        for row in range(self.tbl.rowCount()):
            raw = _txt(self.tbl, row, self.COL_ID)
            digits = "".join(ch for ch in raw if ch.isdigit())
            if not digits:
                continue
            try:
                max_num = max(max_num, int(digits))
            except ValueError:
                continue
        return f"F{max_num + 1:03d}"

    def _mk_bool_item(self, value: bool) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
        item.setText("")
        return item

    def _set_bool_cell(self, row: int, col: int, value: bool) -> None:
        self.tbl.setItem(row, col, self._mk_bool_item(bool(value)))

    def _get_bool_cell(self, row: int, col: int) -> bool:
        item = self.tbl.item(row, col)
        return bool(item is not None and item.checkState() == Qt.CheckState.Checked)

    def _set_calc_cell(self, row: int, col: int, value: float) -> None:
        item = self.tbl.item(row, col) or QTableWidgetItem()
        item.setText(f"{float(value):.3f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.tbl.setItem(row, col, item)

    def _set_m2_cell(self, row: int, value: float) -> None:
        self._set_calc_cell(row, self.COL_M2, value)

    def _set_okl_mb_cell(self, row: int, value: float) -> None:
        self._set_calc_cell(row, self.COL_OKL_MB, value)

    def _recalc_row(self, row: int, fallback_m2: float | None = None, fallback_okl: float | None = None, fallback_lak: float | None = None) -> None:
        length_l = _to_float(_txt(self.tbl, row, self.COL_L))
        length_b = _to_float(_txt(self.tbl, row, self.COL_B))
        qty = _to_float(_txt(self.tbl, row, self.COL_QTY))
        if qty <= 0:
            qty = 1.0
        calc = (length_l * length_b * qty) / 1_000_000.0 if length_l > 0 and length_b > 0 else 0.0
        if calc <= 0 and fallback_m2 is not None and fallback_m2 > 0:
            calc = fallback_m2
        l_mb = length_l / 1000.0 if length_l > 0 else 0.0
        b_mb = length_b / 1000.0 if length_b > 0 else 0.0
        okleina_mb = qty * (
            (l_mb if self._get_bool_cell(row, self.COL_OKL_L) else 0.0)
            + (l_mb if self._get_bool_cell(row, self.COL_OKL_P) else 0.0)
            + (b_mb if self._get_bool_cell(row, self.COL_OKL_G) else 0.0)
            + (b_mb if self._get_bool_cell(row, self.COL_OKL_D) else 0.0)
        )
        if okleina_mb <= 0 and fallback_okl is not None and fallback_okl > 0:
            okleina_mb = fallback_okl
        lakier_1 = self._get_bool_cell(row, self.COL_LAK_1)
        lakier_2 = self._get_bool_cell(row, self.COL_LAK_2)
        if lakier_2:
            lakier_m2 = calc * 2.0
        elif lakier_1:
            lakier_m2 = calc
        else:
            lakier_m2 = 0.0
        if lakier_m2 <= 0 and fallback_lak is not None and fallback_lak > 0:
            lakier_m2 = fallback_lak
        self._is_sync = True
        try:
            self._set_m2_cell(row, calc)
            self._set_okl_mb_cell(row, okleina_mb)
        finally:
            self._is_sync = False
        self._update_summary()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_sync:
            return
        recalc_cols = {
            self.COL_L,
            self.COL_B,
            self.COL_QTY,
            self.COL_OKL_L,
            self.COL_OKL_P,
            self.COL_OKL_G,
            self.COL_OKL_D,
            self.COL_LAK_1,
            self.COL_LAK_2,
        }
        if item.column() not in recalc_cols:
            return
        row = item.row()
        col = item.column()
        if col in (self.COL_LAK_1, self.COL_LAK_2):
            other_col = self.COL_LAK_2 if col == self.COL_LAK_1 else self.COL_LAK_1
            if item.checkState() == Qt.CheckState.Checked and self._get_bool_cell(row, other_col):
                self._is_sync = True
                try:
                    other_item = self.tbl.item(row, other_col)
                    if other_item is not None:
                        other_item.setCheckState(Qt.CheckState.Unchecked)
                finally:
                    self._is_sync = False
        self._recalc_row(row)

    def _update_summary(self) -> None:
        total_okl = 0.0
        total_lak = 0.0
        for row in range(self.tbl.rowCount()):
            total_okl += _to_float(_txt(self.tbl, row, self.COL_OKL_MB))
            m2 = _to_float(_txt(self.tbl, row, self.COL_M2))
            lakier_1 = self._get_bool_cell(row, self.COL_LAK_1)
            lakier_2 = self._get_bool_cell(row, self.COL_LAK_2)
            if lakier_2:
                total_lak += 2.0 * m2
            elif lakier_1:
                total_lak += m2
        self.lab_summary.setText(f"Suma okleina: {total_okl:.3f} mb | Suma lakier: {total_lak:.3f} m.kw")

    def _add_row(self, payload: dict[str, Any] | None = None) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        data = payload or {}
        self._is_sync = True
        try:
            _set_readonly(self.tbl, row, self.COL_ID, str(data.get("id", "") or self._next_id()))
            self.tbl.setItem(row, self.COL_NAME, QTableWidgetItem(str(data.get("name", "") or "")))
            self.tbl.setItem(row, self.COL_L, QTableWidgetItem(str(data.get("length_l", "") or "")))
            self.tbl.setItem(row, self.COL_B, QTableWidgetItem(str(data.get("length_b", "") or "")))
            qty = _to_float(data.get("qty", 1.0))
            if qty <= 0:
                qty = 1.0
            qty_item = QTableWidgetItem(f"{qty:.2f}".rstrip("0").rstrip("."))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tbl.setItem(row, self.COL_QTY, qty_item)
            self.tbl.setItem(row, self.COL_NOTES, QTableWidgetItem(str(data.get("notes", "") or "")))

            self._set_bool_cell(row, self.COL_OKL_L, _to_bool(data.get("okleina_l")))
            self._set_bool_cell(row, self.COL_OKL_P, _to_bool(data.get("okleina_p")))
            self._set_bool_cell(row, self.COL_OKL_G, _to_bool(data.get("okleina_g")))
            self._set_bool_cell(row, self.COL_OKL_D, _to_bool(data.get("okleina_d")))
            self._set_bool_cell(row, self.COL_LAK_1, _to_bool(data.get("lakier_1s", data.get("lakier_1str"))))
            self._set_bool_cell(row, self.COL_LAK_2, _to_bool(data.get("lakier_2s", data.get("lakier_2str"))))
            self._set_bool_cell(row, self.COL_PROM_L, _to_bool(data.get("promyk_l")))
            self._set_bool_cell(row, self.COL_PROM_P, _to_bool(data.get("promyk_p")))
            self._set_bool_cell(row, self.COL_PROM_G, _to_bool(data.get("promyk_g")))
            self._set_bool_cell(row, self.COL_PROM_D, _to_bool(data.get("promyk_d")))
            self._set_bool_cell(row, self.COL_ZAK_L, _to_bool(data.get("zakladka_l")))
            self._set_bool_cell(row, self.COL_ZAK_P, _to_bool(data.get("zakladka_p")))
            self._set_bool_cell(row, self.COL_ZAK_G, _to_bool(data.get("zakladka_g")))
            self._set_bool_cell(row, self.COL_ZAK_D, _to_bool(data.get("zakladka_d")))
        finally:
            self._is_sync = False
        self._recalc_row(
            row,
            fallback_m2=_to_float(data.get("m2", data.get("m_kw", 0.0))),
            fallback_okl=_to_float(data.get("okleina_mb", data.get("okleina_m_b", 0.0))),
            fallback_lak=_to_float(data.get("lakier_m2", data.get("lakier_m_kw", 0.0))),
        )

    def _remove_row(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not rows:
            if self.tbl.currentRow() >= 0:
                self.tbl.removeRow(self.tbl.currentRow())
            self._update_summary()
            return
        for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
            self.tbl.removeRow(int(idx.row()))
        self._update_summary()

    def rows(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in range(self.tbl.rowCount()):
            payload = {
                "id": _txt(self.tbl, row, self.COL_ID),
                "name": _txt(self.tbl, row, self.COL_NAME),
                "length_l": _txt(self.tbl, row, self.COL_L),
                "length_b": _txt(self.tbl, row, self.COL_B),
                "qty": _to_float(_txt(self.tbl, row, self.COL_QTY)) or 1.0,
                "m2": _to_float(_txt(self.tbl, row, self.COL_M2)),
                "okleina_l": self._get_bool_cell(row, self.COL_OKL_L),
                "okleina_p": self._get_bool_cell(row, self.COL_OKL_P),
                "okleina_g": self._get_bool_cell(row, self.COL_OKL_G),
                "okleina_d": self._get_bool_cell(row, self.COL_OKL_D),
                "okleina_mb": _to_float(_txt(self.tbl, row, self.COL_OKL_MB)),
                "notes": _txt(self.tbl, row, self.COL_NOTES),
                "lakier_1s": self._get_bool_cell(row, self.COL_LAK_1),
                "lakier_2s": self._get_bool_cell(row, self.COL_LAK_2),
                "promyk_l": self._get_bool_cell(row, self.COL_PROM_L),
                "promyk_p": self._get_bool_cell(row, self.COL_PROM_P),
                "promyk_g": self._get_bool_cell(row, self.COL_PROM_G),
                "promyk_d": self._get_bool_cell(row, self.COL_PROM_D),
                "zakladka_l": self._get_bool_cell(row, self.COL_ZAK_L),
                "zakladka_p": self._get_bool_cell(row, self.COL_ZAK_P),
                "zakladka_g": self._get_bool_cell(row, self.COL_ZAK_G),
                "zakladka_d": self._get_bool_cell(row, self.COL_ZAK_D),
            }
            if payload["lakier_2s"]:
                payload["lakier_m2"] = 2.0 * float(payload["m2"])
            elif payload["lakier_1s"]:
                payload["lakier_m2"] = float(payload["m2"])
            else:
                payload["lakier_m2"] = 0.0
            has_markers = any(
                [
                    payload["name"],
                    payload["length_l"],
                    payload["length_b"],
                    payload["notes"],
                    payload["qty"] != 1.0,
                    payload["m2"] > 0.0,
                    payload["okleina_l"],
                    payload["okleina_p"],
                    payload["okleina_g"],
                    payload["okleina_d"],
                    payload["okleina_mb"] > 0.0,
                    payload["lakier_1s"],
                    payload["lakier_2s"],
                    payload["lakier_m2"] > 0.0,
                    payload["promyk_l"],
                    payload["promyk_p"],
                    payload["promyk_g"],
                    payload["promyk_d"],
                    payload["zakladka_l"],
                    payload["zakladka_p"],
                    payload["zakladka_g"],
                    payload["zakladka_d"],
                ]
            )
            if has_markers:
                out.append(payload)
        return out


class _UslugaQuoteStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (data_dir() / "usluga_quotes.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_quotes(self) -> list[dict[str, Any]]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [dict(row) for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
        except Exception:
            return []

    def get_quote(self, quote_id: str) -> dict[str, Any] | None:
        for row in self.list_quotes():
            if str(row.get("quote_id", "")) == str(quote_id or ""):
                return row
        return None

    def upsert_quote(self, payload: dict[str, Any]) -> None:
        quote_id = str(payload.get("quote_id", "") or "").strip()
        if not quote_id:
            return
        rows = self.list_quotes()
        for idx, row in enumerate(rows):
            if str(row.get("quote_id", "")) == quote_id:
                rows[idx] = dict(payload)
                break
        else:
            rows.append(dict(payload))
        self._path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


class _CennikPanel(QWidget):
    sig_cennik_changed = pyqtSignal()

    _DEFAULT: tuple[tuple[str, str, str, float], ...] = (
        ("Fronty lakierowane BIALY MAT", "lakierowanie", "m2", 284.55),
        ("Fronty lakierowane BIALY POLYSK", "lakierowanie", "m2", 333.33),
        ("Fronty surowe FREZOWANE", "fronty_surowe", "m2", 162.60),
        ("Oklejanie PVC krawedzi 10-18 mm", "oklejanie", "mb", 6.00),
        ("Oklejanie PVC krawedzi powyzej 18 mm", "oklejanie", "mb", 12.00),
        ("Ciecie plyt 3-20 mm", "wycinanie", "mb", 5.00),
        ("Frezowanie frontu", "cnc", "m2", 165.00),
        ("Roboczogodzina stolarz", "robocizna", "h", 95.00),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = ServiceStoreJson()
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.btn_add = QPushButton("+ Dodaj wpis", self)
        self.btn_remove = QPushButton("- Usuń wpis", self)
        self.btn_save = QPushButton("Zapisz cennik", self)
        self.btn_default = QPushButton("Wczytaj domyślny", self)
        for btn in (self.btn_add, self.btn_remove, self.btn_save, self.btn_default):
            top.addWidget(btn, 0)
        top.addStretch(1)
        root.addLayout(top)

        self.tbl = QTableWidget(0, 6, self)
        self.tbl.setHorizontalHeaderLabels(["ID", "Nazwa", "Rodzaj", "j.m", "Cena [zl]", "Uwagi"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        self.lab = QLabel("", self)
        self.lab.setStyleSheet("color:#2f6f3e;")
        root.addWidget(self.lab, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_add.clicked.connect(self._add)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_save.clicked.connect(self._save)
        self.btn_default.clicked.connect(self._default)
        self._reload()

    def _set_row(self, row: int, svc: ServiceDef) -> None:
        _set_readonly(self.tbl, row, 0, str(svc.service_id or new_service_id()))
        self.tbl.setItem(row, 1, QTableWidgetItem(str(svc.name or "")))
        self.tbl.setItem(row, 2, QTableWidgetItem(str(svc.category or "")))
        self.tbl.setItem(row, 3, QTableWidgetItem(str(svc.description or "")))
        price = QTableWidgetItem(f"{float(svc.price or 0.0):.2f}")
        price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl.setItem(row, 4, price)
        self.tbl.setItem(row, 5, QTableWidgetItem(str(svc.note or "")))

    def _reload(self) -> None:
        self.tbl.setRowCount(0)
        for svc in self._store.list_services():
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self._set_row(row, svc)

    def _add(self) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self._set_row(row, ServiceDef(service_id=new_service_id(), name="Nowa usługa", category="robocizna", description="szt", price=0.0))

    def _remove(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not rows:
            if self.tbl.currentRow() >= 0:
                self.tbl.removeRow(self.tbl.currentRow())
            return
        for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
            self.tbl.removeRow(int(idx.row()))

    def _save(self) -> None:
        rows: list[ServiceDef] = []
        for row in range(self.tbl.rowCount()):
            name = _txt(self.tbl, row, 1)
            if not name:
                continue
            rows.append(
                ServiceDef(
                    service_id=_txt(self.tbl, row, 0) or new_service_id(),
                    name=name,
                    category=_txt(self.tbl, row, 2),
                    description=_txt(self.tbl, row, 3),
                    price=_to_float(_txt(self.tbl, row, 4)),
                    note=_txt(self.tbl, row, 5),
                )
            )
        old_ids = {svc.service_id for svc in self._store.list_services() if svc.service_id}
        new_ids = {svc.service_id for svc in rows if svc.service_id}
        for svc in rows:
            self._store.save_service(svc)
        for stale in sorted(old_ids - new_ids):
            self._store.delete_service(stale)
        self.lab.setText("Zapisano cennik.")
        self.sig_cennik_changed.emit()

    def _default(self) -> None:
        have = {
            (str(svc.name or "").strip().lower(), str(svc.category or "").strip().lower())
            for svc in self._store.list_services()
        }
        added = 0
        for name, category, unit, price in self._DEFAULT:
            key = (name.lower(), category.lower())
            if key in have:
                continue
            self._store.save_service(
                ServiceDef(
                    service_id=new_service_id(),
                    name=name,
                    category=category,
                    description=unit,
                    price=float(price),
                )
            )
            have.add(key)
            added += 1
        self._reload()
        self.lab.setText(f"Dodano domyslne pozycje: {added}")
        self.sig_cennik_changed.emit()


class _KlienciPanel(QWidget):
    sig_clients_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = ClientStoreJson()
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.btn_add = QPushButton("+ Dodaj klienta", self)
        self.btn_remove = QPushButton("- Usuń klienta", self)
        self.btn_save = QPushButton("Zapisz klientów", self)
        self.btn_reload = QPushButton("Odśwież", self)
        for btn in (self.btn_add, self.btn_remove, self.btn_save, self.btn_reload):
            top.addWidget(btn, 0)
        top.addStretch(1)
        root.addLayout(top)

        self.tbl = QTableWidget(0, 6, self)
        self.tbl.setHorizontalHeaderLabels(["ID", "Nazwa", "Telefon", "Email", "Miasto", "Uwagi"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        self.lab = QLabel("", self)
        self.lab.setStyleSheet("color:#2f6f3e;")
        root.addWidget(self.lab, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_add.clicked.connect(self._add)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_save.clicked.connect(self._save)
        self.btn_reload.clicked.connect(self._reload)
        self._reload()

    def _set_row(self, row: int, client: ClientDef) -> None:
        _set_readonly(self.tbl, row, 0, str(client.client_id or ""))
        self.tbl.setItem(row, 1, QTableWidgetItem(str(client.name or "")))
        self.tbl.setItem(row, 2, QTableWidgetItem(str(client.phone or "")))
        self.tbl.setItem(row, 3, QTableWidgetItem(str(client.email or "")))
        self.tbl.setItem(row, 4, QTableWidgetItem(str(client.city or "")))
        self.tbl.setItem(row, 5, QTableWidgetItem(str(client.notes or "")))

    def _reload(self) -> None:
        self.tbl.setRowCount(0)
        for client in self._store.list_clients():
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self._set_row(row, client)

    def _add(self) -> None:
        existing = {_txt(self.tbl, r, 0) for r in range(self.tbl.rowCount())}
        for client in self._store.list_clients():
            existing.add(str(client.client_id or ""))
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self._set_row(
            row,
            ClientDef(client_id=_next_client_id(existing), name="Nowy klient"),
        )

    def _remove(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not rows:
            if self.tbl.currentRow() >= 0:
                self.tbl.removeRow(self.tbl.currentRow())
            return
        for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
            self.tbl.removeRow(int(idx.row()))

    def _save(self) -> None:
        old_names = set(self._store.list_names())
        new_names: set[str] = set()
        existing_ids = {_txt(self.tbl, r, 0) for r in range(self.tbl.rowCount())}
        for client in self._store.list_clients():
            existing_ids.add(str(client.client_id or ""))
        for row in range(self.tbl.rowCount()):
            name = _txt(self.tbl, row, 1)
            if not name or name in new_names:
                continue
            client_id = _txt(self.tbl, row, 0)
            if not client_id:
                client_id = _next_client_id(existing_ids)
                existing_ids.add(client_id)
                _set_readonly(self.tbl, row, 0, client_id)
            self._store.overwrite(
                ClientDef(
                    client_id=client_id,
                    name=name,
                    phone=_txt(self.tbl, row, 2),
                    email=_txt(self.tbl, row, 3),
                    city=_txt(self.tbl, row, 4),
                    notes=_txt(self.tbl, row, 5),
                )
            )
            new_names.add(name)
        for stale_name in sorted(old_names - new_names):
            self._store.delete(stale_name)
        self.lab.setText("Zapisano bazę klientów.")
        self.sig_clients_changed.emit()


class _UslugaPanel(QWidget):
    sig_saved = pyqtSignal()
    VAT_PERCENT = 23.0
    COL_NO = 0
    COL_ID = 1
    COL_MATERIAL = 2
    COL_WORK = 3
    COL_RAL = 4
    COL_NCS = 5
    COL_MODEL = 6
    COL_QTY = 7
    COL_MATERIAL_PRICE = 8
    COL_WORK_PRICE = 9
    COL_VAT = 10
    COL_SUM_NETTO = 11
    COL_SUM_BRUTTO = 12
    COL_FORMATKI = 13

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service_store = ServiceStoreJson()
        self._client_store = ClientStoreJson()
        self._quote_store = _UslugaQuoteStore()
        self._material_options: list[dict[str, Any]] = []
        self._work_options: list[dict[str, Any]] = []
        self._formatki_by_row_id: dict[str, list[dict[str, Any]]] = {}
        self._active_quote_id = ""
        self._is_loading = False
        theme = load_ui_theme_settings()
        self._is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        self._card_style = (
            "QFrame { border:1px solid #2a4368; border-radius:8px; background:#111b30; }"
            if self._is_tech
            else "QFrame { border:1px solid #d9e0ea; border-radius:8px; background:#ffffff; }"
        )
        self._status_color = "#8fc4ff" if self._is_tech else "#2f6f3e"
        self._muted_color = "#9bb0cd" if self._is_tech else "#555555"
        self._summary_color = "#dbe9ff" if self._is_tech else "#23344f"
        self._combo_style = (
            "QComboBox { margin:0px; padding:0px 2px; border:1px solid #2f4f80; border-radius:2px; background:#10203a; color:#e8efff; }"
            "QComboBox::drop-down { width:16px; }"
            if self._is_tech
            else "QComboBox { margin:0px; padding:0px 2px; border:1px solid #cfd8e3; border-radius:2px; }"
            "QComboBox::drop-down { width:16px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top_wrap = QVBoxLayout()
        top_wrap.setSpacing(10)

        top_row_1 = QHBoxLayout()
        top_row_1.setSpacing(10)
        top_row_1.addWidget(QLabel("Klient:", self), 0)
        self.cb_client = QComboBox(self)
        self.cb_client.setEditable(False)
        self.cb_client.setMinimumWidth(220)
        top_row_1.addWidget(self.cb_client, 0)

        top_row_1.addWidget(QLabel("Materiał:", self), 0)
        self.cb_material = QComboBox(self)
        self.cb_material.setMinimumWidth(280)
        top_row_1.addWidget(self.cb_material, 0)

        top_row_1.addWidget(QLabel("Usługa:", self), 0)
        self.cb_service = QComboBox(self)
        self.cb_service.setMinimumWidth(260)
        top_row_1.addWidget(self.cb_service, 0)

        top_row_1.addWidget(QLabel("Start:", self), 0)
        self.de_start = QDateEdit(self)
        self.de_start.setCalendarPopup(True)
        self.de_start.setDisplayFormat("yyyy-MM-dd")
        self.de_start.setDate(QDate.currentDate())
        top_row_1.addWidget(self.de_start, 0)

        top_row_1.addWidget(QLabel("Koniec:", self), 0)
        self.de_end = QDateEdit(self)
        self.de_end.setCalendarPopup(True)
        self.de_end.setDisplayFormat("yyyy-MM-dd")
        self.de_end.setDate(QDate.currentDate())
        top_row_1.addWidget(self.de_end, 0)

        top_row_1.addWidget(QLabel("Data wpisu:", self), 0)
        self.ed_entry_date = QLineEdit(self)
        self.ed_entry_date.setReadOnly(True)
        self.ed_entry_date.setMinimumWidth(110)
        self.ed_entry_date.setText(datetime.now().strftime("%Y-%m-%d"))
        top_row_1.addWidget(self.ed_entry_date, 0)
        top_row_1.addStretch(1)
        top_wrap.addLayout(top_row_1)

        top_row_2 = QHBoxLayout()
        top_row_2.setSpacing(10)
        self.btn_add = QPushButton("+ Dodaj pozycje", self)
        self.btn_remove = QPushButton("- Usuń pozycje", self)
        self.btn_formatki = QPushButton("Dodaj formatki", self)
        self.btn_material_list = QPushButton("Spisz materiał", self)
        self.btn_invoice = QPushButton("Faktura", self)
        self.btn_save = QPushButton("Zapisz do bazy", self)
        for btn in (
            self.btn_add,
            self.btn_remove,
            self.btn_formatki,
            self.btn_material_list,
            self.btn_invoice,
            self.btn_save,
        ):
            top_row_2.addWidget(btn, 0)
        top_row_2.addStretch(1)

        self.lab_total = QLabel("Suma netto: 0.00 zl | Suma brutto: 0.00 zl", self)
        self.lab_total.setStyleSheet(f"font-size:16px; font-weight:700; color:{self._summary_color};")
        top_row_2.addWidget(self.lab_total, 0)
        top_wrap.addLayout(top_row_2)
        root.addLayout(top_wrap)

        self.tbl = QTableWidget(0, 14, self)
        self.tbl.setHorizontalHeaderLabels(
            [
                "#",
                "ID",
                "Materiał",
                "Nazwa usługi",
                "RAL",
                "NCS",
                "Model frontu",
                "Ilość",
                "Cena materiału netto",
                "Cena robocizny [zl]",
                "VAT %",
                "Suma netto",
                "Suma brutto",
                "Formatki",
            ]
        )
        self.tbl.setWordWrap(False)
        self.tbl.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(40)
        self.tbl.verticalHeader().setMinimumSectionSize(36)
        self.tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(self.COL_NO, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_ID, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_MATERIAL, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(self.COL_WORK, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(self.COL_RAL, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(self.COL_NCS, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(self.COL_MODEL, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(self.COL_QTY, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_MATERIAL_PRICE, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_WORK_PRICE, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_VAT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_SUM_NETTO, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_SUM_BRUTTO, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_FORMATKI, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setColumnWidth(self.COL_ID, 80)
        self.tbl.setColumnWidth(self.COL_MATERIAL, 430)
        self.tbl.setColumnWidth(self.COL_WORK, 430)
        self.tbl.setColumnWidth(self.COL_QTY, 70)
        self.tbl.setColumnWidth(self.COL_MATERIAL_PRICE, 135)
        self.tbl.setColumnWidth(self.COL_WORK_PRICE, 120)
        self.tbl.setColumnWidth(self.COL_VAT, 70)
        self.tbl.setColumnWidth(self.COL_SUM_NETTO, 115)
        self.tbl.setColumnWidth(self.COL_SUM_BRUTTO, 115)
        self.tbl.setColumnWidth(self.COL_RAL, 100)
        self.tbl.setColumnWidth(self.COL_NCS, 100)
        self.tbl.setColumnWidth(self.COL_MODEL, 130)
        self.tbl.setColumnWidth(self.COL_FORMATKI, 85)
        root.addWidget(self.tbl, 1)

        self.btn_toggle_formatki_list = QPushButton("▼ Lista formatek pozycji", self)
        self.btn_toggle_formatki_list.setCheckable(True)
        self.btn_toggle_formatki_list.setChecked(True)
        root.addWidget(self.btn_toggle_formatki_list, 0, Qt.AlignmentFlag.AlignLeft)

        self.frame_formatki_preview = QFrame(self)
        self.frame_formatki_preview.setStyleSheet(self._card_style)
        preview_root = QVBoxLayout(self.frame_formatki_preview)
        preview_root.setContentsMargins(12, 12, 12, 12)
        preview_root.setSpacing(8)

        preview_top = QHBoxLayout()
        self.lab_formatki_preview = QLabel("Brak wybranej pozycji.", self.frame_formatki_preview)
        self.lab_formatki_preview.setStyleSheet(f"font-weight:600; color:{self._summary_color};")
        preview_top.addWidget(self.lab_formatki_preview, 0)
        preview_top.addStretch(1)
        self.btn_print_formatki = QPushButton("Drukuj formatki", self.frame_formatki_preview)
        self.btn_export_giblab = QPushButton("Eksport GibLab CSV", self.frame_formatki_preview)
        preview_top.addWidget(self.btn_print_formatki, 0)
        preview_top.addWidget(self.btn_export_giblab, 0)
        preview_root.addLayout(preview_top)

        self.tbl_formatki_preview = QTableWidget(0, 10, self.frame_formatki_preview)
        self.tbl_formatki_preview.setHorizontalHeaderLabels(
            [
                "Pozycja",
                "ID",
                "Nazwa",
                "L",
                "B",
                "Sztuki",
                "m.kw",
                "Okleina mb",
                "Lakier m.kw",
                "Uwagi",
            ]
        )
        self.tbl_formatki_preview.verticalHeader().setVisible(False)
        self.tbl_formatki_preview.setAlternatingRowColors(True)
        self.tbl_formatki_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hp = self.tbl_formatki_preview.horizontalHeader()
        hp.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hp.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        hp.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        preview_root.addWidget(self.tbl_formatki_preview, 1)
        root.addWidget(self.frame_formatki_preview, 0)

        bottom = QFrame(self)
        bottom.setStyleSheet(self._card_style)
        row = QHBoxLayout(bottom)
        row.setContentsMargins(12, 10, 12, 10)
        row.addWidget(QLabel("Tabela: materiał z bazy, usługa z cennika, RAL/NCS/model frontu.", self), 0)
        row.addStretch(1)
        self.lab = QLabel("", self)
        self.lab.setStyleSheet(f"color:{self._status_color};")
        row.addWidget(self.lab, 0)
        root.addWidget(bottom, 0)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_formatki.clicked.connect(self._open_formatki_dialog)
        self.btn_material_list.clicked.connect(self._spisz_material)
        self.btn_invoice.clicked.connect(self._faktura)
        self.btn_toggle_formatki_list.toggled.connect(self._toggle_formatki_preview)
        self.btn_print_formatki.clicked.connect(self._print_formatki)
        self.btn_export_giblab.clicked.connect(self._export_formatki_giblab)
        self.btn_save.clicked.connect(self._save_quote)
        self.cb_material.currentIndexChanged.connect(self._on_material_picker_changed)
        self.cb_service.currentIndexChanged.connect(self._on_service_picker_changed)
        self.tbl.itemChanged.connect(self._on_item_changed)
        self.tbl.itemSelectionChanged.connect(self._refresh_formatki_preview)

        self.reload_sources()

    def reload_sources(self) -> None:
        self._load_clients()
        self._load_materials()
        self._reload_material_picker(str(self.cb_material.currentData() or ""))
        self._load_work()
        self._reload_service_picker(str(self.cb_service.currentData() or ""))
        if self.tbl.rowCount() == 0:
            self._new_quote()
        self._refresh_formatki_preview()

    def _toggle_formatki_preview(self, checked: bool) -> None:
        self.frame_formatki_preview.setVisible(bool(checked))
        self.btn_toggle_formatki_list.setText("▼ Lista formatek pozycji" if checked else "▶ Lista formatek pozycji")

    def _selected_row_index(self) -> int:
        row = self.tbl.currentRow()
        if row < 0 and self.tbl.rowCount() > 0:
            row = 0
        return row

    def _selected_row_id(self) -> str:
        row = self._selected_row_index()
        if row < 0:
            return ""
        return _txt(self.tbl, row, self.COL_ID)

    def _selected_row_label(self) -> str:
        row = self._selected_row_index()
        if row < 0:
            return ""
        material = _txt(self.tbl, row, self.COL_MATERIAL)
        service = _txt(self.tbl, row, self.COL_WORK)
        if not material and isinstance(self.tbl.cellWidget(row, self.COL_MATERIAL), QComboBox):
            material = str(self.tbl.cellWidget(row, self.COL_MATERIAL).currentText() or "").strip()  # type: ignore[union-attr]
        if not service and isinstance(self.tbl.cellWidget(row, self.COL_WORK), QComboBox):
            service = str(self.tbl.cellWidget(row, self.COL_WORK).currentText() or "").strip()  # type: ignore[union-attr]
        return " | ".join([part for part in [material, service] if part and part != "[brak]"])

    def _formatki_rows_for_selected(self) -> list[dict[str, Any]]:
        row_id = self._selected_row_id()
        if not row_id:
            return []
        out: list[dict[str, Any]] = []
        for row in self._formatki_by_row_id.get(row_id, []):
            if isinstance(row, dict):
                out.append(dict(row))
        return out

    def _calc_lakier_m2(self, fmt: dict[str, Any]) -> float:
        m2 = _to_float(fmt.get("m2", 0.0))
        if m2 <= 0:
            l = _to_float(fmt.get("length_l", 0.0))
            b = _to_float(fmt.get("length_b", 0.0))
            q = _to_float(fmt.get("qty", 1.0))
            if q <= 0:
                q = 1.0
            if l > 0 and b > 0:
                m2 = (l * b * q) / 1_000_000.0
        if _to_bool(fmt.get("lakier_2s", False)):
            return 2.0 * m2
        if _to_bool(fmt.get("lakier_1s", False)):
            return m2
        return _to_float(fmt.get("lakier_m2", 0.0))

    def _refresh_formatki_preview(self) -> None:
        row_id = self._selected_row_id()
        rows = self._formatki_rows_for_selected()
        self.tbl_formatki_preview.setRowCount(0)
        if not row_id:
            self.lab_formatki_preview.setText("Brak wybranej pozycji.")
            return
        label = self._selected_row_label()
        total_qty = 0.0
        for fmt in rows:
            r = self.tbl_formatki_preview.rowCount()
            self.tbl_formatki_preview.insertRow(r)
            _set_readonly(self.tbl_formatki_preview, r, 0, row_id)
            _set_readonly(self.tbl_formatki_preview, r, 1, str(fmt.get("id", "") or ""))
            _set_readonly(self.tbl_formatki_preview, r, 2, str(fmt.get("name", "") or ""))
            _set_readonly(self.tbl_formatki_preview, r, 3, str(fmt.get("length_l", "") or ""))
            _set_readonly(self.tbl_formatki_preview, r, 4, str(fmt.get("length_b", "") or ""))
            qty = _to_float(fmt.get("qty", 1.0))
            if qty <= 0:
                qty = 1.0
            _set_readonly(self.tbl_formatki_preview, r, 5, f"{qty:.2f}".rstrip("0").rstrip("."))
            _set_readonly(self.tbl_formatki_preview, r, 6, f"{_to_float(fmt.get('m2', 0.0)):.3f}")
            _set_readonly(self.tbl_formatki_preview, r, 7, f"{_to_float(fmt.get('okleina_mb', 0.0)):.3f}")
            _set_readonly(self.tbl_formatki_preview, r, 8, f"{self._calc_lakier_m2(fmt):.3f}")
            _set_readonly(self.tbl_formatki_preview, r, 9, str(fmt.get("notes", "") or ""))
            total_qty += qty
        self.lab_formatki_preview.setText(
            f"Pozycja {row_id}: {label or '[bez nazwy]'} | Formatki: {len(rows)} | Sztuki razem: {total_qty:.2f}".rstrip("0").rstrip(".")
        )

    def _load_clients(self) -> None:
        current = str(self.cb_client.currentData() or "")
        self.cb_client.blockSignals(True)
        try:
            self.cb_client.clear()
            self.cb_client.addItem("[wybierz klienta]", "")
            for client in self._client_store.list_clients():
                name = str(client.name or "").strip()
                if not name:
                    continue
                self.cb_client.addItem(name, name)
            idx = self.cb_client.findData(current) if current else 0
            self.cb_client.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_client.blockSignals(False)

    def _load_materials(self) -> None:
        options: list[dict[str, Any]] = [{"id": "", "name": "[brak]", "price": 0.0, "label": "[brak]"}]
        path = data_dir() / "baza_materialu.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            rows = raw.get("rows", []) if isinstance(raw, dict) else []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("nazwa", "") or "").strip()
                if not name:
                    continue
                mat_id = str(row.get("id", "") or "").strip()
                typ = str(row.get("typ", "") or "").strip()
                price = _to_float(row.get("cena_zl", 0.0))
                label = " | ".join([part for part in [mat_id, name, typ] if part]) or name
                options.append({"id": mat_id, "name": name, "price": price, "label": f"{label} | {price:.2f} zl"})
        except Exception:
            pass
        self._material_options = options

    def _load_work(self) -> None:
        options: list[dict[str, Any]] = [{"id": "", "name": "[brak]", "price": 0.0, "label": "[brak]"}]
        for svc in self._service_store.list_services():
            name = str(svc.name or "").strip()
            if not name:
                continue
            category = str(svc.category or "").strip()
            unit = str(svc.description or "").strip()
            price = float(svc.price or 0.0)
            label = f"{name} | {price:.2f} zl"
            if category:
                label = f"{label} | {category}"
            if unit:
                label = f"{label} ({unit})"
            options.append(
                {
                    "id": str(svc.service_id or ""),
                    "name": name,
                    "price": price,
                    "category": category,
                    "unit": unit,
                    "label": label,
                }
            )
        self._work_options = options

    def _reload_service_picker(self, selected: str = "") -> None:
        self.cb_service.blockSignals(True)
        try:
            self.cb_service.clear()
            self.cb_service.addItem("[wybierz usługę z cennika]", "")
            for entry in self._work_options:
                service_id = str(entry.get("id", "") or "")
                if not service_id:
                    continue
                self.cb_service.addItem(str(entry.get("label", "")), service_id)
            idx = self.cb_service.findData(selected) if selected else 0
            self.cb_service.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_service.blockSignals(False)

    def _reload_material_picker(self, selected: str = "") -> None:
        self.cb_material.blockSignals(True)
        try:
            self.cb_material.clear()
            self.cb_material.addItem("[wybierz material z bazy]", "")
            for entry in self._material_options:
                mat_id = str(entry.get("id", "") or "")
                if not mat_id:
                    continue
                self.cb_material.addItem(str(entry.get("label", "")), mat_id)
            idx = self.cb_material.findData(selected) if selected else 0
            self.cb_material.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_material.blockSignals(False)

    def _new_quote(self) -> None:
        self._is_loading = True
        self.tbl.setRowCount(0)
        self._active_quote_id = ""
        self._formatki_by_row_id.clear()
        if self.cb_client.count() > 0:
            self.cb_client.setCurrentIndex(0)
        if self.cb_material.count() > 0:
            self.cb_material.setCurrentIndex(0)
        if self.cb_service.count() > 0:
            self.cb_service.setCurrentIndex(0)
        self.de_start.setDate(QDate.currentDate())
        self.de_end.setDate(QDate.currentDate())
        self.ed_entry_date.setText(datetime.now().strftime("%Y-%m-%d"))
        self._is_loading = False
        self._add_row()
        self._update_total()
        self._refresh_formatki_preview()
        self.lab.setText("Nowa usługa.")

    def _combo_row(self, combo: QComboBox) -> int:
        for row in range(self.tbl.rowCount()):
            if self.tbl.cellWidget(row, self.COL_MATERIAL) is combo or self.tbl.cellWidget(row, self.COL_WORK) is combo:
                return row
        return -1

    def _next_row_id(self) -> str:
        max_num = 0
        for row in range(self.tbl.rowCount()):
            raw = _txt(self.tbl, row, self.COL_ID)
            digits = "".join(ch for ch in raw if ch.isdigit())
            if not digits:
                continue
            try:
                max_num = max(max_num, int(digits))
            except ValueError:
                continue
        return f"U{max_num + 1:04d}"

    def _fill_combo(self, combo: QComboBox, options: list[dict[str, Any]], wanted_id: str, wanted_name: str) -> None:
        combo.clear()
        for entry in options:
            combo.addItem(str(entry.get("label", "")), dict(entry))
        if wanted_id:
            for idx in range(combo.count()):
                payload = combo.itemData(idx)
                if isinstance(payload, dict) and str(payload.get("id", "")) == wanted_id:
                    combo.setCurrentIndex(idx)
                    return
        if wanted_name:
            wanted = wanted_name.strip().lower()
            for idx in range(combo.count()):
                payload = combo.itemData(idx)
                if isinstance(payload, dict) and str(payload.get("name", "")).strip().lower() == wanted:
                    combo.setCurrentIndex(idx)
                    return
            if combo.isEditable():
                combo.setEditText(wanted_name)
                return
        combo.setCurrentIndex(0 if combo.count() > 0 else -1)

    def _add_row(self, row_data: dict[str, Any] | None = None) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self.tbl.setRowHeight(row, 40)
        payload = row_data or {}
        _set_readonly(self.tbl, row, self.COL_NO, str(row + 1))
        row_id = str(payload.get("row_id", "") or self._next_row_id())
        _set_readonly(self.tbl, row, self.COL_ID, row_id)
        material = QComboBox(self.tbl)
        work = QComboBox(self.tbl)
        for cb in (material, work):
            cb.setEditable(True)
            cb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(1)
            cb.setMinimumWidth(8)
            cb.setMinimumHeight(20)
            cb.setMaximumHeight(20)
            cb.setStyleSheet(self._combo_style)
        material.currentIndexChanged.connect(self._on_combo_changed)
        work.currentIndexChanged.connect(self._on_combo_changed)
        self.tbl.setCellWidget(row, self.COL_MATERIAL, material)
        self.tbl.setCellWidget(row, self.COL_WORK, work)

        self._fill_combo(
            material,
            self._material_options,
            str(payload.get("material_id", "") or ""),
            str(payload.get("material_name", "") or ""),
        )
        default_work_id = str(payload.get("work_id", "") or "")
        default_work_name = str(payload.get("work_name", "") or "")
        if not default_work_id:
            default_work_id = str(self.cb_service.currentData() or "")
        self._fill_combo(work, self._work_options, default_work_id, default_work_name)
        self.tbl.setItem(row, self.COL_RAL, QTableWidgetItem(str(payload.get("ral", "") or "")))
        self.tbl.setItem(row, self.COL_NCS, QTableWidgetItem(str(payload.get("ncs", "") or "")))
        self.tbl.setItem(row, self.COL_MODEL, QTableWidgetItem(str(payload.get("model", "") or "")))
        qty = _to_float(payload.get("qty", 1))
        if qty <= 0:
            qty = 1.0
        qty_item = QTableWidgetItem(f"{qty:.2f}".rstrip("0").rstrip("."))
        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl.setItem(row, self.COL_QTY, qty_item)
        _set_money(self.tbl, row, self.COL_MATERIAL_PRICE, 0.0, readonly=False)
        _set_money(self.tbl, row, self.COL_WORK_PRICE, 0.0, readonly=False)
        vat_val = _to_float(payload.get("vat", self.VAT_PERCENT))
        if vat_val < 0:
            vat_val = 0.0
        vat_item = QTableWidgetItem(f"{vat_val:.2f}".rstrip("0").rstrip("."))
        vat_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl.setItem(row, self.COL_VAT, vat_item)
        _set_money(self.tbl, row, self.COL_SUM_NETTO, 0.0)
        _set_money(self.tbl, row, self.COL_SUM_BRUTTO, 0.0)
        existing_formatki = payload.get("formatki", [])
        if isinstance(existing_formatki, list):
            self._formatki_by_row_id[row_id] = [dict(x) for x in existing_formatki if isinstance(x, dict)]
        else:
            self._formatki_by_row_id.setdefault(row_id, [])
        self._set_formatki_cell(row)
        self._sync_row(row)
        self._update_total()
        self._refresh_formatki_preview()

    def _remove_row(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        remove_ids: list[str] = []
        if not rows:
            if self.tbl.currentRow() >= 0:
                remove_ids.append(_txt(self.tbl, self.tbl.currentRow(), self.COL_ID))
                self.tbl.removeRow(self.tbl.currentRow())
        else:
            for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
                remove_ids.append(_txt(self.tbl, int(idx.row()), self.COL_ID))
                self.tbl.removeRow(int(idx.row()))
        for row_id in remove_ids:
            self._formatki_by_row_id.pop(str(row_id or ""), None)
        for row in range(self.tbl.rowCount()):
            _set_readonly(self.tbl, row, self.COL_NO, str(row + 1))
            self._set_formatki_cell(row)
        self._update_total()
        self._refresh_formatki_preview()

    def _set_formatki_cell(self, row: int) -> None:
        row_id = _txt(self.tbl, row, self.COL_ID)
        cnt = len(self._formatki_by_row_id.get(row_id, []))
        _set_readonly(self.tbl, row, self.COL_FORMATKI, str(cnt))

    def _open_formatki_dialog(self) -> None:
        row = self.tbl.currentRow()
        if row < 0 and self.tbl.rowCount() > 0:
            row = 0
            self.tbl.setCurrentCell(row, self.COL_ID)
        if row < 0:
            self.lab.setText("Najpierw dodaj pozycje.")
            return
        row_id = _txt(self.tbl, row, self.COL_ID)
        if not row_id:
            self.lab.setText("Brak ID pozycji.")
            return
        dialog = _FormatkiDialog(self._formatki_by_row_id.get(row_id, []), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._formatki_by_row_id[row_id] = dialog.rows()
        self._set_formatki_cell(row)
        self._refresh_formatki_preview()
        self.lab.setText(f"Zapisano formatki dla pozycji: {row_id}")

    def _sync_row(self, row: int) -> None:
        mat_widget = self.tbl.cellWidget(row, self.COL_MATERIAL)
        work_widget = self.tbl.cellWidget(row, self.COL_WORK)
        mat_data = mat_widget.currentData() if isinstance(mat_widget, QComboBox) and mat_widget.currentIndex() >= 0 else {}
        work_data = work_widget.currentData() if isinstance(work_widget, QComboBox) and work_widget.currentIndex() >= 0 else {}
        if not isinstance(mat_data, dict):
            mat_data = {}
        if not isinstance(work_data, dict):
            work_data = {}
        mat_text = str(mat_widget.currentText() if isinstance(mat_widget, QComboBox) else "").strip()
        work_text = str(work_widget.currentText() if isinstance(work_widget, QComboBox) else "").strip()
        mat_name = str(mat_data.get("name", "") or "").strip()
        work_name = str(work_data.get("name", "") or "").strip()
        mat_id = str(mat_data.get("id", "") or "").strip()
        work_id = str(work_data.get("id", "") or "").strip()
        has_mat_option = bool(mat_id) or (
            bool(mat_name)
            and mat_name != "[brak]"
            and mat_text
            and mat_text.lower() == mat_name.lower()
        )
        has_work_option = bool(work_id) or (
            bool(work_name)
            and work_name != "[brak]"
            and work_text
            and work_text.lower() == work_name.lower()
        )
        mat_price = _to_float(mat_data.get("price", 0.0)) if has_mat_option else _to_float(_txt(self.tbl, row, self.COL_MATERIAL_PRICE))
        work_price = _to_float(work_data.get("price", 0.0)) if has_work_option else _to_float(_txt(self.tbl, row, self.COL_WORK_PRICE))
        vat = _to_float(_txt(self.tbl, row, self.COL_VAT))
        if vat < 0:
            vat = 0.0
        if _txt(self.tbl, row, self.COL_VAT) == "":
            vat = self.VAT_PERCENT
        qty = _to_float(_txt(self.tbl, row, self.COL_QTY))
        if qty <= 0:
            qty = 1.0
        prev_loading = self._is_loading
        self._is_loading = True
        try:
            if qty <= 0:
                item = self.tbl.item(row, self.COL_QTY)
                if item is not None:
                    item.setText("1")
                qty = 1.0
            _set_money(self.tbl, row, self.COL_MATERIAL_PRICE, mat_price, readonly=False)
            _set_money(self.tbl, row, self.COL_WORK_PRICE, work_price, readonly=False)
            vat_item = self.tbl.item(row, self.COL_VAT)
            if vat_item is not None and vat_item.text().strip() == "":
                vat_item.setText(f"{self.VAT_PERCENT:.0f}")
            sum_netto = qty * (mat_price + work_price)
            sum_brutto = sum_netto * (1.0 + vat / 100.0)
            _set_money(self.tbl, row, self.COL_SUM_NETTO, sum_netto)
            _set_money(self.tbl, row, self.COL_SUM_BRUTTO, sum_brutto)
        finally:
            self._is_loading = prev_loading

    def _on_service_picker_changed(self, _index: int) -> None:
        service_id = str(self.cb_service.currentData() or "")
        if not service_id:
            return
        row = self.tbl.currentRow()
        if row < 0:
            return
        combo = self.tbl.cellWidget(row, self.COL_WORK)
        if not isinstance(combo, QComboBox):
            return
        for idx in range(combo.count()):
            payload = combo.itemData(idx)
            if isinstance(payload, dict) and str(payload.get("id", "")) == service_id:
                self._is_loading = True
                combo.setCurrentIndex(idx)
                self._is_loading = False
                self._sync_row(row)
                self._update_total()
                return

    def _on_material_picker_changed(self, _index: int) -> None:
        material_id = str(self.cb_material.currentData() or "")
        if not material_id:
            return
        row = self.tbl.currentRow()
        if row < 0 and self.tbl.rowCount() > 0:
            row = 0
            self.tbl.setCurrentCell(0, self.COL_MATERIAL)
        if row < 0:
            return
        combo = self.tbl.cellWidget(row, self.COL_MATERIAL)
        if not isinstance(combo, QComboBox):
            return
        for idx in range(combo.count()):
            payload = combo.itemData(idx)
            if isinstance(payload, dict) and str(payload.get("id", "")) == material_id:
                self._is_loading = True
                combo.setCurrentIndex(idx)
                self._is_loading = False
                self._sync_row(row)
                self._update_total()
                return

    def _spisz_material(self) -> None:
        rows = self._collect_rows()
        if not rows:
            self.lab.setText("Brak materialow do spisania.")
            return
        grouped: dict[str, dict[str, float]] = {}
        for row in rows:
            name = str(row.get("material_name", "") or "").strip() or "[brak materialu]"
            qty = _to_float(row.get("qty", 0.0))
            price = _to_float(row.get("material_price", 0.0))
            rec = grouped.setdefault(name, {"qty": 0.0, "net": 0.0})
            rec["qty"] += qty
            rec["net"] += qty * price
        parts: list[str] = []
        for name, rec in grouped.items():
            parts.append(f"{name}: ilosc {rec['qty']:.2f}, netto {rec['net']:.2f} zl")
        self.lab.setText("Spis materiału: " + " | ".join(parts))

    def _faktura(self) -> None:
        client = str(self.cb_client.currentData() or self.cb_client.currentText() or "").strip() or "[brak klienta]"
        self.lab.setText(f"Faktura przygotowana: {client} | {self.lab_total.text()}")

    def _print_formatki(self) -> None:
        row_id = self._selected_row_id()
        rows = self._formatki_rows_for_selected()
        if not row_id or not rows:
            self.lab.setText("Brak formatek do wydruku.")
            return
        header = self._selected_row_label()
        html = [
            "<h2>Lista formatek</h2>",
            f"<p><b>Pozycja:</b> {escape(row_id)}<br><b>Opis:</b> {escape(header)}</p>",
            "<table border='1' cellspacing='0' cellpadding='4'>",
            "<tr><th>ID</th><th>Nazwa</th><th>L</th><th>B</th><th>Szt</th><th>m.kw</th><th>Okleina mb</th><th>Lakier m.kw</th><th>Uwagi</th></tr>",
        ]
        for row in rows:
            html.append(
                "<tr>"
                f"<td>{escape(str(row.get('id', '') or ''))}</td>"
                f"<td>{escape(str(row.get('name', '') or ''))}</td>"
                f"<td>{escape(str(row.get('length_l', '') or ''))}</td>"
                f"<td>{escape(str(row.get('length_b', '') or ''))}</td>"
                f"<td>{_to_float(row.get('qty', 1.0)):.2f}</td>"
                f"<td>{_to_float(row.get('m2', 0.0)):.3f}</td>"
                f"<td>{_to_float(row.get('okleina_mb', 0.0)):.3f}</td>"
                f"<td>{self._calc_lakier_m2(row):.3f}</td>"
                f"<td>{escape(str(row.get('notes', '') or ''))}</td>"
                "</tr>"
            )
        html.append("</table>")
        doc = QTextDocument()
        doc.setHtml("".join(html))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            doc.print(printer)
            self.lab.setText(f"Wydrukowano formatki pozycji: {row_id}")

    def _export_formatki_giblab(self) -> None:
        row_id = self._selected_row_id()
        rows = self._formatki_rows_for_selected()
        if not row_id or not rows:
            self.lab.setText("Brak formatek do eksportu.")
            return
        default_name = f"giblab_{row_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Eksport do GibLab (CSV)", str(data_dir() / default_name), "CSV (*.csv)")
        if not path:
            return
        material_name = ""
        row_idx = self._selected_row_index()
        if row_idx >= 0 and isinstance(self.tbl.cellWidget(row_idx, self.COL_MATERIAL), QComboBox):
            material_name = str(self.tbl.cellWidget(row_idx, self.COL_MATERIAL).currentText() or "").strip()  # type: ignore[union-attr]
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(
                [
                    "Pozycja",
                    "Materiał",
                    "ID",
                    "Nazwa",
                    "L_mm",
                    "B_mm",
                    "Sztuki",
                    "Okleina_L",
                    "Okleina_P",
                    "Okleina_G",
                    "Okleina_D",
                    "Uwagi",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row_id,
                        material_name,
                        str(row.get("id", "") or ""),
                        str(row.get("name", "") or ""),
                        str(row.get("length_l", "") or ""),
                        str(row.get("length_b", "") or ""),
                        f"{_to_float(row.get('qty', 1.0)):.2f}".rstrip("0").rstrip("."),
                        "1" if _to_bool(row.get("okleina_l")) else "0",
                        "1" if _to_bool(row.get("okleina_p")) else "0",
                        "1" if _to_bool(row.get("okleina_g")) else "0",
                        "1" if _to_bool(row.get("okleina_d")) else "0",
                        str(row.get("notes", "") or ""),
                    ]
                )
        self.lab.setText(f"Eksport GibLab zapisany: {path}")

    def _on_combo_changed(self, _index: int) -> None:
        if self._is_loading:
            return
        combo = self.sender()
        if not isinstance(combo, QComboBox):
            return
        row = self._combo_row(combo)
        if row < 0:
            return
        self._sync_row(row)
        self._update_total()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_loading or item.column() not in (self.COL_QTY, self.COL_MATERIAL_PRICE, self.COL_WORK_PRICE, self.COL_VAT):
            return
        self._sync_row(item.row())
        self._update_total()

    def _collect_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in range(self.tbl.rowCount()):
            row_id = _txt(self.tbl, row, self.COL_ID)
            formatki_rows = [dict(x) for x in self._formatki_by_row_id.get(row_id, []) if isinstance(x, dict)]
            mat_widget = self.tbl.cellWidget(row, self.COL_MATERIAL)
            work_widget = self.tbl.cellWidget(row, self.COL_WORK)
            mat_data = mat_widget.currentData() if isinstance(mat_widget, QComboBox) and mat_widget.currentIndex() >= 0 else {}
            work_data = work_widget.currentData() if isinstance(work_widget, QComboBox) and work_widget.currentIndex() >= 0 else {}
            if not isinstance(mat_data, dict):
                mat_data = {}
            if not isinstance(work_data, dict):
                work_data = {}
            material_name = str(mat_data.get("name", "") or "").strip()
            work_name = str(work_data.get("name", "") or "").strip()
            material_id = str(mat_data.get("id", "") or "").strip()
            work_id = str(work_data.get("id", "") or "").strip()
            material_text = str(mat_widget.currentText() if isinstance(mat_widget, QComboBox) else "").strip()
            work_text = str(work_widget.currentText() if isinstance(work_widget, QComboBox) else "").strip()
            has_material_option = bool(material_id) or (
                bool(material_name)
                and material_name != "[brak]"
                and material_text
                and material_text.lower() == material_name.lower()
            )
            has_work_option = bool(work_id) or (
                bool(work_name)
                and work_name != "[brak]"
                and work_text
                and work_text.lower() == work_name.lower()
            )
            if not has_material_option:
                material_id = ""
                material_name = material_text
            if not has_work_option:
                work_id = ""
                work_name = work_text
            if not material_name and not work_name and not formatki_rows:
                continue
            rows.append(
                {
                    "material_id": material_id,
                    "material_name": material_name,
                    "work_id": work_id,
                    "work_name": work_name,
                    "ral": _txt(self.tbl, row, self.COL_RAL),
                    "ncs": _txt(self.tbl, row, self.COL_NCS),
                    "model": _txt(self.tbl, row, self.COL_MODEL),
                    "row_id": row_id,
                    "qty": _to_float(_txt(self.tbl, row, self.COL_QTY)) or 1.0,
                    "material_price": _to_float(_txt(self.tbl, row, self.COL_MATERIAL_PRICE)),
                    "work_price": _to_float(_txt(self.tbl, row, self.COL_WORK_PRICE)),
                    "vat": _to_float(_txt(self.tbl, row, self.COL_VAT)) if _txt(self.tbl, row, self.COL_VAT) else self.VAT_PERCENT,
                    "row_sum_netto": _to_float(_txt(self.tbl, row, self.COL_SUM_NETTO)),
                    "row_sum_brutto": _to_float(_txt(self.tbl, row, self.COL_SUM_BRUTTO)),
                    "formatki": formatki_rows,
                }
            )
        return rows

    def _save_quote(self) -> None:
        rows = self._collect_rows()
        if not rows:
            self.lab.setText("Brak pozycji do zapisu.")
            return
        quote_id = str(self._active_quote_id or "").strip() or datetime.now().strftime("U%Y%m%d_%H%M%S")
        client = str(self.cb_client.currentData() or self.cb_client.currentText() or "").strip()
        service_id = str(self.cb_service.currentData() or "")
        service_name = str(self.cb_service.currentText() or "")
        date_start = self.de_start.date().toString("yyyy-MM-dd")
        date_end = self.de_end.date().toString("yyyy-MM-dd")
        entry_date = str(self.ed_entry_date.text() or "").strip() or datetime.now().strftime("%Y-%m-%d")
        net_total = sum(float(row.get("row_sum_netto", 0.0) or 0.0) for row in rows)
        brutto_total = sum(float(row.get("row_sum_brutto", 0.0) or 0.0) for row in rows)
        payload = {
            "quote_id": quote_id,
            "client": client,
            "service_id": service_id,
            "service_name": service_name,
            "entry_date": entry_date,
            "date_start": date_start,
            "date_end": date_end,
            "rows": rows,
            "net_total": net_total,
            "brutto_total": brutto_total,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._quote_store.upsert_quote(payload)
        self._active_quote_id = quote_id
        self._sync_calendar(payload)
        self._sync_alarm(payload)
        self._update_total()
        self.lab.setText("Zapisano do bazy + kalendarz + alarm.")
        self.sig_saved.emit()

    def _load_quote_by_id(self, quote_id: str) -> None:
        quote_id = str(quote_id or "").strip()
        if not quote_id:
            return
        payload = self._quote_store.get_quote(quote_id)
        if not isinstance(payload, dict):
            return
        self._is_loading = True
        self.tbl.setRowCount(0)
        self._formatki_by_row_id.clear()
        client = str(payload.get("client", "") or "").strip()
        if client:
            idx = self.cb_client.findData(client)
            if idx >= 0:
                self.cb_client.setCurrentIndex(idx)
        date_start = str(payload.get("date_start", "") or "")
        date_end = str(payload.get("date_end", "") or "")
        entry_date = str(payload.get("entry_date", "") or "")
        if not entry_date:
            entry_date = str(payload.get("updated_at", "") or "")[:10]
        if entry_date:
            self.ed_entry_date.setText(entry_date)
        q_start = QDate.fromString(date_start, "yyyy-MM-dd")
        q_end = QDate.fromString(date_end, "yyyy-MM-dd")
        if q_start.isValid():
            self.de_start.setDate(q_start)
        if q_end.isValid():
            self.de_end.setDate(q_end)
        service_id = str(payload.get("service_id", "") or "")
        if service_id:
            idx_service = self.cb_service.findData(service_id)
            if idx_service >= 0:
                self.cb_service.setCurrentIndex(idx_service)
        rows = payload.get("rows", [])
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                self._add_row(row)
        self._active_quote_id = quote_id
        self._is_loading = False
        for row in range(self.tbl.rowCount()):
            _set_readonly(self.tbl, row, self.COL_NO, str(row + 1))
            self._set_formatki_cell(row)
            self._sync_row(row)
        self._update_total()
        self._refresh_formatki_preview()

    def _sync_calendar(self, payload: dict[str, Any]) -> None:
        quote_id = str(payload.get("quote_id", "") or "")
        if not quote_id:
            return
        start = str(payload.get("date_start", "") or "")
        end = str(payload.get("date_end", "") or "")
        if not start:
            return
        client = str(payload.get("client", "") or "")
        service = str(payload.get("service_name", "") or "")
        store = CalendarEventStoreJson()
        for event in store.list_events():
            if str(event.order_code or "") == quote_id and "USLUGA_TAB" in str(event.notes or ""):
                store.delete(event.id)
        event = CalendarEvent.new(
            event_type="zlecenie",
            station="Biuro",
            title=f"Usługa: {service} | {client}",
            date=start,
            date_end=end,
            order_code=quote_id,
            notes="USLUGA_TAB",
        )
        store.save(event)

    def _sync_alarm(self, payload: dict[str, Any]) -> None:
        quote_id = str(payload.get("quote_id", "") or "")
        if not quote_id:
            return
        due = str(payload.get("date_end", "") or payload.get("date_start", "") or "")
        if not due:
            return
        client = str(payload.get("client", "") or "")
        service = str(payload.get("service_name", "") or "")
        store = AlarmStoreJson()
        for alarm in store.list_alarms():
            if str(alarm.related_order or "") == quote_id and str((alarm.extra or {}).get("source", "")) == "usluga_tab":
                store.delete_alarm(alarm.alarm_id)
        store.save_alarm(
            AlarmDef(
                alarm_id=new_alarm_id(),
                category="terminy",
                severity="info",
                title=f"Termin usługi: {quote_id}",
                description=f"{service} | {client}",
                related_order=quote_id,
                related_client=client,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                due_date=due,
                extra={"source": "usluga_tab"},
            )
        )

    def _update_total(self) -> None:
        netto = 0.0
        brutto = 0.0
        for row in range(self.tbl.rowCount()):
            netto += _to_float(_txt(self.tbl, row, self.COL_SUM_NETTO))
            brutto += _to_float(_txt(self.tbl, row, self.COL_SUM_BRUTTO))
        self.lab_total.setText(f"Suma netto: {netto:.2f} zl | Suma brutto: {brutto:.2f} zl")


class _BazaUslugPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = _UslugaQuoteStore()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.btn_reload = QPushButton("Odśwież", self)
        top.addWidget(self.btn_reload, 0)
        top.addStretch(1)
        root.addLayout(top)

        self.tbl = QTableWidget(0, 7, self)
        self.tbl.setHorizontalHeaderLabels(["#", "ID", "Data", "Klient", "Suma netto", "Suma brutto", "Data oddane"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.tbl, 1)

        self.btn_reload.clicked.connect(self.reload_data)
        self.reload_data()

    def reload_data(self) -> None:
        rows = self._store.list_quotes()
        rows.sort(key=lambda r: str(r.get("updated_at", "") or ""), reverse=True)
        self.tbl.setRowCount(0)
        for idx, row in enumerate(rows, start=1):
            table_row = self.tbl.rowCount()
            self.tbl.insertRow(table_row)
            entry_date = str(row.get("entry_date", "") or "")
            if not entry_date:
                entry_date = str(row.get("updated_at", "") or "")[:10]
            _set_readonly(self.tbl, table_row, 0, str(idx))
            _set_readonly(self.tbl, table_row, 1, str(row.get("quote_id", "") or ""))
            _set_readonly(self.tbl, table_row, 2, entry_date)
            _set_readonly(self.tbl, table_row, 3, str(row.get("client", "") or ""))
            _set_money(self.tbl, table_row, 4, _to_float(row.get("net_total", row.get("total", 0.0))))
            _set_money(self.tbl, table_row, 5, _to_float(row.get("brutto_total", 0.0)))
            _set_readonly(self.tbl, table_row, 6, str(row.get("date_end", "") or ""))


class TabUslugi(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = load_ui_theme_settings()
        is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        title_color = "#e8efff" if is_tech else "#111827"
        subtitle_color = "#9bb0cd" if is_tech else "#555555"
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Usługi", self)
        title.setStyleSheet(f"font-size:22px; font-weight:800; color:{title_color};")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Cennik, klienci, nowa usługa i baza usług.", self)
        subtitle.setStyleSheet(f"color:{subtitle_color};")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.tabs = QTabWidget(self)
        self.tab_cenik = _CennikPanel(self)
        self.tab_klijenty = _KlienciPanel(self)
        self.tab_nowa_usluga = _UslugaPanel(self)
        self.tab_usluga = self.tab_nowa_usluga
        self.tab_baza_uslug = _BazaUslugPanel(self)
        self.tabs.addTab(self.tab_cenik, "Cennik")
        self.tabs.addTab(self.tab_klijenty, "Klienci")
        self.tabs.addTab(self.tab_nowa_usluga, "Nowa usługa")
        self.tabs.addTab(self.tab_baza_uslug, "Baza usług")
        root.addWidget(self.tabs, 1)

        self.tab_cenik.sig_cennik_changed.connect(self.tab_nowa_usluga.reload_sources)
        self.tab_klijenty.sig_clients_changed.connect(self.tab_nowa_usluga.reload_sources)
        self.tab_nowa_usluga.sig_saved.connect(self.tab_baza_uslug.reload_data)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx: int) -> None:
        if idx == self.tabs.indexOf(self.tab_nowa_usluga):
            self.tab_nowa_usluga.reload_sources()
        if idx == self.tabs.indexOf(self.tab_baza_uslug):
            self.tab_baza_uslug.reload_data()

    def get_project_model(self) -> ProjectModel | None:
        quotes = self.tab_nowa_usluga._quote_store.list_quotes()
        quotes.sort(key=lambda r: str(r.get("updated_at", "") or ""), reverse=True)
        if not quotes:
            return None
        payload = quotes[0]
        if not isinstance(payload, dict):
            return None
        return build_service_quote_project_model(
            payload,
            source_path=str(data_dir() / "usluga_quotes.json"),
            pricing_policy="services",
            policy_multiplier=1.0,
        )
