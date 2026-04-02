"""
PartsTableBlock – tabela „Lista formatek" zastępująca ProjectTreeBlock.

Kolumny:
  Lp | 👁 | Nazwa | Typ | Materiał | Gr. | Wymiary | Il. | ↕ | Obrzeże

Sygnały:
  sig_selected_part(str)       – klucz wybranej formatki
  sig_visibility_changed(str, bool) – klucz + nowy stan widoczności
  sig_grain_changed(str, str)  – klucz + nowy grain_direction
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QBrush, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.module_models import (
    GRAIN_HORIZONTAL,
    GRAIN_LABELS,
    GRAIN_NONE,
    GRAIN_VERTICAL,
    ModuleDef,
    PartDef,
)

if TYPE_CHECKING:
    pass

# ── KOLUMNY ──────────────────────────────────────────────────────────────────
_COL_LP    = 0
_COL_EYE   = 1
_COL_NAME  = 2
_COL_TYPE  = 3
_COL_MAT   = 4
_COL_THICK = 5
_COL_DIMS  = 6
_COL_QTY   = 7
_COL_GRAIN = 8
_COL_EDGE  = 9
_NUM_COLS  = 10

_HEADERS = ["Lp", "👁", "Nazwa elementu", "Typ", "Materiał", "Gr.", "Wymiary", "Il.", "↕", "Obrzeże"]

# Szerokości kolumn (px)
_COL_WIDTHS = [28, 26, 130, 72, 110, 38, 76, 26, 30, 68]

# Typ formatki → czytelna etykieta
_PART_TYPE_LABELS: dict[str, str] = {
    "side_left":  "Bok",
    "side_right": "Bok",
    "top":        "Wieniec",
    "bottom":     "Wieniec",
    "back":       "Tyl",
    "front":      "Front",
    "divider":    "Przegroda",
}

# Kolejnosc wierszy
_BASE_ORDER = ["side_left", "side_right", "top", "bottom", "back", "front", "divider"]


def _part_type_label(key: str) -> str:
    base = key.split("_")[0]
    if base == "shelf":
        return "Polka"
    if base == "drawer":
        return "Szuflada"
    return _PART_TYPE_LABELS.get(key, _PART_TYPE_LABELS.get(base, base.capitalize()))


def _dims_label(dims: dict) -> str:
    w = dims.get("w", "")
    h = dims.get("h", "")
    if w and h:
        wi = int(w) if float(w) == int(float(w)) else float(w)
        hi = int(h) if float(h) == int(float(h)) else float(h)
        return f"{wi} × {hi}"
    return "-"


def _edge_label(eb: dict) -> str:
    count = sum(1 for v in eb.values() if v)
    if count == 0:
        return "-"
    return f"{count}×"


def _grain_symbol(grain: str) -> str:
    if grain == GRAIN_VERTICAL:
        return "↕"
    if grain == GRAIN_HORIZONTAL:
        return "↔"
    return "—"


# ── WIDGET ───────────────────────────────────────────────────────────────────
class PartsTableBlock(QWidget):
    """Tabela lista formatek z kolumna widocznosci i kierunku uslojenia."""

    sig_selected_part = pyqtSignal(str)            # klucz wybranej formatki
    sig_visibility_changed = pyqtSignal(str, bool)  # klucz, widoczna?
    sig_grain_changed = pyqtSignal(str, str)        # klucz, grain_direction

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._module: Optional[ModuleDef] = None
        self._keys: list[str] = []          # kolejnosc wierszy
        self._loading = False               # blokada sygnałów podczas ladowania

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── naglowek ──
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 4, 4, 2)
        self._lbl_title = QLabel("Lista formatek")
        self._lbl_title.setStyleSheet("font-weight:700; font-size:11px;")
        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet("color:#64748b; font-size:10px;")
        hdr.addWidget(self._lbl_title)
        hdr.addWidget(self._lbl_count)
        hdr.addStretch(1)
        lay.addLayout(hdr)

        # ── tabela ──
        self.table = QTableWidget(0, _NUM_COLS, self)
        self.table.setHorizontalHeaderLabels(_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setShowGrid(False)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # szerokosci kolumn
        for i, w in enumerate(_COL_WIDTHS):
            self.table.setColumnWidth(i, w)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(_COL_NAME, 120)

        lay.addWidget(self.table, 1)

        # ── pasek podsumowania ──
        footer = QWidget(self)
        footer.setObjectName("parts_footer")
        footer.setStyleSheet("""
            QWidget#parts_footer {
                background: #f1f5f9;
                border-top: 1px solid #cbd5e1;
            }
        """)
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(6, 3, 6, 3)
        foot_lay.setSpacing(14)

        self._stat_count = QLabel("El.: 0")
        self._stat_area  = QLabel("Pow.: 0,00 m²")
        self._stat_edge  = QLabel("Obr.: 0,00 m")
        for lbl in (self._stat_count, self._stat_area, self._stat_edge):
            lbl.setStyleSheet("font-size:10px; color:#475569;")
            foot_lay.addWidget(lbl)
        foot_lay.addStretch(1)

        lay.addWidget(footer, 0)

        # ── sygnaly ──
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def rebuild_from_module(self, m: ModuleDef) -> None:
        """Pelne przeladowanie tabeli z modelu."""
        self._module = m
        self._loading = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._keys.clear()

        vp = set(getattr(m, "visible_parts", set()) or set())

        # kolejnosc: baza → polki → reszta
        parts = dict(m.parts or {})
        shelf_keys = sorted(
            [k for k in parts if k.startswith("shelf_")],
            key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 999,
        )
        div_keys = sorted(
            [k for k in parts if k.startswith("divider_") and k not in _BASE_ORDER],
        )
        ordered = [k for k in _BASE_ORDER if k in parts] + shelf_keys + div_keys
        rest = [k for k in parts if k not in ordered]
        ordered += sorted(rest)

        area_total = 0.0
        edge_total = 0.0

        for lp, key in enumerate(ordered, start=1):
            part = parts[key]
            self._keys.append(key)
            row = self.table.rowCount()
            self.table.insertRow(row)

            visible = key in vp
            grain = part.effective_grain()
            dims = part.dims_mm or {}
            thick_mm = dims.get("t", 18.0)

            # powierzchnia i obrzeze do sumy
            w_mm = float(dims.get("w", 0.0))
            h_mm = float(dims.get("h", 0.0))
            area_total += (w_mm * h_mm) / 1_000_000.0
            edge_count = sum(1 for v in (part.edge_banding or {}).values() if v)
            edge_total += (w_mm + h_mm) * 2.0 / 1000.0 * (edge_count / 4.0) if edge_count else 0.0

            # Lp
            item_lp = QTableWidgetItem(str(lp))
            item_lp.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            item_lp.setForeground(QBrush(QColor("#94a3b8")))
            item_lp.setData(Qt.ItemDataRole.UserRole, key)
            self.table.setItem(row, _COL_LP, item_lp)

            # 👁 widocznosc
            item_eye = QTableWidgetItem("👁" if visible else "○")
            item_eye.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            item_eye.setForeground(QBrush(QColor("#3b82f6") if visible else QColor("#cbd5e1")))
            item_eye.setToolTip("Kliknij aby ukryc/pokazac element na rysunku")
            self.table.setItem(row, _COL_EYE, item_eye)

            # Nazwa
            item_name = QTableWidgetItem(part.name_pl or key)
            f = QFont()
            f.setBold(True)
            item_name.setFont(f)
            self.table.setItem(row, _COL_NAME, item_name)

            # Typ
            item_type = QTableWidgetItem(_part_type_label(key))
            item_type.setForeground(QBrush(QColor("#7c3aed")))
            self.table.setItem(row, _COL_TYPE, item_type)

            # Material (klucz, bo nazwy wymagaja katalogu)
            mat_key = str(part.material_override_key or part.material_key or "-")
            item_mat = QTableWidgetItem(mat_key)
            item_mat.setForeground(QBrush(QColor("#374151")))
            self.table.setItem(row, _COL_MAT, item_mat)

            # Grubość
            thick_int = int(thick_mm) if float(thick_mm) == int(float(thick_mm)) else thick_mm
            item_thick = QTableWidgetItem(f"{thick_int}")
            item_thick.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            item_thick.setForeground(QBrush(QColor("#64748b")))
            self.table.setItem(row, _COL_THICK, item_thick)

            # Wymiary
            item_dims = QTableWidgetItem(_dims_label(dims))
            item_dims.setForeground(QBrush(QColor("#0369a1")))
            self.table.setItem(row, _COL_DIMS, item_dims)

            # Ilosc (na razie zawsze 1 – rozbudowac jesli modul ma qty per part)
            item_qty = QTableWidgetItem("1")
            item_qty.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.table.setItem(row, _COL_QTY, item_qty)

            # Kierunek uslojenia
            symbol = _grain_symbol(grain)
            item_grain = QTableWidgetItem(symbol)
            item_grain.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            if grain == GRAIN_VERTICAL:
                item_grain.setForeground(QBrush(QColor("#0891b2")))
            elif grain == GRAIN_HORIZONTAL:
                item_grain.setForeground(QBrush(QColor("#d97706")))
            else:
                item_grain.setForeground(QBrush(QColor("#94a3b8")))
            item_grain.setToolTip("Kliknij aby zmienic kierunek uslojenia")
            self.table.setItem(row, _COL_GRAIN, item_grain)

            # Obrzeze
            item_edge = QTableWidgetItem(_edge_label(part.edge_banding or {}))
            item_edge.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            if edge_count > 0:
                item_edge.setForeground(QBrush(QColor("#dc2626")))
            self.table.setItem(row, _COL_EDGE, item_edge)

        self.table.blockSignals(False)
        self._loading = False

        count = len(ordered)
        self._lbl_count.setText(f"  {count} el.")
        self._stat_count.setText(f"El.: {count}")
        self._stat_area.setText(f"Pow.: {area_total:.2f} m\u00b2")
        self._stat_edge.setText(f"Obr.: {edge_total:.2f} m")

    def select_part(self, part_key: str) -> None:
        """Zaznacza wiersz odpowiadajacy part_key."""
        if part_key in self._keys:
            row = self._keys.index(part_key)
            self.table.selectRow(row)

    def selected_part_keys(self) -> list[str]:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        return [self._keys[r] for r in sorted(rows) if r < len(self._keys)]

    def update_material_label(self, part_key: str, mat_label: str) -> None:
        """Odswiezenie nazwy materialu w tabeli bez pelnego rebuild."""
        if part_key not in self._keys:
            return
        row = self._keys.index(part_key)
        item = self.table.item(row, _COL_MAT)
        if item:
            item.setText(mat_label)

    # ─────────────────────────────────────────────────────────────────────────
    # SLOTS WEWNETRZNE
    # ─────────────────────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        if self._loading:
            return
        keys = self.selected_part_keys()
        if keys:
            self.sig_selected_part.emit(keys[0])

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if row >= len(self._keys):
            return
        key = self._keys[row]

        if col == _COL_EYE:
            self._toggle_visibility(row, key)
        elif col == _COL_GRAIN:
            self._cycle_grain(row, key)

    def _toggle_visibility(self, row: int, key: str) -> None:
        item = self.table.item(row, _COL_EYE)
        if not item:
            return
        currently_visible = item.text() == "👁"
        new_visible = not currently_visible
        item.setText("👁" if new_visible else "○")
        item.setForeground(QBrush(QColor("#3b82f6") if new_visible else QColor("#cbd5e1")))
        self.sig_visibility_changed.emit(key, new_visible)

    def _cycle_grain(self, row: int, key: str) -> None:
        item = self.table.item(row, _COL_GRAIN)
        if not item:
            return
        current = item.text()
        # cykl: ↕ → ↔ → — → ↕
        cycle = {_grain_symbol(GRAIN_VERTICAL): GRAIN_HORIZONTAL,
                 _grain_symbol(GRAIN_HORIZONTAL): GRAIN_NONE,
                 _grain_symbol(GRAIN_NONE): GRAIN_VERTICAL}
        new_grain = cycle.get(current, GRAIN_VERTICAL)
        symbol = _grain_symbol(new_grain)
        item.setText(symbol)
        if new_grain == GRAIN_VERTICAL:
            item.setForeground(QBrush(QColor("#0891b2")))
        elif new_grain == GRAIN_HORIZONTAL:
            item.setForeground(QBrush(QColor("#d97706")))
        else:
            item.setForeground(QBrush(QColor("#94a3b8")))
        self.sig_grain_changed.emit(key, new_grain)
