from __future__ import annotations
import json, os
from PySide6 import QtCore, QtWidgets

from .edge_widget import EdgeWidget
from .views import TwoViews

class FormatkiPane(QtWidgets.QWidget):
    """
    Independent sub-tab: FORMATKI
    - list of formatki
    - front/top views
    - edge banding selection
    - materials + qty summary (by material_code)
    Sync:
      - listens ctx.bus.formatka_selected / material_chosen
      - emits ctx.bus.formatka_selected on selection
      - emits ctx.bus.formatki_changed when list changes
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._formatki = []   # list[dict]
        self._selected_id = ""

        self.tbl = QtWidgets.QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["ID", "Nazwa", "W(mm)", "H(mm)", "Materiał", "Qty"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.btnAdd = QtWidgets.QPushButton("Dodaj")
        self.btnDel = QtWidgets.QPushButton("Usuń")
        self.btnSample = QtWidgets.QPushButton("Dodaj przykładowe")

        self.edId   = QtWidgets.QLineEdit()
        self.edName = QtWidgets.QLineEdit()
        self.spW = QtWidgets.QSpinBox(); self.spW.setRange(1, 10000); self.spW.setValue(600)
        self.spH = QtWidgets.QSpinBox(); self.spH.setRange(1, 10000); self.spH.setValue(720)
        self.spQty = QtWidgets.QSpinBox(); self.spQty.setRange(1, 999); self.spQty.setValue(1)

        self.edMat = QtWidgets.QLineEdit()
        self.edMat.setPlaceholderText("material code (np. EG_U999, MDF18)")

        self.edge = EdgeWidget()

        self.chkTop = QtWidgets.QCheckBox("Góra")
        self.chkBottom = QtWidgets.QCheckBox("Dół")
        self.chkLeft = QtWidgets.QCheckBox("Lewa")
        self.chkRight = QtWidgets.QCheckBox("Prawa")

        self.views = TwoViews()

        self.sum = QtWidgets.QTableWidget(0, 3)
        self.sum.setHorizontalHeaderLabels(["Materiał", "Szt.", "Powierzchnia (m2)"])
        self.sum.horizontalHeader().setStretchLastSection(True)
        self.sum.setMinimumHeight(140)

        # layout left
        form = QtWidgets.QFormLayout()
        form.addRow("ID:", self.edId)
        form.addRow("Nazwa:", self.edName)
        form.addRow("W:", self.spW)
        form.addRow("H:", self.spH)
        form.addRow("Qty:", self.spQty)
        form.addRow("Materiał:", self.edMat)

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.btnAdd)
        btns.addWidget(self.btnDel)
        btns.addWidget(self.btnSample)

        left = QtWidgets.QVBoxLayout()
        left.addLayout(form)
        left.addLayout(btns)
        left.addWidget(self.tbl, 1)

        # right side (views + edge)
        edgeBox = QtWidgets.QVBoxLayout()
        edgeBox.addWidget(self.edge)

        edgeChecks = QtWidgets.QGridLayout()
        edgeChecks.addWidget(self.chkTop, 0, 0)
        edgeChecks.addWidget(self.chkBottom, 0, 1)
        edgeChecks.addWidget(self.chkLeft, 1, 0)
        edgeChecks.addWidget(self.chkRight, 1, 1)
        edgeBox.addLayout(edgeChecks)
        edgeBox.addStretch(1)

        bottomRight = QtWidgets.QHBoxLayout()
        bottomRight.addLayout(edgeBox, 0)
        bottomRight.addWidget(self.sum, 1)

        right = QtWidgets.QVBoxLayout()
        right.addWidget(self.views, 2)
        right.addLayout(bottomRight, 1)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        wL = QtWidgets.QWidget(); wL.setLayout(left)
        wR = QtWidgets.QWidget(); wR.setLayout(right)
        split.addWidget(wL)
        split.addWidget(wR)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([420, 900])

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(split, 1)

        # wiring
        self.btnAdd.clicked.connect(self.add_or_update)
        self.btnDel.clicked.connect(self.delete_selected)
        self.btnSample.clicked.connect(self.add_sample)

        self.tbl.itemSelectionChanged.connect(self._on_tbl_sel)

        # edge sync
        self.edge.changed.connect(self._edge_from_widget)
        for chk in (self.chkTop, self.chkBottom, self.chkLeft, self.chkRight):
            chk.stateChanged.connect(self._edge_from_checks)

        # bus sync
        bus = self._bus()
        if bus is not None:
            if hasattr(bus, "formatka_selected"):
                bus.formatka_selected.connect(self.select_by_id)
            if hasattr(bus, "material_chosen"):
                bus.material_chosen.connect(self._material_from_tree)

        self.refresh_all()

    def _bus(self):
        try:
            if isinstance(self.ctx, dict):
                return self.ctx.get("bus", None)
            return getattr(self.ctx, "bus", None)
        except Exception:
            return None

    def get_formatki(self) -> list:
        return list(self._formatki)

    def set_formatki(self, items: list):
        self._formatki = [dict(x) for x in (items or []) if isinstance(x, dict)]
        if self._selected_id and not any(x.get("id")==self._selected_id for x in self._formatki):
            self._selected_id = ""
        self.refresh_all()

    def _emit_changed(self):
        bus = self._bus()
        if bus is not None and hasattr(bus, "formatki_changed"):
            bus.formatki_changed.emit()

    def _emit_selected(self, fid: str):
        bus = self._bus()
        if bus is not None and hasattr(bus, "formatka_selected"):
            bus.formatka_selected.emit(str(fid))

    def refresh_all(self):
        self._fill_table()
        self._update_views()
        self._update_edge_ui()
        self._update_summary()

    def _fill_table(self):
        self.tbl.setRowCount(0)
        for o in self._formatki:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            vals = [
                str(o.get("id","")),
                str(o.get("name","")),
                str(int(o.get("w_mm",0) or 0)),
                str(int(o.get("h_mm",0) or 0)),
                str(o.get("material_code","")),
                str(int(o.get("qty",1) or 1)),
            ]
            for c, v in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(v)
                it.setFlags(it.flags() & ~QtCore.Qt.ItemIsEditable)
                self.tbl.setItem(r, c, it)

        # reselect
        if self._selected_id:
            for r in range(self.tbl.rowCount()):
                if self.tbl.item(r,0).text() == self._selected_id:
                    self.tbl.selectRow(r)
                    break

    def _update_views(self):
        self.views.set_formatki(self._formatki, self._selected_id)

    def _selected_obj(self):
        for o in self._formatki:
            if str(o.get("id","")) == str(self._selected_id):
                return o
        return None

    def _update_edge_ui(self):
        o = self._selected_obj()
        if not o:
            self.edge.set_edge({})
            for chk in (self.chkTop, self.chkBottom, self.chkLeft, self.chkRight):
                chk.blockSignals(True); chk.setChecked(False); chk.blockSignals(False)
            return

        e = o.get("edge", {}) if isinstance(o.get("edge", {}), dict) else {}
        self.edge.set_edge(e)

        mapping = {"top": self.chkTop, "bottom": self.chkBottom, "left": self.chkLeft, "right": self.chkRight}
        for k, chk in mapping.items():
            chk.blockSignals(True)
            chk.setChecked(bool(e.get(k, False)))
            chk.blockSignals(False)

        # also reflect selected material in editor
        self.edMat.setText(str(o.get("material_code","") or ""))

    def _edge_from_widget(self, e: dict):
        o = self._selected_obj()
        if not o:
            return
        o["edge"] = dict(e)
        self._update_edge_ui()
        self._emit_changed()

    def _edge_from_checks(self, *_):
        o = self._selected_obj()
        if not o:
            return
        e = {
            "top": self.chkTop.isChecked(),
            "bottom": self.chkBottom.isChecked(),
            "left": self.chkLeft.isChecked(),
            "right": self.chkRight.isChecked(),
        }
        o["edge"] = e
        self.edge.set_edge(e)
        self._emit_changed()

    def _material_from_tree(self, code: str):
        # when user clicks material in ProjectTree and we have a selected formatka
        o = self._selected_obj()
        if not o:
            return
        code = str(code or "").strip()
        if not code:
            return
        o["material_code"] = code
        self.edMat.setText(code)
        self._fill_table()
        self._update_summary()
        self._emit_changed()

    def _update_summary(self):
        # group by material_code: qty + area m2
        agg = {}
        for o in self._formatki:
            code = str(o.get("material_code","") or "").strip()
            if not code:
                code = "(brak)"
            qty = int(o.get("qty", 1) or 1)
            w = float(o.get("w_mm", 0) or 0)
            h = float(o.get("h_mm", 0) or 0)
            area_m2 = (w * h / 1_000_000.0) * qty
            if code not in agg:
                agg[code] = {"qty": 0, "area": 0.0}
            agg[code]["qty"] += qty
            agg[code]["area"] += area_m2

        rows = sorted(agg.items(), key=lambda kv: kv[0])
        self.sum.setRowCount(0)
        for code, a in rows:
            r = self.sum.rowCount()
            self.sum.insertRow(r)
            self.sum.setItem(r, 0, QtWidgets.QTableWidgetItem(code))
            self.sum.setItem(r, 1, QtWidgets.QTableWidgetItem(str(a["qty"])))
            self.sum.setItem(r, 2, QtWidgets.QTableWidgetItem(f'{a["area"]:.3f}'))

    def select_by_id(self, fid: str):
        fid = str(fid or "").strip()
        if not fid:
            return
        self._selected_id = fid
        self._fill_table()
        self._update_views()
        self._update_edge_ui()

    def _on_tbl_sel(self):
        r = self.tbl.currentRow()
        if r < 0:
            return
        fid = self.tbl.item(r, 0).text()
        self._selected_id = fid
        self._update_views()
        self._update_edge_ui()
        self._emit_selected(fid)

    def add_or_update(self):
        fid = (self.edId.text() or "").strip()
        if not fid:
            QtWidgets.QMessageBox.warning(self, "Brak ID", "Podaj ID formatki (np. F01)")
            return
        o = None
        for x in self._formatki:
            if str(x.get("id","")) == fid:
                o = x
                break
        if o is None:
            o = {"id": fid, "edge": {"top": False, "bottom": False, "left": False, "right": False}}
            self._formatki.append(o)

        o["name"] = (self.edName.text() or "").strip()
        o["w_mm"] = int(self.spW.value())
        o["h_mm"] = int(self.spH.value())
        o["qty"]  = int(self.spQty.value())
        o["material_code"] = (self.edMat.text() or "").strip()

        self._selected_id = fid
        self.refresh_all()
        self._emit_changed()
        self._emit_selected(fid)

    def delete_selected(self):
        if not self._selected_id:
            return
        fid = self._selected_id
        self._formatki = [x for x in self._formatki if str(x.get("id","")) != fid]
        self._selected_id = ""
        self.refresh_all()
        self._emit_changed()

    def add_sample(self):
        if self._formatki:
            if QtWidgets.QMessageBox.question(self, "Przykład", "Dodać przykładowe formatki do istniejących?") != QtWidgets.QMessageBox.Yes:
                return

        sample = [
            {"id":"F01","name":"Bok L","w_mm":720,"h_mm":560,"qty":1,"material_code":"EG_U999","edge":{"top":True,"bottom":False,"left":True,"right":False}},
            {"id":"F02","name":"Bok P","w_mm":720,"h_mm":560,"qty":1,"material_code":"EG_U999","edge":{"top":True,"bottom":False,"left":False,"right":True}},
            {"id":"F03","name":"Dno","w_mm":600,"h_mm":560,"qty":1,"material_code":"MDF18","edge":{"top":False,"bottom":False,"left":False,"right":False}},
        ]
        self._formatki.extend(sample)
        self.refresh_all()
        self._emit_changed()
