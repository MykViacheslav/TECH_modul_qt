from __future__ import annotations
from PySide6 import QtWidgets

from tabs.page_modul_constructor import ModulConstructorPage

class ScianaPage(QtWidgets.QWidget):
    """
    KOMPLET -> Ściana
    Inside: Moduł (constructor + db save)
    """

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        self.subtabs = QtWidgets.QTabWidget()
        root.addWidget(self.subtabs)

        self.subtabs.addTab(ModulConstructorPage(ctx=ctx, parent=self), "Moduł (konstruktor)")
