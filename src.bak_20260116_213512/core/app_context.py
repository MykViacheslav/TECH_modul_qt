from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QSettings
from .event_bus import EventBus


from .catalog_store import CatalogStore
@dataclass
class AppContext:
    """
    Wspólny kontekst aplikacji (DI-lite).
    Tu później podłączymy: repozytoria (DB/JSON), serwisy, cache, itp.
    """
    settings: QSettings
    bus: EventBus

    catalogs: CatalogStore
    # przyszłe miejsca:
    # repos: Repositories
    # services: Services



