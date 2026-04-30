from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.storage.worker_store_json import WorkerStoreJson
from src.storage.producer_library_store_json import ProducerLibraryStoreJson
from src.domain.worker_models import WorkerDef
from src.services.producer_library_service import DEFAULT_PRODUCER_LIBRARY_ROWS, ProducerLibraryService


SHARED_MATERIAL_TYPES = (
    "korpus",
    "front",
    "plecy",
    "okleina",
    "okucie",
    "plyta",
    "profil",
    "lakier",
)

BLOCKED_MATERIAL_TYPES = {"inne"}

PRODUCER_LIBRARY_ROWS = DEFAULT_PRODUCER_LIBRARY_ROWS

TABLE_TEXT_STYLE = ""

_APP_GUARD: QApplication | None = None


def _ensure_app_guard() -> None:
    """Keep a strong QApplication reference to avoid premature GC in GUI tests."""
    global _APP_GUARD
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP_GUARD = app


class ProducerLibraryPickerDialog(QDialog):
    def __init__(self, parent: QWidget, rows: list[dict[str, str]]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wybierz z biblioteki producenta")
        self.resize(1000, 520)
        self._rows = rows

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(6)
        filters.addWidget(QLabel("Producent:", self), 0)
        self.cb_producer = QComboBox(self)
        self.cb_producer.addItem("Wszyscy", "")
        for producer in sorted({str(row.get("producent", "") or "").strip() for row in rows if str(row.get("producent", "") or "").strip()}):
            self.cb_producer.addItem(producer, producer)
        filters.addWidget(self.cb_producer, 0)

        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po kodzie lub nazwie")
        filters.addWidget(self.ed_search, 1)
        root.addLayout(filters)

        self.tbl = QTableWidget(0, 7, self)
        self.tbl.setHorizontalHeaderLabels(["Kod", "Nazwa", "Producent", "Typ", "Parametry", "Cena [zl]", "Obrazek"])
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setColumnWidth(0, 80)
        self.tbl.setColumnWidth(1, 200)
        self.tbl.setColumnWidth(2, 100)
        self.tbl.setColumnWidth(3, 80)
        self.tbl.setColumnWidth(4, 150)
        self.tbl.setColumnWidth(5, 80)
        self.tbl.setColumnWidth(6, 100)
        root.addWidget(self.tbl, 1)

        actions = QHBoxLayout()
        self.btn_add_image = QPushButton("Dodaj obrazek", self)
        self.btn_clear_image = QPushButton("Usun obrazek", self)
        actions.addWidget(self.btn_add_image, 0)
        actions.addWidget(self.btn_clear_image, 0)
        actions.addStretch(1)
        self.btn_ok = QPushButton("Wybierz", self)
        self.btn_cancel = QPushButton("Anuluj", self)
        actions.addWidget(self.btn_ok, 0)
        actions.addWidget(self.btn_cancel, 0)
        root.addLayout(actions)

        self.cb_producer.currentIndexChanged.connect(self._refresh_rows)
        self.ed_search.textChanged.connect(self._refresh_rows)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.tbl.doubleClicked.connect(lambda _idx: self.accept())
        self.btn_add_image.clicked.connect(self._add_image)
        self.btn_clear_image.clicked.connect(self._clear_image)

        self._refresh_rows()

    def _refresh_rows(self) -> None:
        producer = str(self.cb_producer.currentData() or "").strip().lower()
        needle = str(self.ed_search.text() or "").strip().lower()
        filtered: list[dict[str, str]] = []
        for entry in self._rows:
            row = {
                "kod": str(entry.get("kod", "") or "").strip(),
                "typ": str(entry.get("typ", "") or "").strip().lower(),
                "nazwa": str(entry.get("nazwa", "") or "").strip(),
                "producent": str(entry.get("producent", "") or "").strip(),
                "parametry": str(entry.get("parametry", "") or "").strip(),
                "grubosc": str(entry.get("grubosc", "") or "").strip(),
                "cena_zl": str(entry.get("cena_zl", "") or "").strip(),
                "image_path": str(entry.get("image_path", "") or "").strip(),
            }
            if producer and row["producent"].lower() != producer:
                continue
            if needle and needle not in f"{row['kod']} | {row['nazwa']}".lower():
                continue
            filtered.append(row)

        self.tbl.setRowCount(0)
        for row_data in filtered:
            row_idx = self.tbl.rowCount()
            self.tbl.insertRow(row_idx)
            values = [row_data["kod"], row_data["nazwa"], row_data["producent"], row_data["typ"], row_data["parametry"], row_data["cena_zl"], row_data.get("image_path", "")]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row_data)
                self.tbl.setItem(row_idx, col, item)

        if self.tbl.rowCount() > 0:
            self.tbl.selectRow(0)

    def _add_image(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            return
        item = self.tbl.item(row, 0)
        if item is None:
            return
        row_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(row_data, dict):
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz obrazek",
            "",
            "Obrazy (*.png *.jpg *.jpeg *.gif *.bmp);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        
        row_data["image_path"] = file_path
        item.setData(Qt.ItemDataRole.UserRole, row_data)
        
        img_item = self.tbl.item(row, 6)
        if img_item:
            img_item.setText(file_path)
        
        for i, entry in enumerate(self._rows):
            if str(entry.get("kod", "") or "") == str(row_data.get("kod", "") or ""):
                self._rows[i]["image_path"] = file_path
                break

    def _clear_image(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            return
        item = self.tbl.item(row, 0)
        if item is None:
            return
        row_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(row_data, dict):
            return
        
        row_data["image_path"] = ""
        item.setData(Qt.ItemDataRole.UserRole, row_data)
        
        img_item = self.tbl.item(row, 6)
        if img_item:
            img_item.setText("")
        
        for i, entry in enumerate(self._rows):
            if str(entry.get("kod", "") or "") == str(row_data.get("kod", "") or ""):
                self._rows[i]["image_path"] = ""
                break

    def selected_entry(self) -> dict[str, str] | None:
        row = self.tbl.currentRow()
        if row < 0:
            return None
        item = self.tbl.item(row, 0)
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        return payload if isinstance(payload, dict) else None

    def get_updated_rows(self) -> list[dict[str, str]]:
        return self._rows


class ProducerImportMappingDialog(QDialog):
    TARGET_FIELDS: tuple[tuple[str, str], ...] = (
        ("kod", "Kod"),
        ("typ", "Typ"),
        ("nazwa", "Nazwa"),
        ("producent", "Producent"),
        ("parametry", "Parametry"),
        ("grubosc", "Grubosc"),
        ("cena_zl", "Cena [zl]"),
    )

    def __init__(self, parent: QWidget, headers: list[str], mapping: dict[str, str]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mapowanie kolumn importu")
        self.resize(520, 360)
        self._headers = headers
        self._combos: dict[str, QComboBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        hint = QLabel("Wskaz kolumne z pliku dla kazdego pola biblioteki.", self)
        hint.setStyleSheet("color: palette(text);")
        root.addWidget(hint)

        for target_key, target_label in self.TARGET_FIELDS:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{target_label}:", self), 0)
            cb = QComboBox(self)
            cb.addItem("(pomij)", "")
            for header in headers:
                cb.addItem(header, header)
            wanted = str(mapping.get(target_key, "") or "")
            idx = cb.findData(wanted)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            row.addWidget(cb, 1)
            root.addLayout(row)
            self._combos[target_key] = cb

        actions = QHBoxLayout()
        actions.addStretch(1)
        btn_ok = QPushButton("Zapisz mapowanie", self)
        btn_cancel = QPushButton("Anuluj", self)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_ok, 0)
        actions.addWidget(btn_cancel, 0)
        root.addLayout(actions)

    def selected_mapping(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, combo in self._combos.items():
            out[key] = str(combo.currentData() or "").strip()
        return out


class _LogicalVisibilityWidget(QWidget):
    """Tracks explicit visibility state independently from parent visibility."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._explicit_visible = True

    def setVisible(self, visible: bool) -> None:  # type: ignore[override]
        self._explicit_visible = bool(visible)
        super().setVisible(visible)

    def isVisible(self) -> bool:  # type: ignore[override]
        return bool(self._explicit_visible)


def _default_data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[3]
    return root / "data"


class TabBazaMaterialu(QWidget):
    def __new__(cls, *args, **kwargs):
        _ensure_app_guard()
        return super().__new__(cls)

    def __init__(self, parent: QWidget | None = None) -> None:
        _ensure_app_guard()
        super().__init__(parent)

        self._is_refreshing = False
        self._store_path = _default_data_dir() / "baza_materialu.json"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_synced_type = ""
        self._last_synced_name = ""
        self._worker_store = WorkerStoreJson()
        self._material_entry_library_locked = False
        self._library_store = ProducerLibraryStoreJson()
        self._library_service = ProducerLibraryService()

        persisted = self._library_store.load()
        persisted_rows = persisted.get("rows", []) if isinstance(persisted, dict) else []
        self._producer_library_rows: list[dict[str, str]] = self._library_service.normalize_rows(
            persisted_rows if isinstance(persisted_rows, list) and persisted_rows else [dict(row) for row in PRODUCER_LIBRARY_ROWS]
        )
        self._import_headers: list[str] = [str(v or "") for v in persisted.get("import_headers", [])] if isinstance(persisted, dict) else []
        self._import_rows: list[list[str]] = []
        import_mapping = persisted.get("import_mapping", {}) if isinstance(persisted, dict) else {}
        self._import_mapping: dict[str, str] = {str(k or ""): str(v or "") for k, v in import_mapping.items()} if isinstance(import_mapping, dict) else {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        title = QLabel("BAZA MATERIALU", self)
        title.setStyleSheet("font-size:28px; font-weight:900;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        # ── Typy materialow ──────────────────────────────────────────────
        types_header = QHBoxLayout()
        types_header.setSpacing(8)

        self.btn_toggle_types = QToolButton(self)
        self.btn_toggle_types.setCheckable(True)
        self.btn_toggle_types.setChecked(True)
        self.btn_toggle_types.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle_types.setToolTip("Zwin / rozwin tabele typow")
        types_header.addWidget(self.btn_toggle_types, 0)

        self.lbl_types_title = QLabel(
            "Typy materialow (wspolna lista): ID / TYP / Nazwa / Producent",
            self,
        )
        types_header.addWidget(self.lbl_types_title, 0)
        types_header.addStretch(1)
        root.addLayout(types_header)

        self.types_body = QWidget(self)
        types_body_layout = QVBoxLayout(self.types_body)
        types_body_layout.setContentsMargins(0, 0, 0, 0)
        types_body_layout.setSpacing(6)

        type_actions = QHBoxLayout()
        type_actions.setSpacing(8)
        self.btn_add_type = QPushButton("+ Dodaj typ", self)
        self.btn_remove_type = QPushButton("Usun typ", self)
        type_actions.addWidget(self.btn_add_type, 0)
        type_actions.addWidget(self.btn_remove_type, 0)
        type_actions.addStretch(1)
        types_body_layout.addLayout(type_actions)

        self.type_entry_bar = QWidget(self)
        type_entry_layout = QHBoxLayout(self.type_entry_bar)
        type_entry_layout.setContentsMargins(0, 0, 0, 0)
        type_entry_layout.setSpacing(6)
        type_entry_layout.addWidget(QLabel("Nowy typ:", self), 0)

        self.ed_type_id = QLineEdit(self)
        self.ed_type_id.setReadOnly(True)
        self.ed_type_id.setMinimumWidth(80)
        self.ed_type_id.setPlaceholderText("ID")

        self.ed_type_typ = QLineEdit(self)
        self.ed_type_typ.setMinimumWidth(120)
        self.ed_type_typ.setPlaceholderText("TYP")

        self.ed_type_nazwa = QLineEdit(self)
        self.ed_type_nazwa.setMinimumWidth(180)
        self.ed_type_nazwa.setPlaceholderText("Nazwa")

        self.ed_type_producent = QLineEdit(self)
        self.ed_type_producent.setMinimumWidth(150)
        self.ed_type_producent.setPlaceholderText("Producent")

        self.btn_type_confirm = QPushButton("Dodaj wpis", self)
        self.btn_type_cancel = QPushButton("Zamknij", self)
        self.btn_type_confirm.setMinimumWidth(110)
        self.btn_type_cancel.setMinimumWidth(90)

        type_entry_layout.addWidget(self.ed_type_id, 0)
        type_entry_layout.addWidget(self.ed_type_typ, 1)
        type_entry_layout.addWidget(self.ed_type_nazwa, 2)
        type_entry_layout.addWidget(self.ed_type_producent, 1)
        type_entry_layout.addWidget(self.btn_type_confirm, 0)
        type_entry_layout.addWidget(self.btn_type_cancel, 0)
        self.type_entry_bar.setVisible(False)
        types_body_layout.addWidget(self.type_entry_bar, 0)

        self.tbl_types = QTableWidget(0, 4, self)
        self.tbl_types.setHorizontalHeaderLabels(["ID", "TYP", "Nazwa", "Producent"])
        self.tbl_types.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_types.setAlternatingRowColors(True)
        self.tbl_types.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_types.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_types.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.tbl_types.verticalHeader().setVisible(False)
        self.tbl_types.setSortingEnabled(False)
        self.tbl_types.setMinimumHeight(120)
        self.tbl_types.setMaximumHeight(220)
        self.tbl_types.horizontalHeader().setSectionsMovable(True)
        types_body_layout.addWidget(self.tbl_types, 0)
        root.addWidget(self.types_body, 0)

        # ── Biblioteka producentow (MVP) ────────────────────────────────
        library_header = QHBoxLayout()
        library_header.setSpacing(8)

        self.btn_toggle_library = QToolButton(self)
        self.btn_toggle_library.setCheckable(True)
        self.btn_toggle_library.setChecked(False)
        self.btn_toggle_library.setArrowType(Qt.ArrowType.RightArrow)
        self.btn_toggle_library.setToolTip("Zwin / rozwin biblioteke producentow")
        library_header.addWidget(self.btn_toggle_library, 0)

        self.lbl_library_title = QLabel(
            "Biblioteka producentow: EGGER, Swisskrono, BLUM, PEKA, Kessebohmer, SEVROLL, WURTH, ADLER",
            self,
        )
        library_header.addWidget(self.lbl_library_title, 0)
        library_header.addStretch(1)
        root.addLayout(library_header)

        self.library_body = QWidget(self)
        library_layout = QVBoxLayout(self.library_body)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(6)

        library_filters = QHBoxLayout()
        library_filters.setSpacing(6)
        library_filters.addWidget(QLabel("Producent:", self), 0)
        self.cb_library_producer = QComboBox(self)
        self.cb_library_producer.setMinimumWidth(170)
        self.cb_library_producer.addItem("Wszyscy", "")
        library_filters.addWidget(self.cb_library_producer, 0)

        self.ed_library_search = QLineEdit(self)
        self.ed_library_search.setPlaceholderText("Szukaj: kod / nazwa / typ / parametry")
        library_filters.addWidget(self.ed_library_search, 1)
        library_layout.addLayout(library_filters)

        self.tbl_library = QTableWidget(0, 6, self)
        self.tbl_library.setHorizontalHeaderLabels(["TYP", "Nazwa", "Producent", "Parametry", "Grubosc", "Cena [zl]"])
        self.tbl_library.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_library.setAlternatingRowColors(True)
        self.tbl_library.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_library.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_library.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_library.verticalHeader().setVisible(False)
        self.tbl_library.setMinimumHeight(120)
        self.tbl_library.setMaximumHeight(220)
        self.tbl_library.horizontalHeader().setSectionsMovable(True)
        library_layout.addWidget(self.tbl_library, 0)

        library_actions = QHBoxLayout()
        library_actions.setSpacing(6)
        self.btn_import_library_selected = QPushButton("Dodaj zaznaczone do bazy", self)
        self.btn_import_library_all_visible = QPushButton("Dodaj wszystkie widoczne", self)
        self.btn_library_import_file = QPushButton("Import CSV/XLSX", self)
        self.btn_library_map_columns = QPushButton("Mapowanie kolumn", self)
        self.btn_library_update_prices = QPushButton("Aktualizuj ceny z biblioteki", self)
        library_actions.addWidget(self.btn_library_import_file, 0)
        library_actions.addWidget(self.btn_library_map_columns, 0)
        library_actions.addWidget(self.btn_import_library_selected, 0)
        library_actions.addWidget(self.btn_import_library_all_visible, 0)
        library_actions.addWidget(self.btn_library_update_prices, 0)
        library_actions.addStretch(1)
        library_layout.addLayout(library_actions)

        self.lab_library_status = QLabel("", self)
        self.lab_library_status.setStyleSheet("color: palette(text);")
        library_layout.addWidget(self.lab_library_status, 0)

        self.library_body.setVisible(False)
        root.addWidget(self.library_body, 0)

        # ── Przyciski akcji glownej tabeli ────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_add_row = QPushButton("Dodaj", self)
        self.btn_remove_row = QPushButton("Usun wiersz", self)
        self.btn_toggle_filter = QPushButton("Filtr", self)

        self.btn_filter_to_buy = QPushButton("DO KUPNA", self)
        self.btn_filter_to_buy.setCheckable(True)
        self.btn_filter_to_buy.setMinimumWidth(100)
        self.btn_filter_to_buy.setStyleSheet("""
            QPushButton:checked {
                background-color: #9f1239;
                color: white;
                font-weight: bold;
                border: 1px solid #4c0519;
            }
        """)
        actions.addWidget(self.btn_filter_to_buy, 0)

        actions.addWidget(self.btn_toggle_filter, 0)
        actions.addWidget(self.btn_add_row, 0)
        actions.addWidget(self.btn_remove_row, 0)
        self.btn_add_row.setMinimumWidth(110)
        self.btn_toggle_filter.setMinimumWidth(90)
        actions.addStretch(1)
        root.addLayout(actions)

        # ── Pasek dodawania materialu ────────────────────────────────────
        self.material_entry_bar = QWidget(self)
        material_entry_layout = QVBoxLayout(self.material_entry_bar)
        material_entry_layout.setContentsMargins(0, 0, 0, 0)
        material_entry_layout.setSpacing(6)

        self.ed_mat_id = QLineEdit(self)
        self.ed_mat_id.setReadOnly(True)
        self.ed_mat_id.setMinimumWidth(80)
        self.ed_mat_id.setPlaceholderText("ID")

        self.cb_mat_typ = QComboBox(self)
        self.cb_mat_typ.setMinimumWidth(120)

        self.ed_mat_nazwa = QLineEdit(self)
        self.ed_mat_nazwa.setMinimumWidth(180)
        self.ed_mat_nazwa.setPlaceholderText("Nazwa")

        self.cb_mat_producent = QComboBox(self)
        self.cb_mat_producent.setMinimumWidth(140)
        self.cb_mat_producent.setEditable(True)
        self.cb_mat_producent.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_mat_producent.setEnabled(False)
        # Backward-compatible alias expected by tests and older code.
        self.ed_mat_producent = self.cb_mat_producent
        self.ed_mat_producent.setText = self.cb_mat_producent.setCurrentText  # type: ignore[attr-defined]

        self.ed_mat_szer = QLineEdit(self)
        self.ed_mat_szer.setMinimumWidth(90)
        self.ed_mat_szer.setPlaceholderText("Szerokosc")

        self.ed_mat_dlug = QLineEdit(self)
        self.ed_mat_dlug.setMinimumWidth(90)
        self.ed_mat_dlug.setPlaceholderText("Dlugosc")

        self.ed_mat_grub = QLineEdit(self)
        self.ed_mat_grub.setMinimumWidth(90)
        self.ed_mat_grub.setPlaceholderText("Grubosc")

        self.ed_mat_param = QLineEdit(self)
        self.ed_mat_param.setMinimumWidth(150)
        self.ed_mat_param.setPlaceholderText("Parametry")

        self.ed_mat_cena = QLineEdit(self)
        self.ed_mat_cena.setMinimumWidth(90)
        self.ed_mat_cena.setPlaceholderText("Cena [zl]")

        self.ed_mat_ilosc = QLineEdit(self)
        self.ed_mat_ilosc.setMinimumWidth(90)
        self.ed_mat_ilosc.setPlaceholderText("Ilosc")

        self.ed_mat_spisano = QLineEdit(self)
        self.ed_mat_spisano.setMinimumWidth(90)
        self.ed_mat_spisano.setPlaceholderText("Spisano")

        self.ed_mat_magazyn = QLineEdit(self)
        self.ed_mat_magazyn.setMinimumWidth(100)
        self.ed_mat_magazyn.setPlaceholderText("Na magazynie")

        self.cb_mat_pracownik = QComboBox(self)
        self.cb_mat_pracownik.setMinimumWidth(140)
        self.cb_mat_pracownik.setEditable(True)
        self.cb_mat_pracownik.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_mat_pracownik.lineEdit().setPlaceholderText("Pracownik")
        # Backward-compatible alias expected by tests and older code.
        self.ed_mat_pracownik = self.cb_mat_pracownik
        self.ed_mat_pracownik.setText = self.cb_mat_pracownik.setCurrentText  # type: ignore[attr-defined]

        self.ed_mat_data = QLineEdit(self)
        self.ed_mat_data.setMinimumWidth(120)
        self.ed_mat_data.setPlaceholderText("Data wpisu")

        self.ed_mat_zakup = QLineEdit(self)
        self.ed_mat_zakup.setMinimumWidth(110)
        self.ed_mat_zakup.setPlaceholderText("Zakup")

        self.ed_mat_faktura = QLineEdit(self)
        self.ed_mat_faktura.setMinimumWidth(130)
        self.ed_mat_faktura.setPlaceholderText("Numer faktury")

        self.ed_mat_data_zakupu = QLineEdit(self)
        self.ed_mat_data_zakupu.setMinimumWidth(120)
        self.ed_mat_data_zakupu.setPlaceholderText("Data zakupu")

        fields_row_top = QHBoxLayout()
        fields_row_top.setSpacing(6)
        for widget in (
            self.ed_mat_id,
            self.cb_mat_typ,
            self.ed_mat_nazwa,
            self.cb_mat_producent,
            self.ed_mat_cena,
            self.ed_mat_ilosc,
            self.ed_mat_spisano,
            self.ed_mat_magazyn,
        ):
            fields_row_top.addWidget(widget, 0)
        fields_row_top.addStretch(1)

        fields_row_bottom = QHBoxLayout()
        fields_row_bottom.setSpacing(6)
        for widget in (
            self.ed_mat_szer,
            self.ed_mat_dlug,
            self.ed_mat_grub,
            self.ed_mat_param,
            self.cb_mat_pracownik,
            self.ed_mat_data,
            self.ed_mat_zakup,
            self.ed_mat_faktura,
            self.ed_mat_data_zakupu,
        ):
            fields_row_bottom.addWidget(widget, 0)
        fields_row_bottom.addStretch(1)

        self.btn_mat_confirm = QPushButton("Dodaj wpis", self)
        self.btn_mat_cancel = QPushButton("Zamknij", self)
        self.btn_mat_pick_library = QPushButton("Wybierz z biblioteki", self)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(6)
        row_actions.addStretch(1)
        row_actions.addWidget(self.btn_mat_pick_library, 0)
        row_actions.addWidget(self.btn_mat_confirm, 0)
        row_actions.addWidget(self.btn_mat_cancel, 0)

        material_entry_layout.addLayout(fields_row_top)
        material_entry_layout.addLayout(fields_row_bottom)
        material_entry_layout.addLayout(row_actions)
        self.material_entry_bar.setVisible(False)
        root.addWidget(self.material_entry_bar, 0)

        # ── Glowna tabela materialow ─────────────────────────────────────
        self.tbl = QTableWidget(0, 22, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels(
            [
                "ID",
                "TYP",
                "Nazwa",
                "Producent",
                "Szerokosc",
                "Dlugosc",
                "Grubosc",
                "Parametry",
                "Cena [zl]",
                "Ilosc",
                "Spisano na zamowienie",
                "Ilosc na magazynie",
                "Pracownik",
                "Data wpisu",
                "Zakup",
                "Numer faktury",
                "Data zakupu",
                "Suma zam. kw [zl]",
                "Suma za szt [zl]",
                "Magazyn ID",
                "Magazyn",
                "Status",
            ]
        )
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.tbl.horizontalHeader().setSectionsMovable(True)
        
        # Set column widths for better navigation
        self.tbl.setColumnWidth(0, 60)   # ID
        self.tbl.setColumnWidth(1, 80)   # TYP
        self.tbl.setColumnWidth(2, 200)  # Nazwa
        self.tbl.setColumnWidth(3, 100)  # Producent
        self.tbl.setColumnWidth(8, 80)   # Cena
        self.tbl.setColumnWidth(9, 60)   # Ilosc
        self.tbl.setColumnWidth(10, 80)  # Spisano
        self.tbl.setColumnWidth(11, 80)  # Magazyn
        self.tbl.setColumnWidth(21, 100) # Status

        # ── Panel filtrow ────────────────────────────────────────────────
        self.filter_panel = _LogicalVisibilityWidget(self)
        self.filter_panel.setVisible(False)
        filter_panel_layout = QVBoxLayout(self.filter_panel)
        filter_panel_layout.setContentsMargins(0, 0, 0, 0)
        filter_panel_layout.setSpacing(6)
        self._filter_inputs: list[QLineEdit] = []

        filter_row_top = QHBoxLayout()
        filter_row_top.setSpacing(6)
        filter_row_bottom = QHBoxLayout()
        filter_row_bottom.setSpacing(6)
        split_index = (self.tbl.columnCount() + 1) // 2

        for col in range(self.tbl.columnCount()):
            holder = QWidget(self.filter_panel)
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(2)
            lbl = QLabel(self.tbl.horizontalHeaderItem(col).text(), holder)
            edit = QLineEdit(holder)
            edit.setPlaceholderText("filtr")
            edit.textChanged.connect(self._apply_filters)
            holder_layout.addWidget(lbl, 0)
            holder_layout.addWidget(edit, 0)
            self._filter_inputs.append(edit)
            if col < split_index:
                filter_row_top.addWidget(holder, 1)
            else:
                filter_row_bottom.addWidget(holder, 1)

        filter_panel_layout.addLayout(filter_row_top)
        filter_panel_layout.addLayout(filter_row_bottom)

        filter_actions = QHBoxLayout()
        filter_actions.setSpacing(6)
        self.btn_clear_filters = QPushButton("Wyczysc filtr", self.filter_panel)
        filter_actions.addWidget(self.btn_clear_filters, 0)
        filter_actions.addStretch(1)
        filter_panel_layout.addLayout(filter_actions)

        root.addWidget(self.filter_panel, 0)
        root.addWidget(self.tbl, 1)

        # ── Sygnaly ───────────────────────────────────────────────────────
        self.btn_toggle_types.toggled.connect(self._on_toggle_types_table)
        self.btn_toggle_library.toggled.connect(self._on_toggle_library_table)
        self.btn_add_type.clicked.connect(self._show_type_entry_bar)
        self.btn_remove_type.clicked.connect(self._remove_selected_type_rows)
        self.tbl_types.itemChanged.connect(self._on_type_table_item_changed)
        self.btn_type_confirm.clicked.connect(self._confirm_type_entry)
        self.btn_type_cancel.clicked.connect(self._hide_type_entry_bar)

        self.btn_add_row.clicked.connect(self._show_material_entry_bar)
        self.btn_remove_row.clicked.connect(self._remove_selected_rows)
        self.btn_toggle_filter.clicked.connect(self._toggle_filter_panel)
        self.tbl.itemChanged.connect(self._on_item_changed)
        self.btn_mat_confirm.clicked.connect(self._confirm_material_entry)
        self.btn_mat_cancel.clicked.connect(self._hide_material_entry_bar)
        self.btn_mat_pick_library.clicked.connect(self._pick_material_from_library)
        self.btn_clear_filters.clicked.connect(self._clear_filters)
        self.btn_filter_to_buy.toggled.connect(self._apply_filters)
        self.cb_mat_typ.currentTextChanged.connect(self._sync_material_entry_name)
        self.cb_library_producer.currentIndexChanged.connect(self._refresh_library_table)
        self.ed_library_search.textChanged.connect(self._refresh_library_table)
        self.btn_library_import_file.clicked.connect(self._import_library_from_file)
        self.btn_library_map_columns.clicked.connect(self._edit_library_import_mapping)
        self.btn_library_update_prices.clicked.connect(self._update_existing_material_prices_from_library)
        self.btn_import_library_selected.clicked.connect(self._import_selected_library_rows)
        self.btn_import_library_all_visible.clicked.connect(self._import_all_visible_library_rows)

        self._wire_entry_bar_keyboard_navigation()
        self._load_store()
        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._refresh_material_entry_work_combo()
        self._refresh_library_producer_combo()
        self._refresh_library_table()
        self._refresh_quantity_warnings()

    def _wire_entry_bar_keyboard_navigation(self) -> None:
        self.ed_type_typ.returnPressed.connect(self._confirm_type_entry)
        self.ed_type_nazwa.returnPressed.connect(self._confirm_type_entry)
        self.ed_type_producent.returnPressed.connect(self._confirm_type_entry)

        for edit in (
            self.ed_mat_nazwa,
            self.ed_mat_szer,
            self.ed_mat_dlug,
            self.ed_mat_grub,
            self.ed_mat_param,
            self.ed_mat_cena,
            self.ed_mat_ilosc,
            self.ed_mat_spisano,
            self.ed_mat_magazyn,
            self.ed_mat_data,
            self.ed_mat_zakup,
            self.ed_mat_faktura,
            self.ed_mat_data_zakupu,
        ):
            edit.returnPressed.connect(self._confirm_material_entry)

        QWidget.setTabOrder(self.ed_type_typ, self.ed_type_nazwa)
        QWidget.setTabOrder(self.ed_type_nazwa, self.ed_type_producent)
        QWidget.setTabOrder(self.ed_type_producent, self.btn_type_confirm)
        QWidget.setTabOrder(self.btn_type_confirm, self.btn_type_cancel)

        material_tab_chain = [
            self.cb_mat_typ,
            self.ed_mat_nazwa,
            self.cb_mat_producent,
            self.ed_mat_szer,
            self.ed_mat_dlug,
            self.ed_mat_grub,
            self.ed_mat_param,
            self.ed_mat_cena,
            self.ed_mat_ilosc,
            self.ed_mat_spisano,
            self.ed_mat_magazyn,
            self.cb_mat_pracownik,
            self.ed_mat_data,
            self.ed_mat_zakup,
            self.ed_mat_faktura,
            self.ed_mat_data_zakupu,
            self.btn_mat_confirm,
            self.btn_mat_cancel,
        ]
        for current, nxt in zip(material_tab_chain, material_tab_chain[1:]):
            QWidget.setTabOrder(current, nxt)

    def _on_toggle_types_table(self, expanded: bool) -> None:
        self.types_body.setVisible(expanded)
        self.btn_toggle_types.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _on_toggle_library_table(self, expanded: bool) -> None:
        self.library_body.setVisible(expanded)
        self.btn_toggle_library.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _save_library_store(self) -> None:
        self._library_store.save(self._producer_library_rows, self._import_headers, self._import_mapping)

    def _refresh_library_producer_combo(self) -> None:
        current = str(self.cb_library_producer.currentData() or "").strip()
        self.cb_library_producer.blockSignals(True)
        self.cb_library_producer.clear()
        self.cb_library_producer.addItem("Wszyscy", "")
        producers = sorted(
            {
                str(row.get("producent", "") or "").strip()
                for row in self._producer_library_rows
                if str(row.get("producent", "") or "").strip()
            }
        )
        for producer in producers:
            self.cb_library_producer.addItem(producer, producer)
        idx = self.cb_library_producer.findData(current)
        self.cb_library_producer.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_library_producer.blockSignals(False)

    def _load_rows_from_csv_or_tsv(self, file_path: Path) -> tuple[list[str], list[list[str]]]:
        return self._library_service.load_rows_from_csv_or_tsv(file_path)

    def _load_rows_from_xlsx(self, file_path: Path) -> tuple[list[str], list[list[str]]]:
        return self._library_service.load_rows_from_xlsx(file_path)

    def _rows_from_import_buffer(self) -> list[dict[str, str]]:
        return self._library_service.rows_from_import_buffer(self._import_headers, self._import_rows, self._import_mapping)

    def _merge_import_rows_into_library(self, rows: list[dict[str, str]]) -> int:
        merged, added = self._library_service.merge_rows(self._producer_library_rows, rows)
        self._producer_library_rows = merged
        if added:
            self._save_library_store()
        return added

    def _import_library_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik biblioteki producenta",
            "",
            "Pliki danych (*.csv *.tsv *.txt *.xlsx)",
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            if path.suffix.lower() == ".xlsx":
                headers, data_rows = self._load_rows_from_xlsx(path)
            else:
                headers, data_rows = self._load_rows_from_csv_or_tsv(path)
        except Exception as exc:
            self.lab_library_status.setText(f"Import biblioteki: blad odczytu pliku ({exc}).")
            return

        if not headers or not data_rows:
            self.lab_library_status.setText("Import biblioteki: plik nie zawiera danych.")
            return

        self._import_headers = [str(h or "").strip() for h in headers]
        self._import_rows = [list(row) for row in data_rows]
        self._import_mapping = self._library_service.guess_import_mapping(self._import_headers)

        mapped_rows = self._rows_from_import_buffer()
        added = self._merge_import_rows_into_library(mapped_rows)
        self._refresh_library_producer_combo()
        self._refresh_library_table()
        self.lab_library_status.setText(
            f"Import biblioteki: dodano {added} wpis(ow) z pliku {path.name}."
        )
        self._save_library_store()

    def _edit_library_import_mapping(self) -> None:
        if not self._import_headers:
            self.lab_library_status.setText("Mapowanie: najpierw wczytaj plik CSV/XLSX.")
            return

        dialog = ProducerImportMappingDialog(self, self._import_headers, self._import_mapping)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._import_mapping = dialog.selected_mapping()
        rows = self._rows_from_import_buffer()
        added = self._merge_import_rows_into_library(rows)
        self._refresh_library_producer_combo()
        self._refresh_library_table()
        self.lab_library_status.setText(f"Mapowanie: dodano {added} wpis(ow) po aktualizacji mapowania.")
        self._save_library_store()

    @staticmethod
    def _extract_library_code(text: str) -> str:
        return ProducerLibraryService.extract_library_code(text)

    @staticmethod
    def _compose_parametry_with_code(entry: dict[str, str]) -> str:
        return ProducerLibraryService().compose_parametry_with_code(entry)

    def _update_existing_material_prices_from_library(self) -> None:
        material_rows = [
            {
                "row": str(row),
                "typ": self._row_col_text(row, 1),
                "nazwa": self._row_col_text(row, 2),
                "producent": self._row_col_text(row, 3),
                "parametry": self._row_col_text(row, 7),
                "cena_zl": self._row_col_text(row, 8),
            }
            for row in range(self.tbl.rowCount())
        ]
        updated_rows, updated = self._library_service.update_material_prices(material_rows, self._producer_library_rows)
        for row_data in updated_rows:
            try:
                row_idx = int(str(row_data.get("row", "0") or "0"))
            except ValueError:
                continue
            if 0 <= row_idx < self.tbl.rowCount():
                self.tbl.setItem(row_idx, 8, QTableWidgetItem(str(row_data.get("cena_zl", "") or "")))

        self._refresh_quantity_warnings()
        self._save_store()
        self.lab_library_status.setText(f"Aktualizacja cen: zaktualizowano {updated} pozycji w bazie.")

    def _library_rows_filtered(self) -> list[dict[str, str]]:
        selected_producer = str(self.cb_library_producer.currentData() or "")
        needle = str(self.ed_library_search.text() or "")
        return self._library_service.filter_rows(self._producer_library_rows, selected_producer, needle)

    def _refresh_library_table(self) -> None:
        rows = self._library_rows_filtered()
        self.tbl_library.setColumnCount(7)
        self.tbl_library.setHorizontalHeaderLabels(["Kod", "TYP", "Nazwa", "Producent", "Parametry", "Grubosc", "Cena [zl]"])
        self.tbl_library.setRowCount(0)
        for row_data in rows:
            row_idx = self.tbl_library.rowCount()
            self.tbl_library.insertRow(row_idx)
            values = [
                row_data["kod"],
                row_data["typ"],
                row_data["nazwa"],
                row_data["producent"],
                row_data["parametry"],
                row_data["grubosc"],
                row_data["cena_zl"],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setData(Qt.ItemDataRole.UserRole, row_data)
                self.tbl_library.setItem(row_idx, col, item)
        self.lab_library_status.setText(f"Biblioteka: {len(rows)} widocznych wpisow.")

    def _library_entry_from_table_row(self, row: int) -> dict[str, str] | None:
        item = self.tbl_library.item(row, 1)
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return None
        return {
            "kod": str(payload.get("kod", "") or "").strip(),
            "typ": str(payload.get("typ", "") or "").strip().lower(),
            "nazwa": str(payload.get("nazwa", "") or "").strip(),
            "producent": str(payload.get("producent", "") or "").strip(),
            "parametry": str(payload.get("parametry", "") or "").strip(),
            "grubosc": str(payload.get("grubosc", "") or "").strip(),
            "cena_zl": str(payload.get("cena_zl", "") or "").strip(),
        }

    def _material_exists(self, typ: str, nazwa: str, producent: str, parametry: str) -> bool:
        typ_norm = str(typ or "").strip().lower()
        name_norm = str(nazwa or "").strip().lower()
        prod_norm = str(producent or "").strip().lower()
        par_norm = str(parametry or "").strip().lower()
        for row in range(self.tbl.rowCount()):
            row_typ = self._row_col_text(row, 1).strip().lower()
            row_name = self._row_col_text(row, 2).strip().lower()
            row_prod = self._row_col_text(row, 3).strip().lower()
            row_par = self._row_col_text(row, 7).strip().lower()
            if row_typ == typ_norm and row_name == name_norm and row_prod == prod_norm and row_par == par_norm:
                return True
        return False

    def _ensure_type_exists(self, typ: str, nazwa: str, producent: str) -> None:
        typ_norm = str(typ or "").strip().lower()
        if not typ_norm or typ_norm in BLOCKED_MATERIAL_TYPES:
            return
        for row in range(self.tbl_types.rowCount()):
            existing_typ = str(self.tbl_types.item(row, 1).text() if self.tbl_types.item(row, 1) else "").strip().lower()
            if existing_typ == typ_norm:
                if self.tbl_types.item(row, 3) is not None and not str(self.tbl_types.item(row, 3).text() or "").strip():
                    self.tbl_types.item(row, 3).setText(str(producent or "").strip())
                return

        row_idx = self.tbl_types.rowCount()
        self.tbl_types.insertRow(row_idx)
        default_name = str(nazwa or "").strip() or typ_norm.capitalize()
        self._set_type_row(
            row_idx,
            self._next_type_id(),
            typ_norm,
            default_name,
            str(producent or "").strip(),
        )

    def _import_library_rows(self, rows: list[dict[str, str]]) -> int:
        imported = 0
        for entry in rows:
            typ = str(entry.get("typ", "") or "").strip().lower()
            nazwa = str(entry.get("nazwa", "") or "").strip()
            producent = str(entry.get("producent", "") or "").strip()
            parametry = self._compose_parametry_with_code(entry)
            if not typ or not nazwa or typ in BLOCKED_MATERIAL_TYPES:
                continue
            if self._material_exists(typ, nazwa, producent, parametry):
                continue

            self._ensure_type_exists(typ, nazwa=typ.capitalize(), producent=producent)
            values = [
                self._next_id(),
                typ,
                nazwa,
                producent,
                "",
                "",
                str(entry.get("grubosc", "") or "").strip(),
                parametry,
                str(entry.get("cena_zl", "") or "").strip(),
                "",
                "",
                "",
                "",
                datetime.now().strftime("%Y-%m-%d"),
                "",
                "",
                "",
            ]
            self._insert_material_row(values)
            imported += 1

        if imported:
            self._normalize_type_table()
            self._refresh_material_entry_type_combo()
            self._refresh_material_entry_prod_combo()
        return imported

    def _import_selected_library_rows(self) -> None:
        selection_model = self.tbl_library.selectionModel()
        selected_rows = selection_model.selectedRows() if selection_model is not None else []
        rows_to_import: list[dict[str, str]] = []
        for model_index in selected_rows:
            entry = self._library_entry_from_table_row(model_index.row())
            if entry is not None:
                rows_to_import.append(entry)

        if not rows_to_import:
            self.lab_library_status.setText("Biblioteka: zaznacz co najmniej jeden wpis do importu.")
            return

        imported = self._import_library_rows(rows_to_import)
        self.lab_library_status.setText(
            f"Biblioteka: dodano {imported} wpis(ow) do naszej bazy."
            if imported
            else "Biblioteka: nic nowego do dodania (duplikaty lub niepoprawne dane)."
        )

    def _import_all_visible_library_rows(self) -> None:
        rows_to_import: list[dict[str, str]] = []
        for row in range(self.tbl_library.rowCount()):
            entry = self._library_entry_from_table_row(row)
            if entry is not None:
                rows_to_import.append(entry)
        if not rows_to_import:
            self.lab_library_status.setText("Biblioteka: brak widocznych wpisow do importu.")
            return

        imported = self._import_library_rows(rows_to_import)
        self.lab_library_status.setText(
            f"Biblioteka: dodano {imported} wpis(ow) do naszej bazy."
            if imported
            else "Biblioteka: nic nowego do dodania (duplikaty lub niepoprawne dane)."
        )

    def _show_type_entry_bar(self) -> None:
        self.type_entry_bar.setVisible(True)
        self.ed_type_id.setText(self._next_type_id())
        self.ed_type_typ.clear()
        self.ed_type_nazwa.clear()
        self.ed_type_producent.clear()
        self.ed_type_typ.setFocus()

    def _hide_type_entry_bar(self) -> None:
        self.type_entry_bar.setVisible(False)
        self.ed_type_id.clear()
        self.ed_type_typ.clear()
        self.ed_type_nazwa.clear()
        self.ed_type_producent.clear()

    def _confirm_type_entry(self) -> None:
        typ = str(self.ed_type_typ.text() or "").strip().lower()
        name = str(self.ed_type_nazwa.text() or "").strip()
        producent = str(self.ed_type_producent.text() or "").strip()

        if not typ and not name and not producent:
            return
        if typ in BLOCKED_MATERIAL_TYPES:
            self._hide_type_entry_bar()
            return
        if typ:
            for row in range(self.tbl_types.rowCount()):
                existing_typ = str(self.tbl_types.item(row, 1).text() if self.tbl_types.item(row, 1) else "").strip().lower()
                if existing_typ == typ:
                    self._hide_type_entry_bar()
                    return

        self._is_refreshing = True
        self.tbl_types.blockSignals(True)
        try:
            row_idx = self.tbl_types.rowCount()
            self.tbl_types.insertRow(row_idx)
            self._set_type_row(
                row_idx,
                str(self.ed_type_id.text() or "").strip() or self._next_type_id(),
                typ,
                name,
                producent,
            )
        finally:
            self.tbl_types.blockSignals(False)
            self._is_refreshing = False

        self._hide_type_entry_bar()
        self._normalize_type_table()
        self._normalize_material_type_rows()
        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._save_store()

    def _remove_selected_type_rows(self) -> None:
        rows = self.tbl_types.selectionModel().selectedRows() if self.tbl_types.selectionModel() is not None else []
        self._is_refreshing = True
        self.tbl_types.blockSignals(True)
        try:
            for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
                self.tbl_types.removeRow(idx.row())
        finally:
            self.tbl_types.blockSignals(False)
            self._is_refreshing = False

        self._normalize_type_table()
        self._normalize_material_type_rows()
        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._save_store()

    def _on_type_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_refreshing:
            return

        new_text = str(item.text() or "").strip()
        if item.column() == 1:
            new_text = new_text.lower()

        if new_text != item.text():
            self._is_refreshing = True
            self.tbl_types.blockSignals(True)
            try:
                item.setText(new_text)
            finally:
                self.tbl_types.blockSignals(False)
                self._is_refreshing = False

        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._normalize_material_type_rows()
        self._save_store()

    def _next_type_id(self) -> str:
        used: set[str] = set()
        for row in range(self.tbl_types.rowCount()):
            item = self.tbl_types.item(row, 0)
            if item is not None:
                used.add(str(item.text() or "").strip())
        counter = 1
        while True:
            candidate = f"T{counter:04d}"
            if candidate not in used:
                return candidate
            counter += 1

    def _set_type_row(
        self,
        row: int,
        type_id: str,
        typ_value: str,
        name_value: str,
        producent_value: str = "",
    ) -> None:
        id_item = QTableWidgetItem(str(type_id or "").strip())
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tbl_types.setItem(row, 0, id_item)
        self.tbl_types.setItem(row, 1, QTableWidgetItem(str(typ_value or "").strip().lower()))
        self.tbl_types.setItem(row, 2, QTableWidgetItem(str(name_value or "").strip()))
        self.tbl_types.setItem(row, 3, QTableWidgetItem(str(producent_value or "").strip()))

    def _default_type_rows(self) -> list[dict[str, str]]:
        return [
            {"id": "T0001", "typ": "korpus", "nazwa": "Korpus", "producent": ""},
            {"id": "T0002", "typ": "front", "nazwa": "Front", "producent": ""},
            {"id": "T0003", "typ": "plecy", "nazwa": "Plecy", "producent": ""},
            {"id": "T0004", "typ": "okleina", "nazwa": "Okleina", "producent": ""},
            {"id": "T0005", "typ": "okucie", "nazwa": "Okucie", "producent": ""},
            {"id": "T0006", "typ": "plyta", "nazwa": "Plyta", "producent": ""},
            {"id": "T0007", "typ": "profil", "nazwa": "Profil", "producent": ""},
            {"id": "T0008", "typ": "lakier", "nazwa": "Lakier", "producent": ""},
        ]

    def _load_default_type_rows(self) -> None:
        self._is_refreshing = True
        self.tbl_types.blockSignals(True)
        try:
            self.tbl_types.setRowCount(0)
            for entry in self._default_type_rows():
                row_idx = self.tbl_types.rowCount()
                self.tbl_types.insertRow(row_idx)
                self._set_type_row(
                    row_idx,
                    entry["id"],
                    entry["typ"],
                    entry["nazwa"],
                    entry["producent"],
                )
        finally:
            self.tbl_types.blockSignals(False)
            self._is_refreshing = False

        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._save_store()

    def _normalize_type_table(self) -> None:
        row_count = self.tbl_types.rowCount()
        if row_count <= 0:
            return

        seen_types: set[str] = set()
        normalized_rows: list[tuple[str, str, str, str]] = []
        used_ids: set[str] = set()

        for row in range(row_count):
            id_text = str(self.tbl_types.item(row, 0).text() if self.tbl_types.item(row, 0) else "").strip()
            typ_text = str(self.tbl_types.item(row, 1).text() if self.tbl_types.item(row, 1) else "").strip().lower()
            name_text = str(self.tbl_types.item(row, 2).text() if self.tbl_types.item(row, 2) else "").strip()
            prod_text = str(self.tbl_types.item(row, 3).text() if self.tbl_types.item(row, 3) else "").strip()

            if not typ_text and not name_text and not prod_text:
                continue
            if typ_text in BLOCKED_MATERIAL_TYPES:
                continue

            if not id_text or id_text in used_ids:
                id_text = self._next_type_id()
            used_ids.add(id_text)

            if typ_text in seen_types:
                continue
            seen_types.add(typ_text)
            normalized_rows.append((id_text, typ_text, name_text, prod_text))

        self._is_refreshing = True
        self.tbl_types.blockSignals(True)
        try:
            self.tbl_types.setRowCount(0)
            for row_idx, row_data in enumerate(normalized_rows):
                self.tbl_types.insertRow(row_idx)
                self._set_type_row(
                    row_idx,
                    row_data[0],
                    row_data[1],
                    row_data[2],
                    row_data[3],
                )
        finally:
            self.tbl_types.blockSignals(False)
            self._is_refreshing = False

    def _type_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in range(self.tbl_types.rowCount()):
            id_item = self.tbl_types.item(row, 0)
            typ_item = self.tbl_types.item(row, 1)
            name_item = self.tbl_types.item(row, 2)
            prod_item = self.tbl_types.item(row, 3)
            rows.append(
                {
                    "id": str(id_item.text() if id_item is not None else "").strip(),
                    "typ": str(typ_item.text() if typ_item is not None else "").strip().lower(),
                    "nazwa": str(name_item.text() if name_item is not None else "").strip(),
                    "producent": str(prod_item.text() if prod_item is not None else "").strip(),
                }
            )
        return rows

    def _type_options(self) -> list[str]:
        types = [entry["typ"] for entry in self._type_rows() if entry["typ"] and entry["typ"] not in BLOCKED_MATERIAL_TYPES]
        unique = sorted(set(types))
        return unique if unique else list(SHARED_MATERIAL_TYPES)

    def _normalize_material_type_rows(self) -> None:
        allowed_types = self._type_options()
        if not allowed_types:
            return
        fallback = allowed_types[0]
        col_type = 1
        for row in range(self.tbl.rowCount()):
            current = self._row_col_text(row, col_type).strip().lower()
            if current and current not in BLOCKED_MATERIAL_TYPES and current in allowed_types:
                continue
            self.tbl.setItem(row, col_type, QTableWidgetItem(fallback))

    def _type_display_name(self, typ: str, default: str = "") -> str:
        typ_norm = str(typ or "").strip().lower()
        for entry in self._type_rows():
            if entry["typ"] == typ_norm:
                name = str(entry.get("nazwa", "") or "").strip()
                if name:
                    return name
        return default

    def _type_producer_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for entry in self._type_rows():
            typ = str(entry.get("typ", "") or "").strip().lower()
            producent = str(entry.get("producent", "") or "").strip()
            if typ and typ not in mapping:
                mapping[typ] = producent
        return mapping

    def _producer_for_type(self, typ: str) -> str:
        return self._type_producer_map().get(str(typ or "").strip().lower(), "")

    def _refresh_material_entry_type_combo(self) -> None:
        current = str(self.cb_mat_typ.currentText() or "").strip().lower()
        options = self._type_options()
        self.cb_mat_typ.blockSignals(True)
        self.cb_mat_typ.clear()
        self.cb_mat_typ.addItems(options)
        if current in options:
            self.cb_mat_typ.setCurrentText(current)
        elif options:
            self.cb_mat_typ.setCurrentIndex(0)
        self.cb_mat_typ.blockSignals(False)
        self._sync_material_entry_name()

    def _refresh_material_entry_prod_combo(self) -> None:
        producent = self._producer_for_type(self.cb_mat_typ.currentText())
        self.cb_mat_producent.blockSignals(True)
        self.cb_mat_producent.clear()
        self.cb_mat_producent.addItem(producent)
        self.cb_mat_producent.setCurrentIndex(0)
        self.cb_mat_producent.blockSignals(False)

    def _worker_options(self) -> list[str]:
        names = [worker.name.strip() for worker in self._worker_store.list_workers() if worker.name.strip()]
        return sorted(set(names))

    def _worker_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for worker in self._worker_store.list_workers():
            name = str(worker.name or "").strip()
            if not name:
                continue
            rows.append({"id": str(worker.worker_id or "").strip(), "pracownik": name})
        return rows

    def _import_worker_rows(self, rows: list[dict[str, str]]) -> None:
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("pracownik", "") or "").strip()
            if not name:
                continue
            if self._worker_store.get(name) is not None:
                continue
            worker = WorkerDef(
                name=name,
                worker_id=str(entry.get("id", "") or "").strip(),
            )
            self._worker_store.save_new(worker)

    def _refresh_material_entry_work_combo(self) -> None:
        current = str(self.cb_mat_pracownik.currentText() or "").strip()
        options = self._worker_options()
        self.cb_mat_pracownik.blockSignals(True)
        self.cb_mat_pracownik.clear()
        self.cb_mat_pracownik.addItems([""] + options)
        if current in options:
            self.cb_mat_pracownik.setCurrentText(current)
        else:
            self.cb_mat_pracownik.setCurrentIndex(0)
        self.cb_mat_pracownik.blockSignals(False)

    def _sync_material_entry_name(self) -> None:
        if self._material_entry_library_locked:
            return
        typ = str(self.cb_mat_typ.currentText() or "").strip().lower()
        current_name = str(self.ed_mat_nazwa.text() or "").strip()

        if not current_name or current_name == self._last_synced_name:
            display = self._type_display_name(typ, default=typ.capitalize())
            self.ed_mat_nazwa.setText(display)
            self._last_synced_name = display

        self._refresh_material_entry_prod_combo()
        self._last_synced_type = typ

    def _set_material_entry_library_lock(self, enabled: bool) -> None:
        lock = bool(enabled)
        self._material_entry_library_locked = lock
        self.cb_mat_typ.setEnabled(not lock)
        self.cb_mat_producent.setEnabled(not lock)
        self.ed_mat_nazwa.setReadOnly(lock)
        self.ed_mat_szer.setReadOnly(lock)
        self.ed_mat_dlug.setReadOnly(lock)
        self.ed_mat_grub.setReadOnly(lock)
        self.ed_mat_param.setReadOnly(lock)
        self.cb_mat_pracownik.setEnabled(not lock)

    def _pick_material_from_library(self) -> None:
        dialog = ProducerLibraryPickerDialog(self, self._producer_library_rows)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        updated_rows = dialog.get_updated_rows()
        if updated_rows is not None:
            self._producer_library_rows = updated_rows
            self._library_store.save(self._producer_library_rows, self._import_headers, self._import_mapping)
        
        entry = dialog.selected_entry()
        if not isinstance(entry, dict):
            return

        typ = str(entry.get("typ", "") or "").strip().lower()
        producent = str(entry.get("producent", "") or "").strip()
        self._ensure_type_exists(typ, nazwa=typ.capitalize(), producent=producent)
        self._refresh_material_entry_type_combo()
        self.cb_mat_typ.setCurrentText(typ)
        self.ed_mat_nazwa.setText(str(entry.get("nazwa", "") or "").strip())
        self.ed_mat_grub.setText(str(entry.get("grubosc", "") or "").strip())
        self.ed_mat_param.setText(self._compose_parametry_with_code(entry))
        self.ed_mat_cena.setText(str(entry.get("cena_zl", "") or "").strip())
        self.ed_mat_szer.clear()
        self.ed_mat_dlug.clear()
        self._refresh_material_entry_prod_combo()
        self._set_material_entry_library_lock(True)
        self.ed_mat_ilosc.setFocus()

    def _show_material_entry_bar(self) -> None:
        self._hide_type_entry_bar()
        self.ed_mat_id.setText(self._next_id())
        self._set_material_entry_library_lock(False)
        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._refresh_material_entry_work_combo()
        self._last_synced_type = ""
        self._last_synced_name = ""
        self.ed_mat_nazwa.clear()
        self._sync_material_entry_name()
        self.ed_mat_szer.clear()
        self.ed_mat_dlug.clear()
        self.ed_mat_grub.clear()
        self.ed_mat_param.clear()
        self.ed_mat_cena.clear()
        self.ed_mat_ilosc.clear()
        self.ed_mat_spisano.clear()
        self.ed_mat_magazyn.clear()
        self.cb_mat_pracownik.setCurrentIndex(0)
        self.ed_mat_data.setText(datetime.now().strftime("%Y-%m-%d"))
        self.ed_mat_zakup.clear()
        self.ed_mat_faktura.clear()
        self.ed_mat_data_zakupu.clear()
        self.material_entry_bar.setVisible(True)
        self.ed_mat_nazwa.setFocus()

    def _hide_material_entry_bar(self) -> None:
        self.material_entry_bar.setVisible(False)
        self._set_material_entry_library_lock(False)
        self._last_synced_type = ""
        self._last_synced_name = ""
        self.ed_mat_id.clear()
        self.ed_mat_nazwa.clear()
        self.ed_mat_szer.clear()
        self.ed_mat_dlug.clear()
        self.ed_mat_grub.clear()
        self.ed_mat_param.clear()
        self.ed_mat_cena.clear()
        self.ed_mat_ilosc.clear()
        self.ed_mat_spisano.clear()
        self.ed_mat_magazyn.clear()
        self.ed_mat_data.clear()
        self.ed_mat_zakup.clear()
        self.ed_mat_faktura.clear()
        self.ed_mat_data_zakupu.clear()
        self.cb_mat_producent.clear()

    def _insert_material_row(self, values: list[str]) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self._is_refreshing = True
        self.tbl.blockSignals(True)
        try:
            self._set_id_item(row, values[0] or self._next_id())
            for col in range(self.tbl.columnCount()):
                if col == 0:
                    continue
                if col in (17, 18, 21): # Money and Status col
                    continue
                value = values[col] if col < len(values) else ""
                self.tbl.setItem(row, col, QTableWidgetItem(value))
        finally:
            self.tbl.blockSignals(False)
            self._is_refreshing = False
        self._refresh_quantity_warnings()
        self._save_store()

    def _confirm_material_entry(self) -> None:
        selected_typ = str(self.cb_mat_typ.currentText() or "").strip().lower()
        if not selected_typ or selected_typ in BLOCKED_MATERIAL_TYPES:
            options = self._type_options()
            selected_typ = options[0] if options else ""

        producent = str(self.cb_mat_producent.currentText() or "").strip()
        if not producent:
            producent = self._producer_for_type(selected_typ)
        row_values = [
            str(self.ed_mat_id.text() or "").strip(),
            selected_typ,
            str(self.ed_mat_nazwa.text() or "").strip(),
            producent,
            str(self.ed_mat_szer.text() or "").strip(),
            str(self.ed_mat_dlug.text() or "").strip(),
            str(self.ed_mat_grub.text() or "").strip(),
            str(self.ed_mat_param.text() or "").strip(),
            str(self.ed_mat_cena.text() or "").strip(),
            str(self.ed_mat_ilosc.text() or "").strip(),
            str(self.ed_mat_spisano.text() or "").strip(),
            str(self.ed_mat_magazyn.text() or "").strip(),
            str(self.cb_mat_pracownik.currentText() or "").strip(),
            str(self.ed_mat_data.text() or "").strip(),
            str(self.ed_mat_zakup.text() or "").strip(),
            str(self.ed_mat_faktura.text() or "").strip(),
            str(self.ed_mat_data_zakupu.text() or "").strip(),
        ]
        self._insert_material_row(row_values)
        self._hide_material_entry_bar()

    def _remove_selected_rows(self) -> None:
        model = self.tbl.selectionModel()
        rows = model.selectedRows() if model is not None else []
        if not rows:
            current = self.tbl.currentRow()
            if current >= 0:
                self.tbl.removeRow(current)
                self._refresh_quantity_warnings()
                self._save_store()
            return

        for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
            self.tbl.removeRow(idx.row())

        self._refresh_quantity_warnings()
        self._save_store()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_refreshing:
            return

        self._is_refreshing = True
        self.tbl.blockSignals(True)
        try:
            text = str(item.text() or "").strip()
            if item.column() == 1:
                text = text.lower()
                item.setText(text)
                producer_item = self.tbl.item(item.row(), 3)
                if producer_item is None:
                    producer_item = QTableWidgetItem()
                    self.tbl.setItem(item.row(), 3, producer_item)
                producer_item.setText(self._producer_for_type(text))
        finally:
            self.tbl.blockSignals(False)
            self._is_refreshing = False

        self._refresh_quantity_warnings()
        self._save_store()

    def _on_toggle_types_table(self, checked: bool) -> None:
        self.types_body.setVisible(checked)
        self.btn_toggle_types.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def _on_toggle_library_table(self, checked: bool) -> None:
        self.library_body.setVisible(checked)
        self.btn_toggle_library.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def _toggle_filter_panel(self) -> None:
        show = not self.filter_panel.isVisible()
        self.filter_panel.setVisible(show)
        self.btn_toggle_filter.setText("Ukryj filtr" if show else "Filtr")
        self._apply_filters()

    def _clear_filters(self) -> None:
        for edit in self._filter_inputs:
            edit.blockSignals(True)
            edit.clear()
            edit.blockSignals(False)
        self._apply_filters()

    def _row_col_text(self, row: int, col: int) -> str:
        item = self.tbl.item(row, col)
        return str(item.text() if item is not None else "")

    def _apply_filters(self) -> None:
        filters = {
            idx: str(edit.text() or "").strip().lower()
            for idx, edit in enumerate(self._filter_inputs)
            if str(edit.text() or "").strip()
        }
        show_only_to_buy = self.btn_filter_to_buy.isChecked()
        col_status = 21

        for row in range(self.tbl.rowCount()):
            text_match = all(needle in self._row_col_text(row, col).lower() for col, needle in filters.items())
            
            if show_only_to_buy:
                status_text = self._row_col_text(row, col_status).strip().upper()
                status_match = (status_text == "DO KUPNA")
            else:
                status_match = True
                
            self.tbl.setRowHidden(row, not (text_match and status_match))

    def _to_float(self, value: str) -> float:
        raw = str(value or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0

    def _clear_quantity_cell_warning(self, row: int, col: int) -> None:
        item = self.tbl.item(row, col)
        if item is None:
            return
        # Reset explicit warning colors back to the table's default palette.
        item.setData(Qt.ItemDataRole.BackgroundRole, None)
        item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def _refresh_quantity_warnings(self) -> None:
        prev_refreshing = self._is_refreshing
        was_blocked = self.tbl.blockSignals(True)
        self._is_refreshing = True

        col_cena = 8
        col_ilosc = 9
        col_spisano = 10
        col_magazyn = 11
        col_sum_zam_kw = 17
        col_sum_za_szt = 18
        col_status = 21
        try:
            for row in range(self.tbl.rowCount()):
                self._clear_quantity_cell_warning(row, col_spisano)
                self._clear_quantity_cell_warning(row, col_magazyn)
                self._clear_quantity_cell_warning(row, col_status)
                
                cena = self._to_float(self._row_col_text(row, col_cena))
                qty = self._to_float(self._row_col_text(row, col_ilosc))
                assigned = self._to_float(self._row_col_text(row, col_spisano))
                stock = self._to_float(self._row_col_text(row, col_magazyn))

                self._set_computed_money_cell(row, col_sum_zam_kw, cena * assigned)
                self._set_computed_money_cell(row, col_sum_za_szt, cena * qty)

                required = assigned if assigned > 0 else (qty if qty > 0 else 0)
                
                # Update status
                status_item = self.tbl.item(row, col_status)
                if status_item is None:
                    status_item = QTableWidgetItem()
                    self.tbl.setItem(row, col_status, status_item)
                
                if stock <= 0 and required > 0:
                    status_item.setText("DO KUPNA")
                    status_item.setForeground(QColor("#9f1239")) # Rose 800
                elif stock < required and required > 0:
                    status_item.setText("BRAKI")
                    status_item.setForeground(QColor("#b45309")) # Amber 700
                elif stock <= 1.0 and stock > 0:
                    status_item.setText("NISKI STAN")
                    status_item.setForeground(QColor("#d97706")) # Amber 600
                else:
                    status_item.setText("OK")
                    status_item.setForeground(QColor("#16a34a")) # Green 600

                if required <= 0:
                    continue
                for col in (col_spisano, col_magazyn):
                    item = self.tbl.item(row, col)
                    if item is None:
                        continue
                    if stock < required:
                        item.setBackground(QColor("#f8d7da"))
                        item.setForeground(QColor("#7f1d1d"))
                    elif stock == required:
                        item.setBackground(QColor("#fff3cd"))
                        item.setForeground(QColor("#7a4b00"))
        finally:
            self._is_refreshing = prev_refreshing
            self.tbl.blockSignals(was_blocked)

    def _set_computed_money_cell(self, row: int, col: int, value: float) -> None:
        item = self.tbl.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self.tbl.setItem(row, col, item)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setText(f"{value:.2f}" if value > 0 else "")

    def _next_id(self) -> str:
        return self._material_store.generate_next_id()

    def _next_id_from_used(self, used: set[str], start_num: int = 0) -> tuple[str, int]:
        counter = int(start_num)
        while True:
            counter += 1
            candidate = f"M{counter:04d}"
            if candidate not in used:
                return candidate, counter

    def _set_id_item(self, row: int, value: str) -> None:
        item = QTableWidgetItem(str(value or "").strip())
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.tbl.setItem(row, 0, item)

    def _table_rows(self) -> list[dict]:
        rows: list[dict] = []
        for row in range(self.tbl.rowCount()):
            values: list[str] = []
            for col in range(self.tbl.columnCount()):
                item = self.tbl.item(row, col)
                values.append(str(item.text() if item is not None else "").strip())
            rows.append(
                {
                    "id": values[0],
                    "typ": values[1].lower(),
                    "nazwa": values[2],
                    "producent": values[3],
                    "szerokosc": values[4],
                    "dlugosc": values[5],
                    "grubosc": values[6],
                    "parametry": values[7],
                    "cena_zl": values[8],
                    "ilosc": values[9],
                    "spisano_zamowienie": values[10],
                    "ilosc_magazyn": values[11],
                    "pracownik": values[12],
                    "data_wpisu": values[13],
                    "zakup": values[14],
                    "numer_faktury": values[15],
                    "data_zakupu": values[16],
                    "suma_zam_kw": values[17] if len(values) > 17 else "",
                    "suma_za_szt": values[18] if len(values) > 18 else "",
                    "magazyn_id": values[19] if len(values) > 19 else "",
                    "magazyn_typ": values[20] if len(values) > 20 else "",
                }
            )
        return rows

    def _capture_main_table_layout(self) -> dict:
        header = self.tbl.horizontalHeader()
        try:
            state_b64 = bytes(header.saveState().toBase64()).decode("ascii")
        except Exception:
            state_b64 = ""
        return {"header_state_b64": state_b64}

    def _restore_main_table_layout(self, layout: dict | None) -> None:
        if not isinstance(layout, dict):
            return
        state_b64 = str(layout.get("header_state_b64", "") or "").strip()
        if not state_b64:
            return
        try:
            state = QByteArray.fromBase64(state_b64.encode("ascii"))
            if state.isEmpty():
                return
            self.tbl.horizontalHeader().restoreState(state)
        except Exception:
            return

    def _split_legacy_dimension(self, value: str) -> tuple[str, str, str]:
        raw = str(value or "").strip().lower()
        if not raw:
            return "", "", ""
        compact = raw.replace(" ", "").replace(",", ".").replace("mm", "")
        parts = [p for p in re.split(r"[x*/|;:_-]+", compact) if p]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
        if len(parts) == 2:
            return parts[0], parts[1], ""
        if len(parts) == 1:
            return parts[0], "", ""
        return "", "", ""

    def _save_store(self) -> None:
        payload = {
            "types": self._type_rows(),
            "pracownicy": self._worker_rows(),
            "rows": self._table_rows(),
            "main_table_layout": self._capture_main_table_layout(),
        }
        self._store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_store(self) -> None:
        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
        except Exception:
            raw = {}

        type_rows = raw.get("types", [])
        if not isinstance(type_rows, list):
            type_rows = []
        seed_default_types = not bool(type_rows)
        if seed_default_types:
            type_rows = [dict(entry) for entry in self._default_type_rows()]

        work_rows = raw.get("pracownicy", [])
        if not isinstance(work_rows, list):
            work_rows = []

        rows = raw.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        main_table_layout = raw.get("main_table_layout", {})
        if not isinstance(main_table_layout, dict):
            main_table_layout = {}

        self._is_refreshing = True
        self.tbl_types.blockSignals(True)
        self.tbl.blockSignals(True)
        try:
            self.tbl_types.setRowCount(0)
            if type_rows:
                for entry in type_rows:
                    if not isinstance(entry, dict):
                        continue
                    row_idx = self.tbl_types.rowCount()
                    self.tbl_types.insertRow(row_idx)
                    row_id = str(entry.get("id", "") or "").strip() or self._next_type_id()
                    self._set_type_row(
                        row_idx,
                        row_id,
                        str(entry.get("typ", "") or ""),
                        str(entry.get("nazwa", "") or ""),
                        str(entry.get("producent", "") or ""),
                    )
            self._import_worker_rows(work_rows)

            self.tbl.setRowCount(0)
            used_material_ids: set[str] = set()
            max_material_num = 0

            for entry in rows:
                if not isinstance(entry, dict):
                    continue
                raw_id_scan = str(entry.get("id", "") or "").strip()
                digits_scan = "".join(ch for ch in raw_id_scan if ch.isdigit())
                if digits_scan:
                    try:
                        max_material_num = max(max_material_num, int(digits_scan))
                    except ValueError:
                        pass

            for entry in rows:
                if not isinstance(entry, dict):
                    continue

                row_idx = self.tbl.rowCount()
                self.tbl.insertRow(row_idx)
                legacy_w, legacy_l, legacy_g = self._split_legacy_dimension(
                    str(entry.get("wymiar", "") or "")
                )

                values = [
                    str(entry.get("id", "") or ""),
                    str(entry.get("typ", "") or "").lower(),
                    str(entry.get("nazwa", "") or ""),
                    str(entry.get("producent", "") or self._producer_for_type(str(entry.get("typ", "") or ""))),
                    str(entry.get("szerokosc", "") or legacy_w),
                    str(entry.get("dlugosc", "") or legacy_l),
                    str(entry.get("grubosc", "") or legacy_g),
                    str(entry.get("parametry", "") or ""),
                    str(entry.get("cena_zl", "") or ""),
                    str(entry.get("ilosc", "") or ""),
                    str(entry.get("spisano_zamowienie", "") or ""),
                    str(entry.get("ilosc_magazyn", "") or ""),
                    str(entry.get("pracownik", "") or ""),
                    str(entry.get("data_wpisu", "") or ""),
                    str(entry.get("zakup", "") or ""),
                    str(entry.get("numer_faktury", "") or ""),
                    str(entry.get("data_zakupu", "") or ""),
                    str(entry.get("suma_zam_kw", "") or ""),
                    str(entry.get("suma_za_szt", "") or ""),
                    str(entry.get("magazyn_id", "") or ""),
                    str(entry.get("magazyn_typ", "") or ""),
                ]

                requested_id = values[0].strip()
                if requested_id and requested_id not in used_material_ids:
                    id_value = requested_id
                else:
                    id_value, max_material_num = self._next_id_from_used(
                        used_material_ids,
                        max_material_num,
                    )

                used_material_ids.add(id_value)
                self._set_id_item(row_idx, id_value)

                for col in range(1, self.tbl.columnCount()):
                    if col in (17, 18, 21): # Money and Status col
                        continue
                    value = values[col] if col < len(values) else ""
                    self.tbl.setItem(row_idx, col, QTableWidgetItem(value))

            self._restore_main_table_layout(main_table_layout)
        finally:
            self.tbl_types.blockSignals(False)
            self.tbl.blockSignals(False)
            self._is_refreshing = False

        if self.tbl_types.rowCount() <= 0:
            seed_default_types = True
            self._is_refreshing = True
            self.tbl_types.blockSignals(True)
            try:
                self.tbl_types.setRowCount(0)
                for entry in self._default_type_rows():
                    row_idx = self.tbl_types.rowCount()
                    self.tbl_types.insertRow(row_idx)
                    self._set_type_row(
                        row_idx,
                        str(entry.get("id", "") or "").strip(),
                        str(entry.get("typ", "") or "").strip(),
                        str(entry.get("nazwa", "") or "").strip(),
                        str(entry.get("producent", "") or "").strip(),
                    )
            finally:
                self.tbl_types.blockSignals(False)
                self._is_refreshing = False

        self._normalize_type_table()
        self._normalize_material_type_rows()
        self._refresh_material_entry_type_combo()
        self._refresh_material_entry_prod_combo()
        self._refresh_material_entry_work_combo()
        self._refresh_quantity_warnings()
        self._apply_filters()

        if seed_default_types:
            self._save_store()
