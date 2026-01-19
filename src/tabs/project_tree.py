from __future__ import annotations
import json, os
from PySide6 import QtCore, QtWidgets

class ProjectTree(QtWidgets.QWidget):
    """
    Shared Project Tree (left panel).
    Shows:
      - Projects/Modules (from DB)
      - Active module -> Formatki (with Płyta + Okleina details)
      - Materials (from DB)
    Actions:
      - module double-click -> bus.module_load_requested(anchor)
      - material double-click -> bus.material_chosen(code) + copy to clipboard
      - formatka click -> bus.formatka_selected(id)
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
        self.tree.itemClicked.connect(self._on_click)
        self.tree.itemDoubleClicked.connect(self._on_double)

        # bus hooks
        bus = self._bus()
        if bus is not None:
            if hasattr(bus, "active_module_changed"):
                bus.active_module_changed.connect(lambda *_: self.reload())
            if hasattr(bus, "formatki_changed"):
                bus.formatki_changed.connect(self.reload)
            if hasattr(bus, "formatka_selected"):
                bus.formatka_selected.connect(self._select_formatka)

        self._items_cache = []
        self._roots = {}
        self._formatka_items = {}
        self._last_selected_formatka = ""

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
        self._formatka_items = {}

        root_projects = QtWidgets.QTreeWidgetItem(["PROJEKTY"])
        root_projects.setExpanded(True)
        root_materials = QtWidgets.QTreeWidgetItem(["MATERIAŁY (baza)"])
        root_materials.setExpanded(True)

        self.tree.addTopLevelItem(root_projects)
        self.tree.addTopLevelItem(root_materials)
        self._roots = {"projects": root_projects, "materials": root_materials}

        active = (self._state() or {}).get("active_module", {}) if isinstance(self._state(), dict) else {}
        active_anchor = str(active.get("anchor", "")) if isinstance(active, dict) else ""

        # modules (DB)
        for o in self._load_modules():
            anchor = str(o.get("anchor", ""))
            name = str(o.get("name", ""))
            label = f"{anchor} | {name}".strip(" |")
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, {"type": "module", "anchor": anchor, "module": o})
            root_projects.addChild(it)
            self._items_cache.append((it, label.lower()))

            if anchor and anchor == active_anchor:
                self._append_formatki_tree(it, active)

        # if no DB modules but active module exists, still show it
        if not root_projects.childCount() and active_anchor:
            it = QtWidgets.QTreeWidgetItem([active_anchor])
            it.setData(0, QtCore.Qt.UserRole, {"type": "module", "anchor": active_anchor, "module": active})
            root_projects.addChild(it)
            self._append_formatki_tree(it, active)

        # materials (DB)
        for o in self._load_materials():
            code = str(o.get("code", ""))
            name = str(o.get("name", ""))
            th = o.get("thickness_mm", None)
            ths = (f"{th:g}mm" if isinstance(th, (int, float)) else "")
            kind = str(o.get("kind", ""))
            label = f"{code} | {name} | {kind} {ths}".strip()
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, {"type": "material", "code": code, "material": o})
            root_materials.addChild(it)
            self._items_cache.append((it, label.lower()))

        self.apply_filter()
        if self._last_selected_formatka:
            self._select_formatka(self._last_selected_formatka)

    def _append_formatki_tree(self, module_item: QtWidgets.QTreeWidgetItem, active: dict):
        fmt = active.get("formatki", []) if isinstance(active, dict) else []
        for o in (fmt or []):
            if not isinstance(o, dict):
                continue
            fid = str(o.get("id", ""))
            name = str(o.get("name", ""))
            mat = str(o.get("material_code", ""))
            label = f"{fid} | {name}".strip(" |")
            fmt_item = QtWidgets.QTreeWidgetItem([label])
            fmt_item.setData(0, QtCore.Qt.UserRole, {"type": "formatka", "id": fid, "formatka": o})
            module_item.addChild(fmt_item)
            self._items_cache.append((fmt_item, f"{label} {mat}".lower()))
            self._formatka_items[fid] = fmt_item

            mat_label = f"Płyta: {mat}" if mat else "Płyta: (brak)"
            mat_item = QtWidgets.QTreeWidgetItem([mat_label])
            mat_item.setData(0, QtCore.Qt.UserRole, {"type": "formatka_material", "formatka_id": fid, "code": mat})
            fmt_item.addChild(mat_item)
            self._items_cache.append((mat_item, mat_label.lower()))

            edge = o.get("edge", {}) if isinstance(o.get("edge", {}), dict) else {}
            edge_label = self._edge_summary(edge)
            edge_item = QtWidgets.QTreeWidgetItem([edge_label])
            edge_item.setData(0, QtCore.Qt.UserRole, {"type": "formatka_edge", "formatka_id": fid, "edge": edge})
            fmt_item.addChild(edge_item)
            self._items_cache.append((edge_item, edge_label.lower()))

    def _edge_summary(self, edge: dict) -> str:
        names = []
        if edge.get("top"):
            names.append("góra")
        if edge.get("bottom"):
            names.append("dół")
        if edge.get("left"):
            names.append("lewa")
        if edge.get("right"):
            names.append("prawa")
        if not names:
            return "Okleina: (brak)"
        return "Okleina: " + ", ".join(names)

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

    def _select_formatka(self, fid: str):
        fid = str(fid or "").strip()
        if not fid:
            return
        self._last_selected_formatka = fid
        it = self._formatka_items.get(fid)
        if not it:
            return
        self.tree.setCurrentItem(it)
        self.tree.scrollToItem(it)

    def _on_click(self, item, _col):
        data = item.data(0, QtCore.Qt.UserRole) or {}
        if not isinstance(data, dict):
            return
        bus = self._bus()

        if data.get("type") == "formatka":
            if bus is not None and hasattr(bus, "formatka_selected"):
                bus.formatka_selected.emit(str(data.get("id", "")))
        elif data.get("type") in {"formatka_material", "formatka_edge"}:
            fid = str(data.get("formatka_id", ""))
            if fid and bus is not None and hasattr(bus, "formatka_selected"):
                bus.formatka_selected.emit(fid)
                self._select_formatka(fid)

    def _on_double(self, item, _col):
        data = item.data(0, QtCore.Qt.UserRole) or {}
        if not isinstance(data, dict):
            return
        bus = self._bus()

        if data.get("type") == "module":
            if bus is not None and hasattr(bus, "module_load_requested"):
                bus.module_load_requested.emit(str(data.get("anchor", "")))
        elif data.get("type") == "material":
            code = str(data.get("code", ""))
            if code:
                QtWidgets.QApplication.clipboard().setText(code)
            if bus is not None and hasattr(bus, "material_chosen"):
                bus.material_chosen.emit(code)

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
