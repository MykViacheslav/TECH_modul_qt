from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """
    Minimalny bus zdarzeń (pień komunikacji).
    Zakładki nie wołają się bezpośrednio – emitują sygnały / proszą o dane przez kontekst.
    """
    # Przykładowe sygnały (później rozszerzymy)
    data_changed = Signal(str)         # np. "materials", "employees"
    request_refresh = Signal(str)      # np. "summary"

    def __init__(self) -> None:
        super().__init__()
