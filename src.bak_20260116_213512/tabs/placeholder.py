from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel

from .base import BaseTab


class PlaceholderTab(BaseTab):
    TAB_KEY = "placeholder"
    TAB_TITLE_PL = "W budowie"

    def __init__(self, ctx, title: str, parent=None) -> None:
        super().__init__(ctx, parent)
        self.TAB_TITLE_PL = title

        layout = QVBoxLayout(self)
        h = QLabel(title)
        h.setStyleSheet("font-size: 18px; font-weight: 600; background: transparent;")
        layout.addWidget(h)

        txt = QLabel("Ta zakładka jest przygotowana w szkielecie. Logika i UI będą dodawane etapami.")
        txt.setWordWrap(True)
        txt.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(txt)

        layout.addStretch(1)

    def export_state(self) -> Dict[str, Any]:
        return {"title": self.TAB_TITLE_PL, "ready": False}
