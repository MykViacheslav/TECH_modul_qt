from __future__ import annotations

import traceback
from PySide6 import QtWidgets
from .base import BaseTab

class Tab(BaseTab):
    TAB_TITLE_PL = "Moduł"
    tab_title = "Moduł"
    tab_id = "module"

    def __init__(self, ctx=None, parent=None):
        super().__init__(ctx=ctx, parent=parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        try:
            from .module_widget import ModuleWidget

            # try both signatures (ctx or not)
            w = None
            try:
                w = ModuleWidget(ctx=ctx, parent=self)
            except TypeError:
                w = ModuleWidget(self)

            lay.addWidget(w)

        except Exception:
            box = QtWidgets.QTextEdit(self)
            box.setReadOnly(True)
            box.setPlainText("Module tab failed:\n\n" + traceback.format_exc())
            lay.addWidget(box)