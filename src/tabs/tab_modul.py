from __future__ import annotations
from PySide6 import QtWidgets

from tabs.page_sciana import ScianaPage
from tabs.page_komplet_modulu import KompletModuluPage

class ModulTab(QtWidgets.QWidget):
    """
    TOP TAB: MODUL
    Inside: independent sub-tabs/pages:
      - Ściana
      - Komplet MODULU
    """

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        self.subtabs = QtWidgets.QTabWidget()
        root.addWidget(self.subtabs)

        self.subtabs.addTab(ScianaPage(ctx=ctx, parent=self), "Ściana")
        self.subtabs.addTab(KompletModuluPage(ctx=ctx, parent=self), "Komplet MODULU")
