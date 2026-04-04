from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QComboBox, QPushButton, QHBoxLayout
from src.domain.module_models import ModuleDef, PartDef
from src.storage.catalog_store_json import CatalogStoreJson
from src.core.costing.module_costs import calculate_module_cost_breakdown
from src.app.app_settings import load_drawing_settings
from src.tabs.modul.edge_banding_block import EDGE_SIDES_PL

if TYPE_CHECKING:
    pass


class BomBlock(QWidget):
    sig_material_changed = pyqtSignal(str)
    sig_material_reset_requested = pyqtSignal()

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog

        self._is_loading_material_editor = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.setStyleSheet("""
            QLabel {
                color: #1f2937;
            }
            QLabel[bom_meta="true"] {
                color: #64748b;
            }
        """)

        self.title = QLabel("BOM (wybierz element)")
        self.title.setStyleSheet("font-weight:700;")
        lay.addWidget(self.title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.v_name = QLabel("-")
        self.v_mat = QLabel("-")
        self.v_dims = QLabel("-")
        self.v_edge = QLabel("-")
        self.v_offsets = QLabel("-")
        for label in (self.v_name, self.v_mat, self.v_dims, self.v_edge, self.v_offsets):
            label.setProperty("bom_meta", True)

        self.form.addRow("Nazwa", self.v_name)
        self.form.addRow("Material", self.v_mat)
        self.form.addRow("Wymiary", self.v_dims)
        self.form.addRow("Oklejanie", self.v_edge)
        self.form.addRow("Offsety wiencow", self.v_offsets)

        self.cb_part_material = QComboBox()

        self.btn_reset_part_material = QPushButton("Reset do grupy")
        self.btn_reset_part_material.setEnabled(False)

        material_row = QWidget(self)
        material_row_lay = QHBoxLayout(material_row)
        material_row_lay.setContentsMargins(0, 0, 0, 0)
        material_row_lay.setSpacing(6)
        material_row_lay.addWidget(self.cb_part_material, 1)
        material_row_lay.addWidget(self.btn_reset_part_material, 0)

        self.form.addRow("Material detalu", material_row)

        lay.addLayout(self.form)

        self.sum_title = QLabel("Podsumowanie materialow (szt / m2 / zl)")
        self.sum_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.sum_title)

        self.v_sum = QLabel("-")
        self.v_sum.setWordWrap(True)
        self.v_sum.setProperty("bom_meta", True)
        lay.addWidget(self.v_sum)

        self.eb_title = QLabel("Podsumowanie okleiny (mb)")
        self.eb_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.eb_title)

        self.v_eb = QLabel("-")
        self.v_eb.setWordWrap(True)
        self.v_eb.setProperty("bom_meta", True)
        lay.addWidget(self.v_eb)

        self.hw_title = QLabel("Podsumowanie okuc (szt / kpl / zl)")
        self.hw_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.hw_title)

        self.v_hw = QLabel("-")
        self.v_hw.setWordWrap(True)
        self.v_hw.setProperty("bom_meta", True)
        lay.addWidget(self.v_hw)

        self.total_title = QLabel("Koszt modulu")
        self.total_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.total_title)

        self.v_total = QLabel("-")
        self.v_total.setWordWrap(True)
        self.v_total.setProperty("bom_meta", True)
        lay.addWidget(self.v_total)

        lay.addStretch(1)

        self._reload_catalog_cache()
        self.cb_part_material.currentIndexChanged.connect(self._emit_material_changed)
        self.btn_reset_part_material.clicked.connect(self.sig_material_reset_requested.emit)
        self.clear_part()

    def _reload_catalog_cache(self) -> None:
        materials = self._catalog.list_materials() or []
        self._mat_name = {m.key: m.name_pl for m in materials}
        self._mat_price = {}
        for material in materials:
            try:
                price = float(getattr(material, "price_pln_per_m2", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._mat_price[material.key] = price

        edgebands = self._catalog.list_edgebands() or []
        self._eb_name = {e.key: e.name_pl for e in edgebands}
        self._eb_price = {}
        for edgeband in edgebands:
            try:
                price = float(getattr(edgeband, "price_pln_per_m", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._eb_price[edgeband.key] = price

        hardware = self._catalog.list_hardware() or []
        self._hw_name = {item.key: item.name_pl for item in hardware}
        self._hw_price = {}
        for item in hardware:
            try:
                price = float(getattr(item, "price_pln", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._hw_price[item.key] = price

        current_key = str(self.cb_part_material.currentData() or "")
        self._is_loading_material_editor = True
        try:
            self.cb_part_material.clear()
            for material in materials:
                self.cb_part_material.addItem(self._material_combo_label(material), material.key)
            idx = self.cb_part_material.findData(current_key)
            if idx < 0 and self.cb_part_material.count() > 0:
                idx = 0
            if idx >= 0:
                self.cb_part_material.setCurrentIndex(idx)
        finally:
            self._is_loading_material_editor = False

    def reload_catalog(self) -> None:
        self._reload_catalog_cache()

    def _material_combo_label(self, material) -> str:
        label = f"{material.key} ({material.thickness_mm:g} mm) - {material.name_pl}"
        manufacturer = str(getattr(material, "manufacturer", "") or "").strip()
        material_type = str(getattr(material, "material_type", "") or "").strip()
        extras = [value for value in (manufacturer, material_type) if value]
        if extras:
            label += f" [{', '.join(extras)}]"
        price = float(getattr(material, "price_pln_per_m2", 0.0) or 0.0)
        if price > 0.0:
            label += f" - {price:.2f} zl/m2"
        return label

    def _emit_material_changed(self, _index: int) -> None:
        if self._is_loading_material_editor:
            return
        self.sig_material_changed.emit(str(self.cb_part_material.currentData() or ""))

    def _set_material_editor_state(
        self,
        material_key: str,
        default_material_key: str = "",
        enabled: bool = False,
        override_active: bool = False,
    ) -> None:
        self._is_loading_material_editor = True
        try:
            current_key = str(material_key or default_material_key or "").strip()
            idx = self.cb_part_material.findData(current_key)
            if idx < 0 and default_material_key:
                idx = self.cb_part_material.findData(default_material_key)
            if idx < 0 and self.cb_part_material.count() > 0:
                idx = 0
            if idx >= 0:
                self.cb_part_material.setCurrentIndex(idx)

            self.cb_part_material.setEnabled(bool(enabled))
            self.btn_reset_part_material.setEnabled(bool(enabled and override_active))

            tooltip = ""
            if default_material_key:
                tooltip = f"Domyslny z grupy: {default_material_key}"
            self.btn_reset_part_material.setToolTip(tooltip)
        finally:
            self._is_loading_material_editor = False

    def clear_part(self) -> None:
        self.v_name.setText("-")
        self.v_mat.setText("-")
        self.v_dims.setText("-")
        self.v_edge.setText("-")
        self.v_offsets.setText("-")
        self._set_material_editor_state("", enabled=False, override_active=False)

    def _material_label(self, key: str) -> str:
        name = self._mat_name.get(key, "")
        if not name or name == key:
            return key or "-"
        return f"{key} - {name}"

    def set_part(self, part: PartDef, default_material_key: str = "") -> None:
        current_material_key = str(part.material_key or default_material_key or "-")
        override_key = str(getattr(part, "material_override_key", "") or "").strip()

        self.v_name.setText(part.name_pl or "-")
        self.v_mat.setText(self._material_label(current_material_key))
        d = part.dims_mm or {}
        self.v_dims.setText(f'{d.get("w","-")} x {d.get("h","-")} x {d.get("t","-")} mm')

        eb = part.edge_banding or {}
        if not eb:
            self.v_edge.setText("-")
        else:
            chunks = []
            for side, key in eb.items():
                name_pl = self._eb_name.get(key, key)
                chunks.append(f'{EDGE_SIDES_PL.get(side, side)}={name_pl}')
            self.v_edge.setText(", ".join(chunks))

        self._set_material_editor_state(
            material_key=current_material_key,
            default_material_key=default_material_key,
            enabled=True,
            override_active=bool(override_key) or (
                bool(default_material_key) and current_material_key != default_material_key
            ),
        )

    def set_module(self, m: ModuleDef) -> None:
        vp = set(getattr(m, "visible_parts", set()) or set())
        top_offset_mm = float(getattr(m, "top_rail_offset_mm", 0.0) or 0.0)
        bottom_offset_mm = float(getattr(m, "bottom_rail_offset_mm", 0.0) or 0.0)

        top_txt = f"gora {top_offset_mm:.1f} mm" if "top" in vp else "gora: brak"
        bottom_txt = f"dol {bottom_offset_mm:.1f} mm" if "bottom" in vp else "dol: brak"
        self.v_offsets.setText(f"{top_txt}, {bottom_txt}")

        breakdown = calculate_module_cost_breakdown(
            m,
            self._catalog,
            auto_double_front_width_mm=float(load_drawing_settings().auto_double_front_width_mm or 600.0),
        )

        if not breakdown.material_lines:
            self.v_sum.setText("-")
        else:
            lines = []
            for line in breakdown.material_lines:
                if line.priced:
                    lines.append(f"{line.label}: {line.count} szt, {line.area_m2:.3f} m2, {line.cost_pln:.2f} zl")
                else:
                    lines.append(f"{line.label}: {line.count} szt, {line.area_m2:.3f} m2")
            if any(line.priced for line in breakdown.material_lines):
                lines.append(f"RAZEM: {breakdown.material_total_pln:.2f} zl")
            self.v_sum.setText("\n".join(lines))

        if not breakdown.edgeband_lines:
            self.v_eb.setText("-")
        else:
            lines = []
            for line in breakdown.edgeband_lines:
                if line.priced:
                    lines.append(f"{line.label}: {line.length_m:.2f} mb, {line.cost_pln:.2f} zl")
                else:
                    lines.append(f"{line.label}: {line.length_m:.2f} mb")
            if any(line.priced for line in breakdown.edgeband_lines):
                lines.append(f"RAZEM: {breakdown.edgeband_total_pln:.2f} zl")
            self.v_eb.setText("\n".join(lines))

        if not breakdown.hardware_lines:
            self.v_hw.setText("-")
        else:
            lines = []
            for line in breakdown.hardware_lines:
                qty = float(line.quantity or 0.0)
                qty_txt = str(int(qty)) if abs(qty - round(qty)) < 0.001 else f"{qty:.2f}"
                label = line.label
                if line.manufacturer:
                    label += f" [{line.manufacturer}]"
                note = f", {line.note}" if line.note else ""
                if line.priced:
                    lines.append(f"{label}: {qty_txt} {line.unit}, {line.cost_pln:.2f} zl{note}")
                else:
                    lines.append(f"{label}: {qty_txt} {line.unit}{note}")

            if breakdown.hardware_lines:
                lines.append(f"RAZEM: {breakdown.hardware_total_pln:.2f} zl")
            self.v_hw.setText("\n".join(lines) if lines else "-")

        total_lines = [
            f"Materialy: {breakdown.material_total_pln:.2f} zl",
            f"Okleina: {breakdown.edgeband_total_pln:.2f} zl",
            f"Okucia: {breakdown.hardware_total_pln:.2f} zl",
            f"RAZEM: {breakdown.grand_total_pln:.2f} zl",
        ]
        self.v_total.setText("\n".join(total_lines))
