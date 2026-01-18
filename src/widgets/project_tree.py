from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from PySide6 import QtCore, QtWidgets


@dataclass
class TreePart:
    key: str
    name_pl: str
    a_mm: float
    b_mm: float
    thick_mm: float
    material: str = ""


class ProjectTreeWidget(QtWidgets.QWidget):
    """
    Simple 'project tree' for the module.
    Emits partSelected(key) when user clicks a part in the tree.
    """
    partSelected = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.itemClicked.connect(self._on_item_clicked)

        lay.addWidget(self.tree, 1)

        self._root_module = None
        self._root_parts = None

    def set_module(self, name: str, W: float, H: float, D: float, qty: int, parts: Dict[str, TreePart]) -> None:
        self.tree.blockSignals(True)
        try:
            self.tree.clear()

            mod_title = f"Модуль: {name or '—'}"
            self._root_module = QtWidgets.QTreeWidgetItem([mod_title])
            self.tree.addTopLevelItem(self._root_module)
            self._root_module.setExpanded(True)

            dims = QtWidgets.QTreeWidgetItem([f"W×H×D: {int(W)}×{int(H)}×{int(D)} мм"])
            dims.setFlags(dims.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
            self._root_module.addChild(dims)

            q = QtWidgets.QTreeWidgetItem([f"Qty: {int(qty)}"])
            q.setFlags(q.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
            self._root_module.addChild(q)

            self._root_parts = QtWidgets.QTreeWidgetItem(["Деталі (parts)"])
            self._root_module.addChild(self._root_parts)
            self._root_parts.setExpanded(True)

            # sort keys for stable order
            for key in sorted(parts.keys()):
                p = parts[key]
                title = f"{p.name_pl}  [{p.key}]"
                sub = f"{int(p.a_mm)}×{int(p.b_mm)}×{int(p.thick_mm)} мм"
                if p.material:
                    sub += f" | {p.material}"

                it = QtWidgets.QTreeWidgetItem([title])
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole, p.key)
                it2 = QtWidgets.QTreeWidgetItem([sub])
                it2.setFlags(it2.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)

                it.addChild(it2)
                it.setExpanded(False)
                self._root_parts.addChild(it)

            self.tree.expandItem(self._root_parts)
        finally:
            self.tree.blockSignals(False)

    def select_key(self, key: str) -> None:
        # best-effort: find and select the item with matching UserRole
        it = self._find_item_by_key(key)
        if it is not None:
            self.tree.setCurrentItem(it)

    def _find_item_by_key(self, key: str) -> Optional[QtWidgets.QTreeWidgetItem]:
        if not key:
            return None
        root_count = self.tree.topLevelItemCount()
        for i in range(root_count):
            top = self.tree.topLevelItem(i)
            found = self._scan(top, key)
            if found is not None:
                return found
        return None

    def _scan(self, node: QtWidgets.QTreeWidgetItem, key: str) -> Optional[QtWidgets.QTreeWidgetItem]:
        if node.data(0, QtCore.Qt.ItemDataRole.UserRole) == key:
            return node
        for i in range(node.childCount()):
            found = self._scan(node.child(i), key)
            if found is not None:
                return found
        return None

    def _on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, col: int) -> None:
        key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(key, str) and key:
            self.partSelected.emit(key)
