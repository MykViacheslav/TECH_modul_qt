from __future__ import annotations

from typing import Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QVBoxLayout, QWidget, 
    QDoubleSpinBox, QCheckBox, QLabel
)
from src.storage.catalog_store_json import CatalogStoreJson
from src.core.rules.drawers import DRAWER_SYSTEMS
from PyQt6.QtWidgets import QSpinBox

LEG_TYPES_PL: Dict[str, str] = {
    "plastic_std": "Plastikowe regulowane (std)",
    "furniture_metal": "Metalowe ozdobne",
    "plinth_brackets": "Zaczepy cokołu (bez nóżek)",
}

class HardwareBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # --- SEKCIJA: ZAWIASY ---
        self.lab_hinges = QLabel("ZAWIASY")
        self.lab_hinges.setStyleSheet("font-weight: 700; color: #64748b; font-size: 10px;")
        form.addRow(self.lab_hinges)
        
        self.cb_hinge_vendor = QComboBox()
        form.addRow("Producent", self.cb_hinge_vendor)

        # --- SEKCIJA: SZUFLADY ---
        self.lab_drawers = QLabel("SZUFLADY")
        self.lab_drawers.setStyleSheet("font-weight: 700; color: #64748b; font-size: 10px; margin-top: 8px;")
        form.addRow(self.lab_drawers)

        self.cb_drawer_vendor = QComboBox()
        form.addRow("System", self.cb_drawer_vendor)

        self.sp_drawer_count = QSpinBox()
        self.sp_drawer_count.setRange(0, 10)
        self.sp_drawer_count.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Ilość szuflad", self.sp_drawer_count)

        self.chk_tipon = QCheckBox("TIP-ON / Push-to-open")
        self.chk_tipon.toggled.connect(self.sig_changed.emit)
        form.addRow("", self.chk_tipon)

        # --- SEKCIJA: NÓŻKI ---
        self.lab_legs = QLabel("NÓŻKI I PODPARCIE")
        self.lab_legs.setStyleSheet("font-weight: 700; color: #64748b; font-size: 10px; margin-top: 8px;")
        form.addRow(self.lab_legs)

        self.cb_leg_type = QComboBox()
        for key, label in LEG_TYPES_PL.items():
            self.cb_leg_type.addItem(label, key)
        self.cb_leg_type.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Typ podparcia", self.cb_leg_type)

        self.sp_leg_h = QDoubleSpinBox()
        self.sp_leg_h.setRange(0, 300)
        self.sp_leg_h.setSuffix(" mm")
        self.sp_leg_h.setValue(100.0)
        self.sp_leg_h.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Wysokość nóżek", self.sp_leg_h)

        lay.addLayout(form)
        self._reload_vendors()
        
        self.cb_hinge_vendor.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_drawer_vendor.currentIndexChanged.connect(self.sig_changed.emit)

    def _reload_vendors(self) -> None:
        # HINGES
        h_vendors = list(self._catalog.list_hardware_manufacturers(category="hinge") or ["generic", "blum", "hettich"])
        self.cb_hinge_vendor.clear()
        for v in h_vendors:
            self.cb_hinge_vendor.addItem(str(v).capitalize(), str(v).lower())
        
        # DRAWERS (Zintegrowane z DRAWER_SYSTEMS)
        self.cb_drawer_vendor.clear()
        for sys_id, sys_def in DRAWER_SYSTEMS.items():
            self.cb_drawer_vendor.addItem(sys_def.name, sys_id)
        
        # Fallback if catalog has more
        d_vendors = list(self._catalog.list_hardware_manufacturers(category="drawer_system") or [])
        for v in d_vendors:
             if self.cb_drawer_vendor.findData(v) < 0:
                 self.cb_drawer_vendor.addItem(str(v).capitalize(), str(v).lower())

    def set_values(self, data: Dict[str, Any]) -> None:
        self.blockSignals(True)
        idx_h = self.cb_hinge_vendor.findData(str(data.get("hinge_vendor", "generic")))
        self.cb_hinge_vendor.setCurrentIndex(idx_h if idx_h >= 0 else 0)
        
        idx_d = self.cb_drawer_vendor.findData(str(data.get("drawer_vendor", "blum_antaro")))
        self.cb_drawer_vendor.setCurrentIndex(idx_d if idx_d >= 0 else 0)
        
        self.sp_drawer_count.setValue(int(data.get("drawer_count", 3)))
        self.chk_tipon.setChecked(bool(data.get("drawer_tip_on", False)))
        
        idx_l = self.cb_leg_type.findData(str(data.get("leg_type", "plastic_std")))
        self.cb_leg_type.setCurrentIndex(idx_l if idx_l >= 0 else 0)
        
        self.sp_leg_h.setValue(float(data.get("legs_height_mm", 100.0)))
        self.blockSignals(False)

    def get_values(self) -> Dict[str, Any]:
        return {
            "hinge_vendor": str(self.cb_hinge_vendor.currentData() or "generic"),
            "drawer_vendor": str(self.cb_drawer_vendor.currentData() or "blum_antaro"),
            "drawer_count": int(self.sp_drawer_count.value()),
            "drawer_tip_on": bool(self.chk_tipon.isChecked()),
            "leg_type": str(self.cb_leg_type.currentData() or "plastic_std"),
            "legs_height_mm": float(self.sp_leg_h.value()),
        }
