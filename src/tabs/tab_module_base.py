from __future__ import annotations
import json
import os
from PySide6 import QtCore, QtWidgets

class ModuleBaseTab(QtWidgets.QWidget):
    """
    BAZA MODULU:
      - list/search modules from SQLite
      - emits bus.module_load_requested(anchor)
      - auto refresh on bus.modules_changed / bus.module_saved
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._items = []

        self.edSearch = QtWidgets.QLineEdit()
        self.edSearch.setPlaceholderText("Szukaj (anchor / name / materials)...")

        self.btnRefresh = QtWidgets.QPushButton("Odśwież")
        self.btnLoad = QtWidgets.QPushButton("Wczytaj do MODUL")
        self.btnCopy = QtWidgets.QPushButton("Kopiuj anchor")
        self.btnDelete = QtWidgets.QPushButton("Usuń")

        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.txt = QtWidgets.QPlainTextEdit()
        self.txt.setReadOnly(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.edSearch, 1)
        top.addWidget(self.btnRefresh)
        top.addWidget(self.btnLoad)
        top.addWidget(self.btnCopy)
        top.addWidget(self.btnDelete)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.list, 1)
        lay.addWidget(self.txt, 1)

        self.btnRefresh.clicked.connect(self.refresh)
        self.edSearch.textChanged.connect(lambda *_: self.refresh())
        self.list.currentRowChanged.connect(self.show_current)
        self.list.itemDoubleClicked.connect(lambda *_: self.load_to_modul())
        self.btnLoad.clicked.connect(self.load_to_modul)
        self.btnCopy.clicked.connect(self.copy_anchor)
        self.btnDelete.clicked.connect(self.delete_current)

        bus = self._bus()
        if bus is not None:
            if hasattr(bus, "modules_changed"):
                try: bus.modules_changed.connect(self.refresh)
                except Exception: pass
            if hasattr(bus, "module_saved"):
                try: bus.module_saved.connect(lambda *_: self.refresh())
                except Exception: pass

        self.refresh()

    def _bus(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("bus")
            return getattr(self.ctx, "bus", None)
        except Exception:
            return None

    def _db_path(self) -> str:
        try:
            if isinstance(self.ctx, dict) and self.ctx.get("db_path"):
                return str(self.ctx["db_path"])
        except Exception:
            pass
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src/tabs -> .../src
        proj = os.path.dirname(root)
        return os.path.join(proj, "data", "tech.db")

    def _load_list(self):
        from tools import module_db_cli
        con = module_db_cli.connect(self._db_path())
        module_db_cli.ensure_schema(con)
        rows = con.execute("SELECT payload_json FROM modules ORDER BY updated_at DESC LIMIT 800").fetchall()
        out = []
        for r in rows:
            try:
                out.append(json.loads(r["payload_json"]))
            except Exception:
                pass
        return out

    def refresh(self):
        q = (self.edSearch.text() or "").strip().lower()
        items = self._load_list()

        if q:
            def hit(o):
                s = " ".join([
                    str(o.get("anchor","")),
                    str(o.get("name","")),
                    str(o.get("materials","")),
                ]).lower()
                return q in s
            items = [o for o in items if hit(o)]

        self._items = items
        self.list.clear()
        for o in items:
            anchor = o.get("anchor","")
            name = o.get("name","")
            mats = o.get("materials","")
            label = f"{anchor}   | {name}   | {mats}"
            self.list.addItem(label)

        if items:
            self.list.setCurrentRow(0)
        else:
            self.txt.setPlainText("Brak wyników.")

    def _current_obj(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def show_current(self, *_):
        o = self._current_obj()
        if not o:
            self.txt.setPlainText("")
            return
        self.txt.setPlainText(json.dumps(o, ensure_ascii=False, indent=2))

    def load_to_modul(self):
        o = self._current_obj()
        if not o:
            return
        anchor = str(o.get("anchor","")).strip()
        if not anchor:
            return
        bus = self._bus()
        if bus is not None and hasattr(bus, "module_load_requested"):
            try:
                bus.module_load_requested.emit(anchor)
            except Exception:
                pass

    def copy_anchor(self):
        o = self._current_obj()
        if not o:
            return
        anchor = str(o.get("anchor",""))
        QtWidgets.QApplication.clipboard().setText(anchor)

    def delete_current(self):
        o = self._current_obj()
        if not o:
            return
        anchor = str(o.get("anchor","")).strip()
        if not anchor:
            return
        if QtWidgets.QMessageBox.question(self, "Usuń", f"Usunąć '{anchor}'?") != QtWidgets.QMessageBox.Yes:
            return
        from tools import module_db_cli
        con = module_db_cli.connect(self._db_path())
        module_db_cli.ensure_schema(con)
        con.execute("DELETE FROM modules WHERE anchor = ?", (anchor,))
        con.commit()
        bus = self._bus()
        if bus is not None and hasattr(bus, "modules_changed"):
            try: bus.modules_changed.emit()
            except Exception: pass
        self.refresh()
