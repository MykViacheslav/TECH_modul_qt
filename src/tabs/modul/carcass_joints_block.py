from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QVBoxLayout, QWidget


JOINT_TYPES_PL: Dict[str, str] = {
    "type1": "Typ 1: wience miedzy bokami",
    "type2": "Typ 2: boki miedzy wiencami",
}


class CarcassJointsBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_joint = QComboBox()
        for key, label in JOINT_TYPES_PL.items():
            self.cb_joint.addItem(label, key)

        self.cb_joint.currentIndexChanged.connect(self.sig_changed.emit)
        form.addRow("Typ laczenia", self.cb_joint)
        lay.addLayout(form)

    def set_value(self, joint_key: str) -> None:
        idx = self.cb_joint.findData(joint_key)
        self.cb_joint.blockSignals(True)
        self.cb_joint.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_joint.blockSignals(False)

    def get_value(self) -> str:
        return str(self.cb_joint.currentData() or "type1")
