from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QSpinBox, QWidget


class DividersBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        lay = QFormLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form = lay

        self.sp_count = QSpinBox()
        self.sp_count.setRange(0, 4)
        self.sp_count.setValue(0)

        self.cb_mount = QComboBox()
        self.cb_mount.addItem("Polki po LEWEJ stronie pionu", "left")
        self.cb_mount.addItem("Polki po PRAWEJ stronie pionu", "right")
        self.cb_mount.addItem("Polki po OBU stronach pionu", "both")
        self.cb_mount.setCurrentIndex(self.cb_mount.findData("right"))

        lay.addRow("Ilosc pionow", self.sp_count)
        lay.addRow("Polki", self.cb_mount)

        self.sp_count.valueChanged.connect(lambda _v: self.sig_changed.emit())
        self.cb_mount.currentIndexChanged.connect(lambda _i: self.sig_changed.emit())

    def get_count(self) -> int:
        return int(self.sp_count.value())

    def get_mount(self) -> str:
        return str(self.cb_mount.currentData() or "right")

    def set_mount_enabled(self, enabled: bool) -> None:
        if hasattr(self, "cb_mount"):
            self.cb_mount.setEnabled(bool(enabled))

    def set_values(self, count: int, mount: str) -> None:
        self.blockSignals(True)
        self.sp_count.setValue(int(count))
        idx = self.cb_mount.findData(str(mount))
        if idx < 0:
            idx = self.cb_mount.findData("right")
        self.cb_mount.setCurrentIndex(idx)
        self.blockSignals(False)
        self.sig_changed.emit()

    def set_enabled(self, enabled: bool) -> None:
        self.sp_count.setEnabled(bool(enabled))
        self.cb_mount.setEnabled(bool(enabled))
