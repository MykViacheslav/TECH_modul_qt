from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QWidget
from core.app_context import AppContext


class BaseTab(QWidget):
    """
    Bazowa zakładka: niezależna.
    Jedyny kanał współpracy: ctx (kontekst) + export_state().
    """
    TAB_KEY: str = "base"
    TAB_TITLE_PL: str = "Zakładka"

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx

    def export_state(self) -> Dict[str, Any]:
        """
        Każda zakładka zwraca własny kawałek danych do pnia.
        Na razie zwracamy minimalnie.
        """
        return {"status": "ok"}
