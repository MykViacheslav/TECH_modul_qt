from __future__ import annotations
import json, os
from PySide6 import QtCore, QtWidgets

from tabs.module_panes.formatki_pane import FormatkiPane

class ModuleTab(QtWidgets.QWidget):
    """
    MODUL (constructor + zapis do bazy)
    Wkladki (sub-tabs) are independent components.
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.edAnchor = QtWidgets.QLineEdit()
        self.edAnchor.setPlaceholderText("Anchor (np. M01)")

        self.edName = QtWidgets.QLineEdit()
        self.edName.setPlaceholderText("Nazwa (opcjonalnie)")

        self.spW = QtWidgets.QSpinBox(); self.spW.setRange(1, 10000); self.spW.setValue(600)
        self.spH = QtWidgets.QSpinBox(); self.spH.setRange(1, 10000); self.spH.setValue(720)
        self.spD = QtWidgets.QSpinBox(); self.spD.setRange(1, 10000); self.spD.setValue(560)

        self.edMaterials = QtWidgets.QLineEdit()
        self.edMaterials.setPlaceholderText("Opis materiału (na razie tekst)")

        self.btnLoad = QtWidgets.QPushButton("Load")
        self.btnSave = QtWidgets.QPushButton("Save")
        self.btnNew  = QtWidgets.QPushButton("New")

        top = QtWidgets.QGridLayout()
        top.addWidget(QtWidgets.QLabel("Anchor:"), 0, 0)
        top.addWidget(self.edAnchor, 0, 1)
        top.addWidget(self.btnLoad, 0, 2)
        top.addWidget(self.btnSave, 0, 3)
        top.addWidget(self.btnNew, 0, 4)

        top.addWidget(QtWidgets.QLabel("Nazwa:"), 1, 0)
        top.addWidget(self.edName, 1, 1, 1, 2)
        top.addWidget(QtWidgets.QLabel("W:"), 1, 3); top.addWidget(self.spW, 1, 4)

        top.addWidget(QtWidgets.QLabel("H:"), 2, 3); top.addWidget(self.spH, 2, 4)
        top.addWidget(QtWidgets.QLabel("D:"), 2, 0); top.addWidget(self.spD, 2, 1)

        top.addWidget(QtWidgets.QLabel("Materiały:"), 3, 0)
        top.addWidget(self.edMaterials, 3, 1, 1, 4)

        self.subtabs = QtWidgets.QTabWidget()
        self.paneFormatki = FormatkiPane(ctx)

        # only first subtab now
        self.subtabs.addTab(self.paneFormatki, "FORMATKI")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.subtabs, 1)

        self.btnNew.clicked.connect(self.new_module)
        self.btnLoad.clicked.connect(self.load_module)
        self.btnSave.clicked.connect(self.save_module)

        # bus: respond to load requests from BAZA MODULU / ProjectTree
        bus = self._bus()
        if bus is not None and hasattr(bus, "module_load_requested"):
            bus.module_load_requested.connect(self._on_load_requested)

        # whenever formatki changed -> update ctx.state + notify tree
        if bus is not None and hasattr(bus, "formatki_changed"):
            bus.formatki_changed.connect(self._sync_state_from_ui)
        if bus is not None and hasattr(bus, "formatka_selected"):
            bus.formatka_selected.connect(self._on_formatka_selected)

        self._ensure_state()

    def _bus(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("bus", None)
            return getattr(self.ctx, "bus", None)
        except Exception:
            return None

    def _ensure_state(self):
        # ensure ctx.state exists
        try:
            if isinstance(self.ctx, dict):
                if "state" not in self.ctx or not isinstance(self.ctx["state"], dict):
                    self.ctx["state"] = {}
                return self.ctx["state"]
            else:
                if not hasattr(self.ctx, "state") or not isinstance(self.ctx.state, dict):
                    self.ctx.state = {}
                return self.ctx.state
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

    def new_module(self):
        self.edName.setText("")
        self.spW.setValue(600)
        self.spH.setValue(720)
        self.spD.setValue(560)
        self.edMaterials.setText("")
        self.paneFormatki.set_formatki([])
        self._sync_state_from_ui()

    def _payload_from_ui(self) -> dict:
        return {
            "anchor": (self.edAnchor.text() or "").strip(),
            "name": (self.edName.text() or "").strip(),
            "width": float(self.spW.value()),
            "height": float(self.spH.value()),
            "depth": float(self.spD.value()),
            "materials": (self.edMaterials.text() or "").strip(),
            "formatki": self.paneFormatki.get_formatki(),
        }

    def _apply_payload(self, obj: dict):
        self.edAnchor.setText(str(obj.get("anchor","")))
        self.edName.setText(str(obj.get("name","")))
        try: self.spW.setValue(int(float(obj.get("width", self.spW.value()))))
        except Exception: pass
        try: self.spH.setValue(int(float(obj.get("height", self.spH.value()))))
        except Exception: pass
        try: self.spD.setValue(int(float(obj.get("depth", self.spD.value()))))
        except Exception: pass
        self.edMaterials.setText(str(obj.get("materials","")))
        self.paneFormatki.set_formatki(obj.get("formatki", []) or [])
        self._sync_state_from_ui()

    def _sync_state_from_ui(self):
        st = self._ensure_state()
        obj = self._payload_from_ui()
        st["active_module"] = obj

        bus = self._bus()
        if bus is not None and hasattr(bus, "active_module_changed"):
            bus.active_module_changed.emit(str(obj.get("anchor","") or ""))

    def _on_load_requested(self, anchor: str):
        self.edAnchor.setText(str(anchor or ""))
        self.load_module()

    def _on_formatka_selected(self, _fid: str):
        idx = self.subtabs.indexOf(self.paneFormatki)
        if idx >= 0:
            self.subtabs.setCurrentIndex(idx)

    def load_module(self):
        anchor = (self.edAnchor.text() or "").strip()
        if not anchor:
            QtWidgets.QMessageBox.warning(self, "Brak anchor", "Podaj anchor (np. M01)")
            return
        from tools import module_db_cli
        con = module_db_cli.connect(self._db_path())
        module_db_cli.ensure_schema(con)
        row = con.execute("SELECT payload_json FROM modules WHERE anchor = ?", (anchor,)).fetchone()
        if not row:
            QtWidgets.QMessageBox.information(self, "Nie znaleziono", f"Brak '{anchor}' w bazie.")
            return
        obj = json.loads(row["payload_json"])
        self._apply_payload(obj)

    def save_module(self):
        obj = self._payload_from_ui()
        anchor = (obj.get("anchor") or "").strip()
        if not anchor:
            QtWidgets.QMessageBox.warning(self, "Brak anchor", "Podaj anchor (np. M01)")
            return
        from tools import module_db_cli
        con = module_db_cli.connect(self._db_path())
        # overwrite=True from GUI (to allow update); history enabled
        module_db_cli.upsert(con, obj, overwrite=True, history=True)
        self._sync_state_from_ui()
        QtWidgets.QMessageBox.information(self, "OK", f"Zapisano '{anchor}' do bazy.")
