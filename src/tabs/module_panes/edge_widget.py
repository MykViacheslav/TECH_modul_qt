from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets

class EdgeWidget(QtWidgets.QWidget):
    """
    Click edges to toggle edge banding:
      top / bottom / left / right
    Emits: changed(dict)
    """
    changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 140)
        self._edge = {"top": False, "bottom": False, "left": False, "right": False}

    def set_edge(self, edge: dict):
        e = {"top": False, "bottom": False, "left": False, "right": False}
        if isinstance(edge, dict):
            for k in e.keys():
                e[k] = bool(edge.get(k, False))
        self._edge = e
        self.update()

    def edge(self) -> dict:
        return dict(self._edge)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        r = self.rect().adjusted(14, 14, -14, -14)
        x, y = ev.position().x(), ev.position().y()

        # detect nearest edge zone
        pad = 16
        zone = None
        if r.contains(int(x), int(y)):
            if y < r.top() + pad: zone = "top"
            elif y > r.bottom() - pad: zone = "bottom"
            elif x < r.left() + pad: zone = "left"
            elif x > r.right() - pad: zone = "right"

        if zone:
            self._edge[zone] = not self._edge[zone]
            self.update()
            self.changed.emit(self.edge())

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        r = self.rect()
        p.fillRect(r, self.palette().window())

        box = r.adjusted(14, 14, -14, -14)

        # base rect
        pen = QtGui.QPen(self.palette().text().color(), 2)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(box, 10, 10)

        # draw edges highlighted
        def draw_edge(which: str, on: bool):
            if not on:
                return
            pen2 = QtGui.QPen(QtGui.QColor(30, 180, 90), 6)  # okleina
            pen2.setCapStyle(QtCore.Qt.RoundCap)
            p.setPen(pen2)
            if which == "top":
                p.drawLine(box.topLeft() + QtCore.QPoint(10, 0), box.topRight() - QtCore.QPoint(10, 0))
            elif which == "bottom":
                p.drawLine(box.bottomLeft() + QtCore.QPoint(10, 0), box.bottomRight() - QtCore.QPoint(10, 0))
            elif which == "left":
                p.drawLine(box.topLeft() + QtCore.QPoint(0, 10), box.bottomLeft() - QtCore.QPoint(0, 10))
            elif which == "right":
                p.drawLine(box.topRight() + QtCore.QPoint(0, 10), box.bottomRight() - QtCore.QPoint(0, 10))

        for k in ("top", "bottom", "left", "right"):
            draw_edge(k, self._edge.get(k, False))

        # labels
        p.setPen(self.palette().text().color())
        f = p.font()
        f.setPointSize(max(8, f.pointSize()-1))
        p.setFont(f)
        p.drawText(r.adjusted(0, 0, 0, -4), QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter, "Kliknij krawędź okleiny")
