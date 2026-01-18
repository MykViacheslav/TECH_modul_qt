from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.collapsible import CollapsibleSection


@dataclass(frozen=True)
class Divider:
    x: int          # mm from left
    h: int          # height mm from bottom


@dataclass(frozen=True)
class Board:
    y: int          # mm from bottom
    x1: int         # mm
    x2: int         # mm
    kind: str = "shelf"  # shelf/cap/bottom etc


@dataclass
class Compartment:
    x1: int; x2: int
    y1: int; y2: int
    # label for debug
    tag: str = ""


class _UF:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


class _PickRect(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect: QtCore.QRectF, idx: int, owner: "ModuleProtoWidget"):
        super().__init__(rect)
        self._idx = idx
        self._owner = owner
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, ev):
        self.setPen(QtGui.QPen(QtGui.QColor(60, 140, 255), 2))
        super().hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev):
        if self._owner._sel_idx == self._idx:
            self.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 2))
        else:
            self.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
        super().hoverLeaveEvent(ev)

    def mousePressEvent(self, ev):
        self._owner._select_compartment(self._idx)
        ev.accept()


class ModuleProtoWidget(QtWidgets.QWidget):
    """
    Proto module UI:
      - mid divider with height
      - cap shelf at divider top (LEFT/RIGHT/BOTH/NONE) => makes segment end at that shelf
      - shelves are added INSIDE selected compartment; once added, they SPLIT it -> can't add "above segment" accidentally
    """
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self._user_boards: List[Board] = []
        self._comps: List[Compartment] = []
        self._sel_idx: Optional[int] = None

        self._build_ui()
        self._wire()
        self._recalc()

    # ---------- UI ----------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        top.addStretch(1)
        self.status = QtWidgets.QLabel("OK")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setFixedWidth(64)
        self._set_ok(True)
        top.addWidget(self.status)
        root.addLayout(top)

        self.split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(self.split, 1)

        # LEFT
        leftWrap = QtWidgets.QWidget()
        leftLay = QtWidgets.QVBoxLayout(leftWrap)
        leftLay.setContentsMargins(0, 0, 0, 0)
        leftLay.setSpacing(10)

        # dims
        self.secDims = CollapsibleSection("Wymiary")
        dims = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(dims)
        g.setContentsMargins(0, 0, 0, 0)

        self.w = QtWidgets.QSpinBox(); self.w.setRange(50, 5000); self.w.setValue(600)
        self.h = QtWidgets.QSpinBox(); self.h.setRange(50, 5000); self.h.setValue(720)

        g.addWidget(QtWidgets.QLabel("W (mm)"), 0, 0); g.addWidget(self.w, 0, 1)
        g.addWidget(QtWidgets.QLabel("H (mm)"), 1, 0); g.addWidget(self.h, 1, 1)

        self._sec_add(self.secDims, dims)
        leftLay.addWidget(self.secDims)

        # mid divider
        self.secMid = CollapsibleSection("Mid-stенка (высота + cap полка)")
        mid = QtWidgets.QWidget()
        g2 = QtWidgets.QGridLayout(mid)
        g2.setContentsMargins(0, 0, 0, 0)

        self.midOn = QtWidgets.QCheckBox("Enable mid")
        self.midX  = QtWidgets.QSpinBox(); self.midX.setRange(1, 4999); self.midX.setValue(300)
        self.midH  = QtWidgets.QSpinBox(); self.midH.setRange(1, 4999); self.midH.setValue(300)

        self.midCap = QtWidgets.QComboBox()
        self.midCap.addItems(["NONE", "LEFT", "RIGHT", "BOTH"])  # BOTH = full-width cap (via two halves)

        g2.addWidget(self.midOn, 0, 0, 1, 2)
        g2.addWidget(QtWidgets.QLabel("X (mm)"), 1, 0); g2.addWidget(self.midX, 1, 1)
        g2.addWidget(QtWidgets.QLabel("Height (mm)"), 2, 0); g2.addWidget(self.midH, 2, 1)
        g2.addWidget(QtWidgets.QLabel("Cap shelf"), 3, 0); g2.addWidget(self.midCap, 3, 1)

        note = QtWidgets.QLabel("Cap shelf = межа сегменту. Нижній сегмент закінчується полицею.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666;")
        g2.addWidget(note, 4, 0, 1, 2)

        self._sec_add(self.secMid, mid)
        leftLay.addWidget(self.secMid)

        # shelves
        self.secShelves = CollapsibleSection("Półki (вибраний сегмент)")
        sh = QtWidgets.QWidget()
        g3 = QtWidgets.QGridLayout(sh)
        g3.setContentsMargins(0, 0, 0, 0)

        self.selInfo = QtWidgets.QLabel("Selected: —")
        self.selInfo.setStyleSheet("font-weight:700;")

        self.shelfRel = QtWidgets.QSpinBox()
        self.shelfRel.setRange(1, 4999)
        self.shelfRel.setValue(150)

        self.btnAddShelf = QtWidgets.QPushButton("+ Dodaj półkę w segmencie")
        self.btnClearShelves = QtWidgets.QPushButton("Clear shelves (proto)")
        self.btnClearShelves.setStyleSheet("color:#b00000;")

        g3.addWidget(self.selInfo, 0, 0, 1, 2)
        g3.addWidget(QtWidgets.QLabel("Y від низу сегменту (mm)"), 1, 0); g3.addWidget(self.shelfRel, 1, 1)
        g3.addWidget(self.btnAddShelf, 2, 0, 1, 2)
        g3.addWidget(self.btnClearShelves, 3, 0, 1, 2)

        self._sec_add(self.secShelves, sh)
        leftLay.addWidget(self.secShelves)

        leftLay.addStretch(1)
        leftScroll = QtWidgets.QScrollArea()
        leftScroll.setWidgetResizable(True)
        leftScroll.setWidget(leftWrap)

        # CENTER view
        center = QtWidgets.QWidget()
        cLay = QtWidgets.QVBoxLayout(center)
        cLay.setContentsMargins(0, 0, 0, 0)

        t = QtWidgets.QLabel("Widok (proto) — kliknij segment")
        t.setStyleSheet("font-weight:800;")
        cLay.addWidget(t)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        cLay.addWidget(self.view, 1)

        # RIGHT debug/bom
        right = QtWidgets.QWidget()
        rLay = QtWidgets.QVBoxLayout(right)
        rLay.setContentsMargins(0, 0, 0, 0)

        rt = QtWidgets.QLabel("Debug / BOM (proto)")
        rt.setStyleSheet("font-weight:800;")
        self.bom = QtWidgets.QPlainTextEdit()
        self.bom.setReadOnly(True)

        rLay.addWidget(rt)
        rLay.addWidget(self.bom, 1)

        self.split.addWidget(leftScroll)
        self.split.addWidget(center)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setStretchFactor(2, 0)
        self.split.setSizes([360, 820, 340])

    def _sec_add(self, sec: CollapsibleSection, w: QtWidgets.QWidget):
        # compat: some versions used contentLayout, some content_layout
        if hasattr(sec, "contentLayout"):
            sec.contentLayout.addWidget(w)
        elif hasattr(sec, "content_layout"):
            sec.content_layout.addWidget(w)
        elif hasattr(sec, "content") and sec.content.layout():
            sec.content.layout().addWidget(w)
        else:
            lay = QtWidgets.QVBoxLayout(sec)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(w)

    def _wire(self):
        for sp in (self.w, self.h, self.midX, self.midH, self.shelfRel):
            sp.valueChanged.connect(self._recalc)
        self.midOn.toggled.connect(self._recalc)
        self.midCap.currentIndexChanged.connect(self._recalc)
        self.btnAddShelf.clicked.connect(self._add_shelf_in_selected)
        self.btnClearShelves.clicked.connect(self._clear_shelves)

    # ---------- MODEL ----------
    def _get_dividers(self) -> List[Divider]:
        divs: List[Divider] = []
        if self.midOn.isChecked():
            x = int(self.midX.value())
            h = int(self.midH.value())
            W = int(self.w.value())
            H = int(self.h.value())
            x = max(1, min(W - 1, x))
            h = max(1, min(H - 1, h))
            divs.append(Divider(x=x, h=h))
        return divs

    def _get_boards(self) -> List[Board]:
        boards = list(self._user_boards)

        # auto cap shelf at mid top -> makes "segment end at shelf"
        W = int(self.w.value())
        divs = self._get_dividers()
        if divs:
            d = divs[0]
            mode = self.midCap.currentText()
            y = d.h
            if mode == "LEFT":
                boards.append(Board(y=y, x1=0, x2=d.x, kind="cap"))
            elif mode == "RIGHT":
                boards.append(Board(y=y, x1=d.x, x2=W, kind="cap"))
            elif mode == "BOTH":
                # two halves = behaves like full-width shelf but still ok
                boards.append(Board(y=y, x1=0, x2=d.x, kind="cap"))
                boards.append(Board(y=y, x1=d.x, x2=W, kind="cap"))
        return boards

    def _compute_compartments(self, W: int, H: int, divs: List[Divider], boards: List[Board]) -> List[Compartment]:
        # grid breaks must include divider x and board endpoints
        xs = {0, W}
        ys = {0, H}

        for d in divs:
            xs.add(int(d.x))
            ys.add(int(d.h))
        for b in boards:
            xs.add(int(b.x1)); xs.add(int(b.x2))
            ys.add(int(b.y))

        x_list = sorted(xs)
        y_list = sorted(ys)

        nx = len(x_list) - 1
        ny = len(y_list) - 1
        if nx <= 0 or ny <= 0:
            return []

        def cell_id(ix: int, iy: int) -> int:
            return iy * nx + ix

        uf = _UF(nx * ny)

        # map divider at x -> height
        div_by_x = {d.x: d.h for d in divs}

        # helper: board separator at boundary y for x-interval
        def has_board_sep(yb: int, x0: int, x1: int) -> bool:
            for b in boards:
                if b.y != yb:
                    continue
                if b.x1 <= x0 and b.x2 >= x1:
                    return True
            return False

        # Horizontal unions inside each layer (merge across divider boundaries if divider NOT active at this y)
        for iy in range(ny):
            y0 = y_list[iy]
            for ix in range(nx - 1):
                # boundary x = x_list[ix+1]
                xb = x_list[ix + 1]
                h = div_by_x.get(xb, None)
                divider_active = (h is not None and h > y0)
                if not divider_active:
                    uf.union(cell_id(ix, iy), cell_id(ix + 1, iy))

        # Vertical unions across y boundaries when there is NO board separator
        for iy in range(ny - 1):
            yb = y_list[iy + 1]
            for ix in range(nx):
                x0, x1 = x_list[ix], x_list[ix + 1]
                if not has_board_sep(yb, x0, x1):
                    uf.union(cell_id(ix, iy), cell_id(ix, iy + 1))

        # collect cells by component
        comp_cells = {}
        for iy in range(ny):
            for ix in range(nx):
                root = uf.find(cell_id(ix, iy))
                comp_cells.setdefault(root, []).append((ix, iy))

        # Split each component into rectangles (greedy) so selection is always rectangular
        comps: List[Compartment] = []
        for root, cells in comp_cells.items():
            grid = [[False]*nx for _ in range(ny)]
            for ix, iy in cells:
                grid[iy][ix] = True

            for iy in range(ny):
                for ix in range(nx):
                    if not grid[iy][ix]:
                        continue

                    # maximal width
                    w = 0
                    while ix + w < nx and grid[iy][ix + w]:
                        w += 1

                    # maximal height with same width
                    h = 1
                    while iy + h < ny:
                        ok = True
                        for k in range(w):
                            if not grid[iy + h][ix + k]:
                                ok = False
                                break
                        if not ok:
                            break
                        h += 1

                    # mark used
                    for dy in range(h):
                        for dx in range(w):
                            grid[iy + dy][ix + dx] = False

                    x1 = x_list[ix]
                    x2 = x_list[ix + w]
                    y1 = y_list[iy]
                    y2 = y_list[iy + h]
                    comps.append(Compartment(x1=x1, x2=x2, y1=y1, y2=y2, tag=""))

        # sort for nicer order: bottom->top, left->right
        comps.sort(key=lambda c: (c.y1, c.x1, c.y2, c.x2))
        return comps

    # ---------- ACTIONS ----------
    def _clear_shelves(self):
        self._user_boards = []
        self._sel_idx = None
        self._recalc()

    def _add_shelf_in_selected(self):
        if self._sel_idx is None or self._sel_idx < 0 or self._sel_idx >= len(self._comps):
            self._set_ok(False, "Select a segment first (click on view).")
            return

        comp = self._comps[self._sel_idx]
        rel = int(self.shelfRel.value())
        y = comp.y1 + rel

        # must be INSIDE segment (not above it)
        if y <= comp.y1 or y >= comp.y2:
            self._set_ok(False, f"Shelf Y={y} is outside selected segment [{comp.y1}..{comp.y2}].")
            return

        b = Board(y=y, x1=comp.x1, x2=comp.x2, kind="shelf")
        if any((bb.y==b.y and bb.x1==b.x1 and bb.x2==b.x2) for bb in self._user_boards):
            self._set_ok(False, "This shelf already exists in that segment.")
            return

        self._user_boards.append(b)

        # after add shelf -> segment splits, so selection resets
        self._sel_idx = None
        self._recalc()

    def _select_compartment(self, idx: int):
        self._sel_idx = idx
        if 0 <= idx < len(self._comps):
            c = self._comps[idx]
            self.selInfo.setText(f"Selected: x[{c.x1}..{c.x2}] y[{c.y1}..{c.y2}]")
            # set default shelf rel to mid-height of compartment
            mid = max(1, (c.y2 - c.y1)//2)
            self.shelfRel.setValue(min(self.shelfRel.maximum(), mid))
        self._draw()  # refresh highlight

    # ---------- DRAW + RECALC ----------
    def _set_ok(self, ok: bool, msg: str = "OK"):
        if ok:
            self.status.setText("OK")
            self.status.setStyleSheet("QLabel{padding:4px 10px;border-radius:10px;background:#d7ffe1;color:#000;font-weight:700;}")
        else:
            self.status.setText("ERR")
            self.status.setStyleSheet("QLabel{padding:4px 10px;border-radius:10px;background:#ffd6d6;color:#000;font-weight:700;}")
            self.bom.setPlainText(msg)

    def _recalc(self):
        try:
            W, H = int(self.w.value()), int(self.h.value())
            divs = self._get_dividers()
            boards = self._get_boards()

            self._comps = self._compute_compartments(W, H, divs, boards)

            # update info label if selection invalid
            if self._sel_idx is None:
                self.selInfo.setText("Selected: —")
            elif self._sel_idx >= len(self._comps):
                self._sel_idx = None
                self.selInfo.setText("Selected: —")

            # debug
            txt = []
            txt.append(f"W/H: {W}/{H}")
            if divs:
                d = divs[0]
                txt.append(f"Mid: x={d.x}, h={d.h}, cap={self.midCap.currentText()}")
            else:
                txt.append("Mid: off")
            txt.append("")
            txt.append("Boards:")
            for b in boards:
                txt.append(f" - {b.kind}: y={b.y}, x=[{b.x1}..{b.x2}]")
            txt.append("")
            txt.append(f"Compartments: {len(self._comps)}")
            for i, c in enumerate(self._comps[:24]):
                txt.append(f" [{i}] x[{c.x1}..{c.x2}] y[{c.y1}..{c.y2}]")
            self.bom.setPlainText("\n".join(txt))

            self._set_ok(True)
            self._draw()
        except Exception:
            import traceback
            self._set_ok(False, traceback.format_exc())

    def _draw(self):
        self.scene.clear()

        W, H = int(self.w.value()), int(self.h.value())
        divs = self._get_dividers()
        boards = self._get_boards()

        # scale to fit
        scale = 0.85
        pxW = W * scale
        pxH = H * scale

        penOuter = QtGui.QPen(QtGui.QColor(40, 40, 40), 2)
        self.scene.addRect(QtCore.QRectF(0, 0, pxW, pxH), penOuter)

        # helpers: mm->px (y inverted)
        def X(mm: int) -> float:
            return mm * scale
        def Y(mm_from_bottom: int) -> float:
            return (H - mm_from_bottom) * scale

        # draw dividers
        for d in divs:
            x = X(d.x)
            y_top = Y(d.h)
            y_bot = Y(0)
            self.scene.addLine(x, y_top, x, y_bot, QtGui.QPen(QtGui.QColor(70, 70, 70), 2))

        # draw boards
        for b in boards:
            y = Y(b.y)
            x1 = X(b.x1)
            x2 = X(b.x2)
            col = QtGui.QColor(80, 80, 80) if b.kind == "shelf" else QtGui.QColor(120, 80, 20)
            self.scene.addLine(x1, y, x2, y, QtGui.QPen(col, 3))

        # compartments clickable
        for i, c in enumerate(self._comps):
            rect = QtCore.QRectF(X(c.x1), Y(c.y2), (c.x2 - c.x1)*scale, (c.y2 - c.y1)*scale)
            item = _PickRect(rect, i, self)

            if self._sel_idx == i:
                item.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 2))
                item.setBrush(QtGui.QBrush(QtGui.QColor(255, 80, 80, 30)))
            else:
                item.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
                item.setBrush(QtGui.QBrush(QtGui.QColor(80, 140, 255, 18)))

            self.scene.addItem(item)

        self.scene.setSceneRect(-20, -20, pxW + 40, pxH + 40)

    # ---------- public test hook ----------
    def compartments(self) -> List[Tuple[int,int,int,int]]:
        return [(c.x1, c.x2, c.y1, c.y2) for c in self._comps]