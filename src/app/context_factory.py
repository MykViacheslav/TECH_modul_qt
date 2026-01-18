from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QSettings

@dataclass
class AppContext:
    settings: QSettings

def build_ctx() -> AppContext:
    # minimal stable context for the app
    settings = QSettings("TECH_modul", "TECH_modul_qt")
    return AppContext(settings=settings)