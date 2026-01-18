from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QFrame

from .base import BaseTab
from .module_widget import ModuleWidget


class Tab(BaseTab):
    TAB_KEY = "module"
    TAB_TITLE_PL = "Moduł"

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(ctx, parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        card = QFrame()
        card.setObjectName("cardContainer")
        # styl karty jest też wspierany w ui/theme.py (QFrame#cardContainer)
        card.setStyleSheet("""
            QFrame#cardContainer {
                background: #F7F9FB;
                border: 1px solid #C5D0DF;
                border-radius: 14px;
            }
        """)
        root.addWidget(card, 1)

        cardL = QVBoxLayout(card)
        cardL.setContentsMargins(14, 14, 14, 14)
        cardL.setSpacing(10)

        self.mod = ModuleWidget(ctx)
        cardL.addWidget(self.mod, 1)

    def export_state(self) -> Dict[str, Any]:
        return {"title": self.TAB_TITLE_PL, "ready": True}
