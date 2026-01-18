from PySide6 import QtWidgets, QtCore


def _qt_export_snapshot(obj) -> dict:
    """
    Generic fallback exporter: collects values from known Qt widgets stored as attributes.
    """
    snap = {"__type__": type(obj).__name__, "fields": {}}

    for name, w in vars(obj).items():
        try:
            if isinstance(w, QtWidgets.QSpinBox) or isinstance(w, QtWidgets.QDoubleSpinBox):
                snap["fields"][name] = ("spin", w.value())
            elif isinstance(w, QtWidgets.QCheckBox):
                snap["fields"][name] = ("check", bool(w.isChecked()))
            elif isinstance(w, QtWidgets.QLineEdit):
                snap["fields"][name] = ("text", w.text())
            elif isinstance(w, QtWidgets.QComboBox):
                # store text + data (if serializable)
                data = w.currentData()
                snap["fields"][name] = ("combo", {"text": w.currentText(), "data": data})
        except Exception:
            pass

    return snap


def _qt_apply_snapshot(obj, payload: dict) -> None:
    fields = (payload or {}).get("fields") or {}
    for name, item in fields.items():
        if not hasattr(obj, name):
            continue
        w = getattr(obj, name, None)
        try:
            kind, val = item
            if kind == "spin" and hasattr(w, "setValue"):
                w.setValue(val)
            elif kind == "check" and hasattr(w, "setChecked"):
                w.setChecked(bool(val))
            elif kind == "text" and hasattr(w, "setText"):
                w.setText("" if val is None else str(val))
            elif kind == "combo" and isinstance(w, QtWidgets.QComboBox):
                # prefer matching by text
                txt = (val or {}).get("text", "")
                idx = w.findText(txt)
                if idx >= 0:
                    w.setCurrentIndex(idx)
        except Exception:
            pass


