from __future__ import annotations
from PySide6 import QtWidgets

class ModulConstructorPage(QtWidgets.QWidget):
    """
    Ściana -> Moduł (konstruktor + zapis do bazy)
    IMPORTANT: Moduł is NOT a top-level tab.
    """

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._ctor = None

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # top bar
        bar = QtWidgets.QHBoxLayout()
        root.addLayout(bar)

        self.btnSave = QtWidgets.QPushButton("Zapisz do bazy")
        self.lbl = QtWidgets.QLabel("")
        self.lbl.setWordWrap(True)

        bar.addWidget(self.btnSave)
        bar.addWidget(self.lbl, 1)

        self.btnSave.clicked.connect(self._save_to_db_safe)

        # constructor widget (reuse existing)
        try:
            from tabs.module_proto_widget import ModuleProtoWidget
            self._ctor = ModuleProtoWidget(ctx=ctx, parent=self)
            root.addWidget(self._ctor, 1)
        except Exception as e:
            msg = QtWidgets.QLabel("Nie udało się załadować konstruktora (ModuleProtoWidget).\n" + str(e))
            msg.setWordWrap(True)
            root.addWidget(msg, 1)

    def _extract_payload(self):
        """
        Try common patterns without assuming exact API.
        """
        w = self._ctor
        if w is None:
            return None

        # try a few likely method names (safe)
        for name in ("to_dict", "export", "export_state", "serialize", "get_state", "state"):
            fn = getattr(w, name, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:
                    pass
        return None

    def _save_to_db_safe(self):
        try:
            payload = self._extract_payload()
            if payload is None:
                self.lbl.setText("Brak danych do zapisu (brak eksportu ze konstruktora).")
                return

            # Try ctx.save_module(payload) or ctx.db.save_module(payload)
            if self.ctx is not None:
                fn = getattr(self.ctx, "save_module", None)
                if callable(fn):
                    fn(payload)
                    self.lbl.setText("Zapisano do bazy (ctx.save_module).")
                    return

                db = getattr(self.ctx, "db", None)
                if db is not None:
                    fn2 = getattr(db, "save_module", None)
                    if callable(fn2):
                        fn2(payload)
                        self.lbl.setText("Zapisano do bazy (ctx.db.save_module).")
                        return

            self.lbl.setText("Nie znaleziono funkcji zapisu (ctx.save_module / ctx.db.save_module).")
        except Exception as e:
            self.lbl.setText("Błąd zapisu: " + str(e))
