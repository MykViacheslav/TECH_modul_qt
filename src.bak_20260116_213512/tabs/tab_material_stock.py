from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel
from .base import BaseTab


class Tab(BaseTab):
    TAB_KEY = "material_stock"
    TAB_TITLE_PL = "Stan materiałów"

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(ctx, parent)
        layout = QVBoxLayout(self)

        title = QLabel("Stan materiałów")
        title.setStyleSheet("font-size: 18px; font-weight: 600; background: transparent;")
        layout.addWidget(title)

        info = QLabel("Ile mamy materiału (magazyn/stan).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(info)

        layout.addStretch(1)

    def export_state(self) -> Dict[str, Any]:
        # Na razie minimalnie – później tu pójdą realne dane zakładki.
        return {
            "title": self.TAB_TITLE_PL,
            "ready": False
        }
