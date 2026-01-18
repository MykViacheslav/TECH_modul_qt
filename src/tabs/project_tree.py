from __future__ import annotations
import json, os
from PySide6 import QtCore, QtWidgets

class ProjectTree(QtWidgets.QWidget):
    """
    Shared Project Tree (left panel).
    Shows:
      - Modules (from DB)
      - Materials (from DB)
      - Formatki (from ctx.state.active_module["formatki"])
    Double-click:
      - module    -> bus.module_load_requested(anchor)
      - material  -> bus.material_chosen(code) + copy to clipboard
      - formatka  -> bus.formatka_selected(id)
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.edFilter = QtWidgets.QLineEdit()
        self.edFilter.setPlaceholderText("Filter: module/material/formatka...")

        self.btnRefresh = QtWidgets.QPushButton("Refresh")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.edFilter, 1)
        top.addWidget(self.btnRefresh)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(top)
        lay.addWidget(self.tree, 1)

        self.btnRefresh.clicked.connect(self.reload)
        self.edFilter.textChanged.connect(self.apply_filter)
        self.tree.itemDoubleClicked.connect(self._on_double)

        # bus hooks
        bus = self._bus()
        if bus is not None:
            if hasattr(bus, "active_module_changed"):
                bus.active_module_changed.connect(lambda *_: self.reload())
            if hasattr(bus, "formatki_changed"):
                bus.formatki_changed.connect(self.reload)

        self._items_cache = []
        self._roots = {}

        self.reload()

    def _bus(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("bus", None)
            return getattr(self.ctx, "bus", None)
        except Exception:
            return None

    def _state(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("state", {})
            return getattr(self.ctx, "state", {})
        except Exception:
            return {}

    def _db_path(self) -> str:
        try:
            if isinstance(self.ctx, dict) and self.ctx.get("db_path"):
                return str(self.ctx["db_path"])
        except Exception:
            pass
        try:
            if self.ctx is not None and getattr(self.ctx, "db_path", None):
                return str(self.ctx.db_path)
        except Exception:
            pass
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src/tabs -> .../src
        proj = os.path.dirname(root)
        return os.path.join(proj, "data", "tech.db")

    def reload(self):
        self.tree.clear()
        self._items_cache = []

        root_modules = QtWidgets.QTreeWidgetItem(["Modules"])
        root_modules.setExpanded(True)
        root_materials = QtWidgets.QTreeWidgetItem(["Materials"])
        root_materials.setExpanded(True)
        root_formatki = QtWidgets.QTreeWidgetItem(["Formatki (aktywny modul)"])
        root_formatki.setExpanded(True)

        self.tree.addTopLevelItem(root_modules)
        self.tree.addTopLevelItem(root_materials)
        self.tree.addTopLevelItem(root_formatki)
        self._roots = {"modules": root_modules, "materials": root_materials, "formatki": root_formatki}

        # modules
        for o in self._load_modules():
            anchor = str(o.get("anchor",""))
            name = str(o.get("name",""))
            label = f"{anchor} | {name}".strip(" |")
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, ("module", anchor, o))
            root_modules.addChild(it)
            self._items_cache.append((it, label.lower()))

        # materials
        for o in self._load_materials():
            code = str(o.get("code",""))
            name = str(o.get("name",""))
            th = o.get("thickness_mm", None)
            ths = (f"{th:g}mm" if isinstance(th, (int,float)) else "")
            kind = str(o.get("kind",""))
            label = f"{code} | {name} | {kind} {ths}".strip()
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, ("material", code, o))
            root_materials.addChild(it)
            self._items_cache.append((it, label.lower()))

        # formatki from active module
        active = (self._state() or {}).get("active_module", {}) if isinstance(self._state(), dict) else {}
        fmt = active.get("formatki", []) if isinstance(active, dict) else []
        for o in (fmt or []):
            if not isinstance(o, dict):
                continue
            fid = str(o.get("id",""))
            name = str(o.get("name",""))
            mat  = str(o.get("material_code",""))
            label = f"{fid} | {name} | {mat}".strip(" |")
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, ("formatka", fid, o))
            root_formatki.addChild(it)
            self._items_cache.append((it, label.lower()))

        self.apply_filter()

    def apply_filter(self):
        q = (self.edFilter.text() or "").strip().lower()
        if not q:
            for it, _ in self._items_cache:
                it.setHidden(False)
        else:
            for it, s in self._items_cache:
                it.setHidden(q not in s)

        # hide roots if all hidden
        for root in self._roots.values():
            any_vis = False
            for i in range(root.childCount()):
                if not root.child(i).isHidden():
                    any_vis = True
                    break
            root.setHidden(not any_vis)

    def _on_double(self, item, _col):
        data = item.data(0, QtCore.Qt.UserRole)
        if not data:
            return
        kind, code, obj = data
        bus = self._bus()

        if kind == "module":
            if bus is not None and hasattr(bus, "module_load_requested"):
                bus.module_load_requested.emit(str(code))
        elif kind == "material":
            QtWidgets.QApplication.clipboard().setText(str(code))
            if bus is not None and hasattr(bus, "material_chosen"):
                bus.material_chosen.emit(str(code))
        elif kind == "formatka":
            if bus is not None and hasattr(bus, "formatka_selected"):
                bus.formatka_selected.emit(str(code))

    def _load_modules(self):
        try:
            from tools import module_db_cli
            con = module_db_cli.connect(self._db_path())
            module_db_cli.ensure_schema(con)
            rows = con.execute("SELECT payload_json FROM modules ORDER BY updated_at DESC LIMIT 500").fetchall()
            out = []
            for r in rows:
                try: out.append(json.loads(r["payload_json"]))
                except Exception: pass
            return out
        except Exception:
            return []

    def _load_materials(self):
        try:
            from tools import material_db_cli
            con = material_db_cli.connect(self._db_path())
            material_db_cli.ensure_schema(con)
            rows = con.execute("SELECT payload_json FROM materials ORDER BY updated_at DESC LIMIT 800").fetchall()
            out = []
            for r in rows:
                try: out.append(json.loads(r["payload_json"]))
                except Exception: pass
            return out
        except Exception:
            return []
