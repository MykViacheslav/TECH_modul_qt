from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget


PARTS_PL: Dict[str, str] = {
    "side_left": "Bok lewy",
    "side_right": "Bok prawy",
    "top": "Wieniec gorny",
    "bottom": "Wieniec dolny",
    "shelf": "Polka",
    "back": "Plecy",
    "front": "Front",
    "divider": "Pion",
}


class VisiblePartsBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setMinimumHeight(150)
        self.setMaximumHeight(220)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.chk: Dict[str, QCheckBox] = {}

        order = [
            "side_left",
            "side_right",
            "top",
            "bottom",
            "shelf",
            "back",
            "front",
            "divider",
        ]

        for key in order:
            label = PARTS_PL.get(key, key)
            cb = QCheckBox(label)
            cb.stateChanged.connect(self.sig_changed.emit)
            self.chk[key] = cb
            lay.addWidget(cb)

        lay.addStretch(1)

    def set_checked(self, visible_parts: set[str]) -> None:
        for key, cb in self.chk.items():
            cb.blockSignals(True)
            cb.setChecked(key in visible_parts)
            cb.blockSignals(False)

    def get_visible_parts(self) -> set[str]:
        return {k for k, cb in self.chk.items() if cb.isChecked()}

    def set_part_checked(self, key: str, checked: bool) -> None:
        cb = self.chk.get(str(key))
        if cb is None:
            return
        cb.blockSignals(True)
        cb.setChecked(bool(checked))
        cb.blockSignals(False)

    def set_part_enabled(self, key: str, enabled: bool) -> None:
        cb = self.chk.get(str(key))
        if cb is None:
            return
        cb.setEnabled(bool(enabled))

    def is_part_enabled(self, key: str) -> bool:
        cb = self.chk.get(str(key))
        if cb is None:
            return False
        return bool(cb.isEnabled())

    def is_part_checked(self, key: str) -> bool:
        cb = self.chk.get(str(key))
        if cb is None:
            return False
        return bool(cb.isChecked())
