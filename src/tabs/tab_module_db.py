from PySide6 import QtWidgets, QtCore


class ModuleDbTab(QtWidgets.QWidget):
    """
    BAZA modułu — lista rekordów + podgląd JSON + usuń.
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._fallback_db = None

        root = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.btnRefresh = QtWidgets.QPushButton("Odśwież")
        self.btnDelete  = QtWidgets.QPushButton("Usuń")
        self.btnCopy    = QtWidgets.QPushButton("Kopiuj JSON")

        top.addWidget(self.btnRefresh)
        top.addWidget(self.btnDelete)
        top.addWidget(self.btnCopy)
        top.addStretch(1)
        root.addLayout(top)

        split = QtWidgets.QSplitter()
        split.setOrientation(QtCore.Qt.Orientation.Horizontal)

        self.list = QtWidgets.QListWidget()
        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)

        split.addWidget(self.list)
        split.addWidget(self.text)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        root.addWidget(split, 1)

        self.lbl = QtWidgets.QLabel("")
        root.addWidget(self.lbl)

        self.btnRefresh.clicked.connect(self.refresh)
        self.btnDelete.clicked.connect(self.delete_selected)
        self.btnCopy.clicked.connect(self.copy_json)
        self.list.currentTextChanged.connect(self.show_selected)

        QtCore.QTimer.singleShot(0, self.refresh)

    def _db(self):
        db = getattr(self.ctx, "db", None) if self.ctx is not None else None
        if db is not None:
            return db
        if self._fallback_db is None:
            try:
                from app.module_db import ModuleDB
                self._fallback_db = ModuleDB()
            except Exception:
                self._fallback_db = None
        return self._fallback_db

    def refresh(self):
        db = self._db()
        self.list.clear()
        self.text.setPlainText("")
        if db is None:
            self.lbl.setText("Brak bazy.")
            return

        try:
            if hasattr(db, "list_names"):
                items = db.list_names()  # [(name, updated_at),...]
                for name, ts in items:
                    self.list.addItem(f"{name}    [{ts}]")
            elif hasattr(db, "list_modules"):
                items = db.list_modules()
                for it in items:
                    self.list.addItem(str(it))
            else:
                self.lbl.setText("ctx.db nie ma list_names/list_modules.")
                return
            self.lbl.setText(f"Rekordów: {self.list.count()}")
        except Exception as e:
            self.lbl.setText(f"ERROR list: {e!r}")

    def _extract_name(self, line: str) -> str:
        # our format: "NAME    [ts]"
        if "    [" in line:
            return line.split("    [", 1)[0].strip()
        return line.strip()

    def show_selected(self, line: str):
        name = self._extract_name(line)
        if not name:
            return
        db = self._db()
        if db is None:
            return
        try:
            if hasattr(db, "get"):
                payload = db.get(name)
            elif hasattr(db, "get_module"):
                payload = db.get_module(name)
            else:
                payload = None
            import json
            self.text.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as e:
            self.text.setPlainText(f"ERROR: {e!r}")

    def delete_selected(self):
        it = self.list.currentItem()
        if it is None:
            return
        name = self._extract_name(it.text())
        if not name:
            return
        db = self._db()
        if db is None:
            return
        try:
            if hasattr(db, "delete"):
                db.delete(name)
            elif hasattr(db, "delete_module"):
                db.delete_module(name)
            self.refresh()
        except Exception as e:
            self.lbl.setText(f"ERROR delete: {e!r}")

    def copy_json(self):
        txt = self.text.toPlainText()
        if not txt:
            return
        QtWidgets.QApplication.clipboard().setText(txt)
        self.lbl.setText("Skopiowano JSON do schowka.")
