from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QScrollArea,
    QWidget,
)

from .base import BaseTab
from core.catalog_store import BoardSpec
from core.materials_store import MaterialSpec, EdgeSpec, FittingSpec


def _float_cell(table: QTableWidget, r: int, c: int, default: float = 0.0) -> float:
    item = table.item(r, c)
    if not item:
        return default
    txt = (item.text() or "").strip().replace(",", ".")
    try:
        return float(txt)
    except Exception:
        return default


def _str_cell(table: QTableWidget, r: int, c: int, default: str = "") -> str:
    item = table.item(r, c)
    if not item:
        return default
    return (item.text() or default).strip()


class Tab(BaseTab):
    TAB_KEY = "catalogs"
    TAB_TITLE_PL = "Baza: materiały i okucia"

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(ctx, parent)

        root = QVBoxLayout(self)

        title = QLabel("Baza wspólna (materiały / okucia / krawędzie) — dla wszystkich zakładek")
        title.setStyleSheet("font-size: 18px; font-weight: 600; background: transparent;")
        root.addWidget(title)

        hint = QLabel(
            "Tu trzymamy parametry, z których korzystają inne zakładki: Moduł, Ściana, Zestaw mebli itd.\n"
            "Zakładki czytają dane z ctx.catalogs (jedno źródło prawdy)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; background: transparent;")
        root.addWidget(hint)

        # Scroll (żeby nie robić gigantycznego okna)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll, 1)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)

        # --- Materials ---
        gb_mat = QGroupBox("Materiały")
        layout.addWidget(gb_mat)
        v1 = QVBoxLayout(gb_mat)
        self.tbl_mat = QTableWidget(0, 6)
        self.tbl_mat.setHorizontalHeaderLabels(["Nazwa", "Kategoria", "Grubość (mm)", "Cena", "Jednostka", "Waluta"])
        v1.addWidget(self.tbl_mat)

        # --- Fittings ---
        gb_fit = QGroupBox("Okucia")
        layout.addWidget(gb_fit)
        v2 = QVBoxLayout(gb_fit)
        self.tbl_fit = QTableWidget(0, 4)
        self.tbl_fit.setHorizontalHeaderLabels(["Nazwa", "Kategoria", "Cena/szt", "Waluta"])
        v2.addWidget(self.tbl_fit)

        # --- Edges ---
        gb_edge = QGroupBox("Krawędzie")
        layout.addWidget(gb_edge)
        v3 = QVBoxLayout(gb_edge)
        self.tbl_edge = QTableWidget(0, 5)
        self.tbl_edge.setHorizontalHeaderLabels(["Nazwa", "Grubość (mm)", "Wysokość (mm)", "Cena/mb", "Waluta"])
        v3.addWidget(self.tbl_edge)

        # Buttons
        btns = QHBoxLayout()
        self.btn_sample = QPushButton("Wczytaj przykładowe")
        self.btn_apply = QPushButton("Zapisz w aplikacji")
        btns.addWidget(self.btn_sample)
        btns.addWidget(self.btn_apply)
        btns.addStretch(1)
        root.addLayout(btns)

        self.btn_sample.clicked.connect(self._load_sample)
        self.btn_apply.clicked.connect(self._apply)

        self._load_from_store()

    def _load_from_store(self) -> None:
        # existing boards are still in store, but this tab focuses on materials/fittings/edges.
        self._set_materials(self.ctx.catalogs.get_materials())
        self._set_fittings(self.ctx.catalogs.get_fittings())
        self._set_edges(self.ctx.catalogs.get_edges())

    # ----------- set tables -----------
    def _set_materials(self, items: List[MaterialSpec]) -> None:
        self.tbl_mat.setRowCount(0)
        for m in items:
            r = self.tbl_mat.rowCount()
            self.tbl_mat.insertRow(r)
            self.tbl_mat.setItem(r, 0, QTableWidgetItem(m.name))
            self.tbl_mat.setItem(r, 1, QTableWidgetItem(m.category))
            self.tbl_mat.setItem(r, 2, QTableWidgetItem(str(m.thickness_mm)))
            self.tbl_mat.setItem(r, 3, QTableWidgetItem(str(m.price)))
            self.tbl_mat.setItem(r, 4, QTableWidgetItem(m.unit))
            self.tbl_mat.setItem(r, 5, QTableWidgetItem(m.currency))

    def _set_fittings(self, items: List[FittingSpec]) -> None:
        self.tbl_fit.setRowCount(0)
        for f in items:
            r = self.tbl_fit.rowCount()
            self.tbl_fit.insertRow(r)
            self.tbl_fit.setItem(r, 0, QTableWidgetItem(f.name))
            self.tbl_fit.setItem(r, 1, QTableWidgetItem(f.category))
            self.tbl_fit.setItem(r, 2, QTableWidgetItem(str(f.price_per_piece)))
            self.tbl_fit.setItem(r, 3, QTableWidgetItem(f.currency))

    def _set_edges(self, items: List[EdgeSpec]) -> None:
        self.tbl_edge.setRowCount(0)
        for e in items:
            r = self.tbl_edge.rowCount()
            self.tbl_edge.insertRow(r)
            self.tbl_edge.setItem(r, 0, QTableWidgetItem(e.name))
            self.tbl_edge.setItem(r, 1, QTableWidgetItem(str(e.thickness_mm)))
            self.tbl_edge.setItem(r, 2, QTableWidgetItem(str(e.height_mm)))
            self.tbl_edge.setItem(r, 3, QTableWidgetItem(str(e.price_per_mb)))
            self.tbl_edge.setItem(r, 4, QTableWidgetItem(e.currency))

    def _load_sample(self) -> None:
        mats = [
            MaterialSpec(name="Płyta laminowana biała", category="Płyta", thickness_mm=18.0, price=75.0, unit="m²"),
            MaterialSpec(name="MDF lakier", category="MDF", thickness_mm=19.0, price=140.0, unit="m²"),
            MaterialSpec(name="Sklejka brzozowa", category="Sklejka", thickness_mm=18.0, price=160.0, unit="m²"),
        ]
        fits = [
            FittingSpec(name="Zawias puszkowy", category="Zawias", price_per_piece=7.50),
            FittingSpec(name="Prowadnica szuflady 500", category="Prowadnica", price_per_piece=38.00),
            FittingSpec(name="Podnośnik frontu", category="Podnośnik", price_per_piece=95.00),
        ]
        edges = [
            EdgeSpec(name="ABS 1.0", thickness_mm=1.0, height_mm=22.0, price_per_mb=2.60),
            EdgeSpec(name="ABS 2.0", thickness_mm=2.0, height_mm=22.0, price_per_mb=3.80),
        ]
        self._set_materials(mats)
        self._set_fittings(fits)
        self._set_edges(edges)

    def _apply(self) -> None:
        mats: List[MaterialSpec] = []
        for r in range(self.tbl_mat.rowCount()):
            name = _str_cell(self.tbl_mat, r, 0, "").strip()
            if not name:
                continue
            mats.append(
                MaterialSpec(
                    name=name,
                    category=_str_cell(self.tbl_mat, r, 1, "Płyta"),
                    thickness_mm=_float_cell(self.tbl_mat, r, 2, 0.0),
                    price=_float_cell(self.tbl_mat, r, 3, 0.0),
                    unit=_str_cell(self.tbl_mat, r, 4, "m²") or "m²",
                    currency=_str_cell(self.tbl_mat, r, 5, "PLN") or "PLN",
                )
            )

        fits: List[FittingSpec] = []
        for r in range(self.tbl_fit.rowCount()):
            name = _str_cell(self.tbl_fit, r, 0, "").strip()
            if not name:
                continue
            fits.append(
                FittingSpec(
                    name=name,
                    category=_str_cell(self.tbl_fit, r, 1, "Okucie"),
                    price_per_piece=_float_cell(self.tbl_fit, r, 2, 0.0),
                    currency=_str_cell(self.tbl_fit, r, 3, "PLN") or "PLN",
                )
            )

        edges: List[EdgeSpec] = []
        for r in range(self.tbl_edge.rowCount()):
            name = _str_cell(self.tbl_edge, r, 0, "").strip()
            if not name:
                continue
            edges.append(
                EdgeSpec(
                    name=name,
                    thickness_mm=_float_cell(self.tbl_edge, r, 1, 0.0),
                    height_mm=_float_cell(self.tbl_edge, r, 2, 0.0),
                    price_per_mb=_float_cell(self.tbl_edge, r, 3, 0.0),
                    currency=_str_cell(self.tbl_edge, r, 4, "PLN") or "PLN",
                )
            )

        self.ctx.catalogs.set_materials(mats)
        self.ctx.catalogs.set_fittings(fits)
        self.ctx.catalogs.set_edges(edges)

        self.ctx.bus.data_changed.emit("catalogs")

        QMessageBox.information(self, "Zapisano", "Baza materiałów i okuć została zaktualizowana (w pamięci aplikacji).")

    def export_state(self) -> Dict[str, Any]:
        return {
            "title": self.TAB_TITLE_PL,
            "materials_count": len(self.ctx.catalogs.get_materials()),
            "fittings_count": len(self.ctx.catalogs.get_fittings()),
            "edges_count": len(self.ctx.catalogs.get_edges()),
        }
