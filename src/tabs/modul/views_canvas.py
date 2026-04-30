from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QEvent
from PyQt6.QtGui import QBrush, QPen, QPainter, QColor, QPolygonF, QPalette
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QGraphicsItem, QSizePolicy
)
from src.domain.module_models import (
    GRAIN_HORIZONTAL,
    GRAIN_VERTICAL,
    ModuleDef,
)
from src.app.app_settings import DrawingSettings, load_drawing_settings
from src.tabs.modul.module_defaults import normalize_rail_offsets_mm
from PyQt6.QtGui import QLinearGradient, QGradient

if TYPE_CHECKING:
    pass


class ZoomGraphicsView(QGraphicsView):
    def wheelEvent(self, e):
        # zoom kolkem (zamiast przewijania)
        factor = 1.15
        if e.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        e.accept()


class ViewsCanvas(QWidget):
    sig_clicked_part = pyqtSignal(str)
    sig_front_zone_handle_clicked = pyqtSignal(str)
    sig_front_zone_handle_dragged = pyqtSignal(str, float)
    sig_rail_offset_handle_clicked = pyqtSignal(str)
    sig_rail_offset_handle_dragged = pyqtSignal(str, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Front + top view need enough vertical room to stay readable.
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._is_resizing = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.view = ZoomGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor("#ffffff")) # Pure white for premium look
        self.view.setScene(self.scene)
        self.view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: #ffffff;
            }
        """)

        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.view.viewport().installEventFilter(self)

        lay.addWidget(self.view, 1)

        # TECH:
        # preview_mode = uproszczony podglad w zakladce "Modul"
        # bez technicznych napisow i bez linii wymiarowych.
        self._preview_mode = False

        # UX handles in preview
        self._last_front_zone_handle_key = ""
        self._last_rail_offset_handle_key = ""
        self._viewport_drag_handle_key = ""
        self._show_front_zone_handle_labels = True
        self._show_grain_overlay = True

    def _fit_scene_to_view(self) -> None:
        scene_rect = self.scene.sceneRect()
        if scene_rect.isNull() or scene_rect.isEmpty():
            return
        self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._is_resizing:
            return
        self._is_resizing = True
        try:
            self._fit_scene_to_view()
        finally:
            self._is_resizing = False

    @staticmethod
    def _is_front_zone_handle_key(handle_key: str) -> bool:
        return str(handle_key or "").startswith("front_zone_handle__")

    @staticmethod
    def _is_rail_offset_handle_key(handle_key: str) -> bool:
        return str(handle_key or "").startswith("rail_offset_handle__")

    @classmethod
    def _is_preview_handle_key(cls, handle_key: str) -> bool:
        return cls._is_front_zone_handle_key(handle_key) or cls._is_rail_offset_handle_key(handle_key)

    def set_preview_hide_front(self, hide: bool) -> None:
        self._preview_hide_front = bool(hide)

    def is_preview_front_hidden(self) -> bool:
        return bool(self._preview_hide_front)

    def set_preview_mode(self, on: bool) -> None:
        self._preview_mode = bool(on)

    def is_preview_mode(self) -> bool:
        return bool(getattr(self, "_preview_mode", False))

    def set_show_grain_overlay(self, on: bool) -> None:
        self._show_grain_overlay = bool(on)

    def show_grain_overlay(self) -> bool:
        return bool(getattr(self, "_show_grain_overlay", True))

    def set_active_front_zone_handle(self, handle_key: str) -> None:
        key = str(handle_key or "").strip()
        self._last_front_zone_handle_key = key if self._is_front_zone_handle_key(key) else ""
        if self._last_front_zone_handle_key:
            self._last_rail_offset_handle_key = ""

    def clear_active_front_zone_handle(self) -> None:
        self._last_front_zone_handle_key = ""

    def active_front_zone_handle_key(self) -> str:
        return str(getattr(self, "_last_front_zone_handle_key", "") or "").strip()

    def set_active_rail_offset_handle(self, handle_key: str) -> None:
        key = str(handle_key or "").strip()
        self._last_rail_offset_handle_key = key if self._is_rail_offset_handle_key(key) else ""
        if self._last_rail_offset_handle_key:
            self._last_front_zone_handle_key = ""

    def clear_active_rail_offset_handle(self) -> None:
        self._last_rail_offset_handle_key = ""

    def active_rail_offset_handle_key(self) -> str:
        return str(getattr(self, "_last_rail_offset_handle_key", "") or "").strip()

    def set_active_preview_handle(self, handle_key: str) -> None:
        key = str(handle_key or "").strip()
        if self._is_front_zone_handle_key(key):
            self.set_active_front_zone_handle(key)
        elif self._is_rail_offset_handle_key(key):
            self.set_active_rail_offset_handle(key)
        else:
            self.clear_active_preview_handle()

    def clear_active_preview_handle(self) -> None:
        self._last_front_zone_handle_key = ""
        self._last_rail_offset_handle_key = ""

    def active_preview_handle_key(self) -> str:
        return self.active_rail_offset_handle_key() or self.active_front_zone_handle_key()

    @staticmethod
    def _normalize_preview_handle_key(raw_key: str) -> str:
        key = str(raw_key or "").strip()
        if key.endswith("__label"):
            key = key[:-7]
        return key

    def _preview_handle_key_from_view_pos(self, pos) -> str:
        item = self.view.itemAt(pos)
        if item is None:
            return ""

        try:
            key = self._normalize_preview_handle_key(str(item.data(0) or ""))
        except Exception:
            key = ""

        return key if self._is_preview_handle_key(key) else ""

    def eventFilter(self, obj, event):
        if obj is self.view.viewport():
            et = event.type()

            if et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                key = self._preview_handle_key_from_view_pos(event.pos())
                if key:
                    self._viewport_drag_handle_key = key
                    self.set_active_preview_handle(key)
                    if self._is_rail_offset_handle_key(key):
                        self.sig_rail_offset_handle_clicked.emit(key)
                    elif self._is_front_zone_handle_key(key):
                        self.sig_front_zone_handle_clicked.emit(key)
                    event.accept()
                    return True

            elif et == QEvent.Type.MouseMove and self._viewport_drag_handle_key:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    scene_pos = self.view.mapToScene(event.pos())
                    key = self._viewport_drag_handle_key
                    if self._is_rail_offset_handle_key(key):
                        self.sig_rail_offset_handle_dragged.emit(key, float(scene_pos.y()))
                    elif self._is_front_zone_handle_key(key):
                        self.sig_front_zone_handle_dragged.emit(key, float(scene_pos.y()))
                    event.accept()
                    return True

            elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._viewport_drag_handle_key:
                    self._viewport_drag_handle_key = ""
                    event.accept()
                    return True

        return super().eventFilter(obj, event)

    def front_zone_handle_labels_enabled(self) -> bool:
        return bool(getattr(self, "_show_front_zone_handle_labels", True))
    @staticmethod
    def _pen(color_hex: str, px: int, dashed: bool = False) -> QPen:
        pen = QPen(QColor(color_hex))
        pen.setWidth(max(1, int(px)))
        pen.setCosmetic(True)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def _add_text_centered(self, text: str, cx: float, cy: float, rotation_deg: float = 0.0) -> None:
        t = self.scene.addText(text)
        t.setZValue(20)
        t.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        br = t.boundingRect()
        t.setTransformOriginPoint(br.center())
        t.setRotation(rotation_deg)
        t.setPos(cx - br.center().x(), cy - br.center().y())

    def _draw_grid(self, bounds: QRectF, step_mm: float, color_hex: str, width_px: int) -> None:
        pen = QPen(QColor(color_hex))
        pen.setWidth(max(1, int(width_px)))
        pen.setCosmetic(True)

        left = int(bounds.left() // step_mm) * int(step_mm)
        right = int(bounds.right() // step_mm + 1) * int(step_mm)
        top = int(bounds.top() // step_mm) * int(step_mm)
        bottom = int(bounds.bottom() // step_mm + 1) * int(step_mm)

        x = float(left)
        while x <= right:
            self.scene.addLine(x, bounds.top(), x, bounds.bottom(), pen)
            x += step_mm

        y = float(top)
        while y <= bottom:
            self.scene.addLine(bounds.left(), y, bounds.right(), y, pen)
            y += step_mm

    def _arrow_head_h(self, x: float, y: float, direction: int, size: float, pen: QPen) -> None:
        tip = QPointF(x, y)
        back = QPointF(x - direction * size, y)
        p1 = QPointF(back.x(), back.y() - size * 0.45)
        p2 = QPointF(back.x(), back.y() + size * 0.45)
        poly = QPolygonF([tip, p1, p2])
        self.scene.addPolygon(poly, pen, QBrush(pen.color()))

    def _arrow_head_v(self, x: float, y: float, direction: int, size: float, pen: QPen) -> None:
        tip = QPointF(x, y)
        back = QPointF(x, y - direction * size)
        p1 = QPointF(back.x() - size * 0.45, back.y())
        p2 = QPointF(back.x() + size * 0.45, back.y())
        poly = QPolygonF([tip, p1, p2])
        self.scene.addPolygon(poly, pen, QBrush(pen.color()))

    @staticmethod
    def _safe_float(value, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _resolve_front_layout_for_preview(self, m: ModuleDef) -> str:
        layout = str(getattr(m, "front_layout", "") or "").strip().lower()
        if layout in ("overlay", "inset"):
            return layout

        s = load_drawing_settings()
        mode = str(getattr(s, "front_mode", "external") or "external").strip().lower()
        return "inset" if mode == "internal" else "overlay"

    def _resolve_front_zone_offsets_mm(
            self,
            m: ModuleDef,
            H: float,
            t_carcass: float,
            layout: str,
    ) -> tuple[str, float, float]:
        """
        Zwraca:
        - mode
        - top_offset_mm
        - bottom_offset_mm
        """
        mode = str(getattr(m, "front_height_mode", "full") or "full").strip().lower()

        H = max(0.0, float(H))
        t_carcass = max(0.0, float(t_carcass))
        min_face_h = 2.0

        try:
            top_raw = float(getattr(m, "front_offset_top_mm", 0.0) or 0.0)
        except Exception:
            top_raw = 0.0

        try:
            bottom_raw = float(getattr(m, "front_offset_bottom_mm", 0.0) or 0.0)
        except Exception:
            bottom_raw = 0.0

        top_ref_mode = str(getattr(m, "front_top_ref_mode", "rail_end") or "rail_end").strip().lower()
        bottom_ref_mode = str(getattr(m, "front_bottom_ref_mode", "rail_end") or "rail_end").strip().lower()

        vp = set(getattr(m, "visible_parts", set()) or set())

        raw_top_rail_offset_mm = float(getattr(m, "top_rail_offset_mm", 0.0) or 0.0)
        raw_bottom_rail_offset_mm = float(getattr(m, "bottom_rail_offset_mm", 0.0) or 0.0)

        norm_top_rail_offset_mm, norm_bottom_rail_offset_mm = normalize_rail_offsets_mm(
            height_mm=H,
            rail_thickness_mm=t_carcass,
            top_offset_mm=raw_top_rail_offset_mm,
            bottom_offset_mm=raw_bottom_rail_offset_mm,
        )

        rail_top_shift_mm = norm_top_rail_offset_mm if "top" in vp else 0.0
        rail_bottom_shift_mm = norm_bottom_rail_offset_mm if "bottom" in vp else 0.0

        def _top_ref_to_offset(ref_mode: str) -> float:
            if ref_mode == "rail_start":
                return rail_top_shift_mm + 0.0
            if ref_mode == "rail_center":
                return rail_top_shift_mm + t_carcass * 0.5
            if ref_mode == "rail_end":
                return rail_top_shift_mm + t_carcass
            if ref_mode == "custom":
                return top_raw
            return rail_top_shift_mm + t_carcass

        def _bottom_ref_base_offset(ref_mode: str) -> float:
            if ref_mode == "rail_end":
                return rail_bottom_shift_mm + 0.0
            if ref_mode == "rail_center":
                return rail_bottom_shift_mm + t_carcass * 0.5
            if ref_mode == "rail_start":
                return rail_bottom_shift_mm + t_carcass
            if ref_mode == "custom":
                return 0.0
            return rail_bottom_shift_mm + 0.0

        if mode == "full":
            return "full", 0.0, 0.0

        if mode == "to_top_rail":
            top_off = max(0.0, min(_top_ref_to_offset(top_ref_mode), H))

            if bottom_ref_mode == "custom":
                bottom_candidate = bottom_raw
            else:
                bottom_candidate = _bottom_ref_base_offset(bottom_ref_mode) + bottom_raw

            max_bottom = max(0.0, H - top_off - min_face_h)
            bottom_off = max(0.0, min(bottom_candidate, max_bottom))

            max_top = max(0.0, H - bottom_off - min_face_h)
            top_off = max(0.0, min(top_off, max_top))

            return "to_top_rail", top_off, bottom_off

        top_off = max(0.0, min(top_raw, H))
        max_bottom = max(0.0, H - top_off - min_face_h)
        bottom_off = max(0.0, min(bottom_raw, max_bottom))

        max_top_2 = max(0.0, H - bottom_off - min_face_h)
        top_off = max(0.0, min(top_off, max_top_2))

        return "offsets", top_off, bottom_off

    def _resolve_front_face_gaps_mm(self, m: ModuleDef) -> tuple[float, float, float, float]:
        def _num(attr_name: str) -> float:
            try:
                return max(0.0, float(getattr(m, attr_name, 0.0) or 0.0))
            except Exception:
                return 0.0

        gap_left = _num("front_gap_left_mm")
        gap_right = _num("front_gap_right_mm")
        gap_top = _num("front_gap_top_mm")
        gap_bottom = _num("front_gap_bottom_mm")
        return gap_left, gap_right, gap_top, gap_bottom

    def _build_front_rect_front_view(
            self,
            front_view: QRectF,
            m: ModuleDef,
            L: float,
            H: float,
            t_carcass: float,
    ) -> QRectF:
        layout = self._resolve_front_layout_for_preview(m)
        _mode, top_off, bottom_off = self._resolve_front_zone_offsets_mm(
            m=m,
            H=H,
            t_carcass=t_carcass,
            layout=layout,
        )
        gap_left, gap_right, gap_top, gap_bottom = self._resolve_front_face_gaps_mm(m)

        L = max(0.0, float(L))
        H = max(0.0, float(H))
        t_carcass = max(0.0, float(t_carcass))

        if layout == "inset":
            x = front_view.left() + t_carcass + gap_left
            w = max(0.0, L - 2.0 * t_carcass - gap_left - gap_right)
        else:
            side_gap = 2.0
            x = front_view.left() + side_gap + gap_left
            w = max(0.0, L - 2.0 * side_gap - gap_left - gap_right)

        y = front_view.top() + float(top_off) + gap_top
        h = max(0.0, H - float(top_off) - float(bottom_off) - gap_top - gap_bottom)

        return QRectF(x, y, w, h)

    def _front_zone_handles_enabled(self, m: ModuleDef) -> bool:
        mode = str(getattr(m, "front_height_mode", "full") or "full").strip().lower()
        return mode in ("offsets", "to_top_rail")

    def _build_front_zone_handle_rects(
            self,
            front_rect: QRectF | None,
            m: ModuleDef,
    ) -> list[tuple[str, QRectF]]:
        if front_rect is None:
            return []

        if front_rect.width() <= 0.0 or front_rect.height() <= 0.0:
            return []

        if not self._front_zone_handles_enabled(m):
            return []

        mode = str(getattr(m, "front_height_mode", "full") or "full").strip().lower()

        grip_h = 8.0
        side_pad = max(10.0, min(40.0, float(front_rect.width()) * 0.2))
        gx = front_rect.left() + side_pad
        gw = max(24.0, float(front_rect.width()) - 2.0 * side_pad)

        out: list[tuple[str, QRectF]] = []

        if mode == "offsets":
            out.append(
                (
                    "front_zone_handle__top",
                    QRectF(gx, front_rect.top() - grip_h / 2.0, gw, grip_h),
                )
            )

        out.append(
            (
                "front_zone_handle__bottom",
                QRectF(gx, front_rect.bottom() - grip_h / 2.0, gw, grip_h),
            )
        )

        return out

    def _build_rail_offset_handle_label_specs(
            self,
            handle_rects: list[tuple[str, QRectF]],
            top_offset_mm: float,
            bottom_offset_mm: float,
    ) -> list[tuple[str, str, QPointF]]:
        out: list[tuple[str, str, QPointF]] = []

        for handle_key, handle_rect in handle_rects:
            value_mm = float(top_offset_mm if handle_key.endswith("__top") else bottom_offset_mm)
            caption = (
                f"GORA {value_mm:.1f} mm"
                if handle_key.endswith("__top")
                else f"DOL {value_mm:.1f} mm"
            )

            if handle_key.endswith("__top"):
                pos = QPointF(
                    handle_rect.center().x() - 34.0,
                    handle_rect.top() - 18.0,
                )
            else:
                pos = QPointF(
                    handle_rect.center().x() - 30.0,
                    handle_rect.bottom() + 2.0,
                )

            out.append((handle_key, caption, pos))

        return out

    def _build_front_zone_handle_label_specs(
            self,
            handle_rects: list[tuple[str, QRectF]],
    ) -> list[tuple[str, str, QPointF]]:
        out: list[tuple[str, str, QPointF]] = []

        if not self.front_zone_handle_labels_enabled():
            return out

        for handle_key, handle_rect in handle_rects:
            caption = "GORA" if handle_key.endswith("__top") else "DOL"

            if handle_key.endswith("__top"):
                pos = QPointF(
                    handle_rect.center().x() - 18.0,
                    handle_rect.top() - 18.0,
                )
            else:
                pos = QPointF(
                    handle_rect.center().x() - 14.0,
                    handle_rect.bottom() + 2.0,
                )

            out.append((handle_key, caption, pos))

        return out

    def render_module(
            self,
            m: ModuleDef,
            fit: bool = True,
            selected_part_key: str = "",
            show_dimensions: bool = True,
            show_view_labels: bool = True,
    ) -> None:
        import os, time as _time
        from src.core.perf.perf_timer import perf_log
        _PERF = os.environ.get("TECH_PERF") == "1"
        _rm_t0 = _time.perf_counter_ns() if _PERF else 0

        s = load_drawing_settings()
        self.scene.clear()

        preview_mode = bool(getattr(self, "_preview_mode", False))
        effective_show_dimensions = bool(show_dimensions)
        effective_show_view_labels = bool(show_view_labels) and (not preview_mode)

        pen_rect = self._pen(s.rect_line_color, s.rect_line_width_px)
        pen_dim = self._pen(s.dim_line_color, s.dim_line_width_px)

        L = float(m.width_mm)
        W = float(m.depth_mm)
        H = float(m.height_mm)

        # grubosc korpusu z czesci (jesli jest)
        t_carcass = 18.0
        p_sl = (m.parts or {}).get("side_left")
        if p_sl and p_sl.dims_mm and "t" in p_sl.dims_mm:
            t_carcass = float(p_sl.dims_mm["t"])

        # grubosci front/plecy
        t_front = float((m.parts.get("front").dims_mm.get("t", 18.0)) if m.parts.get("front") else 18.0)
        t_back = float((m.parts.get("back").dims_mm.get("t", 3.0)) if m.parts.get("back") else 3.0)

        front_view = QRectF(0, 0, L, H)
        # Gap miedzy widokiem z przodu a widokiem z gory:
        # mniejszy = wiecej miejsca na canvas, mniej "powietrza"
        gap = max(60.0, H * 0.08)
        top_view = QRectF(0, H + gap, L, W)

        dim_off = 80.0
        label_off_x = 120.0

        def _guess_body_thickness_mm() -> float:
            raw = ""
            try:
                raw = str((getattr(m, "materials", {}) or {}).get("carcass", "") or "")
            except Exception:
                raw = ""

            token = []
            started = False
            dot_used = False

            for ch in raw:
                if ch.isdigit():
                    token.append(ch)
                    started = True
                elif ch in ",." and started and not dot_used:
                    token.append(".")
                    dot_used = True
                elif started:
                    break

            try:
                return float("".join(token)) if token else 18.0
            except Exception:
                return 18.0

        body_t = _guess_body_thickness_mm()

        preview_hide_front = False
        for _attr in (
                "_temp_hide_front_preview",
                "_preview_hide_front",
                "_front_hidden_in_preview",
                "_hide_front_in_preview",
        ):
            preview_hide_front = preview_hide_front or bool(getattr(self, _attr, False))

        if hasattr(self, "is_front_hidden_in_preview"):
            try:
                preview_hide_front = preview_hide_front or bool(self.is_front_hidden_in_preview())
            except Exception:
                pass

        vp = set(m.visible_parts or set())

        front_layout = self._resolve_front_layout_for_preview(m)

        show_front_on_preview = bool(getattr(s, "show_front_part", True)) and (not preview_hide_front) and (
                "front" in vp
        )

        def _resolve_front_face_rect() -> QRectF | None:
            if not show_front_on_preview:
                return None

            rect = self._build_front_rect_front_view(
                front_view=front_view,
                m=m,
                L=L,
                H=H,
                t_carcass=t_carcass,
            )

            if rect.width() <= 0.0 or rect.height() <= 0.0:
                return None

            return rect

        def _resolve_front_top_rect() -> QRectF | None:
            if not show_front_on_preview:
                return None

            ft = max(2.0, min(float(t_front), float(W)))

            if front_layout == "overlay":
                out = 5.0
                return QRectF(top_view.left(), top_view.bottom() + out, L, ft)

            return QRectF(
                top_view.left() + body_t,
                top_view.bottom() - ft,
                max(0.0, L - 2 * body_t),
                ft,
            )

        front_top_rect = _resolve_front_top_rect()

        # dodatkowy margines na front zewnetrzny w rzucie z gory
        extra_bottom = 0.0
        if front_top_rect is not None and front_layout == "overlay":
            extra_bottom = front_top_rect.height() + 35.0

        left_extra = (label_off_x + 120.0) if effective_show_view_labels else 60.0
        top_extra = (dim_off + 140.0) if effective_show_dimensions else 60.0
        right_extra = (dim_off + 200.0) if effective_show_dimensions else 80.0
        bottom_extra = 200.0 if effective_show_dimensions else 80.0

        bounds = QRectF(
            min(front_view.left() - left_extra, top_view.left() - left_extra),
            min(front_view.top() - top_extra, top_view.top() - top_extra),
            max(front_view.right() + right_extra, top_view.right() + right_extra),
            max(front_view.bottom() + bottom_extra, top_view.bottom() + bottom_extra + extra_bottom),
        )

        if s.grid_enabled:
            self._draw_grid(bounds, s.grid_step_mm, s.grid_color, s.grid_width_px)

        # obrys rzutow
        self.scene.addRect(front_view, pen_rect, QBrush(Qt.BrushStyle.NoBrush))
        self.scene.addRect(top_view, pen_rect, QBrush(Qt.BrushStyle.NoBrush))

        # etykiety
        if effective_show_view_labels:
            self._add_text_centered("PRZOD", front_view.left() - label_off_x, front_view.top() + 24.0, 0.0)
            self._add_text_centered("GORA", top_view.left() - label_off_x, top_view.top() + 24.0, 0.0)

        # klikalne recty
        class PartRect(QGraphicsRectItem):
            def __init__(
                    self,
                    rect: QRectF,
                    key: str,
                    canvas: "ViewsCanvas",
                    pen: QPen,
                    brush: QBrush,
                    z: float = 0.0,
                    active_handle: bool = False,
            ) -> None:
                super().__init__(rect)
                self.key = str(key)
                self.setData(0, self.key)
                self._canvas = canvas
                self._drag_started = False
                self._active_handle = bool(active_handle)

                self._normal_pen = pen
                self._normal_brush = brush

                # Premium Styling
                self.setPen(pen)
                
                # Dynamic Gradient for different parts
                grad = self._create_premium_gradient(key)
                self.setBrush(grad if grad else brush)
                
                self.setZValue(float(z))
                self.setToolTip(self.key)

                # Add a subtle shadow effect for depth
                self._shadow = None # Could add QGraphicsDropShadowEffect here

                self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

                if self._canvas._is_preview_handle_key(self.key):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                    self.setAcceptHoverEvents(True)
                    self._apply_handle_style(active=self._active_handle, hot=False)
            
            def _create_premium_gradient(self, key: str) -> QLinearGradient:
                rect = self.rect()
                grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
                
                if "front" in key:
                    grad.setColorAt(0, QColor("#fdfdfd"))
                    grad.setColorAt(1, QColor("#f0f4f8")) # Sleek front
                elif "side" in key:
                    grad.setColorAt(0, QColor("#f8fafc"))
                    grad.setColorAt(1, QColor("#e2e8f0")) # Technical side
                elif "bottom" in key or "top" in key:
                    grad.setColorAt(0, QColor("#f1f5f9"))
                    grad.setColorAt(1, QColor("#cbd5e1")) # Depth for top/bottom
                elif "glass" in key:
                    grad.setColorAt(0, QColor("#e0f2fe")) # Glass blue
                    grad.setColorAt(1, QColor("#7dd3fc"))
                else:
                    grad.setColorAt(0, QColor("#ffffff"))
                    grad.setColorAt(1, QColor("#f1f5f9"))
                return grad

            def _apply_handle_style(self, active: bool = False, hot: bool = False) -> None:
                if not self._canvas._is_preview_handle_key(self.key):
                    self.setPen(self._normal_pen)
                    self.setBrush(self._normal_brush)
                    return

                if hot:
                    line = QColor("#c2410c")
                    fill = QColor("#fde2b8")
                    width = 3.0
                elif active:
                    line = QColor("#d97706")
                    fill = QColor("#fde7c7")
                    width = 2.6
                else:
                    line = QColor("#0f4c81")
                    fill = QColor("#d9ebff")
                    width = 2.0

                fill.setAlpha(130)

                pen = QPen(line, width)
                pen.setStyle(Qt.PenStyle.SolidLine)
                brush = QBrush(fill)

                self.setPen(pen)
                self.setBrush(brush)

            def hoverEnterEvent(self, event) -> None:
                try:
                    if self._canvas._is_preview_handle_key(self.key):
                        active = (self._canvas.active_preview_handle_key() == self.key)
                        self._apply_handle_style(active=active, hot=True)
                except Exception:
                    pass
                event.accept()

            def hoverLeaveEvent(self, event) -> None:
                try:
                    if self._canvas._is_preview_handle_key(self.key):
                        active = (self._canvas.active_preview_handle_key() == self.key)
                        self._apply_handle_style(active=active, hot=False)
                except Exception:
                    pass
                event.accept()

            def mousePressEvent(self, event) -> None:
                try:
                    if self._canvas._is_front_zone_handle_key(self.key):
                        self._drag_started = True
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self._canvas.set_active_front_zone_handle(self.key)
                        self._apply_handle_style(active=True, hot=True)
                        self._canvas.sig_front_zone_handle_clicked.emit(self.key)
                    elif self._canvas._is_rail_offset_handle_key(self.key):
                        self._drag_started = True
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self._canvas.set_active_rail_offset_handle(self.key)
                        self._apply_handle_style(active=True, hot=True)
                        self._canvas.sig_rail_offset_handle_clicked.emit(self.key)
                    else:
                        self._canvas.clear_active_preview_handle()
                        self._canvas.sig_clicked_part.emit(self.key)
                except Exception:
                    pass
                event.accept()

            def mouseMoveEvent(self, event) -> None:
                try:
                    if self._canvas._is_front_zone_handle_key(self.key) and self._drag_started:
                        self._canvas.sig_front_zone_handle_dragged.emit(
                            self.key,
                            float(event.scenePos().y()),
                        )
                    elif self._canvas._is_rail_offset_handle_key(self.key) and self._drag_started:
                        self._canvas.sig_rail_offset_handle_dragged.emit(
                            self.key,
                            float(event.scenePos().y()),
                        )
                except Exception:
                    pass
                event.accept()

            def mouseReleaseEvent(self, event) -> None:
                try:
                    if self._canvas._is_preview_handle_key(self.key):
                        self._drag_started = False
                        self.setCursor(Qt.CursorShape.SizeVerCursor)
                        self._apply_handle_style(active=True, hot=False)
                except Exception:
                    pass
                event.accept()
        def add_part_rect(
                key: str,
                rect: QRectF,
                dashed: bool = False,
                z: float = 5.0,
        ) -> None:
            def _base_part_key(raw_key: str) -> str:
                out = str(raw_key or "").strip()
                if "__" in out:
                    out = out.split("__", 1)[0]
                if "@" in out:
                    out = out.split("@", 1)[0]
                return out.strip()

            def _resolve_part_grain(raw_key: str) -> str:
                base_key = _base_part_key(raw_key)
                if not base_key:
                    return ""
                if base_key.startswith("front_zone_handle") or base_key.startswith("rail_offset_handle"):
                    return ""
                part = (m.parts or {}).get(base_key)
                if part is None:
                    return ""
                try:
                    return str(part.effective_grain() or "")
                except Exception:
                    return ""

            def _draw_grain_overlay(raw_rect: QRectF, grain_direction: str, z_value: float) -> None:
                if not self.show_grain_overlay():
                    return
                gd = str(grain_direction or "").strip()
                if gd not in (GRAIN_VERTICAL, GRAIN_HORIZONTAL):
                    return
                if raw_rect.width() < 6.0 or raw_rect.height() < 6.0:
                    return

                s = load_drawing_settings()
                style = str(getattr(s, "grain_overlay_style", "wavy")).strip()
                alpha = int(getattr(s, "grain_overlay_alpha", 80))
                spacing = float(getattr(s, "grain_line_spacing_mm", 15.0))
                image_path = str(getattr(s, "grain_image_path", "") or "").strip()

                if style == "image" and image_path:
                    _draw_image_grain(raw_rect, image_path, gd, z_value, alpha)
                    return

                base = self.palette().color(QPalette.ColorRole.Text)
                color = QColor(base)
                color.setAlpha(alpha)

                pen = QPen(color)
                pen.setWidth(1)
                pen.setCosmetic(True)

                inset = 1.2
                w = raw_rect.width() - inset * 2
                h = raw_rect.height() - inset * 2

                if style == "lines":
                    if gd == GRAIN_VERTICAL:
                        step = max(8.0, min(spacing, w / 4.0))
                        num_lines = int(w / step)
                        for i in range(num_lines + 1):
                            x = raw_rect.left() + inset + i * step
                            if x > raw_rect.right() - inset:
                                break
                            line = self.scene.addLine(
                                x, raw_rect.top() + inset,
                                x, raw_rect.bottom() - inset,
                                pen,
                            )
                            line.setZValue(float(z_value) + 0.15)
                    else:
                        step = max(8.0, min(spacing, h / 4.0))
                        num_lines = int(h / step)
                        for i in range(num_lines + 1):
                            y = raw_rect.top() + inset + i * step
                            if y > raw_rect.bottom() - inset:
                                break
                            line = self.scene.addLine(
                                raw_rect.left() + inset, y,
                                raw_rect.right() - inset, y,
                                pen,
                            )
                            line.setZValue(float(z_value) + 0.15)
                else:
                    if gd == GRAIN_VERTICAL:
                        step = max(8.0, min(spacing, w / 4.0))
                        num_lines = int(w / step)
                        
                        for i in range(num_lines + 1):
                            x_base = raw_rect.left() + inset + i * step
                            if x_base > raw_rect.right() - inset:
                                break
                            
                            points = []
                            num_points = 20
                            amp = 2.5 + (i % 3) * 0.8
                            freq = 0.15 + (i % 2) * 0.05
                            phase = (i % 4) * 0.3
                            
                            for j in range(num_points + 1):
                                t = j / num_points
                                y = raw_rect.top() + inset + t * h
                                
                                import math
                                offset = amp * math.sin(t * math.pi * freq * 4 + phase)
                                offset += (t - 0.5) * 1.5
                                
                                points.append(QPointF(x_base + offset, y))
                            
                            for j in range(len(points) - 1):
                                line = self.scene.addLine(
                                    points[j].x(), points[j].y(),
                                    points[j + 1].x(), points[j + 1].y(),
                                    pen,
                                )
                                line.setZValue(float(z_value) + 0.15)
                    
                    else:
                        step = max(8.0, min(spacing, h / 4.0))
                        num_lines = int(h / step)
                        
                        for i in range(num_lines + 1):
                            y_base = raw_rect.top() + inset + i * step
                            if y_base > raw_rect.bottom() - inset:
                                break
                            
                            points = []
                            num_points = 20
                            amp = 2.5 + (i % 3) * 0.8
                            freq = 0.15 + (i % 2) * 0.05
                            phase = (i % 4) * 0.3
                            
                            for j in range(num_points + 1):
                                t = j / num_points
                                x = raw_rect.left() + inset + t * w
                                
                                import math
                                offset = amp * math.sin(t * math.pi * freq * 4 + phase)
                                offset += (t - 0.5) * 1.5
                                
                                points.append(QPointF(x, y_base + offset))
                            
                            for j in range(len(points) - 1):
                                line = self.scene.addLine(
                                    points[j].x(), points[j].y(),
                                    points[j + 1].x(), points[j + 1].y(),
                                    pen,
                                )
                                line.setZValue(float(z_value) + 0.15)

            def _draw_image_grain(raw_rect: QRectF, image_path: str, gd: str, z_value: float, alpha: int) -> None:
                from pathlib import Path
                if not Path(image_path).exists():
                    return
                
                try:
                    pixmap = QPixmap(image_path)
                    if pixmap.isNull():
                        return
                    
                    target_w = raw_rect.width()
                    target_h = raw_rect.height()
                    
                    scaled = pixmap.scaled(
                        int(target_w), int(target_h),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    
                    if gd == GRAIN_HORIZONTAL:
                        transform = QTransform()
                        transform.rotate(90)
                        scaled = scaled.transformed(transform)
                        scaled = scaled.scaled(
                            int(target_h), int(target_w),
                            Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    
                    item = QGraphicsPixmapItem(scaled)
                    item.setOffset(raw_rect.left(), raw_rect.top())
                    item.setZValue(float(z_value) + 0.1)
                    self.scene.addItem(item)
                    
                except Exception:
                    pass

            sel = (key == selected_part_key) or (
                    selected_part_key == "front" and str(key).startswith("front__")
            )

            p = self._pen(s.rect_line_color, s.rect_line_width_px + (2 if sel else 0), dashed=dashed)

            br = QBrush(Qt.BrushStyle.NoBrush)
            if sel:
                c = QColor(s.dim_line_color)
                c.setAlpha(40)
                br = QBrush(c)

            active_handle = (key == self.active_preview_handle_key())

            item = PartRect(
                rect,
                key,
                self,
                p,
                br,
                z,
                active_handle=active_handle,
            )
            self.scene.addItem(item)

            _draw_grain_overlay(rect, _resolve_part_grain(key), z)

        def add_front_zone_label(
                key: str,
                caption: str,
                pos: QPointF,
                active: bool = False,
        ) -> None:
            item = QGraphicsSimpleTextItem(caption)
            item.setData(0, key)
            item.setPos(pos)
            item.setZValue(13)

            color = QColor("#d97706" if active else "#0f4c81")
            item.setBrush(QBrush(color))
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

            self.scene.addItem(item)


        vp = set(m.visible_parts or set())
        jt = getattr(m, "carcass_joint_type", "type1")

        # ---------------- PRZOD: rama korpusu wg typu ----------------
        t = float(t_carcass)

        raw_top_rail_offset_mm = float(getattr(m, "top_rail_offset_mm", 0.0) or 0.0)
        raw_bottom_rail_offset_mm = float(getattr(m, "bottom_rail_offset_mm", 0.0) or 0.0)

        norm_top_rail_offset_mm, norm_bottom_rail_offset_mm = normalize_rail_offsets_mm(
            height_mm=H,
            rail_thickness_mm=t,
            top_offset_mm=raw_top_rail_offset_mm,
            bottom_offset_mm=raw_bottom_rail_offset_mm,
        )

        top_rail_offset_mm = norm_top_rail_offset_mm if "top" in vp else 0.0
        bottom_rail_offset_mm = norm_bottom_rail_offset_mm if "bottom" in vp else 0.0

        top_rail_presence_mm = t if "top" in vp else 0.0
        bottom_rail_presence_mm = t if "bottom" in vp else 0.0

        top_y = front_view.top() + top_rail_offset_mm
        bot_y = front_view.bottom() - bottom_rail_presence_mm - bottom_rail_offset_mm

        if jt == "type1":
            side_y = front_view.top()
            side_h = H

            top_x = front_view.left() + t
            top_w = max(0.0, L - 2 * t)

            bot_x = top_x
            bot_w = top_w
        else:
            side_y = front_view.top() + top_rail_presence_mm + top_rail_offset_mm
            side_h = max(
                0.0,
                H - top_rail_presence_mm - bottom_rail_presence_mm - top_rail_offset_mm - bottom_rail_offset_mm,
            )

            top_x = front_view.left()
            top_w = L

            bot_x = top_x
            bot_w = top_w

        if "side_left" in vp:
            add_part_rect("side_left", QRectF(front_view.left(), side_y, t, side_h), z=6)
        if "side_right" in vp:
            add_part_rect("side_right", QRectF(front_view.right() - t, side_y, t, side_h), z=6)

        if "top" in vp:
            add_part_rect("top", QRectF(top_x, top_y, top_w, t), z=7)
        if "bottom" in vp:
            add_part_rect("bottom", QRectF(bot_x, bot_y, bot_w, t), z=7)

        rail_handle_rects: list[tuple[str, QRectF]] = []
        rail_grip_h = 20.0

        show_rail_handles = str(selected_part_key or "").strip() != "front"

        if show_rail_handles and "top" in vp and top_w > 0.0:
            top_pad = max(10.0, min(40.0, float(top_w) * 0.2))
            top_handle_w = max(36.0, float(top_w) - 2.0 * top_pad)
            rail_handle_rects.append(
                (
                    "rail_offset_handle__top",
                    QRectF(top_x + top_pad, top_y - rail_grip_h / 2.0, top_handle_w, rail_grip_h),
                )
            )

        if show_rail_handles and "bottom" in vp and bot_w > 0.0:
            bottom_pad = max(10.0, min(40.0, float(bot_w) * 0.2))
            bottom_handle_w = max(36.0, float(bot_w) - 2.0 * bottom_pad)
            rail_handle_rects.append(
                (
                    "rail_offset_handle__bottom",
                    QRectF(bot_x + bottom_pad, bot_y - rail_grip_h / 2.0, bottom_handle_w, rail_grip_h),
                )
            )

        for handle_key, handle_rect in rail_handle_rects:
            add_part_rect(
                handle_key,
                handle_rect,
                dashed=False,
                z=11,
            )

            grip_size = max(10.0, min(14.0, handle_rect.height()))
            grip_y = handle_rect.center().y() - grip_size / 2.0
            left_grip = QRectF(
                handle_rect.left() - grip_size * 0.5,
                grip_y,
                grip_size,
                grip_size,
            )
            right_grip = QRectF(
                handle_rect.right() - grip_size * 0.5,
                grip_y,
                grip_size,
                grip_size,
            )

            add_part_rect(
                handle_key,
                left_grip,
                dashed=False,
                z=12,
            )
            add_part_rect(
                handle_key,
                right_grip,
                dashed=False,
                z=12,
            )

        rail_label_specs = self._build_rail_offset_handle_label_specs(
            rail_handle_rects,
            top_offset_mm=top_rail_offset_mm,
            bottom_offset_mm=bottom_rail_offset_mm,
        )
        for handle_key, caption, pos in rail_label_specs:
            add_front_zone_label(
                key=f"{handle_key}__label",
                caption=caption,
                pos=pos,
                active=(handle_key == self.active_rail_offset_handle_key()),
            )


        active_rail_handle_key = self.active_rail_offset_handle_key()
        if active_rail_handle_key:
            active_rail_rect = None
            for handle_key, handle_rect in rail_handle_rects:
                if handle_key == active_rail_handle_key:
                    active_rail_rect = handle_rect
                    break

            if active_rail_rect is not None:
                guide_pen = self._pen("#d97706", max(2, s.dim_line_width_px), dashed=True)
                guide = self.scene.addLine(
                    front_view.left(),
                    active_rail_rect.center().y(),
                    front_view.right(),
                    active_rail_rect.center().y(),
                    guide_pen,
                )
                guide.setData(0, f"{active_rail_handle_key}__guide")
                guide.setZValue(10.5)
        # --- POLKI/PIONY (klikalne) + POLKI w segmencie left/right ---
        vp = set(getattr(m, "visible_parts", set()) or set())

        div_n = int(getattr(m, "divider_count", 0) or 0) if ("divider" in vp) else 0
        shelf_n = int(getattr(m, "shelf_count", 0) or 0) if ("shelf" in vp) else 0

        parts = getattr(m, "parts", {}) or {}
        parts_keys = list(parts.keys())

        def _idx_of(k: str) -> int:
            s_key = str(k)
            for sep in ("_", "-"):
                if sep in s_key:
                    tail = s_key.split(sep)[-1]
                    if tail.isdigit():
                        return int(tail)
            return 999

        div_keys = sorted(
            [k for k in parts_keys if str(k).startswith("divider_") or str(k).startswith("divider-")],
            key=lambda x: _idx_of(str(x))
        )
        shelf_keys = sorted(
            [k for k in parts_keys if str(k).startswith("shelf_") or str(k).startswith("shelf-")],
            key=lambda x: _idx_of(str(x))
        )

        # fallback (wazne dla testow i gdy parts chwilowo puste)
        if not div_keys and div_n > 0:
            div_keys = [f"divider_{i}" for i in range(1, div_n + 1)]
        if not shelf_keys and shelf_n > 0:
            shelf_keys = [f"shelf_{i}" for i in range(1, shelf_n + 1)]

        # swiat'o (zawsze miedzy wiencami)
        inner_x = front_view.left() + t
        inner_y = front_view.top() + top_rail_presence_mm + top_rail_offset_mm
        inner_w = max(0.0, L - 2 * t)
        inner_h = max(
            0.0,
            H - top_rail_presence_mm - bottom_rail_presence_mm - top_rail_offset_mm - bottom_rail_offset_mm,
        )

        # segmenty + piony:
        # szerokosc przegród bierze sie z realnej czesci (dims_mm["t"]),
        # aby zmiana materialu byla widoczna fizycznie na rysunku.
        divider_widths: list[float] = []
        for i in range(1, div_n + 1):
            key = div_keys[i - 1] if (i - 1) < len(div_keys) else f"divider_{i}"
            try:
                part_t = float(((parts.get(key) or {}).dims_mm or {}).get("t", t) or t)
            except Exception:
                part_t = float(t)
            part_t = max(1.0, min(inner_w, part_t))
            divider_widths.append(part_t)

        seg_w = inner_w
        if div_n > 0:
            clear = max(0.0, inner_w - sum(divider_widths))
            seg_w = clear / (div_n + 1)

        divider_prefix: list[float] = [0.0]
        for w_div in divider_widths:
            divider_prefix.append(divider_prefix[-1] + float(w_div))

        # piony (klikane)
        for i in range(1, div_n + 1):
            key = div_keys[i - 1] if (i - 1) < len(div_keys) else f"divider_{i}"
            divider_w = divider_widths[i - 1] if (i - 1) < len(divider_widths) else float(t)
            x = inner_x + seg_w * i + divider_prefix[i - 1]
            add_part_rect(key=key, rect=QRectF(x, inner_y, divider_w, inner_h), dashed=False, z=6)

        # segment dla po'ek:
        # - gdy pionow brak -> po'ki w ca'ym swietle
        # - gdy piony sa -> po'ki w lewym lub prawym segmencie
        mount = str(getattr(m, "shelf_mount", "right") or "right").lower()
        draw_both_sides = (mount == "both") and (div_n > 0)

        segment_specs: list[tuple[str, int]]
        if div_n <= 0:
            segment_specs = [("single", 0)]
        elif draw_both_sides:
            segment_specs = [("left", 0), ("right", div_n)]
        elif mount == "left":
            segment_specs = [("left", 0)]
        else:
            segment_specs = [("right", div_n)]

        def _parse_shelf_key(raw_key: str) -> tuple[str, int]:
            key = str(raw_key or "").strip().lower()
            if key.startswith("shelf_left_"):
                tail = key[11:]
                return "left", int(tail) if tail.isdigit() else 999
            if key.startswith("shelf_right_"):
                tail = key[12:]
                return "right", int(tail) if tail.isdigit() else 999
            if key.startswith("shelf_"):
                tail = key[6:]
                return "single", int(tail) if tail.isdigit() else 999
            if key.startswith("shelf-"):
                tail = key[6:]
                return "single", int(tail) if tail.isdigit() else 999
            return "single", 999

        shelf_by_slot: dict[tuple[str, int], str] = {}
        for shelf_key in shelf_keys:
            side_key, shelf_idx = _parse_shelf_key(shelf_key)
            if side_key == "single" and draw_both_sides:
                continue
            slot = (side_key, shelf_idx)
            if slot not in shelf_by_slot:
                shelf_by_slot[slot] = shelf_key

        for seg_side, seg_idx in segment_specs:
            seg_x = inner_x + seg_w * seg_idx + divider_prefix[min(seg_idx, len(divider_prefix) - 1)]
            seg_x = max(inner_x, min(inner_x + max(0.0, inner_w - seg_w), seg_x))

            for idx in range(1, shelf_n + 1):
                fallback_key = f"shelf_{idx}"
                if draw_both_sides:
                    fallback_key = f"shelf_{seg_side}_{idx}"
                key = shelf_by_slot.get((seg_side, idx), fallback_key)
                try:
                    shelf_t = float(((parts.get(key) or {}).dims_mm or {}).get("t", t) or t)
                except Exception:
                    shelf_t = float(t)
                shelf_t = max(1.0, min(inner_h, shelf_t))
                y_center = inner_y + (idx / (shelf_n + 1)) * inner_h
                y_top = max(inner_y, min(inner_y + inner_h - shelf_t, y_center - shelf_t / 2.0))
                add_part_rect(key=key, rect=QRectF(seg_x, y_top, seg_w, shelf_t), dashed=False, z=6)

        front_rect = _resolve_front_face_rect()
        if front_rect is not None:
            add_part_rect(
                "front__front",
                front_rect,
                dashed=True,
                z=4,
            )

            handle_rects = self._build_front_zone_handle_rects(front_rect, m)

            for handle_key, handle_rect in handle_rects:
                add_part_rect(
                    handle_key,
                    handle_rect,
                    dashed=False,
                    z=12,
                )

            label_specs = self._build_front_zone_handle_label_specs(handle_rects)
            for handle_key, caption, pos in label_specs:
                add_front_zone_label(
                    key=f"{handle_key}__label",
                    caption=caption,
                    pos=pos,
                    active=(handle_key == self.active_front_zone_handle_key()),
                )

            # --------------------------------------------------
            # WSPOLNE USTAWIENIA FRONTU - LICZONE TYLKO RAZ
            # --------------------------------------------------
            facade_mode = str(getattr(m, "facade_mode", "doors") or "doors").strip().lower()
            drawer_count = int(getattr(m, "drawer_count", 3) or 3)

            hinge_edge_offset = float(getattr(s, "hinge_edge_offset_mm", 12.0) or 12.0)
            if hinge_edge_offset < 0.0:
                hinge_edge_offset = 12.0

            auto_double_front_width = float(getattr(s, "auto_double_front_width_mm", 600.0) or 600.0)
            if auto_double_front_width < 100.0:
                auto_double_front_width = 600.0

            try:
                gap_between_vertical = max(
                    0.0,
                    float(getattr(m, "front_gap_between_vertical_mm", 0.0) or 0.0),
                )
            except Exception:
                gap_between_vertical = 0.0

            door_left = front_rect.left()
            door_right = front_rect.right()
            door_top = front_rect.top()
            door_bottom = front_rect.bottom()

            door_w = front_rect.width()
            door_h = front_rect.height()

            is_double_door = (facade_mode == "doors") and (door_w >= auto_double_front_width)

            hinge_offset_y = 80.0
            hinge_size = 28.0

            hinge_pen = QPen(QColor(20, 20, 20))
            hinge_pen.setWidth(2)

            # --------------------------------
            # SZUFLADY
            # --------------------------------
            if facade_mode == "drawers" and drawer_count > 1:
                drawer_layout_mode = str(getattr(m, "drawer_layout_mode", "equal") or "equal").strip().lower()
                try:
                    small_front_h = float(getattr(m, "drawer_small_front_height_mm", 140.0) or 140.0)
                except Exception:
                    small_front_h = 140.0
                small_front_h = max(60.0, small_front_h)

                total_gap = gap_between_vertical * max(0, drawer_count - 1)
                free_h = max(0.0, front_rect.height() - total_gap)

                heights: list[float] = []
                if drawer_layout_mode in ("small_top", "small_bottom") and drawer_count > 1:
                    first_h = min(small_front_h, max(20.0, free_h * 0.45))
                    remaining = max(0.0, free_h - first_h)
                    each_rest = remaining / float(drawer_count - 1)
                    if drawer_layout_mode == "small_top":
                        heights = [first_h] + [each_rest for _ in range(drawer_count - 1)]
                    else:
                        heights = [each_rest for _ in range(drawer_count - 1)] + [first_h]
                else:
                    seg_h = free_h / drawer_count if drawer_count > 0 else 0.0
                    heights = [seg_h for _ in range(drawer_count)]

                cursor_y = front_rect.top()

                for i in range(1, drawer_count):
                    cursor_y += heights[i - 1]
                    split_y = cursor_y + gap_between_vertical * 0.5

                    line = self.scene.addLine(
                        front_rect.left(),
                        split_y,
                        front_rect.right(),
                        split_y,
                        pen_dim,
                    )
                    line.setZValue(9)

                    try:
                        line.key = f"front__drawer_split_{i}"
                        line.setData(0, line.key)
                    except Exception:
                        pass

                    cursor_y += gap_between_vertical

            # --------------------------------
            # DRZWI PODWOJNE
            # --------------------------------
            elif is_double_door:
                mid = door_left + door_w / 2.0

                split_line = self.scene.addLine(
                    mid,
                    door_top,
                    mid,
                    door_bottom,
                    pen_dim
                )
                split_line.setZValue(9)

                split_line.key = "front__split_line"

                hx_left = door_left + hinge_edge_offset
                for hy in (door_top + hinge_offset_y, door_bottom - hinge_offset_y):
                    hinge = self.scene.addRect(
                        hx_left - hinge_size / 2,
                        hy - hinge_size / 2,
                        hinge_size,
                        hinge_size,
                        hinge_pen
                    )
                    hinge.setZValue(10)

                    hinge_dot = self.scene.addEllipse(
                        hx_left - 3,
                        hy - 3,
                        6,
                        6,
                        hinge_pen
                    )
                    hinge_dot.setZValue(11)

                hx_right = door_right - hinge_edge_offset
                for hy in (door_top + hinge_offset_y, door_bottom - hinge_offset_y):
                    hinge = self.scene.addRect(
                        hx_right - hinge_size / 2,
                        hy - hinge_size / 2,
                        hinge_size,
                        hinge_size,
                        hinge_pen
                    )
                    hinge.setZValue(10)

                    hinge_dot = self.scene.addEllipse(
                        hx_right - 3,
                        hy - 3,
                        6,
                        6,
                        hinge_pen
                    )
                    hinge_dot.setZValue(11)

                hy1 = door_top + door_h * 0.4
                hy2 = door_top + door_h * 0.6
                handle_gap = 40.0

                h1 = self.scene.addLine(
                    mid - handle_gap,
                    hy1,
                    mid - handle_gap,
                    hy2,
                    pen_dim
                )
                h1.setZValue(10)

                h2 = self.scene.addLine(
                    mid + handle_gap,
                    hy1,
                    mid + handle_gap,
                    hy2,
                    pen_dim
                )
                h2.setZValue(10)

            # --------------------------------
            # DRZWI POJEDYNCZE
            # --------------------------------
            elif facade_mode == "doors":
                hinge_side = str(getattr(m, "door_hinge_side", "left") or "left").strip().lower()
                if hinge_side not in ("left", "right"):
                    hinge_side = "left"

                if hinge_side == "left":
                    hx = door_left + hinge_edge_offset
                else:
                    hx = door_right - hinge_edge_offset

                for hy in (door_top + hinge_offset_y, door_bottom - hinge_offset_y):
                    hinge = self.scene.addRect(
                        hx - hinge_size / 2,
                        hy - hinge_size / 2,
                        hinge_size,
                        hinge_size,
                        hinge_pen
                    )
                    hinge.setZValue(10)

                    hinge_dot = self.scene.addEllipse(
                        hx - 3,
                        hy - 3,
                        6,
                        6,
                        hinge_pen
                    )
                    hinge_dot.setZValue(11)

                handle_offset = 40.0
                if hinge_side == "left":
                    handle_x = door_right - handle_offset
                else:
                    handle_x = door_left + handle_offset

                hy1 = door_top + door_h * 0.4
                hy2 = door_top + door_h * 0.6

                handle = self.scene.addLine(
                    handle_x,
                    hy1,
                    handle_x,
                    hy2,
                    pen_dim
                )
                handle.setZValue(10)

        # ---------------- INTERNAL DRAWERS (X-RAY) ----------------
        if facade_mode == "drawers":
            d_count = drawer_count
            # Find drawer parts in the module
            drawer_parts = {k: v for k, v in (m.parts or {}).items() if k.startswith("drawer_")}
            
            # Simple X-ray pen
            xray_pen = self._pen("#94a3b8", 1, dashed=True) # Light slate dashed
            
            for i in range(1, d_count + 1):
                bottom_key = f"drawer_{i}_bottom"
                rear_key = f"drawer_{i}_rear"
                
                # We can deduce positions from the front_rect and heights
                # Or use the calculated part dimensions if available
                p_bottom = drawer_parts.get(bottom_key)
                p_rear = drawer_parts.get(rear_key)
                
                if p_bottom:
                    # In Front View: draw as a shelf-like line
                    # Calculate y position based on equal distribution for now
                    # (In a real app, we'd use the resolved positions from rules)
                    y_step = door_h / d_count
                    y_base = door_top + (i * y_step) - 16.0 # 16mm from bottom of front
                    
                    add_part_rect(
                        bottom_key, 
                        QRectF(door_left + t, y_base, door_w - 2.0*t, 16.0), 
                        dashed=True, 
                        z=5
                    )
                    
                    # In Top View: draw as board inside carcass
                    # Shift slightly for each drawer to see stacking? No, just overlap is fine.
                    add_part_rect(
                        bottom_key,
                        QRectF(top_view.left() + t + 2.0, top_view.top() + 30.0, L - 2.0*t - 4.0, W - 40.0),
                        dashed=True,
                        z=5
                    )

                if p_rear:
                    # In Front View: draw as rectangle behind front
                    y_step = door_h / d_count
                    y_base = door_top + ((i-1) * y_step) + 50.0 # start of rear
                    r_h = y_step - 70.0 # height of rear
                    
                    add_part_rect(
                        rear_key,
                        QRectF(door_left + t + 20.0, y_base, door_w - 2.0*t - 40.0, max(10.0, r_h)),
                        dashed=True,
                        z=5
                    )

        # ---------------- GORA: boki + front/plecy ----------------
        # boki jako pasy
        if "side_left" in vp:
            add_part_rect("side_left", QRectF(top_view.left(), top_view.top(), t, W), z=6)
        if "side_right" in vp:
            add_part_rect("side_right", QRectF(top_view.right() - t, top_view.top(), t, W), z=6)

        # plecy (u gory) - domyslnie rysujemy jako pas w srodku korpusu
        if "back" in vp:
            bt = min(t_back, W)
            add_part_rect("back", QRectF(top_view.left(), top_view.top(), L, bt), dashed=True, z=4)

        # front w rzucie z gory - zaleznie od typu: overlay / inset
        if front_top_rect is not None:
            add_part_rect(key="front__top", rect=front_top_rect, dashed=True, z=9)

            # wazne: zeby fitInView nie ucinalo overlay
            bounds = bounds.united(front_top_rect)
        # ---------------- Linie wymiarowe ----------------
        if effective_show_dimensions:
            tick = 26.0
            arrow = 26.0

            def dim_h(x1: float, x2: float, y_obj: float, y_dim: float, text: str) -> None:
                self.scene.addLine(x1, y_obj, x1, y_dim, pen_dim)
                self.scene.addLine(x2, y_obj, x2, y_dim, pen_dim)
                self.scene.addLine(x1, y_dim, x2, y_dim, pen_dim)

                if s.dim_end_style == "arrows":
                    self._arrow_head_h(x1, y_dim, +1, arrow, pen_dim)
                    self._arrow_head_h(x2, y_dim, -1, arrow, pen_dim)
                else:
                    self.scene.addLine(x1, y_dim - tick / 2, x1, y_dim + tick / 2, pen_dim)
                    self.scene.addLine(x2, y_dim - tick / 2, x2, y_dim + tick / 2, pen_dim)

                self._add_text_centered(text, (x1 + x2) / 2, y_dim - 30.0, 0.0)

            def dim_v(y1: float, y2: float, x_obj: float, x_dim: float, text: str) -> None:
                self.scene.addLine(x_obj, y1, x_dim, y1, pen_dim)
                self.scene.addLine(x_obj, y2, x_dim, y2, pen_dim)
                self.scene.addLine(x_dim, y1, x_dim, y2, pen_dim)

                if s.dim_end_style == "arrows":
                    self._arrow_head_v(x_dim, y1, +1, arrow, pen_dim)
                    self._arrow_head_v(x_dim, y2, -1, arrow, pen_dim)
                else:
                    self.scene.addLine(x_dim - tick / 2, y1, x_dim + tick / 2, y1, pen_dim)
                    self.scene.addLine(x_dim - tick / 2, y2, x_dim + tick / 2, y2, pen_dim)

                self._add_text_centered(text, x_dim + 28.0, (y1 + y2) / 2, -90.0)

            dim_h(front_view.left(), front_view.right(), front_view.top(), front_view.top() - dim_off, f"L = {L:g} mm")
            dim_v(front_view.top(), front_view.bottom(), front_view.right(), front_view.right() + dim_off, f"H = {H:g} mm")
            dim_v(top_view.top(), top_view.bottom(), top_view.right(), top_view.right() + dim_off, f"W = {W:g} mm")

        scene_bounds = self.scene.itemsBoundingRect()
        if scene_bounds.isNull() or scene_bounds.isEmpty():
            scene_bounds = bounds
        self.scene.setSceneRect(scene_bounds.adjusted(-20, -20, 20, 20))
        if fit:
            self._fit_scene_to_view()

        if _PERF:
            perf_log("canvas.Modul.render_module", _rm_t0)
