from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class MidWall:
    enabled: bool = False
    x_mm: int = 300          # position from LEFT inside opening
    h_mm: int = 700          # height from BOTTOM (<= innerH)
    cap_type: str = "NONE"   # NONE / SHELF / BOTTOM
    cap_span: str = "FULL"   # FULL / LEFT / RIGHT


class _PickView(QtWidgets.QGraphicsView):
    picked = QtCore.Signal(str)

    def __init__(self, scene: QtWidgets.QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self._pick_map: Dict[int, str] = {}

    def set_pick_map(self, pick_map: Dict[int, str]):
        self._pick_map = pick_map

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        item = self.itemAt(ev.pos())
        if item is not None:
            name = self._pick_map.get(int(item.data(0) or 0))
            if name:
                self.picked.emit(name)
        super().mousePressEvent(ev)


class ModuleProtoWidget(QtWidgets.QWidget):
    """
    Clean V2 (separate file):
    - left panel uses checkable groupboxes -> collapses + actually shrinks
    - mid walls with adjustable height + cap shelf/bottom span FULL/LEFT/RIGHT
    - shelves limited by caps per segment
    """

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self._mid1 = MidWall()
        self._mid2 = MidWall()

        self._selected_seg: str = "ALL"

        self._build_ui()
        self._wire()
        self._recalc()

    # ---------------- UI helpers ----------------
    def _group(self, title: str) -> Tuple[QtWidgets.QGroupBox, QtWidgets.QVBoxLayout]:
        gb = QtWidgets.QGroupBox(title)
        gb.setCheckable(True)
        gb.setChecked(True)
        lay = QtWidgets.QVBoxLayout(gb)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        return gb, lay

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # status pill
        top = QtWidgets.QHBoxLayout()
        top.addStretch(1)
        self.status = QtWidgets.QLabel("OK")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setFixedWidth(60)
        self.status.setStyleSheet("QLabel{padding:4px 10px;border-radius:10px;background:#d7ffe1;color:#000;font-weight:700;}")
        top.addWidget(self.status)
        root.addLayout(top)

        self.split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(self.split, 1)

        # LEFT
        leftWrap = QtWidgets.QWidget()
        leftLay = QtWidgets.QVBoxLayout(leftWrap)
        leftLay.setContentsMargins(0, 0, 0, 0)
        leftLay.setSpacing(8)

        # DIMENSIONS
        gb, lay = self._group("Wymiary + Anchor")
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignTop)

        self.w = QtWidgets.QSpinBox(); self.w.setRange(50, 5000); self.w.setValue(600)
        self.h = QtWidgets.QSpinBox(); self.h.setRange(50, 5000); self.h.setValue(720)
        self.d = QtWidgets.QSpinBox(); self.d.setRange(50, 2000); self.d.setValue(560)

        self.anchor = QtWidgets.QComboBox()
        self.anchor.addItems(["NONE", "LT", "RT", "LB", "RB"])

        form.addRow("W (mm)", self.w)
        form.addRow("H (mm)", self.h)
        form.addRow("D (mm)", self.d)
        form.addRow("Anchor", self.anchor)
        lay.addLayout(form)
        leftLay.addWidget(gb)

        # OFFSETS
        gb2, lay2 = self._group("Przesunięcia (offset)")
        g = QtWidgets.QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)

        self.posL = QtWidgets.QSpinBox(); self.posL.setRange(0, 2000); self.posL.setValue(0)
        self.posR = QtWidgets.QSpinBox(); self.posR.setRange(0, 2000); self.posR.setValue(0)
        self.posT = QtWidgets.QSpinBox(); self.posT.setRange(0, 2000); self.posT.setValue(0)
        self.posB = QtWidgets.QSpinBox(); self.posB.setRange(0, 2000); self.posB.setValue(0)

        self.btnZero = QtWidgets.QPushButton("Zeruj")
        self.btnLR   = QtWidgets.QPushButton("R = L")
        self.btnTB   = QtWidgets.QPushButton("B = T")

        g.addWidget(QtWidgets.QLabel("Left"), 0, 0);   g.addWidget(self.posL, 0, 1)
        g.addWidget(QtWidgets.QLabel("Right"), 1, 0);  g.addWidget(self.posR, 1, 1)
        g.addWidget(QtWidgets.QLabel("Top"), 2, 0);    g.addWidget(self.posT, 2, 1)
        g.addWidget(QtWidgets.QLabel("Bottom"), 3, 0); g.addWidget(self.posB, 3, 1)
        g.addWidget(self.btnZero, 4, 0, 1, 2)
        g.addWidget(self.btnLR,   5, 0, 1, 1)
        g.addWidget(self.btnTB,   5, 1, 1, 1)
        lay2.addLayout(g)
        leftLay.addWidget(gb2)

        # MID WALLS
        gb3, lay3 = self._group("Ścianki środkowe + cap (półka/dno)")
        self.mid_tabs = QtWidgets.QTabWidget()
        self.mid_tabs.setDocumentMode(True)

        self._mid1_ui = self._build_mid_tab("MID1")
        self._mid2_ui = self._build_mid_tab("MID2")

        self.mid_tabs.addTab(self._mid1_ui["root"], "MID1")
        self.mid_tabs.addTab(self._mid2_ui["root"], "MID2")
        lay3.addWidget(self.mid_tabs)

        hint = QtWidgets.QLabel(
            "Cap = półka/dno nad końcem ścianki.\n"
            "Span: FULL (między granicami segmentu), LEFT (do lewej), RIGHT (do prawej).\n"
            "Półki w segmencie NIE wyjdą ponad cap."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666;")
        lay3.addWidget(hint)
        leftLay.addWidget(gb3)

        # SHELVES
        gb4, lay4 = self._group("Półki (segmenty) — tryb: równo / od dołu / od góry")
        form2 = QtWidgets.QFormLayout()
        self.shelf_n = QtWidgets.QSpinBox(); self.shelf_n.setRange(0, 24); self.shelf_n.setValue(1)
        self.shelf_seg = QtWidgets.QComboBox()
        self.shelf_mode = QtWidgets.QComboBox()
        self.shelf_mode.addItem("Równo (equal)", "EQUAL")
        self.shelf_mode.addItem("Od dołu (start+step)", "BOTTOM")
        self.shelf_mode.addItem("Od góry (start+step)", "TOP")
        self.shelf_start = QtWidgets.QSpinBox(); self.shelf_start.setRange(0, 5000); self.shelf_start.setValue(150)
        self.shelf_step  = QtWidgets.QSpinBox(); self.shelf_step.setRange(1, 5000); self.shelf_step.setValue(300)

        form2.addRow("Ilość", self.shelf_n)
        form2.addRow("Gdzie?", self.shelf_seg)
        form2.addRow("Tryb", self.shelf_mode)
        form2.addRow("Start (mm)", self.shelf_start)
        form2.addRow("Step (mm)", self.shelf_step)
        lay4.addLayout(form2)
        leftLay.addWidget(gb4)

        leftLay.addStretch(1)

        leftScroll = QtWidgets.QScrollArea()
        leftScroll.setWidgetResizable(True)
        leftScroll.setWidget(leftWrap)

        # CENTER view
        center = QtWidgets.QWidget()
        cLay = QtWidgets.QVBoxLayout(center)
        cLay.setContentsMargins(0, 0, 0, 0)
        title = QtWidgets.QLabel("Widok (proto v2)")
        title.setStyleSheet("font-weight:800;")
        cLay.addWidget(title)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = _PickView(self.scene, self)
        cLay.addWidget(self.view, 1)

        # RIGHT panel
        right = QtWidgets.QWidget()
        rLay = QtWidgets.QVBoxLayout(right)
        rLay.setContentsMargins(0, 0, 0, 0)

        rTitle = QtWidgets.QLabel("BOM + wymiary")
        rTitle.setStyleSheet("font-weight:800;")
        rLay.addWidget(rTitle)

        self.bom = QtWidgets.QPlainTextEdit()
        self.bom.setReadOnly(True)
        rLay.addWidget(self.bom, 1)

        self.split.addWidget(leftScroll)
        self.split.addWidget(center)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setStretchFactor(2, 0)
        self.split.setSizes([360, 760, 360])

        self._refresh_shelf_seg_items()
        self._sync_shelf_mode()

    def _build_mid_tab(self, label: str):
        root = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(root)

        en = QtWidgets.QCheckBox("Enabled")
        x  = QtWidgets.QSpinBox(); x.setRange(0, 5000); x.setValue(300)
        hh = QtWidgets.QSpinBox(); hh.setRange(0, 5000); hh.setValue(700)

        cap_type = QtWidgets.QComboBox()
        cap_type.addItem("NONE", "NONE")
        cap_type.addItem("SHELF", "SHELF")
        cap_type.addItem("BOTTOM", "BOTTOM")

        cap_span = QtWidgets.QComboBox()
        cap_span.addItem("FULL", "FULL")
        cap_span.addItem("LEFT", "LEFT")
        cap_span.addItem("RIGHT", "RIGHT")

        form.addRow(en)
        form.addRow("Pozycja X (mm)", x)
        form.addRow("Wysokość (mm, od dołu)", hh)
        form.addRow("Cap type", cap_type)
        form.addRow("Cap span", cap_span)

        return {
            "root": root,
            "en": en,
            "x": x,
            "h": hh,
            "cap_type": cap_type,
            "cap_span": cap_span,
        }

    # ---------------- wiring ----------------
    def _wire(self):
        for sp in (self.w, self.h, self.d, self.posL, self.posR, self.posT, self.posB, self.shelf_n, self.shelf_start, self.shelf_step):
            sp.valueChanged.connect(self._recalc)

        self.anchor.currentIndexChanged.connect(self._recalc)

        self.btnZero.clicked.connect(self._zero)
        self.btnLR.clicked.connect(self._lr_same)
        self.btnTB.clicked.connect(self._tb_same)

        self.shelf_mode.currentIndexChanged.connect(self._sync_shelf_mode)
        self.shelf_mode.currentIndexChanged.connect(self._recalc)
        self.shelf_seg.currentIndexChanged.connect(self._recalc)

        # mid tabs
        for ui in (self._mid1_ui, self._mid2_ui):
            ui["en"].toggled.connect(self._recalc)
            ui["x"].valueChanged.connect(self._recalc)
            ui["h"].valueChanged.connect(self._recalc)
            ui["cap_type"].currentIndexChanged.connect(self._recalc)
            ui["cap_span"].currentIndexChanged.connect(self._recalc)

        self.view.picked.connect(self._on_seg_picked)

    # ---------------- helpers ----------------
    def _sync_shelf_mode(self):
        m = self.shelf_mode.currentData() or "EQUAL"
        on = (m != "EQUAL")
        self.shelf_start.setEnabled(on)
        self.shelf_step.setEnabled(on)

    def _zero(self):
        for w in (self.posL, self.posR, self.posT, self.posB):
            w.setValue(0)

    def _lr_same(self):
        self.posR.setValue(int(self.posL.value()))

    def _tb_same(self):
        self.posB.setValue(int(self.posT.value()))

    def _set_ok(self, ok: bool, msg: str = "OK"):
        if ok:
            self.status.setText("OK")
            self.status.setStyleSheet("QLabel{padding:4px 10px;border-radius:10px;background:#d7ffe1;color:#000;font-weight:700;}")
        else:
            self.status.setText("ERR")
            self.status.setStyleSheet("QLabel{padding:4px 10px;border-radius:10px;background:#ffd6d6;color:#000;font-weight:700;}")
            self.bom.setPlainText(msg)

    def _on_seg_picked(self, name: str):
        self._selected_seg = name
        # update combo to match click
        idx = self.shelf_seg.findText(name)
        if idx >= 0:
            self.shelf_seg.setCurrentIndex(idx)
        self._recalc()

    def _refresh_shelf_seg_items(self):
        segs = self._compute_segments(innerW_mm=1000, innerH_mm=1000)[0]
        self.shelf_seg.blockSignals(True)
        self.shelf_seg.clear()
        self.shelf_seg.addItem("ALL")
        for s in segs:
            self.shelf_seg.addItem(s[0])
        # preserve selection if possible
        cur = self._selected_seg
        idx = self.shelf_seg.findText(cur)
        if idx >= 0:
            self.shelf_seg.setCurrentIndex(idx)
        self.shelf_seg.blockSignals(False)

    # ---------------- model compute ----------------
    def _read_mid(self, ui, target: MidWall, innerW: int, innerH: int):
        target.enabled = bool(ui["en"].isChecked())
        target.x_mm = int(ui["x"].value())
        target.h_mm = int(ui["h"].value())
        target.cap_type = str(ui["cap_type"].currentData() or "NONE")
        target.cap_span = str(ui["cap_span"].currentData() or "FULL")
        # clamp
        target.x_mm = max(0, min(innerW, target.x_mm))
        target.h_mm = max(0, min(innerH, target.h_mm))

    def _compute_segments(self, innerW_mm: int, innerH_mm: int):
        # update mids from UI
        self._read_mid(self._mid1_ui, self._mid1, innerW_mm, innerH_mm)
        self._read_mid(self._mid2_ui, self._mid2, innerW_mm, innerH_mm)

        mids: List[Tuple[str, int, int, MidWall]] = []
        if self._mid1.enabled:
            mids.append(("MID1", self._mid1.x_mm, self._mid1.h_mm, self._mid1))
        if self._mid2.enabled:
            mids.append(("MID2", self._mid2.x_mm, self._mid2.h_mm, self._mid2))
        mids.sort(key=lambda t: t[1])

        # build segment boundaries
        xs = [0] + [m[1] for m in mids] + [innerW_mm]
        segs: List[Tuple[str, int, int]] = []
        for i in range(len(xs)-1):
            segs.append((f"SEG{i+1}", xs[i], xs[i+1]))

        # limits (cap reduces segment usable height)
        limits: Dict[str, int] = {name: innerH_mm for (name, _, _) in segs}

        # cap logic: cap placed at top of mid wall => ycap = innerH - midH
        # apply limit to segments covered by span
        for idx_mid, (mid_name, xmid, hmid, mid) in enumerate(mids):
            if mid.cap_type == "NONE":
                continue
            ycap = innerH_mm - hmid
            # determine neighbor boundaries around this mid
            left_boundary = xs[idx_mid]         # boundary before mid
            right_boundary = xs[idx_mid+2]      # boundary after mid
            # FULL means whole "local span" between boundaries
            spans: List[Tuple[int,int]] = []
            if mid.cap_span == "FULL":
                spans = [(left_boundary, right_boundary)]
            elif mid.cap_span == "LEFT":
                spans = [(left_boundary, xmid)]
            else:  # RIGHT
                spans = [(xmid, right_boundary)]

            for seg_name, x1, x2 in segs:
                for a,b in spans:
                    # overlap?
                    if x2 <= a or x1 >= b:
                        continue
                    limits[seg_name] = min(limits[seg_name], ycap)

        return segs, mids, limits

    # ---------------- render / recalc ----------------
    def _recalc(self):
        try:
            W, H, D = int(self.w.value()), int(self.h.value()), int(self.d.value())
            L, R, T, B = int(self.posL.value()), int(self.posR.value()), int(self.posT.value()), int(self.posB.value())

            innerW = max(1, W - L - R)
            innerH = max(1, H - T - B)

            segs, mids, limits = self._compute_segments(innerW, innerH)
            self._refresh_shelf_seg_items()

            # scene
            self.scene.clear()
            scale = 0.60

            pen_box = QtGui.QPen(QtGui.QColor(40, 40, 40), 2)
            pen_mid = QtGui.QPen(QtGui.QColor(20, 20, 20), 2)
            pen_cap = QtGui.QPen(QtGui.QColor(90, 90, 90), 2)
            pen_shelf = QtGui.QPen(QtGui.QColor(60, 60, 60), 2)

            rect = QtCore.QRectF(0, 0, innerW * scale, innerH * scale)
            self.scene.addRect(rect, pen_box)

            # draw segments clickable
            pick_map: Dict[int, str] = {}
            for i, (name, x1, x2) in enumerate(segs, start=1):
                r = QtCore.QRectF(x1*scale, 0, (x2-x1)*scale, limits[name]*scale)
                item = self.scene.addRect(r, QtGui.QPen(QtGui.QColor(160,160,160), 1))
                item.setData(0, i)
                pick_map[i] = name
                # label
                t = self.scene.addText(name)
                t.setDefaultTextColor(QtGui.QColor(80,80,80))
                t.setPos(x1*scale + 6, 6)

            self.view.set_pick_map(pick_map)

            # draw mid walls + caps
            xs = [0] + [m[1] for m in mids] + [innerW]
            for idx_mid, (mid_name, xmid, hmid, mid) in enumerate(mids):
                y_top = (innerH - hmid) * scale
                self.scene.addLine(xmid*scale, y_top, xmid*scale, innerH*scale, pen_mid)

                if mid.cap_type != "NONE":
                    ycap = (innerH - hmid) * scale
                    left_boundary = xs[idx_mid]
                    right_boundary = xs[idx_mid+2]
                    if mid.cap_span == "FULL":
                        a,b = left_boundary, right_boundary
                    elif mid.cap_span == "LEFT":
                        a,b = left_boundary, xmid
                    else:
                        a,b = xmid, right_boundary
                    self.scene.addLine(a*scale, ycap, b*scale, ycap, pen_cap)

            # shelves
            n = int(self.shelf_n.value())
            target = self.shelf_seg.currentText() if self.shelf_seg.count() else "ALL"
            mode = str(self.shelf_mode.currentData() or "EQUAL")
            start_mm = int(self.shelf_start.value())
            step_mm  = int(self.shelf_step.value())

            for name, x1, x2 in segs:
                if target != "ALL" and name != target:
                    continue
                seg_top = 0
                seg_bottom = int(limits.get(name, innerH))
                if n <= 0 or seg_bottom <= seg_top + 5:
                    continue

                ys: List[float] = []
                if mode == "EQUAL":
                    span = seg_bottom - seg_top
                    for i in range(1, n+1):
                        ys.append(seg_top + (i/(n+1))*span)
                elif mode == "BOTTOM":
                    for i in range(0, n):
                        ys.append(seg_bottom - start_mm - i*step_mm)
                else: # TOP
                    for i in range(0, n):
                        ys.append(seg_top + start_mm + i*step_mm)

                for y in ys:
                    if y <= seg_top + 3 or y >= seg_bottom - 3:
                        continue
                    self.scene.addLine(x1*scale, y*scale, x2*scale, y*scale, pen_shelf)

            self.scene.setSceneRect(rect.adjusted(-20, -20, 20, 20))

            # BOM / info
            out = []
            out.append(f"Outer W/H/D: {W} / {H} / {D}")
            out.append(f"Offsets L/R/T/B: {L} / {R} / {T} / {B}")
            out.append(f"Inner W/H: {innerW} / {innerH}")
            out.append("")
            out.append("Segments (x1..x2, limitH):")
            for name,x1,x2 in segs:
                out.append(f" - {name}: {x1}..{x2}  limit={limits.get(name, innerH)}")
            out.append("")
            out.append("Mid walls:")
            for mid_name, xmid, hmid, mid in mids:
                out.append(f" - {mid_name}: x={xmid} h={hmid} cap={mid.cap_type}/{mid.cap_span}")
            out.append("")
            out.append(f"Shelves: n={n} target={target} mode={mode} start={start_mm} step={step_mm}")
            self.bom.setPlainText("\n".join(out))

            self._set_ok(True)

        except Exception as e:
            import traceback
            self._set_ok(False, traceback.format_exc())