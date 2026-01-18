from __future__ import annotations

from PySide6 import QtWidgets
from tabs.module_proto.collapsible import CollapsibleSection
from tabs.module_proto.state import ModuleStore

class OffsetSection(QtWidgets.QWidget):
    def __init__(self, store: ModuleStore, parent=None):
        super().__init__(parent)
        self.store = store

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.sec = CollapsibleSection("Przesunięcia (offset)")
        root.addWidget(self.sec)

        frm = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(frm)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)

        self.posL = QtWidgets.QSpinBox(); self.posL.setRange(0, 2000)
        self.posR = QtWidgets.QSpinBox(); self.posR.setRange(0, 2000)
        self.posT = QtWidgets.QSpinBox(); self.posT.setRange(0, 2000)
        self.posB = QtWidgets.QSpinBox(); self.posB.setRange(0, 2000)

        self.btnZero = QtWidgets.QPushButton("Zeruj")

        g.addWidget(QtWidgets.QLabel("Left"),   0, 0); g.addWidget(self.posL, 0, 1)
        g.addWidget(QtWidgets.QLabel("Right"),  1, 0); g.addWidget(self.posR, 1, 1)
        g.addWidget(QtWidgets.QLabel("Top"),    2, 0); g.addWidget(self.posT, 2, 1)
        g.addWidget(QtWidgets.QLabel("Bottom"), 3, 0); g.addWidget(self.posB, 3, 1)
        g.addWidget(self.btnZero, 4, 0, 1, 2)

        self.sec.contentLayout.addWidget(frm)

        self._sync_from_store()
        self._wire()
        self.store.changed.connect(self._sync_from_store)

    def _wire(self):
        self.posL.valueChanged.connect(lambda v: self.store.update(posL=int(v)))
        self.posR.valueChanged.connect(lambda v: self.store.update(posR=int(v)))
        self.posT.valueChanged.connect(lambda v: self.store.update(posT=int(v)))
        self.posB.valueChanged.connect(lambda v: self.store.update(posB=int(v)))
        self.btnZero.clicked.connect(self._zero)

    def _zero(self):
        self.store.update(posL=0, posR=0, posT=0, posB=0)

    def _sync_from_store(self):
        s = self.store.state
        for sp, val in ((self.posL, s.posL), (self.posR, s.posR), (self.posT, s.posT), (self.posB, s.posB)):
            sp.blockSignals(True); sp.setValue(int(val)); sp.blockSignals(False)