class ModulPage(QtWidgets.QWidget):
    """
    Moduł = konstruktor + zapis/odczyt do bazy.
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._fallback_db = None
        self._constructor = None

        root = QtWidgets.QVBoxLayout(self)

        # --- Top bar (save/load) ---
        bar = QtWidgets.QHBoxLayout()

        bar.addWidget(QtWidgets.QLabel("Nazwa:"))
        self.edName = QtWidgets.QLineEdit()
        self.edName.setPlaceholderText("np. MODUL_1200x2400_A")
        bar.addWidget(self.edName, 2)

        self.cbOverwrite = QtWidgets.QCheckBox("Nadpisz")
        self.cbOverwrite.setChecked(True)
        bar.addWidget(self.cbOverwrite)

        self.btnRefresh = QtWidgets.QPushButton("Odśwież")
        self.btnLoad = QtWidgets.QPushButton("Wczytaj")
        self.btnSave = QtWidgets.QPushButton("Zapisz")

        bar.addWidget(self.btnRefresh)
        bar.addWidget(self.btnLoad)
        bar.addWidget(self.btnSave)

        root.addLayout(bar)

        # selector
        sel = QtWidgets.QHBoxLayout()
        sel.addWidget(QtWidgets.QLabel("Z bazy:"))
        self.cmb = QtWidgets.QComboBox()
        self.cmb.setMinimumWidth(320)
        sel.addWidget(self.cmb, 2)
        root.addLayout(sel)

        self.lblMsg = QtWidgets.QLabel("")
        self.lblMsg.setWordWrap(True)
        root.addWidget(self.lblMsg)

        # --- Constructor widget ---
        widget = None
        err = None
        try:
            from ..module_proto_widget import ModuleProtoWidget
            widget = ModuleProtoWidget(ctx=ctx, parent=self)
        except Exception as e:
            err = e

        if widget is not None:
            self._constructor = widget
            root.addWidget(widget, 1)
        else:
            root.addWidget(QtWidgets.QLabel("MODUŁ — konstruktor (brak ModuleProtoWidget albo błąd importu)"))
            root.addWidget(QtWidgets.QLabel(f"ERROR: {err!r}"))
            root.addStretch(1)

        # wire
        self.btnRefresh.clicked.connect(self.refresh_list)
        self.btnSave.clicked.connect(self.save_to_db)
        self.btnLoad.clicked.connect(self.load_from_db)
        self.cmb.currentTextChanged.connect(self._on_pick)

        # init
        QtCore.QTimer.singleShot(0, self.refresh_list)

    def _db(self):
        # Prefer ctx.db if present and has compatible methods; else fallback ModuleDB
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

    def _set_msg(self, s: str):
        self.lblMsg.setText(s)

    def refresh_list(self):
        db = self._db()
        self.cmb.clear()

        if db is None:
            self._set_msg("Brak bazy (ctx.db i fallback SQLite niedostępny).")
            return

        # compatible listing
        items = []
        try:
            if hasattr(db, "list_names"):
                items = db.list_names()
            elif hasattr(db, "list_modules"):
                items = db.list_modules()
        except Exception as e:
            self._set_msg(f"ERROR list: {e!r}")
            return

        # normalize items to names
        names = []
        for it in items:
            try:
                if isinstance(it, (list, tuple)) and len(it) >= 1:
                    names.append(str(it[0]))
                else:
                    names.append(str(it))
            except Exception:
                pass

        self.cmb.addItems(names)
        self._set_msg(f"Rekordów w bazie: {len(names)}")

    def _export_payload(self) -> dict:
        w = self._constructor
        if w is None:
            return {}

        # Prefer explicit API
        if hasattr(w, "export_state") and callable(getattr(w, "export_state")):
            try:
                return {"schema": "export_state_v1", "data": w.export_state()}
            except Exception:
                pass
        if hasattr(w, "to_dict") and callable(getattr(w, "to_dict")):
            try:
                return {"schema": "to_dict_v1", "data": w.to_dict()}
            except Exception:
                pass

        # fallback snapshot
        return {"schema": "qt_snapshot_v1", "data": _qt_export_snapshot(w)}

    def _apply_payload(self, payload: dict) -> None:
        w = self._constructor
        if w is None:
            return

        schema = (payload or {}).get("schema")
        data = (payload or {}).get("data")

        if schema == "export_state_v1" and hasattr(w, "apply_state"):
            try:
                w.apply_state(data or {})
                if hasattr(w, "_recalc"): w._recalc()
                return
            except Exception:
                pass

        if schema == "to_dict_v1" and hasattr(w, "from_dict"):
            try:
                w.from_dict(data or {})
                if hasattr(w, "_recalc"): w._recalc()
                return
            except Exception:
                pass

        if schema == "qt_snapshot_v1":
            try:
                _qt_apply_snapshot(w, data or {})
                if hasattr(w, "_recalc"): w._recalc()
                return
            except Exception:
                pass

    def save_to_db(self):
        name = (self.edName.text() or "").strip()
        if not name:
            self._set_msg("Podaj nazwę przed zapisem.")
            return

        db = self._db()
        if db is None:
            self._set_msg("Brak bazy.")
            return

        overwrite = bool(self.cbOverwrite.isChecked())
        payload = self._export_payload()

        try:
            # compatible upsert
            if hasattr(db, "upsert"):
                db.upsert(name, payload, overwrite=overwrite)
            elif hasattr(db, "save_module"):
                db.save_module(name, payload, overwrite=overwrite)
            else:
                self._set_msg("ctx.db nie ma metody upsert/save_module.")
                return

            self._set_msg(f"Zapisano: {name}" + (" (nadpisano)" if overwrite else ""))
            self.refresh_list()
            # select saved
            idx = self.cmb.findText(name)
            if idx >= 0:
                self.cmb.setCurrentIndex(idx)
        except Exception as e:
            self._set_msg(f"ERROR save: {e!r}")

    def load_from_db(self):
        name = (self.cmb.currentText() or "").strip()
        if not name:
            self._set_msg("Wybierz rekord z listy.")
            return

        db = self._db()
        if db is None:
            self._set_msg("Brak bazy.")
            return

        try:
            if hasattr(db, "get"):
                payload = db.get(name)
            elif hasattr(db, "get_module"):
                payload = db.get_module(name)
            else:
                self._set_msg("ctx.db nie ma metody get/get_module.")
                return

            if payload is None:
                self._set_msg("Nie znaleziono rekordu.")
                return

            self._apply_payload(payload)
            self.edName.setText(name)
            self._set_msg(f"Wczytano: {name}")
        except Exception as e:
            self._set_msg(f"ERROR load: {e!r}")

    def _on_pick(self, name: str):
        if name and not self.edName.text().strip():
            self.edName.setText(name)
