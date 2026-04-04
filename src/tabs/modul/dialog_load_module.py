from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Dict

from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QTransform, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QFrame,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QMessageBox,
    QInputDialog,
    QTabWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

from src.core.module_parts_service import build_module_parts, normalize_rail_offsets_mm
from src.domain.module_base_group import (
    BASE_GROUP_ORDER,
    BASE_GROUP_LABELS_PL,
    module_base_group_label_pl,
    normalize_module_base_group,
)
from src.domain.module_models import ModuleDef, new_module_id
from src.storage.catalog_store_json import CatalogStoreJson
from src.app.app_settings import load_drawing_settings


def _clone_module(module: ModuleDef) -> ModuleDef:
    if hasattr(module, "to_dict"):
        d = module.to_dict()
        d["module_id"] = new_module_id()
        return ModuleDef.from_dict(d)
    return ModuleDef(module_id=new_module_id())


class ModuleMiniPreview(QWidget):
    """Preview with tabs: Front, Bok (side), Góra"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = CatalogStoreJson()
        self._m: Optional[ModuleDef] = None
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        
        self.tab_front = QWidget()
        self.tab_bok = QWidget()
        self.tab_gora = QWidget()
        
        self.tabs.addTab(self.tab_front, "PRZÓD")
        self.tabs.addTab(self.tab_bok, "BOK")
        self.tabs.addTab(self.tab_gora, "GÓRA")
        
        root.addWidget(self.tabs)
        
        self._setup_tab(self.tab_front)
        self._setup_tab(self.tab_bok)
        self._setup_tab(self.tab_gora)
        
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _setup_tab(self, tab: QWidget) -> None:
        from PyQt6.QtWidgets import QGraphicsView
        view = QGraphicsView(tab)
        view.setRenderHint(True)
        view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        scene = QGraphicsScene(tab)
        view.setScene(scene)
        
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)
        
        setattr(tab, '_view', view)
        setattr(tab, '_scene', scene)

    def set_module(self, m: Optional[ModuleDef]) -> None:
        self._m = m
        self._render_current_view()

    def _on_tab_changed(self, index: int) -> None:
        self._render_current_view()

    def _render_current_view(self) -> None:
        if self._m is None:
            return
        
        module = self._effective_module()
        if module is None:
            return
        
        current_tab = self.tabs.widget(self.tabs.currentIndex())
        if current_tab is None:
            return
        
        view = getattr(current_tab, '_view', None)
        scene = getattr(current_tab, '_scene', None)
        if view is None or scene is None:
            return
        
        scene.clear()
        
        view_w = max(200, view.width() - 10)
        view_h = max(200, view.height() - 10)
        
        tab_index = self.tabs.currentIndex()
        
        if tab_index == 0:
            self._render_front_view(scene, module, view_w, view_h)
        elif tab_index == 1:
            self._render_side_view(scene, module, view_w, view_h)
        else:
            self._render_top_view(scene, module, view_w, view_h)

    def _render_front_view(self, scene: QGraphicsScene, module: ModuleDef, w: float, h: float) -> None:
        L = float(getattr(module, "width_mm", 0.0) or 0.0)
        H = float(getattr(module, "height_mm", 0.0) or 0.0)
        if L <= 0 or H <= 0:
            return
        
        scale = min(w / L, h / H) * 0.85
        
        rect_w = L * scale
        rect_h = H * scale
        x = (w - rect_w) / 2
        y = (h - rect_h) / 2
        
        from PyQt6.QtGui import QPen, QColor, QBrush
        from PyQt6.QtCore import Qt
        
        t = 18.0
        visible = set(getattr(module, "visible_parts", set()) or set())
        
        colors = {
            "side_left": QColor("#dfeaf6"),
            "side_right": QColor("#dfeaf6"),
            "top": QColor("#dfeaf6"),
            "bottom": QColor("#dfeaf6"),
            "front": QColor("#e8f4fc"),
            "back": QColor("#d5dde8"),
        }
        
        if "side_left" in visible:
            rect = scene.addRect(x, y, t * scale, rect_h, QPen(Qt.GlobalColor.black), colors.get("side_left", QBrush()))
        if "side_right" in visible:
            rect = scene.addRect(x + rect_w - t * scale, y, t * scale, rect_h, QPen(Qt.GlobalColor.black), colors.get("side_right", QBrush()))
        if "top" in visible:
            rect = scene.addRect(x, y, rect_w, t * scale, QPen(Qt.GlobalColor.black), colors.get("top", QBrush()))
        if "bottom" in visible:
            rect = scene.addRect(x, y + rect_h - t * scale, rect_w, t * scale, QPen(Qt.GlobalColor.black), colors.get("bottom", QBrush()))
        if "front" in visible:
            inner_x = x + (t if "side_left" in visible else 0) * scale
            inner_w = rect_w - (t if "side_left" in visible else 0) * scale - (t if "side_right" in visible else 0) * scale
            rect = scene.addRect(inner_x, y + (t if "top" in visible else 0) * scale, inner_w, rect_h - (t if "top" in visible else 0) * scale - (t if "bottom" in visible else 0) * scale, QPen(QColor("#1f6ed4"), 2, Qt.PenStyle.DashLine), colors.get("front", QBrush()))
        
        self._add_grain_overlay_to_scene(scene, module, x, y, rect_w, rect_h, "front", scale)

    def _render_side_view(self, scene: QGraphicsScene, module: ModuleDef, w: float, h: float) -> None:
        W = float(getattr(module, "depth_mm", 0.0) or 0.0)
        H = float(getattr(module, "height_mm", 0.0) or 0.0)
        if W <= 0 or H <= 0:
            return
        
        scale = min(w / W, h / H) * 0.85
        
        rect_w = W * scale
        rect_h = H * scale
        x = (w - rect_w) / 2
        y = (h - rect_h) / 2
        
        from PyQt6.QtGui import QPen, QColor, QBrush
        from PyQt6.QtCore import Qt
        
        t = 18.0
        visible = set(getattr(module, "visible_parts", set()) or set())
        
        colors = {
            "side_left": QColor("#dfeaf6"),
            "side_right": QColor("#dfeaf6"),
            "top": QColor("#dfeaf6"),
            "bottom": QColor("#dfeaf6"),
            "front": QColor("#e8f4fc"),
            "back": QColor("#d5dde8"),
        }
        
        if "back" in visible:
            rect = scene.addRect(x + rect_w - t * scale, y, t * scale, rect_h, QPen(Qt.GlobalColor.black), colors.get("back", QBrush()))
        if "bottom" in visible:
            rect = scene.addRect(x, y + rect_h - t * scale, rect_w, t * scale, QPen(Qt.GlobalColor.black), colors.get("bottom", QBrush()))
        if "divider" in visible:
            div_count = int(getattr(module, "divider_count", 0) or 0)
            if div_count > 0:
                segment_w = (rect_w - t * scale) / (div_count + 1)
                for i in range(div_count):
                    dx = x + t * scale + segment_w * (i + 1)
                    scene.addLine(dx, y, dx, y + rect_h, QPen(Qt.GlobalColor.gray, 1))
        
        self._add_grain_overlay_to_scene(scene, module, x, y, rect_w, rect_h, "side", scale)

    def _render_top_view(self, scene: QGraphicsScene, module: ModuleDef, w: float, h: float) -> None:
        L = float(getattr(module, "width_mm", 0.0) or 0.0)
        W = float(getattr(module, "depth_mm", 0.0) or 0.0)
        if L <= 0 or W <= 0:
            return
        
        scale = min(w / L, h / W) * 0.85
        
        rect_w = L * scale
        rect_h = W * scale
        x = (w - rect_w) / 2
        y = (h - rect_h) / 2
        
        from PyQt6.QtGui import QPen, QColor, QBrush
        from PyQt6.QtCore import Qt
        
        t = 18.0
        visible = set(getattr(module, "visible_parts", set()) or set())
        
        colors = {
            "side_left": QColor("#dfeaf6"),
            "side_right": QColor("#dfeaf6"),
            "front": QColor("#e8f4fc"),
            "back": QColor("#d5dde8"),
        }
        
        if "side_left" in visible:
            rect = scene.addRect(x, y, t * scale, rect_h, QPen(Qt.GlobalColor.black), colors.get("side_left", QBrush()))
        if "side_right" in visible:
            rect = scene.addRect(x + rect_w - t * scale, y, t * scale, rect_h, QPen(Qt.GlobalColor.black), colors.get("side_right", QBrush()))
        if "back" in visible:
            rect = scene.addRect(x, y, rect_w, t * scale, QPen(Qt.GlobalColor.black), colors.get("back", QBrush()))
        
        self._add_grain_overlay_to_scene(scene, module, x, y, rect_w, rect_h, "top", scale)

    def _add_grain_overlay_to_scene(self, scene: QGraphicsScene, module: ModuleDef, x: float, y: float, w: float, h: float, view_type: str, scale: float) -> None:
        s = load_drawing_settings()
        if not s.grain_overlay_enabled:
            return
        
        style = str(s.grain_overlay_style or "").strip()
        if style == "image":
            image_path = str(s.grain_image_path or "").strip()
            if image_path:
                self._add_image_to_scene(scene, image_path, x, y, w, h)
            return
        
        if style not in ("wavy", "lines"):
            return
        
        import math
        alpha = s.grain_overlay_alpha
        spacing = s.grain_line_spacing_mm
        
        from PyQt6.QtGui import QColor
        from PyQt6.QtCore import Qt
        
        base_color = self.palette().color(QPalette.ColorRole.Text)
        color = QColor(base_color)
        color.setAlpha(alpha)
        
        pen = QPen(color)
        pen.setWidth(1)
        
        if view_type == "top":
            step = max(4.0, min(spacing, w / 4.0))
            for i in range(int(w / step) + 1):
                x_line = x + i * step
                if x_line > x + w:
                    break
                if style == "wavy":
                    for j in range(20):
                        t = j / 20
                        y1 = y + t * h
                        y2 = y + (j + 1) / 20 * h
                        offset1 = 1.5 * math.sin(t * math.pi * 0.6 + (i % 4) * 0.3)
                        offset2 = 1.5 * math.sin((j + 1) / 20 * math.pi * 0.6 + (i % 4) * 0.3)
                        scene.addLine(x_line + offset1, y1, x_line + offset2, y2, pen)
                else:
                    scene.addLine(x_line, y, x_line, y + h, pen)
        else:
            grain = "vertical" if view_type == "front" else "horizontal"
            step = max(4.0, min(spacing, h / 4.0))
            for i in range(int(h / step) + 1):
                y_line = y + i * step
                if y_line > y + h:
                    break
                if style == "wavy":
                    for j in range(20):
                        t = j / 20
                        x1 = x + t * w
                        x2 = x + (j + 1) / 20 * w
                        offset1 = 1.5 * math.sin(t * math.pi * 0.6 + (i % 4) * 0.3)
                        offset2 = 1.5 * math.sin((j + 1) / 20 * math.pi * 0.6 + (i % 4) * 0.3)
                        scene.addLine(x1, y_line + offset1, x2, y_line + offset2, pen)
                else:
                    scene.addLine(x, y_line, x + w, y_line, pen)

    def _add_image_to_scene(self, scene: QGraphicsScene, image_path: str, x: float, y: float, w: float, h: float) -> None:
        from pathlib import Path
        if not Path(image_path).exists():
            return
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return
            scaled = pixmap.scaled(int(w), int(h), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            item = QGraphicsPixmapItem(scaled)
            item.setOffset(x, y)
            item.setZValue(-1)
            scene.addItem(item)
        except Exception:
            pass

    def _effective_module(self) -> Optional[ModuleDef]:
        if self._m is None:
            return None

        module = _clone_module(self._m)
        module.parts = build_module_parts(module, self._catalog)
        return module

    def build_render_spec(self, width: Optional[float] = None, height: Optional[float] = None) -> Dict[str, object]:
        return {"status": "ok", "front_shapes": [], "top_shapes": [], "side_shapes": []}
        module = self._effective_module()
        if module is None:
            return {
                "status": "empty",
                "front_caption": "Widok z przodu",
                "top_caption": "Widok z gory",
                "front_shapes": [],
                "top_shapes": [],
            }

        width = float(width if width is not None else self.width())
        height = float(height if height is not None else self.height())

        module_width = float(getattr(module, "width_mm", 0.0) or 0.0)
        module_depth = float(getattr(module, "depth_mm", 0.0) or 0.0)
        module_height = float(getattr(module, "height_mm", 0.0) or 0.0)
        if module_width <= 0.0 or module_depth <= 0.0 or module_height <= 0.0:
            return {
                "status": "invalid",
                "front_caption": "Widok z przodu",
                "top_caption": "Widok z gory",
                "front_shapes": [],
                "top_shapes": [],
            }

        margin_x = 18.0
        margin_y = 22.0
        caption_gap = 18.0
        gap_between_views = 24.0
        caption_h = 18.0

        available_w = max(80.0, width - 2.0 * margin_x)
        available_h = max(120.0, height - 2.0 * margin_y)

        front_area_h = max(80.0, (available_h - gap_between_views) * 0.60)
        top_area_h = max(60.0, (available_h - gap_between_views) * 0.40)

        front_scale = min(available_w / module_width, max(10.0, front_area_h - caption_h - caption_gap) / module_height)
        top_scale = min(available_w / module_width, max(10.0, top_area_h - caption_h - caption_gap) / module_depth)
        scale = max(0.0001, min(front_scale, top_scale))

        front_w = module_width * scale
        front_h = module_height * scale
        top_w = module_width * scale
        top_h = module_depth * scale

        front_x = margin_x + (available_w - front_w) / 2.0
        front_y = margin_y + caption_h + caption_gap
        top_x = margin_x + (available_w - top_w) / 2.0
        top_y = margin_y + front_area_h + gap_between_views + caption_h

        front_rect = QRectF(front_x, front_y, front_w, front_h)
        top_rect = QRectF(top_x, top_y, top_w, top_h)

        return {
            "status": "ok",
            "front_caption": "Widok z przodu",
            "top_caption": "Widok z gory",
            "front_caption_pos": (front_rect.left(), front_rect.top() - caption_gap),
            "top_caption_pos": (top_rect.left(), top_rect.top() - caption_gap),
            "front_shapes": self._build_front_shapes(module, front_rect),
            "top_shapes": self._build_top_shapes(module, top_rect),
        }

    def _build_front_shapes(self, module: ModuleDef, view_rect: QRectF) -> list[dict]:
        width_mm = float(getattr(module, "width_mm", 0.0) or 0.0)
        height_mm = float(getattr(module, "height_mm", 0.0) or 0.0)
        if width_mm <= 0.0 or height_mm <= 0.0:
            return []

        visible_parts = set(getattr(module, "visible_parts", set()) or set())
        carcass_key = str((getattr(module, "materials", {}) or {}).get("carcass", "PB18") or "PB18")
        front_key = str((getattr(module, "materials", {}) or {}).get("front", "MDF19") or "MDF19")
        back_key = str((getattr(module, "materials", {}) or {}).get("back", "HDF2.5") or "HDF2.5")

        t_carcass = float(self._catalog.material_thickness(carcass_key, 18.0) or 18.0)
        t_back = float(self._catalog.material_thickness(back_key, 2.5) or 2.5)
        scale = view_rect.width() / width_mm

        top_offset_mm, bottom_offset_mm = normalize_rail_offsets_mm(
            height_mm=height_mm,
            rail_thickness_mm=t_carcass,
            top_offset_mm=float(getattr(module, "top_rail_offset_mm", 0.0) or 0.0),
            bottom_offset_mm=float(getattr(module, "bottom_rail_offset_mm", 0.0) or 0.0),
        )

        top_presence_mm = t_carcass if "top" in visible_parts else 0.0
        bottom_presence_mm = t_carcass if "bottom" in visible_parts else 0.0
        inner_x_mm = t_carcass
        inner_w_mm = max(0.0, width_mm - 2.0 * t_carcass)
        inner_y_mm = top_offset_mm + top_presence_mm
        inner_h_mm = max(0.0, height_mm - top_offset_mm - bottom_offset_mm - top_presence_mm - bottom_presence_mm)

        def mm_rect(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> QRectF:
            return QRectF(
                view_rect.left() + x_mm * scale,
                view_rect.top() + y_mm * scale,
                max(1.0, w_mm * scale),
                max(1.0, h_mm * scale),
            )

        shapes: list[dict] = []
        joint_type = str(getattr(module, "carcass_joint_type", "type1") or "type1")

        if "side_left" in visible_parts:
            side_y_mm = 0.0 if joint_type == "type1" else inner_y_mm
            side_h_mm = height_mm if joint_type == "type1" else inner_h_mm
            shapes.append({"key": "side_left", "rect": mm_rect(0.0, side_y_mm, t_carcass, side_h_mm), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        if "side_right" in visible_parts:
            side_y_mm = 0.0 if joint_type == "type1" else inner_y_mm
            side_h_mm = height_mm if joint_type == "type1" else inner_h_mm
            shapes.append({"key": "side_right", "rect": mm_rect(width_mm - t_carcass, side_y_mm, t_carcass, side_h_mm), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        if "top" in visible_parts:
            top_x_mm = t_carcass if joint_type == "type1" else 0.0
            top_w_mm = max(0.0, width_mm - 2.0 * t_carcass) if joint_type == "type1" else width_mm
            shapes.append({"key": "top", "rect": mm_rect(top_x_mm, top_offset_mm, top_w_mm, t_carcass), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        if "bottom" in visible_parts:
            bottom_x_mm = t_carcass if joint_type == "type1" else 0.0
            bottom_w_mm = max(0.0, width_mm - 2.0 * t_carcass) if joint_type == "type1" else width_mm
            bottom_y_mm = max(0.0, height_mm - t_carcass - bottom_offset_mm)
            shapes.append({"key": "bottom", "rect": mm_rect(bottom_x_mm, bottom_y_mm, bottom_w_mm, t_carcass), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        divider_count = int(getattr(module, "divider_count", 0) or 0)
        if "divider" in visible_parts and divider_count > 0:
            clear_w_mm = max(0.0, inner_w_mm - divider_count * t_carcass)
            segment_w_mm = clear_w_mm / (divider_count + 1) if (divider_count + 1) > 0 else clear_w_mm
            for index in range(1, divider_count + 1):
                x_mm = inner_x_mm + segment_w_mm * index + t_carcass * (index - 1)
                shapes.append({"key": f"divider_{index}", "rect": mm_rect(x_mm, inner_y_mm, t_carcass, inner_h_mm), "fill": "#eef3f8", "pen": "#2f2f2f"})

        shelf_count = int(getattr(module, "shelf_count", 0) or 0)
        if "shelf" in visible_parts and shelf_count > 0:
            clear_w_mm = inner_w_mm - max(0, divider_count) * t_carcass
            segment_w_mm = clear_w_mm / (divider_count + 1) if divider_count >= 0 else clear_w_mm
            mount = str(getattr(module, "shelf_mount", "right") or "right").strip().lower()
            shelf_x_mm = inner_x_mm if mount == "left" else inner_x_mm + max(0, divider_count) * t_carcass + max(0, divider_count) * segment_w_mm
            step_h_mm = inner_h_mm / (shelf_count + 1) if (shelf_count + 1) > 0 else inner_h_mm
            for index in range(1, shelf_count + 1):
                y_mm = inner_y_mm + step_h_mm * index - t_carcass / 2.0
                shapes.append({"key": f"shelf_{index}", "rect": mm_rect(shelf_x_mm, y_mm, max(0.0, segment_w_mm), t_carcass), "fill": "#f4f8fc", "pen": "#2f2f2f"})

        if "back" in visible_parts:
            shapes.append({"key": "back", "rect": mm_rect(max(0.0, width_mm - t_back), inner_y_mm, t_back, inner_h_mm), "fill": "#d5dde8", "pen": "#5d6d7d"})

        if "front" in visible_parts:
            front_layout = str(getattr(module, "front_layout", "overlay") or "overlay").strip().lower()
            if front_layout == "inset":
                x_mm = inner_x_mm
                y_mm = inner_y_mm
                w_mm = inner_w_mm
                h_mm = inner_h_mm
            else:
                x_mm = 0.0
                y_mm = 0.0
                w_mm = width_mm
                h_mm = height_mm
            shapes.append({"key": "front", "rect": mm_rect(x_mm, y_mm, w_mm, h_mm), "fill": None, "pen": "#1f6ed4", "dash": True})

        return shapes

    def _build_top_shapes(self, module: ModuleDef, view_rect: QRectF) -> list[dict]:
        width_mm = float(getattr(module, "width_mm", 0.0) or 0.0)
        depth_mm = float(getattr(module, "depth_mm", 0.0) or 0.0)
        if width_mm <= 0.0 or depth_mm <= 0.0:
            return []

        visible_parts = set(getattr(module, "visible_parts", set()) or set())
        carcass_key = str((getattr(module, "materials", {}) or {}).get("carcass", "PB18") or "PB18")
        front_key = str((getattr(module, "materials", {}) or {}).get("front", "MDF19") or "MDF19")
        back_key = str((getattr(module, "materials", {}) or {}).get("back", "HDF2.5") or "HDF2.5")

        t_carcass = float(self._catalog.material_thickness(carcass_key, 18.0) or 18.0)
        t_front = float(self._catalog.material_thickness(front_key, 19.0) or 19.0)
        t_back = float(self._catalog.material_thickness(back_key, 2.5) or 2.5)
        scale = view_rect.width() / width_mm

        def mm_rect(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> QRectF:
            return QRectF(
                view_rect.left() + x_mm * scale,
                view_rect.top() + y_mm * scale,
                max(1.0, w_mm * scale),
                max(1.0, h_mm * scale),
            )

        shapes: list[dict] = [{"key": "outline", "rect": mm_rect(0.0, 0.0, width_mm, depth_mm), "fill": None, "pen": "#1f1f1f"}]

        if "side_left" in visible_parts:
            shapes.append({"key": "side_left", "rect": mm_rect(0.0, 0.0, t_carcass, depth_mm), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        if "side_right" in visible_parts:
            shapes.append({"key": "side_right", "rect": mm_rect(width_mm - t_carcass, 0.0, t_carcass, depth_mm), "fill": "#dfeaf6", "pen": "#1f1f1f"})

        divider_count = int(getattr(module, "divider_count", 0) or 0)
        inner_x_mm = t_carcass
        inner_w_mm = max(0.0, width_mm - 2.0 * t_carcass)
        if "divider" in visible_parts and divider_count > 0:
            clear_w_mm = max(0.0, inner_w_mm - divider_count * t_carcass)
            segment_w_mm = clear_w_mm / (divider_count + 1) if (divider_count + 1) > 0 else clear_w_mm
            for index in range(1, divider_count + 1):
                x_mm = inner_x_mm + segment_w_mm * index + t_carcass * (index - 1)
                shapes.append({"key": f"divider_{index}", "rect": mm_rect(x_mm, 0.0, t_carcass, depth_mm), "fill": "#eef3f8", "pen": "#2f2f2f"})

        if "front" in visible_parts:
            front_layout = str(getattr(module, "front_layout", "overlay") or "overlay").strip().lower()
            if front_layout == "inset":
                front_y_mm = 0.0
                front_h_mm = min(t_front, depth_mm)
                front_x_mm = t_carcass
                front_w_mm = max(0.0, width_mm - 2.0 * t_carcass)
            else:
                front_y_mm = 0.0
                front_h_mm = min(t_front, depth_mm)
                front_x_mm = 0.0
                front_w_mm = width_mm
            shapes.append({"key": "front", "rect": mm_rect(front_x_mm, front_y_mm, front_w_mm, front_h_mm), "fill": None, "pen": "#1f6ed4", "dash": True})

        if "back" in visible_parts:
            back_h_mm = min(t_back, depth_mm)
            shapes.append({"key": "back", "rect": mm_rect(0.0, max(0.0, depth_mm - back_h_mm), width_mm, back_h_mm), "fill": "#d5dde8", "pen": "#5d6d7d"})

        return shapes

    def paintEvent(self, _event) -> None:
        import math
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        spec = self.build_render_spec()
        status = str(spec.get("status", "empty"))

        if status == "empty":
            painter.setPen(QPen(QColor("#666666")))
            painter.drawText(12, 22, "Brak podgladu")
            return

        if status == "invalid":
            painter.setPen(QPen(QColor("#aa0000")))
            painter.drawText(12, 22, "Nieprawidlowe wymiary")
            return

        painter.setPen(QPen(QColor("#333333")))
        front_caption_pos = spec.get("front_caption_pos", (12.0, 18.0))
        top_caption_pos = spec.get("top_caption_pos", (12.0, 120.0))
        painter.drawText(int(front_caption_pos[0]), int(front_caption_pos[1]), str(spec.get("front_caption", "Widok z przodu")))
        painter.drawText(int(top_caption_pos[0]), int(top_caption_pos[1]), str(spec.get("top_caption", "Widok z gory")))

        self._paint_shapes(painter, list(spec.get("front_shapes", [])))
        self._paint_shapes(painter, list(spec.get("top_shapes", [])))
        
        self._paint_grain_overlay(painter, spec)

    def _paint_grain_overlay(self, painter: QPainter, spec: dict) -> None:
        s = load_drawing_settings()
        if not s.grain_overlay_enabled:
            return
        
        style = str(s.grain_overlay_style or "wavy").strip()
        if style == "image":
            image_path = str(s.grain_image_path or "").strip()
            if not image_path:
                return
            self._paint_image_texture(painter, spec, image_path)
            return
        
        alpha = s.grain_overlay_alpha
        spacing = s.grain_line_spacing_mm
        
        base_color = self.palette().color(QPalette.ColorRole.Text)
        color = QColor(base_color)
        color.setAlpha(alpha)
        
        pen = QPen(color)
        pen.setWidth(1)
        
        front_shapes = list(spec.get("front_shapes", []))
        for shape in front_shapes:
            rect = shape.get("rect")
            if not isinstance(rect, QRectF):
                continue
            
            key = str(shape.get("key", ""))
            grain = self._get_part_grain(key)
            if not grain:
                continue
            
            self._draw_wavy_grain(painter, rect, grain, spacing, pen)

    def _get_part_grain(self, part_key: str) -> str:
        from src.domain.module_models import GRAIN_VERTICAL, GRAIN_HORIZONTAL
        key = str(part_key or "").strip().lower()
        if key in ("side_left", "side_right", "back", "front"):
            return GRAIN_VERTICAL
        if key in ("top", "bottom"):
            return GRAIN_HORIZONTAL
        if key.startswith("divider") or key.startswith("shelf"):
            return GRAIN_VERTICAL
        return GRAIN_VERTICAL

    def _draw_wavy_grain(self, painter: QPainter, rect: QRectF, grain: str, spacing: float, pen) -> None:
        import math
        w = rect.width()
        h = rect.height()
        
        if grain == "vertical":
            step = max(6.0, min(spacing, w / 4.0))
            num_lines = int(w / step)
            for i in range(num_lines + 1):
                x_base = rect.left() + i * step
                if x_base > rect.right():
                    break
                amp = 2.0 + (i % 3) * 0.8
                for j in range(20):
                    t = j / 20
                    y1 = rect.top() + t * h
                    y2 = rect.top() + (j + 1) / 20 * h
                    offset1 = amp * math.sin(t * math.pi * 0.6 + (i % 4) * 0.3)
                    offset2 = amp * math.sin((j + 1) / 20 * math.pi * 0.6 + (i % 4) * 0.3)
                    painter.drawLine(int(x_base + offset1), int(y1), int(x_base + offset2), int(y2))
        else:
            step = max(6.0, min(spacing, h / 4.0))
            num_lines = int(h / step)
            for i in range(num_lines + 1):
                y_base = rect.top() + i * step
                if y_base > rect.bottom():
                    break
                amp = 2.0 + (i % 3) * 0.8
                for j in range(20):
                    t = j / 20
                    x1 = rect.left() + t * w
                    x2 = rect.left() + (j + 1) / 20 * w
                    offset1 = amp * math.sin(t * math.pi * 0.6 + (i % 4) * 0.3)
                    offset2 = amp * math.sin((j + 1) / 20 * math.pi * 0.6 + (i % 4) * 0.3)
                    painter.drawLine(int(x1), int(y_base + offset1), int(x2), int(y_base + offset2))

    def _paint_image_texture(self, painter: QPainter, spec: dict, image_path: str) -> None:
        from pathlib import Path
        if not Path(image_path).exists():
            return
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return
            front_shapes = list(spec.get("front_shapes", []))
            for shape in front_shapes:
                rect = shape.get("rect")
                if not isinstance(rect, QRectF):
                    continue
                scaled = pixmap.scaled(
                    int(rect.width()), int(rect.height()),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(int(rect.left()), int(rect.top()), scaled)
        except Exception:
            pass

    def _paint_shapes(self, painter: QPainter, shapes: list[dict]) -> None:
        for shape in shapes:
            rect = shape.get("rect")
            if not isinstance(rect, QRectF):
                continue

            pen = QPen(QColor(str(shape.get("pen", "#1f1f1f"))))
            pen.setWidth(2)
            if bool(shape.get("dash", False)):
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            fill = shape.get("fill")
            painter.setBrush(QBrush(QColor(str(fill)))) if fill else painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)


@dataclass
class LoadDialogResult:
    name: str
    module: ModuleDef


class LoadModuleDialog(QDialog):
    def __init__(self, parent: QWidget, store: Any) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wczytaj modul")
        self.setModal(True)
        self.resize(980, 560)

        self._store = store
        self._result: Optional[LoadDialogResult] = None

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Moduly w bazie (grupy):", self))

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        left.addWidget(self.tree, 1)

        manage_box = QFrame(self)
        manage_box.setFrameShape(QFrame.Shape.StyledPanel)
        manage_layout = QVBoxLayout(manage_box)
        manage_layout.setContentsMargins(8, 8, 8, 8)
        manage_layout.setSpacing(6)

        manage_layout.addWidget(QLabel("Zarzadzanie modulem:", self))

        move_row = QHBoxLayout()
        self.cb_target_group = QComboBox(self)
        self.btn_move_group = QPushButton("Przenies do grupy", self)
        self.btn_move_group.setEnabled(False)
        move_row.addWidget(self.cb_target_group, 1)
        move_row.addWidget(self.btn_move_group, 0)
        manage_layout.addLayout(move_row)

        self.btn_add_group = QPushButton("Dodaj grupe", self)
        self.btn_add_group.setEnabled(False)
        manage_layout.addWidget(self.btn_add_group)

        self.btn_delete = QPushButton("Usun z bazy", self)
        self.btn_delete.setEnabled(False)
        manage_layout.addWidget(self.btn_delete)

        left.addWidget(manage_box)

        self.lab_err = QLabel("", self)
        self.lab_err.setStyleSheet("color:#aa0000;")
        left.addWidget(self.lab_err)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        box = QFrame(self)
        box.setFrameShape(QFrame.Shape.StyledPanel)
        vb = QVBoxLayout(box)

        vb.addWidget(QLabel("Podglad modulu (z tekstura drewna):", self))
        self.preview = ModuleMiniPreview(self)
        vb.addWidget(self.preview, 1)

        grain_row = QHBoxLayout()
        grain_row.addWidget(QLabel("Tekstura:"))
        self.lbl_grain_status = QLabel("", self)
        self.lbl_grain_status.setStyleSheet("color:#666666;font-size:11px;")
        grain_row.addWidget(self.lbl_grain_status)
        grain_row.addStretch(1)
        vb.addLayout(grain_row)

        vb.addWidget(QLabel("Informacje:", self))
        self.info = QLabel("-", self)
        self.info.setWordWrap(True)
        vb.addWidget(self.info)
        right.addWidget(box, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_ok = QPushButton("Otworz", self)
        self.btn_cancel = QPushButton("Anuluj", self)
        self.btn_ok.setEnabled(False)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        right.addLayout(btns)
        root.addLayout(right, 2)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._accept_current)
        self.tree.currentItemChanged.connect(self._on_pick)
        self.btn_move_group.clicked.connect(self._move_current_to_group)
        self.btn_add_group.clicked.connect(self._add_group_for_current_module)
        self.btn_delete.clicked.connect(self._delete_current)

        self._reload_target_group_options()
        self._fill_tree()
        self._update_grain_status()

    def result_value(self) -> Optional[LoadDialogResult]:
        return self._result

    def _update_grain_status(self) -> None:
        if not hasattr(self, 'lbl_grain_status'):
            return
        s = load_drawing_settings()
        style = str(s.grain_overlay_style or "").strip()
        if style == "image":
            path = str(s.grain_image_path or "").strip()
            if path:
                import os
                name = os.path.basename(path)
                self.lbl_grain_status.setText(f"Obraz: {name}")
            else:
                self.lbl_grain_status.setText("Brak pliku tekstury")
        elif style == "wavy":
            self.lbl_grain_status.setText("Linie faliste")
        elif style == "lines":
            self.lbl_grain_status.setText("Linie proste")
        else:
            self.lbl_grain_status.setText("Wyłączone")

    def _store_load(self, name: str) -> ModuleDef:
        for fn in ("load", "load_module", "get", "read"):
            if hasattr(self._store, fn):
                obj = getattr(self._store, fn)(name)
                if isinstance(obj, ModuleDef):
                    return obj
                if isinstance(obj, dict):
                    return ModuleDef.from_dict(obj)
        raise RuntimeError("ModuleStoreJson nie ma metody load/get/read.")

    def _fill_tree(self) -> None:
        self.tree.clear()
        self.lab_err.setText("")

        current_name = self._selected_name()

        grouped = self._store.list_grouped_names() if hasattr(self._store, "list_grouped_names") else {}
        first_child: Optional[QTreeWidgetItem] = None
        selected_child: Optional[QTreeWidgetItem] = None

        for base_group, names in grouped.items():
            group_item = QTreeWidgetItem([module_base_group_label_pl(base_group)])
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)

            for name in names:
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, name)
                group_item.addChild(child)
                if first_child is None:
                    first_child = child
                if name == current_name:
                    selected_child = child

        self.tree.expandAll()
        self._reload_target_group_options()
        if selected_child is not None:
            self.tree.setCurrentItem(selected_child)
        elif first_child is not None:
            self.tree.setCurrentItem(first_child)
        else:
            self._on_pick(None, None)

    def _selected_name(self) -> str:
        item = self.tree.currentItem()
        if item is None:
            return ""
        return str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.btn_ok.setEnabled(enabled)
        self.btn_move_group.setEnabled(enabled)
        self.btn_add_group.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

    def _reload_target_group_options(self, selected_group: str | None = None) -> None:
        current_group = str(selected_group or self.cb_target_group.currentData() or "").strip()
        groups = list(BASE_GROUP_ORDER)

        if hasattr(self._store, "list_base_groups"):
            try:
                groups = list(self._store.list_base_groups() or groups)
            except Exception:
                groups = list(BASE_GROUP_ORDER)

        normalized_current = normalize_module_base_group(current_group, fallback_key="")
        if normalized_current and normalized_current not in groups:
            groups.append(normalized_current)

        self.cb_target_group.blockSignals(True)
        self.cb_target_group.clear()
        for key in groups:
            self.cb_target_group.addItem(module_base_group_label_pl(key), key)

        idx = self.cb_target_group.findData(normalized_current)
        if idx < 0 and self.cb_target_group.count() > 0:
            idx = 0
        if idx >= 0:
            self.cb_target_group.setCurrentIndex(idx)
        self.cb_target_group.blockSignals(False)

    def _on_pick(self, item: QTreeWidgetItem | None, _prev: QTreeWidgetItem | None) -> None:
        self.lab_err.setText("")
        self._set_actions_enabled(False)
        self._result = None
        self.preview.set_module(None)
        self.info.setText("-")

        if item is None:
            return

        name = str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()
        if not name:
            return

        try:
            module = self._store_load(name)
            self.preview.set_module(module)
            self._reload_target_group_options(str(getattr(module, "base_group", "other") or "other"))

            visible_parts = sorted(list(getattr(module, "visible_parts", set()) or []))
            materials: Dict[str, str] = dict(getattr(module, "materials", {}) or {})

            self.info.setText(
                f"Nazwa: {name}\n"
                f"Grupa bazy: {module_base_group_label_pl(getattr(module, 'base_group', 'other'))}\n"
                f"Rodzina modulu: {getattr(module, 'module_family', '-')}\n"
                f"Wymiary: L={module.width_mm:g}, W={module.depth_mm:g}, H={module.height_mm:g}\n"
                f"Typ szafki: {getattr(module, 'cabinet_kind', '-')}, punkt: {getattr(module, 'ref_point', '-')}\n"
                f"Laczenie: {getattr(module, 'carcass_joint_type', '-')}\n"
                f"Polki: {getattr(module, 'shelf_count', '-')}, Piony: {getattr(module, 'divider_count', '-')}, montaz polek: {getattr(module, 'shelf_mount', '-')}\n"
                f"Materialy: korpus={materials.get('carcass', '-')}, front={materials.get('front', '-')}, plecy={materials.get('back', '-')}\n"
                f"Widoczne: {', '.join(visible_parts) if visible_parts else '-'}"
            )

            self._result = LoadDialogResult(name=name, module=module)
            self._set_actions_enabled(True)
        except Exception as exc:
            self.lab_err.setText(f"Blad wczytania: {exc}")

    def _confirm_delete(self, name: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Usun modul",
            f'Czy na pewno usunac modul "{name}" z bazy...',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _move_current_to_group(self, target_group_override: str | None = None) -> None:
        name = self._selected_name()
        if not name:
            return

        try:
            module = self._store_load(name)
            target_group = normalize_module_base_group(
                str(target_group_override or self.cb_target_group.currentData() or "other")
            )
            current_group = str(getattr(module, "base_group", "other") or "other")
            if current_group == target_group:
                self.lab_err.setText("Modul jest juz w wybranej grupie.")
                return

            module.base_group = target_group
            if hasattr(self._store, "overwrite"):
                result = self._store.overwrite(module)
                if hasattr(result, "ok") and not bool(getattr(result, "ok", False)):
                    self.lab_err.setText(str(getattr(result, "message_pl", "Nie udalo sie przeniesc modulu.")))
                    return

            self._fill_tree()
            self._reload_target_group_options(target_group)
            self._select_name(name)
            self.lab_err.setText(f'Przeniesiono modul "{name}" do grupy "{module_base_group_label_pl(target_group)}".')
        except Exception as exc:
            self.lab_err.setText(f"Blad przenoszenia: {exc}")

    def _add_group_for_current_module(self) -> None:
        name = self._selected_name()
        if not name:
            self.lab_err.setText("Najpierw wybierz modul do przeniesienia.")
            return

        group_name, ok = QInputDialog.getText(self, "Dodaj grupe", "Nazwa nowej grupy:")
        if not ok:
            return

        target_group = normalize_module_base_group(group_name, fallback_key="")
        if not target_group:
            self.lab_err.setText("Nazwa grupy nie moze byc pusta.")
            return

        self._reload_target_group_options(target_group)
        self._move_current_to_group(target_group_override=target_group)

    def _delete_current(self) -> None:
        name = self._selected_name()
        if not name:
            return

        if not self._confirm_delete(name):
            return

        try:
            if hasattr(self._store, "delete"):
                result = self._store.delete(name)
                if hasattr(result, "ok") and not bool(getattr(result, "ok", False)):
                    self.lab_err.setText(str(getattr(result, "message_pl", "Nie udalo sie usunac modulu.")))
                    return

            self._result = None
            self._fill_tree()
            if not self._selected_name():
                self.preview.set_module(None)
                self.info.setText("-")
                self._set_actions_enabled(False)
            self.lab_err.setText(f'Usunieto modul "{name}" z bazy.')
        except Exception as exc:
            self.lab_err.setText(f"Blad usuwania: {exc}")

    def _select_name(self, name: str) -> bool:
        for top_index in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(top_index)
            for child_index in range(group_item.childCount()):
                child = group_item.child(child_index)
                if str(child.data(0, Qt.ItemDataRole.UserRole) or "") == name:
                    self.tree.setCurrentItem(child)
                    return True
        return False

    def _accept_current(self) -> None:
        if self._result is None:
            return
        self.accept()
