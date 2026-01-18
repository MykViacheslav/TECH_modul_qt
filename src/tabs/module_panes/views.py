from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets

class TwoViews(QtWidgets.QWidget):
    """
    Front + Top views using QGraphicsView.
    set_formatki(list, selected_id)
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sceneFront = QtWidgets.QGraphicsScene(self)
        self.sceneTop   = QtWidgets.QGraphicsScene(self)

        self.viewFront = QtWidgets.QGraphicsView(self.sceneFront)
        self.viewTop   = QtWidgets.QGraphicsView(self.sceneTop)

        self.viewFront.setRenderHints(QtGui.QPainter.Antialiasing)
        self.viewTop.setRenderHints(QtGui.QPainter.Antialiasing)

        self.labF = QtWidgets.QLabel("Widok z przodu")
        self.labT = QtWidgets.QLabel("Widok z góry")

        lf = QtWidgets.QVBoxLayout()
        lf.addWidget(self.labF)
        lf.addWidget(self.viewFront, 1)

        lt = QtWidgets.QVBoxLayout()
        lt.addWidget(self.labT)
        lt.addWidget(self.viewTop, 1)

        lay = QtWidgets.QHBoxLayout(self)
        lay.addLayout(lf, 1)
        lay.addLayout(lt, 1)

        self._last = ([], "")

    def set_formatki(self, items: list, selected_id: str = ""):
        self._last = (items or [], selected_id or "")
        self._draw()

    def _draw(self):
        items, sel = self._last
        self.sceneFront.clear()
        self.sceneTop.clear()

        # very simple grid layout (v1)
        # front: w x h
        # top:   w x h (placeholder) - later we will use orientation/depth
        def draw_scene(scene: QtWidgets.QGraphicsScene, title: str):
            margin = 20
            x, y = 0, 0
            row_h = 0
            max_w = 900  # wrap width in scene coords

            for o in items:
                if not isinstance(o, dict):
                    continue
                fid = str(o.get("id",""))
                w = float(o.get("w_mm", 300) or 300)
                h = float(o.get("h_mm", 300) or 300)

                # scale to pixels (mm -> px) crude
                scale = 0.35
                pw = max(30, w * scale)
                ph = max(30, h * scale)

                if x + pw + margin > max_w:
                    x = 0
                    y += row_h + margin
                    row_h = 0

                rect = QtCore.QRectF(x, y, pw, ph)
                pen = QtGui.QPen(QtGui.QColor(40,40,40), 2)
                brush = QtGui.QBrush(QtGui.QColor(240,240,240))

                if fid == sel:
                    pen = QtGui.QPen(QtGui.QColor(30,120,250), 4)
                    brush = QtGui.QBrush(QtGui.QColor(220,235,255))

                scene.addRect(rect, pen, brush)
                txt = f"{fid}\n{int(w)}x{int(h)}"
                t = scene.addText(txt)
                t.setPos(x + 6, y + 6)

                x += pw + margin
                row_h = max(row_h, ph)

            scene.setSceneRect(scene.itemsBoundingRect().adjusted(-20,-20,20,20))

        draw_scene(self.sceneFront, "front")
        draw_scene(self.sceneTop, "top")
