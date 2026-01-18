from __future__ import annotations
import os, sqlite3, json, re
from PySide6 import QtCore, QtWidgets

def _default_db_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proj = os.path.dirname(root)
    return os.path.join(proj, "data", "tech.db")

class MaterialQuery(QtWidgets.QWidget):
    """
    MaterialQuery v2:
      - text field (still works)
      - internal stack: list of {"code","name","kind","thickness_mm"}
      - editor dialog to build stack
      - total_thickness_mm() sums known thicknesses
    """
    valueChanged = QtCore.Signal(str)

    def __init__(self, db_path: str | None = None, parent=None):
        super().__init__(parent)
        self._db_path = db_path or _default_db_path()
        self._stack = []  # list[dict]
        self._items = []

        self.edit = QtWidgets.QLineEdit()
        self.edit.setPlaceholderText("Materiał (np. MDF18 + HPL09)")

        self.lbl = QtWidgets.QLabel("")
        self.lbl.setMinimumWidth(140)

        self.btnPick = QtWidgets.QToolButton()
        self.btnPick.setText("...")

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.lbl)
        lay.addWidget(self.btnPick)

        self.model = QtCore.QStringListModel(self)
        self.completer = QtWidgets.QCompleter(self.model, self)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completer.setFilterMode(QtCore.Qt.MatchContains)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.edit.setCompleter(self.completer)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(180)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._refresh_suggestions)

        self.edit.textEdited.connect(self._on_text_edited)
        self.edit.textChanged.connect(lambda t: self.valueChanged.emit(t))
        self.completer.activated.connect(self._on_activated)
        self.btnPick.clicked.connect(self._open_stack_editor)

        self._refresh_suggestions()
        self._update_label()

    def setDbPath(self, path: str):
        self._db_path = path
        self._refresh_suggestions()
        self._update_label()

    def text(self) -> str:
        return self.edit.text()

    def setText(self, text: str):
        self.edit.setText(text or "")
        # try rebuild stack from text
        self._stack = self._parse_text_to_stack(self.edit.text())
        self._timer.start()
        self._update_label()

    def stack(self) -> list:
        return list(self._stack)

    def setStack(self, stack: list):
        self._stack = []
        if isinstance(stack, list):
            for o in stack:
                if isinstance(o, dict) and o.get("code"):
                    self._stack.append({
                        "code": str(o.get("code","")).strip(),
                        "name": str(o.get("name","")).strip(),
                        "kind": str(o.get("kind","")).strip() or "board",
                        "thickness_mm": o.get("thickness_mm", None),
                    })
        self.edit.setText(self._stack_to_text(self._stack))
        self._update_label()

    def total_thickness_mm(self) -> float:
        s = 0.0
        for o in self._stack:
            th = o.get("thickness_mm", None)
            try:
                if th is not None:
                    s += float(th)
            except Exception:
                pass
        return float(s)

    def _update_label(self):
        if not self._stack:
            self.lbl.setText("")
            return
        th = self.total_thickness_mm()
        self.lbl.setText(f"Suma: {th:g} mm")

    def _connect(self):
        con = sqlite3.connect(self._db_path)
        con.row_factory = sqlite3.Row
        return con

    def _ensure_schema_exists(self) -> bool:
        try:
            con = self._connect()
            try:
                r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materials'").fetchone()
                return bool(r)
            finally:
                con.close()
        except Exception:
            return False

    def _query(self, q: str, limit: int = 20):
        if not self._ensure_schema_exists():
            return []
        q = (q or "").strip()
        like = f"%{q}%"
        try:
            con = self._connect()
            try:
                if not q:
                    rows = con.execute(
                        "SELECT code, name, kind, thickness_mm FROM materials ORDER BY updated_at DESC LIMIT ?",
                        (limit,)
                    ).fetchall()
                else:
                    rows = con.execute(
                        """
                        SELECT code, name, kind, thickness_mm
                        FROM materials
                        WHERE code LIKE ? OR name LIKE ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                        """,
                        (like, like, limit)
                    ).fetchall()
                out = []
                for r in rows:
                    out.append({
                        "code": r["code"],
                        "name": r["name"],
                        "kind": r["kind"],
                        "thickness_mm": r["thickness_mm"],
                    })
                return out
            finally:
                con.close()
        except Exception:
            return []

    def _refresh_suggestions(self):
        q = self.edit.text()
        self._items = self._query(q, limit=30)
        labels = []
        for o in self._items:
            th = o.get("thickness_mm", None)
            ths = "" if th is None else f"{th:g}mm"
            labels.append(f"{o.get('code','')} | {o.get('name','')} | {o.get('kind','')} | {ths}")
        self.model.setStringList(labels)

    def _on_text_edited(self, *_):
        # user typed -> rebuild stack from text (best effort)
        self._stack = self._parse_text_to_stack(self.edit.text())
        self._timer.start()
        self._update_label()

    def _on_activated(self, text: str):
        code = (text or "").split("|")[0].strip()
        if code:
            self.edit.setText(code)
            self._stack = self._parse_text_to_stack(code)
            self.valueChanged.emit(code)
            self._update_label()

    def _parse_text_to_stack(self, text: str) -> list:
        t = (text or "").strip()
        if not t:
            return []
        # split by + (allow spaces)
        parts = [p.strip() for p in re.split(r"\s*\+\s*", t) if p.strip()]
        if not parts:
            return []
        # lookup each code in DB
        items = []
        for code in parts:
            hit = None
            for o in self._query(code, limit=10):
                if str(o.get("code","")).strip().upper() == code.strip().upper():
                    hit = o
                    break
            if hit is None:
                items.append({"code": code, "name":"", "kind":"board", "thickness_mm": None})
            else:
                items.append({
                    "code": str(hit.get("code","")).strip(),
                    "name": str(hit.get("name","")).strip(),
                    "kind": str(hit.get("kind","")).strip() or "board",
                    "thickness_mm": hit.get("thickness_mm", None),
                })
        return items

    def _stack_to_text(self, stack: list) -> str:
        return " + ".join([str(o.get("code","")).strip() for o in stack if o.get("code")])

    def _open_stack_editor(self):
        # legacy entrypoint (kept for compatibility)
        self._open_stack_editor()

    def _open_stack_editor(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Material Stack (warstwy)")
        dlg.resize(780, 520)

        # left: search + results
        ed = QtWidgets.QLineEdit()
        ed.setPlaceholderText("Szukaj materiał (code lub name)...")
        lstRes = QtWidgets.QListWidget()

        # middle: stack
        lstStack = QtWidgets.QListWidget()

        # right: details
        txt = QtWidgets.QPlainTextEdit()
        txt.setReadOnly(True)

        btnAdd = QtWidgets.QPushButton("Dodaj ->")
        btnRem = QtWidgets.QPushButton("<- Usuń")
        btnUp  = QtWidgets.QPushButton("Góra")
        btnDn  = QtWidgets.QPushButton("Dół")

        btnOk = QtWidgets.QPushButton("OK")
        btnCancel = QtWidgets.QPushButton("Anuluj")

        left = QtWidgets.QVBoxLayout()
        left.addWidget(ed)
        left.addWidget(lstRes, 1)

        mid = QtWidgets.QVBoxLayout()
        mid.addWidget(QtWidgets.QLabel("Stack (kolejność warstw):"))
        mid.addWidget(lstStack, 1)

        btnsMid = QtWidgets.QHBoxLayout()
        btnsMid.addWidget(btnAdd)
        btnsMid.addWidget(btnRem)
        btnsMid.addWidget(btnUp)
        btnsMid.addWidget(btnDn)
        mid.addLayout(btnsMid)

        right = QtWidgets.QVBoxLayout()
        right.addWidget(QtWidgets.QLabel("Szczegóły:"))
        right.addWidget(txt, 1)

        main = QtWidgets.QHBoxLayout()
        main.addLayout(left, 1)
        main.addLayout(mid, 1)
        main.addLayout(right, 1)

        bot = QtWidgets.QHBoxLayout()
        bot.addStretch(1)
        bot.addWidget(btnOk)
        bot.addWidget(btnCancel)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addLayout(main, 1)
        lay.addLayout(bot)

        def refill():
            q = ed.text()
            items = self._query(q, limit=200)
            lstRes.clear()
            dlg._res = items
            for o in items:
                th = o.get("thickness_mm", None)
                ths = "" if th is None else f"{th:g}mm"
                lstRes.addItem(f"{o.get('code','')} | {o.get('name','')} | {o.get('kind','')} | {ths}")
            if items:
                lstRes.setCurrentRow(0)
            show_res()

        def show_res():
            row = lstRes.currentRow()
            items = getattr(dlg, "_res", [])
            if row < 0 or row >= len(items):
                txt.setPlainText("")
                return
            o = items[row]
            txt.setPlainText(json.dumps(o, ensure_ascii=False, indent=2))

        def show_stack():
            row = lstStack.currentRow()
            items = getattr(dlg, "_stack", [])
            if row < 0 or row >= len(items):
                return
            # also show on right
            txt.setPlainText(json.dumps(items[row], ensure_ascii=False, indent=2))

        def stack_refresh_list():
            lstStack.clear()
            for o in dlg._stack:
                th = o.get("thickness_mm", None)
                ths = "" if th is None else f"{th:g}mm"
                lstStack.addItem(f"{o.get('code','')} | {o.get('name','')} | {o.get('kind','')} | {ths}")
            if dlg._stack:
                lstStack.setCurrentRow(0)

        def add():
            r = lstRes.currentRow()
            items = getattr(dlg, "_res", [])
            if r < 0 or r >= len(items): return
            o = items[r]
            dlg._stack.append({
                "code": o.get("code",""),
                "name": o.get("name",""),
                "kind": o.get("kind",""),
                "thickness_mm": o.get("thickness_mm", None),
            })
            stack_refresh_list()

        def rem():
            r = lstStack.currentRow()
            if r < 0 or r >= len(dlg._stack): return
            del dlg._stack[r]
            stack_refresh_list()

        def up():
            r = lstStack.currentRow()
            if r <= 0 or r >= len(dlg._stack): return
            dlg._stack[r-1], dlg._stack[r] = dlg._stack[r], dlg._stack[r-1]
            stack_refresh_list()
            lstStack.setCurrentRow(r-1)

        def dn():
            r = lstStack.currentRow()
            if r < 0 or r >= len(dlg._stack)-1: return
            dlg._stack[r+1], dlg._stack[r] = dlg._stack[r], dlg._stack[r+1]
            stack_refresh_list()
            lstStack.setCurrentRow(r+1)

        def accept():
            self.setStack(dlg._stack)
            dlg.accept()

        dlg._stack = list(self._stack)

        ed.textChanged.connect(refill)
        lstRes.currentRowChanged.connect(lambda *_: show_res())
        lstRes.itemDoubleClicked.connect(lambda *_: add())

        lstStack.currentRowChanged.connect(lambda *_: show_stack())
        btnAdd.clicked.connect(add)
        btnRem.clicked.connect(rem)
        btnUp.clicked.connect(up)
        btnDn.clicked.connect(dn)

        btnOk.clicked.connect(accept)
        btnCancel.clicked.connect(dlg.reject)

        refill()
        stack_refresh_list()
        dlg.exec()
