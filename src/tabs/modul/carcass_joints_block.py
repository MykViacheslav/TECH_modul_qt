from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QVBoxLayout, QWidget


JOINT_TYPES_PL: Dict[str, str] = {
    "type1": "Wieńce między bokami",
    "type2": "Boki między wieńcami",
}

RAIL_MODES_PL: Dict[str, str] = {
    "full": "Pełna płyta (Wieniec)",
    "rails_h": "Listwy poziome (Trawersy)",
    "rails_v": "Listwy pionowe",
}


class CarcassJointsBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 1. Typ głównego łączenia
        self.cb_joint = QComboBox()
        for key, label in JOINT_TYPES_PL.items():
            self.cb_joint.addItem(label, key)
        self.cb_joint.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Typ korpusu", self.cb_joint)

        # 2. Tryb góry (Top Rail)
        self.cb_top_mode = QComboBox()
        for key, label in RAIL_MODES_PL.items():
            self.cb_top_mode.addItem(label, key)
        self.cb_top_mode.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Konstrukcja góry", self.cb_top_mode)

        # 3. Tryb dołu (Bottom Rail)
        self.cb_bottom_mode = QComboBox()
        for key, label in RAIL_MODES_PL.items():
            self.cb_bottom_mode.addItem(label, key)
        self.cb_bottom_mode.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Konstrukcja dołu", self.cb_bottom_mode)

        lay.addLayout(form)

    def set_values(self, joint: str, top_mode: str, bottom_mode: str) -> None:
        self.blockSignals(True)
        idx_j = self.cb_joint.findData(joint)
        self.cb_joint.setCurrentIndex(idx_j if idx_j >= 0 else 0)
        
        idx_t = self.cb_top_mode.findData(top_mode)
        self.cb_top_mode.setCurrentIndex(idx_t if idx_t >= 0 else 0)
        
        idx_b = self.cb_bottom_mode.findData(bottom_mode)
        self.cb_bottom_mode.setCurrentIndex(idx_b if idx_b >= 0 else 0)
        self.blockSignals(False)

    def get_values(self) -> Dict[str, str]:
        return {
            "carcass_joint_type": str(self.cb_joint.currentData() or "type1"),
            "carcass_top_mode": str(self.cb_top_mode.currentData() or "full"),
            "carcass_bottom_mode": str(self.cb_bottom_mode.currentData() or "full"),
        }
