from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class EdgePreviewWidget(QWidget):
    sig_toggle_side = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(88)
        self.setMaximumHeight(94)
        self.setMinimumWidth(150)
        self._selected: set[str] = set()
        self._active_part_name: str = ""

    def _preview_rect(self) -> QRectF:
        outer_margin_x = 16.0
        outer_margin_y = 24.0
        bottom_margin = 12.0

        available_w = max(10.0, float(self.width()) - 2.0 * outer_margin_x)
        available_h = max(10.0, float(self.height()) - outer_margin_y - bottom_margin)

        preview_h = min(available_h, max(28.0, available_h * 0.64))
        preview_w = min(available_w, max(72.0, preview_h * 1.7))

        x = (float(self.width()) - preview_w) / 2.0
        y = outer_margin_y + (available_h - preview_h) / 2.0
        return QRectF(x, y, preview_w, preview_h)

    def set_selected_edges(self, edges: set[str]) -> None:
        self._selected = set(edges)
        self.update()

    def set_part_name(self, name_pl: str) -> None:
        self._active_part_name = name_pl
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self._preview_rect()

        p.fillRect(self.rect(), self.palette().window())

        p.setPen(QPen(Qt.GlobalColor.black))
        p.drawText(8, 16, f"Miniatura: {self._active_part_name or '-'}")

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f7f7f7"))
        p.drawRect(rect)

        pen_border = QPen(QColor("#1f1f1f"))
        pen_border.setWidth(2)
        p.setPen(pen_border)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        pen_base = QPen(QColor("#9a9a9a"))
        pen_base.setWidth(2)
        p.setPen(pen_base)
        p.drawLine(int(rect.left()), int(rect.top()), int(rect.right()), int(rect.top()))
        p.drawLine(int(rect.left()), int(rect.bottom()), int(rect.right()), int(rect.bottom()))
        p.drawLine(int(rect.left()), int(rect.top()), int(rect.left()), int(rect.bottom()))
        p.drawLine(int(rect.right()), int(rect.top()), int(rect.right()), int(rect.bottom()))

        pen_edge = QPen(QColor("#1f6feb"))
        pen_edge.setWidth(7)
        pen_edge.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_edge)

        inset = 2.5

        def draw_edge(side: str) -> None:
            if side == "top":
                p.drawLine(
                    int(rect.left() + inset),
                    int(rect.top() + inset),
                    int(rect.right() - inset),
                    int(rect.top() + inset),
                )
            elif side == "bottom":
                p.drawLine(
                    int(rect.left() + inset),
                    int(rect.bottom() - inset),
                    int(rect.right() - inset),
                    int(rect.bottom() - inset),
                )
            elif side == "left":
                p.drawLine(
                    int(rect.left() + inset),
                    int(rect.top() + inset),
                    int(rect.left() + inset),
                    int(rect.bottom() - inset),
                )
            elif side == "right":
                p.drawLine(
                    int(rect.right() - inset),
                    int(rect.top() + inset),
                    int(rect.right() - inset),
                    int(rect.bottom() - inset),
                )

        for side in ("top", "right", "bottom", "left"):
            if side in self._selected:
                draw_edge(side)

    def mousePressEvent(self, e) -> None:
        pos = e.pos()
        rect = self._preview_rect()

        tol = 12
        x = pos.x()
        y = pos.y()

        side: Optional[str] = None
        if rect.contains(x, y):
            d_top = abs(y - rect.top())
            d_bottom = abs(y - rect.bottom())
            d_left = abs(x - rect.left())
            d_right = abs(x - rect.right())
            dmin = min(d_top, d_bottom, d_left, d_right)
            if dmin <= tol:
                if dmin == d_top:
                    side = "top"
                elif dmin == d_bottom:
                    side = "bottom"
                elif dmin == d_left:
                    side = "left"
                else:
                    side = "right"

        if side:
            self.sig_toggle_side.emit(side)
