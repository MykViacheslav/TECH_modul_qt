from __future__ import annotations

from typing import Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QVBoxLayout, QWidget, 
    QDoubleSpinBox
)

BACK_MODES_PL: Dict[str, str] = {
    "overlay": "Plecy nakładane (od tyłu)",
    "insert": "Plecy wpuszczane (między bokami)",
    "recess": "Plecy w nucie (frezowane)",
}

class BackWallBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 1. Tryb montażu
        self.cb_mode = QComboBox()
        for key, label in BACK_MODES_PL.items():
            self.cb_mode.addItem(label, key)
        self.cb_mode.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Montaż pleców", self.cb_mode)

        # 2. Głębokość nutu / osadzenia
        self.sp_recess = QDoubleSpinBox()
        self.sp_recess.setRange(0, 100)
        self.sp_recess.setSuffix(" mm")
        self.sp_recess.setValue(18.0)
        self.sp_recess.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Odsunięcie/Nicie", self.sp_recess)

        # 3. Luz / Redukcja wymiaru
        self.sp_clearance = QDoubleSpinBox()
        self.sp_clearance.setRange(0, 20)
        self.sp_clearance.setSuffix(" mm")
        self.sp_clearance.setValue(0.0)
        self.sp_clearance.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Luz obwodowy", self.sp_clearance)

        lay.addLayout(form)

    def set_values(self, mode: str, recess: float, clearance: float) -> None:
        self.blockSignals(True)
        idx = self.cb_mode.findData(mode)
        self.cb_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self.sp_recess.setValue(recess)
        self.sp_clearance.setValue(clearance)
        self.blockSignals(False)

    def get_values(self) -> Dict[str, Any]:
        return {
            "back_mounting_mode": str(self.cb_mode.currentData() or "insert"),
            "back_recess_depth_mm": float(self.sp_recess.value()),
            "back_clearance_mm": float(self.sp_clearance.value()),
        }
