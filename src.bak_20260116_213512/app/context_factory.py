from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QSettings


@dataclass
class FallbackBus:
    """Minimalny bus (placeholder)."""
    def emit(self, *_args, **_kwargs):  # compat-ish
        return None


@dataclass
class FallbackCatalogs:
    """Minimalne katalogi (placeholder)."""
    def get_materials(self): return []
    def get_edges(self): return []
    def get_fittings(self): return []


@dataclass
class FallbackCtx:
    settings: QSettings
    bus: object
    catalogs: object


def build_ctx():
    """
    Buduje ctx:
    - jeśli mamy core.app_context.AppContext + EventBus + CatalogStore -> użyj ich
    - jeśli jeszcze czegoś brakuje -> fallback, żeby Moduł dało się uruchomić jako tab
    """
    settings = QSettings("TECH_modul", "TECH_modul_qt")

    try:
        from core.app_context import AppContext
        from core.event_bus import EventBus
        from core.catalog_store import CatalogStore
        return AppContext(settings=settings, bus=EventBus(), catalogs=CatalogStore())
    except Exception:
        return FallbackCtx(settings=settings, bus=FallbackBus(), catalogs=FallbackCatalogs())
