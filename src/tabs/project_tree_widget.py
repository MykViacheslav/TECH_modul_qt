from __future__ import annotations
from typing import Any, Dict, Optional
from PySide6 import QtCore, QtGui, QtWidgets

from .project_tree_store import ProjectStore

class ProjectTreeWidget(QtWidgets.QWidget):
    """
    Reusable tree component.
    Uses ctx.project_store (shared) and ctx.bus for broadcasting selection.
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.store: Optional[ProjectStore] = self._get_store()
        self.bus = self._get_bus()

        self.edFilter = QtWidgets.QLineEdit()
        self.edFilter.setPlaceholderText("Szukaj w drzewie...")

        self.view = QtWidgets.QTreeView()
        self.view.setHeaderHidden(True)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.model = QtGui.QStandardItemModel()
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        try:
            self.proxy.setRecursiveFilteringEnabled(True)
        except Exception:
            pass
        self.proxy.setFilterKeyColumn(0)
        self.view.setModel(self.proxy)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6,6,6,6)
        lay.addWidget(self.edFilter)
        lay.addWidget(self.view, 1)

        self.edFilter.textChanged.connect(self.proxy.setFilterFixedString)

        if self.store is not None:
            self.store.ensure_loaded()
            self.store.changed.connect(self.rebuild)
            self.store.selection_changed.connect(self.on_store_selection)

        self.view.selectionModel().selectionChanged.connect(self.on_ui_selection)

        self.rebuild()

    def _get_bus(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("bus", None)
            return getattr(self.ctx, "bus", None)
        except Exception:
            return None

    def _get_store(self) -> Optional[ProjectStore]:
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("project_store", None)
            return getattr(self.ctx, "project_store", None)
        except Exception:
            return None

    def rebuild(self):
        self.model.clear()
        if self.store is None:
            it = QtGui.QStandardItem("Brak store")
            self.model.appendRow(it)
            return

        def add_node(parent_item, node: Dict[str, Any]):
            label = str(node.get("label") or node.get("id") or "???")
            typ = str(node.get("type") or "")
            if typ:
                label = f"{label}  [{typ}]"
            item = QtGui.QStandardItem(label)
            item.setData(node, QtCore.Qt.UserRole)
            parent_item.appendRow(item)

            for ch in node.get("children", []) or []:
                add_node(item, ch)

        roots = self.store.data.get("roots", []) or []
        for r in roots:
            add_node(self.model.invisibleRootItem(), r)

        self.view.expandAll()

        # apply current store selection
        if self.store.selected_id:
            self._select_by_id(self.store.selected_id)

    def _select_by_id(self, node_id: str):
        # find item recursively
        def find_item(parent, want):
            for i in range(parent.rowCount()):
                it = parent.child(i)
                node = it.data(QtCore.Qt.UserRole) or {}
                if str(node.get("id","")) == want:
                    return it
                got = find_item(it, want)
                if got is not None:
                    return got
            return None

        it = find_item(self.model.invisibleRootItem(), str(node_id))
        if it is None:
            return

        src_index = self.model.indexFromItem(it)
        proxy_index = self.proxy.mapFromSource(src_index)
        if proxy_index.isValid():
            self.view.setCurrentIndex(proxy_index)
            self.view.scrollTo(proxy_index)

    @QtCore.Slot(str)
    def on_store_selection(self, node_id: str):
        # store -> ui sync
        self._select_by_id(node_id)

    @QtCore.Slot()
    def on_ui_selection(self):
        if self.store is None:
            return
        idx = self.view.currentIndex()
        if not idx.isValid():
            return
        src = self.proxy.mapToSource(idx)
        it = self.model.itemFromIndex(src)
        node = it.data(QtCore.Qt.UserRole) if it else None
        if not isinstance(node, dict):
            return

        node_id = str(node.get("id",""))
        self.store.set_selected(node_id)

        # broadcast on bus
        if self.bus is not None and hasattr(self.bus, "project_node_selected"):
            try:
                self.bus.project_node_selected.emit(node)
            except Exception:
                pass

        # convenience: if clicked a module -> request load by anchor (non-intrusive)
        if self.bus is not None and hasattr(self.bus, "module_load_requested"):
            try:
                if str(node.get("type","")) == "module" and node.get("anchor"):
                    self.bus.module_load_requested.emit(str(node["anchor"]))
            except Exception:
                pass
