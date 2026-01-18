from __future__ import annotations
from PySide6 import QtCore

class AppBus(QtCore.QObject):
    # existing (if you already had them, keep names the same)
    module_load_requested = QtCore.Signal(str)   # anchor
    material_chosen       = QtCore.Signal(str)   # material code
    refresh_requested     = QtCore.Signal(str)   # topic

    # NEW:
    active_module_changed = QtCore.Signal(str)   # anchor (or "")
    formatka_selected     = QtCore.Signal(str)   # formatka_id
    formatki_changed      = QtCore.Signal()      # notify trees/views to refresh
