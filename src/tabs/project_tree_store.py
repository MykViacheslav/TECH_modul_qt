from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6 import QtCore

def project_root() -> Path:
    # .../src/tabs -> .../
    return Path(__file__).resolve().parents[2]

def default_tree_path() -> Path:
    return project_root() / "data" / "project_tree.json"

def _now_version() -> int:
    return 1

def _default_tree() -> Dict[str, Any]:
    # minimal starter tree
    return {
        "version": _now_version(),
        "roots": [
            {
                "id": "ROOT_PROJECTS",
                "type": "folder",
                "label": "PROJEKTY",
                "children": [
                    {
                        "id": "PRJ001",
                        "type": "project",
                        "label": "PRJ001",
                        "children": [
                            {
                                "id": "MOD_M01",
                                "type": "module",
                                "label": "M01",
                                "anchor": "M01",
                                "children": []
                            }
                        ]
                    }
                ]
            }
        ]
    }

@dataclass
class ProjectStore(QtCore.QObject):
    """
    Shared store for project tree.
    Every tab gets its own tree widget, but all widgets share the same store instance.
    """
    changed = QtCore.Signal()
    selection_changed = QtCore.Signal(str)

    tree_path: Path = field(default_factory=default_tree_path)
    data: Dict[str, Any] = field(default_factory=dict)
    selected_id: str = ""

    def __post_init__(self):
        super().__init__()

    def ensure_loaded(self):
        if not self.data:
            self.load()

    def load(self):
        p = self.tree_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            self.data = _default_tree()
            self.save()
            self.changed.emit()
            return

        try:
            self.data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            self.data = _default_tree()
            self.save()

        # ensure keys exist
        if "roots" not in self.data:
            self.data = _default_tree()

        self.changed.emit()

    def save(self):
        p = self.tree_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def set_selected(self, node_id: str):
        node_id = str(node_id or "").strip()
        if node_id == self.selected_id:
            return
        self.selected_id = node_id
        self.selection_changed.emit(self.selected_id)

    def iter_nodes(self):
        self.ensure_loaded()
        def walk(node):
            yield node
            for ch in node.get("children", []) or []:
                yield from walk(ch)
        for r in self.data.get("roots", []) or []:
            yield from walk(r)

    def find_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        node_id = str(node_id or "").strip()
        if not node_id:
            return None
        for n in self.iter_nodes():
            if str(n.get("id", "")) == node_id:
                return n
        return None
