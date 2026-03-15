from __future__ import annotations

# ==========================================================
# KOMPATYBILNOSC WSTECZNA
# ----------------------------------------------------------
# Ten modul istnieje tylko po to, zeby stary import:
#     from src.core.drawing_settings import ...
# dalej dzialal po przeniesieniu ustawien do:
#     src.app.app_settings
# ==========================================================

from src.app.app_settings import (
    DrawingSettings,
    load_drawing_settings,
    save_drawing_settings,
)

__all__ = [
    "DrawingSettings",
    "load_drawing_settings",
    "save_drawing_settings",
]