from __future__ import annotations

from dataclasses import dataclass
from PySide6 import QtCore

@dataclass
class ModuleState:
    w: int = 600
    h: int = 720
    d: int = 560

    posL: int = 0
    posR: int = 0
    posT: int = 0
    posB: int = 0

    anchor: str = "NONE"

class ModuleStore(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self, state: ModuleState | None = None, parent=None):
        super().__init__(parent)
        self.state = state or ModuleState()

    def update(self, **kwargs):
        s = self.state
        dirty = False
        for k, v in kwargs.items():
            if not hasattr(s, k):
                continue
            if getattr(s, k) != v:
                setattr(s, k, v)
                dirty = True
        if dirty:
            self.changed.emit()