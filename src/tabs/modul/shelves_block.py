from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QSpinBox, QVBoxLayout, QWidget


class ShelvesBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sp_count = QSpinBox()
        self.sp_count.setRange(0, 10)
        self.sp_count.setValue(1)

        form.addRow("Liczba polek", self.sp_count)
        lay.addLayout(form)

        self.sp_count.valueChanged.connect(lambda _v: self.sig_changed.emit())

    def set_value(self, n: int) -> None:
        self.sp_count.blockSignals(True)
        self.sp_count.setValue(max(0, int(n)))
        self.sp_count.blockSignals(False)

    def get_value(self) -> int:
        return int(self.sp_count.value())

    def set_enabled(self, on: bool) -> None:
        self.setEnabled(bool(on))
