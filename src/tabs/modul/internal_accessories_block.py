from __future__ import annotations

from typing import Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, 
    QCheckBox, QLabel, QFrame
)

class InternalAccessoriesBlock(QWidget):
    """
    UI block for wardrobe accessories like hanging rods, internal drawers, and LED.
    Integrated into the 'Wnętrze' (Interior) tab.
    """
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("AKCESORIA WEWNĘTRZNE")
        title.setStyleSheet("font-weight: 700; color: #64748b; font-size: 10px; margin-top: 8px;")
        lay.addWidget(title)

        frame = QFrame()
        frame.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        form = QFormLayout(frame)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sp_rods = QSpinBox()
        self.sp_rods.setRange(0, 5)
        self.sp_rods.setSuffix(" szt")
        self.sp_rods.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Drążki ubraniowe", self.sp_rods)

        self.sp_int_drawers = QSpinBox()
        self.sp_int_drawers.setRange(0, 10)
        self.sp_int_drawers.setSuffix(" szt")
        self.sp_int_drawers.valueChanged.connect(self.sig_changed.emit)
        form.addRow("Szuflady wew.", self.sp_int_drawers)

        self.chk_led = QCheckBox("Oświetlenie LED")
        self.chk_led.toggled.connect(self.sig_changed.emit)
        form.addRow("", self.chk_led)

        lay.addWidget(frame)
        lay.addStretch()

    def set_values(self, data: Dict[str, Any]) -> None:
        self.blockSignals(True)
        self.sp_rods.setValue(int(data.get("hanging_rods_count", 0)))
        self.sp_int_drawers.setValue(int(data.get("internal_drawers_count", 0)))
        self.chk_led.setChecked(bool(data.get("led_lighting_active", False)))
        self.blockSignals(False)

    def get_values(self) -> Dict[str, Any]:
        return {
            "hanging_rods_count": int(self.sp_rods.value()),
            "internal_drawers_count": int(self.sp_int_drawers.value()),
            "led_lighting_active": bool(self.chk_led.isChecked()),
        }
