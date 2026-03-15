from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.storage.catalog_store_json import CatalogStoreJson


@dataclass(frozen=True)
class ColumnSpec:
    key: str
    label: str


class CatalogTablePage(QWidget):
    def __init__(self, title: str, columns: list[ColumnSpec], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._columns = list(columns)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        top = QHBoxLayout()
        self.lab = QLabel(title)
        self.lab.setStyleSheet("font-weight:700;")
        top.addWidget(self.lab)
        top.addStretch(1)

        self.btn_add = QPushButton("Dodaj")
        self.btn_remove = QPushButton("Usun zaznaczony")
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_remove)
        lay.addLayout(top)

        self.table = QTableWidget(0, len(self._columns), self)
        self.table.setHorizontalHeaderLabels([col.label for col in self._columns])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table, 1)

        self.btn_add.clicked.connect(self.add_empty_row)
        self.btn_remove.clicked.connect(self.remove_current_row)

    def load_rows(self, rows: Iterable[dict]) -> None:
        self.table.setRowCount(0)
        for row in rows:
            self._append_row(dict(row or {}))
        self.table.resizeColumnsToContents()

    def rows(self) -> list[dict]:
        out: list[dict] = []
        for row_idx in range(self.table.rowCount()):
            item: dict = {}
            for col_idx, col in enumerate(self._columns):
                cell = self.table.item(row_idx, col_idx)
                item[col.key] = str(cell.text()).strip() if cell is not None else ""
            key = str(item.get("key", "") or "").strip()
            if not key:
                continue
            out.append(item)
        return out

    def add_empty_row(self) -> None:
        seed = {col.key: "" for col in self._columns}
        if "unit" in seed:
            seed["unit"] = "szt"
        self._append_row(seed)
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.editItem(self.table.item(self.table.rowCount() - 1, 0))

    def remove_current_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _append_row(self, row: dict) -> None:
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        for col_idx, col in enumerate(self._columns):
            text = str(row.get(col.key, "") or "")
            item = QTableWidgetItem(text)
            if col.key == "key":
                item.setToolTip("Klucz techniczny pozycji")
            self.table.setItem(row_idx, col_idx, item)


class CatalogEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None, catalog: CatalogStoreJson) -> None:
        super().__init__(parent)
        self._catalog = catalog

        self.setWindowTitle("Edytuj katalog cen")
        self.setModal(True)
        self.resize(1100, 640)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.lab_intro = QLabel(
            "Tu edytujesz wspolna baze materialow, okleiny, okuc i profili. "
            "Zmiany po zapisie od razu trafia do BOM i list wyboru."
        )
        self.lab_intro.setWordWrap(True)
        lay.addWidget(self.lab_intro)

        self.tabs = QTabWidget(self)
        lay.addWidget(self.tabs, 1)

        self.page_materials = CatalogTablePage(
            "Materialy",
            columns=[
                ColumnSpec("key", "Klucz"),
                ColumnSpec("name_pl", "Nazwa"),
                ColumnSpec("manufacturer", "Producent"),
                ColumnSpec("material_type", "Typ"),
                ColumnSpec("material_group", "Grupa"),
                ColumnSpec("finish_group", "Wykonczenie"),
                ColumnSpec("thickness_mm", "Grubosc mm"),
                ColumnSpec("price_pln_per_m2", "Cena zl/m2"),
                ColumnSpec("price_note", "Notatka"),
            ],
        )
        self.page_edgebands = CatalogTablePage(
            "Okleina",
            columns=[
                ColumnSpec("key", "Klucz"),
                ColumnSpec("name_pl", "Nazwa"),
                ColumnSpec("manufacturer", "Producent"),
                ColumnSpec("edgeband_type", "Typ"),
                ColumnSpec("material_group", "Grupa"),
                ColumnSpec("thickness_mm", "Grubosc mm"),
                ColumnSpec("price_pln_per_m", "Cena zl/mb"),
                ColumnSpec("price_note", "Notatka"),
            ],
        )
        self.page_hardware = CatalogTablePage(
            "Okucia",
            columns=[
                ColumnSpec("key", "Klucz"),
                ColumnSpec("name_pl", "Nazwa"),
                ColumnSpec("manufacturer", "Producent"),
                ColumnSpec("category", "Kategoria"),
                ColumnSpec("item_type", "Typ"),
                ColumnSpec("unit", "Jednostka"),
                ColumnSpec("price_pln", "Cena zl"),
                ColumnSpec("price_note", "Notatka"),
            ],
        )
        self.page_profiles = CatalogTablePage(
            "Profile",
            columns=[
                ColumnSpec("key", "Klucz"),
                ColumnSpec("name_pl", "Nazwa"),
                ColumnSpec("description", "Opis"),
                ColumnSpec("material_carcass", "Korpus - material"),
                ColumnSpec("material_front", "Front - material"),
                ColumnSpec("material_back", "Plecy - material"),
                ColumnSpec("edgeband_carcass", "Korpus - okleina"),
                ColumnSpec("edgeband_front", "Front - okleina"),
                ColumnSpec("edgeband_back", "Plecy - okleina"),
                ColumnSpec("hinge_vendor", "Vendor zawiasu"),
                ColumnSpec("drawer_vendor", "Vendor szuflady"),
            ],
        )

        self.tabs.addTab(self.page_materials, "Materialy")
        self.tabs.addTab(self.page_edgebands, "Okleina")
        self.tabs.addTab(self.page_hardware, "Okucia")
        self.tabs.addTab(self.page_profiles, "Profile")

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_save = QPushButton("Zapisz katalog")
        self.btn_cancel = QPushButton("Anuluj")
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        lay.addLayout(btns)

        self.btn_save.clicked.connect(self._save_and_accept)
        self.btn_cancel.clicked.connect(self.reject)

        self._load()

    def _load(self) -> None:
        data = self._catalog.export_catalog()
        self.page_materials.load_rows(data.get("materials") or [])
        self.page_edgebands.load_rows(data.get("edgebands") or [])
        self.page_hardware.load_rows(data.get("hardware") or [])
        self.page_profiles.load_rows(self._profile_rows_to_table_rows(data.get("material_profiles") or []))

    def _save_and_accept(self) -> None:
        self._catalog.replace_catalog(
            materials=self.page_materials.rows(),
            edgebands=self.page_edgebands.rows(),
            hardware=self.page_hardware.rows(),
            material_profiles=self._table_rows_to_profile_rows(self.page_profiles.rows()),
        )
        self.accept()

    @staticmethod
    def _profile_rows_to_table_rows(rows: Iterable[dict]) -> list[dict]:
        out: list[dict] = []
        for row in rows:
            material_map = dict((row or {}).get("material_map", {}) or {})
            edgeband_map = dict((row or {}).get("edgeband_map", {}) or {})
            hardware_map = dict((row or {}).get("hardware_vendor_map", {}) or {})
            out.append(
                {
                    "key": str((row or {}).get("key", "") or ""),
                    "name_pl": str((row or {}).get("name_pl", "") or ""),
                    "description": str((row or {}).get("description", "") or ""),
                    "material_carcass": str(material_map.get("carcass", "") or ""),
                    "material_front": str(material_map.get("front", "") or ""),
                    "material_back": str(material_map.get("back", "") or ""),
                    "edgeband_carcass": str(edgeband_map.get("carcass", "") or ""),
                    "edgeband_front": str(edgeband_map.get("front", "") or ""),
                    "edgeband_back": str(edgeband_map.get("back", "") or ""),
                    "hinge_vendor": str(hardware_map.get("hinge", "") or ""),
                    "drawer_vendor": str(hardware_map.get("drawer_system", "") or ""),
                }
            )
        return out

    @staticmethod
    def _table_rows_to_profile_rows(rows: Iterable[dict]) -> list[dict]:
        out: list[dict] = []
        for row in rows:
            source = dict(row or {})
            key = str(source.get("key", "") or "").strip()
            if not key:
                continue
            out.append(
                {
                    "key": key,
                    "name_pl": str(source.get("name_pl", key) or key),
                    "description": str(source.get("description", "") or ""),
                    "material_map": {
                        "carcass": str(source.get("material_carcass", "") or "").strip(),
                        "front": str(source.get("material_front", "") or "").strip(),
                        "back": str(source.get("material_back", "") or "").strip(),
                    },
                    "edgeband_map": {
                        "carcass": str(source.get("edgeband_carcass", "") or "").strip(),
                        "front": str(source.get("edgeband_front", "") or "").strip(),
                        "back": str(source.get("edgeband_back", "") or "").strip(),
                    },
                    "hardware_vendor_map": {
                        "hinge": str(source.get("hinge_vendor", "") or "").strip(),
                        "drawer_system": str(source.get("drawer_vendor", "") or "").strip(),
                    },
                }
            )
        return out
