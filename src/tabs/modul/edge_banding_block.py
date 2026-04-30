from __future__ import annotations

from typing import Dict, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.storage.catalog_store_json import CatalogStoreJson
from src.tabs.modul.edge_preview_widget import EdgePreviewWidget, _key_to_color


EDGE_SIDES_PL: Dict[str, str] = {
    "left": "Lewa",
    "right": "Prawa",
    "top": "Gora",
    "bottom": "Dol",
}

EDGE_SIDES_SHORT_PL: Dict[str, str] = {
    "left": "L",
    "right": "P",
    "top": "G",
    "bottom": "D",
}


class EdgeBandingBlock(QWidget):
    sig_changed = pyqtSignal()
    sig_apply_to_selected = pyqtSignal()
    sig_apply_to_all_shelves = pyqtSignal()

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        top_row = QHBoxLayout()
        self.lab_part = QLabel("Formatka: (brak)")
        self.lab_part.setStyleSheet("font-weight:700;")
        top_row.addWidget(self.lab_part, 1)

        self.lab_sel = QLabel("Zaznaczone: 1")
        self.lab_sel.setStyleSheet("color:#444;")
        top_row.addWidget(self.lab_sel, 0)
        lay.addLayout(top_row)

        self.preview = EdgePreviewWidget(self)
        lay.addWidget(self.preview)

        self.lbl_legend = QLabel("", self)
        self.lbl_legend.setWordWrap(True)
        self.lbl_legend.setStyleSheet("font-size:9px; color:#374151;")
        lay.addWidget(self.lbl_legend)

        self.chk_all = QCheckBox("Wszystkie strony")
        self.chk_all.setTristate(True)
        lay.addWidget(self.chk_all)

        rows_box = QWidget(self)
        rows_lay = QVBoxLayout(rows_box)
        rows_lay.setContentsMargins(0, 0, 0, 0)
        rows_lay.setSpacing(6)
        lay.addWidget(rows_box)

        edgebands = self._catalog.list_edgebands() or []
        self._default_edgeband_key_cache = next(
            (
                str(eb.key)
                for eb in edgebands
                if str(getattr(eb, "key", "") or "").strip().lower() != "brak"
            ),
            "Brak",
        )
        self._rows: Dict[str, Tuple[QCheckBox, QComboBox]] = {}

        for side_key, side_pl in EDGE_SIDES_PL.items():
            side_short = EDGE_SIDES_SHORT_PL.get(side_key, side_pl[:1].upper())
            row = QWidget(self)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            cb = QCheckBox(side_short)
            cb.setToolTip(side_pl)
            combo = QComboBox()
            for eb in edgebands:
                combo.addItem(self._edgeband_label(eb), eb.key)

            idx0 = combo.findData("Brak")
            combo.setCurrentIndex(idx0 if idx0 >= 0 else 0)
            combo.setEnabled(False)

            def on_cb_changed(_state: int, _combo=combo, _cb=cb) -> None:
                is_checked = _cb.isChecked()
                _combo.setEnabled(is_checked)
                if is_checked:
                    self._ensure_default_edgeband_for_row(_combo)
                self._sync_preview_from_rows()
                self._sync_all_checkbox()
                self.sig_changed.emit()

            cb.stateChanged.connect(on_cb_changed)
            def on_combo_changed(_i: int, _side=side_key) -> None:
                self._sync_preview_from_rows()
                self.sig_changed.emit()

            combo.currentIndexChanged.connect(on_combo_changed)

            row_lay.addWidget(cb, 0)
            row_lay.addWidget(combo, 1)

            rows_lay.addWidget(row)
            self._rows[side_key] = (cb, combo)

        preset_row = QHBoxLayout()
        self.btn_p4 = QPushButton("4 strony")
        self.btn_p_lp = QPushButton("L+P")
        self.btn_p_gd = QPushButton("G+D")
        self.btn_p_top = QPushButton("Tylko gora")
        self.btn_p_clear = QPushButton("Reset")
        for btn in (self.btn_p4, self.btn_p_lp, self.btn_p_gd, self.btn_p_top, self.btn_p_clear):
            preset_row.addWidget(btn)
        lay.addLayout(preset_row)

        self.btn_p4.clicked.connect(lambda: self._preset(set(EDGE_SIDES_PL.keys())))
        self.btn_p_lp.clicked.connect(lambda: self._preset({"left", "right"}))
        self.btn_p_gd.clicked.connect(lambda: self._preset({"top", "bottom"}))
        self.btn_p_top.clicked.connect(lambda: self._preset({"top"}))
        self.btn_p_clear.clicked.connect(lambda: self._preset(set()))

        rows_lay.addStretch(1)

        btn_row = QHBoxLayout()
        self.btn_apply_sel = QPushButton("Zastosuj do zaznaczonych")
        self.btn_apply_shelves = QPushButton("Zastosuj do wszystkich polek")
        btn_row.addWidget(self.btn_apply_sel, 1)
        btn_row.addWidget(self.btn_apply_shelves, 1)
        lay.addLayout(btn_row)

        self.btn_apply_sel.clicked.connect(self.sig_apply_to_selected.emit)
        self.btn_apply_shelves.clicked.connect(self.sig_apply_to_all_shelves.emit)

        self.preview.sig_toggle_side.connect(self._toggle_side_from_preview)
        self.chk_all.stateChanged.connect(self._on_all_changed)
        self._sync_all_checkbox()

    def _edgeband_label(self, edgeband) -> str:
        label = str(getattr(edgeband, "name_pl", getattr(edgeband, "key", "")) or "")
        extras: list[str] = []
        manufacturer = str(getattr(edgeband, "manufacturer", "") or "").strip()
        band_type = str(getattr(edgeband, "edgeband_type", "") or "").strip()
        thickness = float(getattr(edgeband, "thickness_mm", 0.0) or 0.0)
        price = float(getattr(edgeband, "price_pln_per_m", 0.0) or 0.0)

        if manufacturer:
            extras.append(manufacturer)
        if band_type:
            extras.append(band_type)
        if extras:
            label += f" [{', '.join(extras)}]"
        if thickness > 0.0:
            label += f" ({thickness:g} mm)"
        if price > 0.0:
            label += f" - {price:.2f} zl/mb"
        return label

    def reload_catalog(self) -> None:
        current = self.get_edge_banding()
        edgebands = self._catalog.list_edgebands() or []
        self._default_edgeband_key_cache = next(
            (
                str(eb.key)
                for eb in edgebands
                if str(getattr(eb, "key", "") or "").strip().lower() != "brak"
            ),
            "Brak",
        )

        for _side_key, (_cb, combo) in self._rows.items():
            current_key = str(combo.currentData() or "Brak")
            combo.blockSignals(True)
            combo.clear()
            for edgeband in edgebands:
                combo.addItem(self._edgeband_label(edgeband), edgeband.key)
            idx = combo.findData(current_key)
            if idx < 0:
                idx = combo.findData("Brak")
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        self.load_edge_banding(current)

    def set_selected_count(self, n: int) -> None:
        self.lab_sel.setText(f"Zaznaczone: {max(1, int(n))}")

    def set_current_part(self, part_key: str, part_name_pl: str) -> None:
        self.lab_part.setText(f"Formatka: {part_name_pl}")
        self.preview.set_part_name(part_name_pl)

    def set_default_edgeband_key(self, key: str) -> None:
        normalized = str(key or "Brak").strip() or "Brak"
        self._default_edgeband_key_cache = normalized

    def get_default_edgeband_key(self) -> str:
        return self._default_edgeband_key()

    def _default_edgeband_key(self) -> str:
        key = str(getattr(self, "_default_edgeband_key_cache", "Brak") or "Brak").strip()
        return key or "Brak"

    def _ensure_default_edgeband_for_row(self, combo: QComboBox) -> None:
        current_key = str(combo.currentData() or "").strip()
        if current_key and current_key.lower() != "brak":
            return

        default_key = self._default_edgeband_key()
        idx = combo.findData(default_key)
        if idx < 0:
            idx = combo.findData("Brak")
        if idx < 0:
            return

        prev = combo.blockSignals(True)
        combo.setCurrentIndex(idx)
        combo.blockSignals(prev)

    def _preset(self, sides: set[str]) -> None:
        for side_key, (cb, combo) in self._rows.items():
            cb.blockSignals(True)
            cb.setChecked(side_key in sides)
            cb.blockSignals(False)
            combo.setEnabled(cb.isChecked())
            if cb.isChecked():
                self._ensure_default_edgeband_for_row(combo)

        self._sync_preview_from_rows()
        self._sync_all_checkbox()
        self.sig_changed.emit()

    def _on_all_changed(self, state: int) -> None:
        if state == 1:
            return
        want = state == 2
        self._preset(set(EDGE_SIDES_PL.keys()) if want else set())

    def _sync_all_checkbox(self) -> None:
        checked = sum(1 for _side, (cb, _combo) in self._rows.items() if cb.isChecked())
        total = len(self._rows)
        self.chk_all.blockSignals(True)
        if checked == 0:
            self.chk_all.setCheckState(Qt.CheckState.Unchecked)
        elif checked == total:
            self.chk_all.setCheckState(Qt.CheckState.Checked)
        else:
            self.chk_all.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_all.blockSignals(False)

    def load_edge_banding(self, edge_banding: Dict[str, str]) -> None:
        for side_key, (cb, combo) in self._rows.items():
            cb.blockSignals(True)
            combo.blockSignals(True)

            if side_key in edge_banding:
                cb.setChecked(True)
                combo.setEnabled(True)
                key = edge_banding.get(side_key, "Brak")
                idx = combo.findData(key)
                if idx < 0:
                    idx = combo.findData("Brak")
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                cb.setChecked(False)
                combo.setEnabled(False)
                idx0 = combo.findData("Brak")
                combo.setCurrentIndex(idx0 if idx0 >= 0 else 0)

            cb.blockSignals(False)
            combo.blockSignals(False)

        self._sync_preview_from_rows()
        self._sync_all_checkbox()

    def _sync_preview_from_rows(self) -> None:
        bands: dict[str, str] = {}
        labels: dict[str, str] = {}
        full_names: dict[str, str] = {}  # key -> pelna nazwa z combo
        for side, (cb, combo) in self._rows.items():
            if cb.isChecked():
                key = str(combo.currentData() or "").strip()
                if key:
                    bands[side] = key
                    if key not in labels:
                        labels[key] = key[:7]
                    if key not in full_names:
                        full_names[key] = combo.currentText()
        self.preview.set_edge_banding(bands, labels)
        self._update_legend(full_names)

    def _update_legend(self, full_names: dict[str, str]) -> None:
        if not full_names:
            self.lbl_legend.setText("")
            return
        parts: list[str] = []
        for key, name in full_names.items():
            color = _key_to_color(key)
            luma = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            fg = "#fff" if luma < 160 else "#e8efff"
            short = name[:30] + ("..." if len(name) > 30 else "")
            parts.append(
                f'<span style="background:{color.name()};color:{fg};'
                f'padding:1px 4px;border-radius:3px;">&nbsp;{short}&nbsp;</span>'
            )
        self.lbl_legend.setText("  ".join(parts))

    def _toggle_side_from_preview(self, side_key: str) -> None:
        if side_key not in self._rows:
            return
        cb, combo = self._rows[side_key]
        new_checked = not cb.isChecked()
        cb.blockSignals(True)
        cb.setChecked(new_checked)
        cb.blockSignals(False)
        combo.setEnabled(new_checked)
        if new_checked:
            self._ensure_default_edgeband_for_row(combo)
        self._sync_preview_from_rows()
        self._sync_all_checkbox()
        self.sig_changed.emit()

    def get_edge_banding(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for side_key, (cb, combo) in self._rows.items():
            if cb.isChecked():
                key = str(combo.currentData() or "Brak")
                out[side_key] = key if key else "Brak"
        return out
