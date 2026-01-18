from __future__ import annotations
from PySide6 import QtCore

class AppBus(QtCore.QObject):
    # Cross-tab communication (one level, no hierarchy)
    module_load_requested = QtCore.Signal(str)     # anchor
    module_saved          = QtCore.Signal(str)     # anchor
    modules_changed       = QtCore.Signal()        # generic refresh

    material_selected     = QtCore.Signal(str)     # code
    materials_changed     = QtCore.Signal()

    project_item_selected = QtCore.Signal(dict)    # {"type": "...", ...}
