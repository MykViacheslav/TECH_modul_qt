from __future__ import annotations

import hashlib
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

# Paleta kolorow do obrze zy — cykliczna, rozroznialna
_EDGE_COLORS: list[str] = [
    "#2563eb",  # niebieski
    "#16a34a",  # zielony
    "#dc2626",  # czerwony
    "#d97706",  # pomaranczowy
    "#7c3aed",  # fioletowy
    "#0891b2",  # cyan
    "#be185d",  # rozowy
    "#65a30d",  # limonkowy
]

_NO_EDGE_COLOR = "#d1d5db"   # szary — brak obrzeza
_BOARD_FILL    = "#f8fafc"   # wypelnienie formatki
_BOARD_BORDER  = "#374151"   # ramka formatki
_STRIP_W       = 10          # grubosc paska obrzeza (px)
_LABEL_FONT_SZ = 7           # rozmiar czcionki etykiety


def _key_to_color(key: str) -> QColor:
    """Deterministyczny kolor dla klucza obrzeza."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return QColor(_EDGE_COLORS[h % len(_EDGE_COLORS)])


class EdgePreviewWidget(QWidget):
    """
    Podglad wizualny obrze zy formatki.

    Kazda krawedz (top/right/bottom/left) jest rysowana jako kolorowy
    pasek. Kolor zalezny od klucza obrzeza — rozne obrzeza = rozne kolory.
    Brak obrzeza = szary pasek.

    Klikniecie w krawedz emituje sig_toggle_side(side_key).
    """

    sig_toggle_side = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(130)
        self.setMaximumHeight(160)
        self.setMinimumWidth(200)
        # side_key -> edgeband_key (pusty = brak)
        self._bands: dict[str, str] = {}
        # side_key -> short label (np. skrocona nazwa)
        self._labels: dict[str, str] = {}
        self._active_part_name: str = ""

    # ── PUBLIC API ────────────────────────────────────────────────────────

    def set_edge_banding(
        self,
        bands: dict[str, str],
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        bands:  {side_key: edgeband_key}  — tylko te strony maja obrzeze.
        labels: {edgeband_key: short_label} — opcjonalne etykiety dla kluczy.
        """
        self._bands = dict(bands or {})
        self._labels = dict(labels or {})
        self.update()

    # backward-compat: akceptuj tez set (stary interfejs)
    def set_selected_edges(self, edges: set[str]) -> None:
        """Stary interfejs — tylko which sides, brak info o kluczu."""
        self._bands = {s: "__selected__" for s in edges}
        self._labels = {}
        self.update()

    def set_part_name(self, name_pl: str) -> None:
        self._active_part_name = name_pl
        self.update()

    # ── GEOMETRY ─────────────────────────────────────────────────────────

    def _board_rect(self) -> QRectF:
        """Prostokat reprezentujacy srodek formatki (bez paskow)."""
        margin = float(_STRIP_W) + 6.0
        label_h = 18.0
        w = max(60.0, float(self.width())  - 2.0 * margin)
        h = max(30.0, float(self.height()) - 2.0 * margin - label_h)
        x = (float(self.width())  - w) / 2.0
        y = label_h + (float(self.height()) - label_h - h) / 2.0
        return QRectF(x, y, w, h)

    def _side_hit(self, mx: int, my: int) -> Optional[str]:
        """Zwraca klucz strony kliknitej myszka lub None."""
        board = self._board_rect()
        sw = float(_STRIP_W)
        tol = sw + 4.0

        # rozszerzone strefy klikniecia
        strip_top    = QRectF(board.left(),              board.top()    - sw - 2, board.width(), sw + tol)
        strip_bottom = QRectF(board.left(),              board.bottom() - 2,       board.width(), sw + tol)
        strip_left   = QRectF(board.left()   - sw - 2,  board.top(),   sw + tol, board.height())
        strip_right  = QRectF(board.right()  - 2,        board.top(),   sw + tol, board.height())

        pt = QPointF(float(mx), float(my))
        if strip_top.contains(pt):    return "top"
        if strip_bottom.contains(pt): return "bottom"
        if strip_left.contains(pt):   return "left"
        if strip_right.contains(pt):  return "right"

        # fallback: bliskosc do krawedzi wewnatrz formatki
        if board.contains(pt):
            d_top    = abs(my - board.top())
            d_bottom = abs(my - board.bottom())
            d_left   = abs(mx - board.left())
            d_right  = abs(mx - board.right())
            dmin = min(d_top, d_bottom, d_left, d_right)
            if dmin <= tol:
                if dmin == d_top:    return "top"
                if dmin == d_bottom: return "bottom"
                if dmin == d_left:   return "left"
                return "right"
        return None

    # ── PAINT ─────────────────────────────────────────────────────────────

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), self.palette().window())

        # naglowek
        font_hdr = QFont()
        font_hdr.setPointSize(8)
        font_hdr.setBold(True)
        p.setFont(font_hdr)
        p.setPen(QPen(QColor("#374151")))
        p.drawText(6, 14, f"Obrzeza: {self._active_part_name or '-'}")

        board = self._board_rect()
        sw = float(_STRIP_W)

        # paski obrze zy (rysuj przed formatka, zeby formatka je przykryla w naroznikach)
        self._draw_strip(p, "top",    board, sw)
        self._draw_strip(p, "bottom", board, sw)
        self._draw_strip(p, "left",   board, sw)
        self._draw_strip(p, "right",  board, sw)

        # wypelnienie formatki
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_BOARD_FILL))
        p.drawRect(board)

        # ramka formatki
        pen_border = QPen(QColor(_BOARD_BORDER))
        pen_border.setWidth(2)
        p.setPen(pen_border)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(board)

        p.end()

    def _strip_color(self, side: str) -> QColor:
        key = self._bands.get(side, "")
        if not key:
            return QColor(_NO_EDGE_COLOR)
        if key == "__selected__":
            return QColor(_EDGE_COLORS[0])
        return _key_to_color(key)

    def _strip_label(self, side: str) -> str:
        key = self._bands.get(side, "")
        if not key:
            return ""
        if key == "__selected__":
            return "OK"
        # skrocona etykieta z self._labels albo pierwsza czesc klucza
        label = self._labels.get(key, "")
        if not label:
            label = key.split("_")[0][:6] if key else ""
        return label

    def _draw_strip(self, p: QPainter, side: str, board: QRectF, sw: float) -> None:
        color = self._strip_color(side)
        label_txt = self._strip_label(side)

        # prostokat paska
        if side == "top":
            strip = QRectF(board.left(), board.top() - sw, board.width(), sw)
        elif side == "bottom":
            strip = QRectF(board.left(), board.bottom(), board.width(), sw)
        elif side == "left":
            strip = QRectF(board.left() - sw, board.top(), sw, board.height())
        else:  # right
            strip = QRectF(board.right(), board.top(), sw, board.height())

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRect(strip)

        # ramka paska (ciemniejsza)
        darker = color.darker(130)
        pen = QPen(darker)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(strip)

        # etykieta
        if not label_txt:
            return

        font_lbl = QFont()
        font_lbl.setPointSize(_LABEL_FONT_SZ)
        p.setFont(font_lbl)

        # kontrast tekstu
        luma = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
        text_color = QColor("#ffffff") if luma < 160 else QColor("#1f2937")
        p.setPen(QPen(text_color))

        # obrot dla bocznych paskow
        if side in ("left", "right"):
            p.save()
            cx = strip.center().x()
            cy = strip.center().y()
            p.translate(cx, cy)
            p.rotate(-90.0 if side == "left" else 90.0)
            fm_rect = QRectF(-strip.height() / 2, -sw / 2, strip.height(), sw)
            p.drawText(fm_rect, Qt.AlignmentFlag.AlignCenter, label_txt)
            p.restore()
        else:
            p.drawText(strip, Qt.AlignmentFlag.AlignCenter, label_txt)

    # ── MOUSE ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, e) -> None:  # type: ignore[override]
        side = self._side_hit(e.pos().x(), e.pos().y())
        if side:
            self.sig_toggle_side.emit(side)
