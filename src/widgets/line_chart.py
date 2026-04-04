from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget


class LineChart(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 100)
        self._values: List[float] = []
        self._color = QColor('#3b82f6')

    def set_data(self, values: List[float], color: str | None = None) -> None:
        self._values = list(values or [])
        if color:
            self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._values:
            return
        w = self.width()
        h = self.height()
        path_len = max(2, len(self._values) - 1)
        max_val = max(self._values) if self._values else 1.0
        min_val = min(self._values) if self._values else 0.0
        span = max(1e-6, max_val - min_val)
        painter = QPainter(self)
        pen = QPen(self._color, 2)
        painter.setPen(pen)
        # draw polyline
        margin = 8
        x_step = max(1, (w - 2 * margin) / max(1, len(self._values) - 1))
        pts = []
        for i, v in enumerate(self._values):
            x = margin + i * x_step
            if span == 0:
                y = h / 2
            else:
                y = h - margin - ((v - min_val) / span) * (h - 2 * margin)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            painter.drawLine(QPointF(pts[i][0], pts[i][1]), QPointF(pts[i+1][0], pts[i+1][1]))
        painter.end()
