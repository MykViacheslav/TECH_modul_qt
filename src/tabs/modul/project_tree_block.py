from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from src.domain.module_models import ModuleDef


class ProjectTreeBlock(QWidget):
    sig_selected_part = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(240)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumHeight(120)
        self.tree.setMaximumHeight(180)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        lay.addWidget(self.tree, 0)
        lay.addStretch(1)

        self.tree.itemSelectionChanged.connect(self._emit_selection)

        self._root = QTreeWidgetItem(["Modul"])
        self.tree.addTopLevelItem(self._root)

        self._items: Dict[str, QTreeWidgetItem] = {}

    def rebuild_from_module(self, m: ModuleDef) -> None:
        self.tree.blockSignals(True)
        self._root.takeChildren()
        self._items.clear()

        base = ["side_left", "side_right", "top", "bottom", "back", "front", "divider"]
        shelf_keys = sorted(
            [k for k in (m.parts or {}).keys() if k.startswith("shelf_")],
            key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 999,
        )

        keys = [k for k in base if k in (m.parts or {})] + shelf_keys
        rest = [k for k in (m.parts or {}).keys() if k not in keys]
        keys += sorted(rest)

        for key in keys:
            part = m.parts.get(key)
            if not part:
                continue
            it = QTreeWidgetItem([part.name_pl])
            it.setData(0, Qt.ItemDataRole.UserRole, key)
            self._root.addChild(it)
            self._items[key] = it

        self.tree.expandAll()
        self.tree.blockSignals(False)

    def selected_part_keys(self) -> list[str]:
        out: list[str] = []
        for it in self.tree.selectedItems():
            key = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(key, str) and key:
                out.append(key)

        seen: set[str] = set()
        uniq: list[str] = []
        for key in out:
            if key not in seen:
                uniq.append(key)
                seen.add(key)
        return uniq

    def select_part(self, part_key: str) -> None:
        it = self._items.get(part_key)
        if it is None:
            return
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        it.setSelected(True)
        self.tree.setCurrentItem(it)
        self.tree.blockSignals(False)

    def toggle_part(self, part_key: str) -> None:
        it = self._items.get(part_key)
        if it is None:
            return

        self.tree.blockSignals(True)
        selected_before = self.tree.selectedItems()
        is_selected = it.isSelected()
        if is_selected and len(selected_before) <= 1:
            self.tree.setCurrentItem(it)
            self.tree.blockSignals(False)
            return

        it.setSelected(not is_selected)
        self.tree.setCurrentItem(it)
        self.tree.blockSignals(False)

    def _emit_selection(self) -> None:
        cur = self.tree.currentItem()
        if cur is None:
            items = self.tree.selectedItems()
            cur = items[0] if items else None
        if cur is None:
            return

        key = cur.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(key, str) and key:
            self.sig_selected_part.emit(key)
