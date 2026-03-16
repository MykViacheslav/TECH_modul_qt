from __future__ import annotations

import html
import json

from PyQt6.QtCore import QMimeData, QPointF, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QFont, QMouseEvent, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QDoubleSpinBox,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
)

from src.app.app_settings import load_drawing_settings
from src.core.module_parts_service import build_module_parts, normalize_rail_offsets_mm
from src.domain.assembly_models import (
    AssemblyModuleItemDef,
    FurnitureAssemblyDef,
    normalize_assembly_offset_ref_mode,
)
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.domain.module_base_group import module_base_group_label_pl
from src.domain.module_models import ModuleDef, normalize_module_type
from src.domain.wall_models import WallLayoutDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.tabs.sciana.dialog_load_assembly import LoadAssemblyDialog
from src.ui.collapsible_block import CollapsibleBlock


SAVED_MODULE_MIME = "application/x-tech-modul-saved-module"
SAVED_MODULE_NAME_ROLE = int(Qt.ItemDataRole.UserRole)
SAVED_MODULE_WIDTH_ROLE = SAVED_MODULE_NAME_ROLE + 1
SAVED_MODULE_HEIGHT_ROLE = SAVED_MODULE_NAME_ROLE + 2
SAVED_MODULE_KIND_ROLE = SAVED_MODULE_NAME_ROLE + 3

QUICK_LIBRARY_LABELS = {
    "all": "Wszystkie",
    "lower": "Dolne",
    "upper": "Gorne",
    "tall": "Slupki / wysokie",
    "corner": "Narozne",
    "other": "Inne",
}


def _saved_module_quick_group_key(module: ModuleDef | None) -> str:
    if module is None:
        return "other"

    module_type = normalize_module_type(str(getattr(module, "module_type", "legacy") or "legacy"))
    cabinet_kind = str(getattr(module, "cabinet_kind", "lower") or "lower").strip().lower()
    height_mm = float(getattr(module, "height_mm", 0.0) or 0.0)
    name_blob = " ".join(
        [
            str(getattr(module, "name", "") or ""),
            str(getattr(module, "module_family", "") or ""),
            str(getattr(module, "base_group", "") or ""),
        ]
    ).strip().lower()

    if module_type == "corner" or "naroz" in name_blob:
        return "corner"
    if cabinet_kind == "upper" or module_type == "hanging" or any(token in name_blob for token in ("upper", "wisz", "gorn")):
        return "upper"
    if height_mm >= 1800.0 or any(token in name_blob for token in ("slupek", "slupek", "slup", "garder", "wardrobe", "tall")):
        return "tall"
    if cabinet_kind == "lower" or module_type in ("legacy", "legs", "legs_plinth"):
        return "lower"
    return "other"


def _saved_module_quick_group_label(key: str) -> str:
    return QUICK_LIBRARY_LABELS.get(str(key or "").strip().lower(), QUICK_LIBRARY_LABELS["other"])


class SavedModulesTreeWidget(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mimeTypes(self) -> list[str]:
        return [SAVED_MODULE_MIME]

    def mimeData(self, items) -> QMimeData:
        mime = QMimeData()
        for item in items or []:
            name = str(item.data(0, SAVED_MODULE_NAME_ROLE) or "").strip()
            if not name:
                continue
            payload = {
                "name": name,
                "width_mm": float(item.data(0, SAVED_MODULE_WIDTH_ROLE) or 0.0),
                "height_mm": float(item.data(0, SAVED_MODULE_HEIGHT_ROLE) or 0.0),
                "cabinet_kind": str(item.data(0, SAVED_MODULE_KIND_ROLE) or "lower"),
            }
            mime.setData(SAVED_MODULE_MIME, json.dumps(payload).encode("utf-8"))
            mime.setText(name)
            break
        return mime

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction


class AssemblyPreviewView(QGraphicsView):
    sig_saved_module_dropped = pyqtSignal(str, float)
    sig_module_selected = pyqtSignal(int)
    sig_module_reordered = pyqtSignal(int, int)
    sig_module_offset_changed = pyqtSignal(int, float)
    sig_module_position_changed = pyqtSignal(int, float, float)
    sig_module_top_position_changed = pyqtSignal(int, float, float)

    def __init__(
        self,
        parent: QWidget | None = None,
        wall_store: WallStoreJson | None = None,
        view_mode: str = "front",
    ) -> None:
        super().__init__(parent)
        self._catalog = CatalogStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._view_mode = str(view_mode or "front").strip().lower()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(self.renderHints())
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self._item_rects: list[QRectF] = []
        self._top_item_rects: list[QRectF] = []
        self._front_view_rect = QRectF()
        self._drag_index = -1
        self._drag_started = False
        self._drag_start_scene = QPointF()
        self._drag_mode = ""
        self._drag_left_offset = 0.0
        self._drag_top_offset = 0.0
        self._drop_indicator_x: float | None = None
        self._last_assembly: FurnitureAssemblyDef | None = None
        self._last_resolved_items = []
        self._last_selected_index = -1
        self._last_wall_width = 100.0
        self._ghost_rect: QRectF | None = None
        self._ghost_label = ""
        self._front_drag_offset_mm: float | None = None
        self._front_drag_y_mm: float | None = None
        self._vertical_reference_mode = "top"

    def set_vertical_reference_mode(self, mode: str) -> None:
        self._vertical_reference_mode = "bottom" if str(mode or "").strip().lower() == "bottom" else "top"

    def _style_readable_text(
        self,
        item: QGraphicsTextItem,
        color: str,
        point_size: int = 9,
        bold: bool = False,
        z_value: float = 30.0,
    ) -> None:
        font = QFont(item.font())
        font.setPointSize(point_size)
        font.setBold(bool(bold))
        item.setFont(font)
        item.setDefaultTextColor(QColor(color))
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        item.setZValue(float(z_value))

    def _module_material_thickness_mm(self, module: ModuleDef, slot: str, default: float) -> float:
        materials = dict(getattr(module, "materials", {}) or {})
        key = str(materials.get(slot, "") or "").strip()
        if not key:
            return float(default)
        try:
            return float(self._catalog.material_thickness(key, default) or default)
        except Exception:
            return float(default)

    def _module_rect_from_mm(
        self,
        module_rect: QRectF,
        module_width_mm: float,
        module_height_mm: float,
        x_mm: float,
        y_mm: float,
        w_mm: float,
        h_mm: float,
    ) -> QRectF:
        width_scale = float(module_rect.width()) / max(1.0, float(module_width_mm))
        height_scale = float(module_rect.height()) / max(1.0, float(module_height_mm))
        return QRectF(
            float(module_rect.left()) + float(x_mm) * width_scale,
            float(module_rect.top()) + float(y_mm) * height_scale,
            max(1.0, float(w_mm) * width_scale),
            max(1.0, float(h_mm) * height_scale),
        )

    def _build_module_front_shapes(self, module: ModuleDef, module_rect: QRectF) -> list[dict[str, object]]:
        width_mm = float(getattr(module, "width_mm", 0.0) or 0.0)
        height_mm = float(getattr(module, "height_mm", 0.0) or 0.0)
        if width_mm <= 0.0 or height_mm <= 0.0:
            return []

        visible_parts = set(getattr(module, "visible_parts", set()) or set())
        t_carcass = self._module_material_thickness_mm(module, "carcass", 18.0)
        t_back = self._module_material_thickness_mm(module, "back", 2.5)

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
        joint_type = str(getattr(module, "carcass_joint_type", "type1") or "type1")

        def mm_rect(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> QRectF:
            return self._module_rect_from_mm(
                module_rect,
                width_mm,
                height_mm,
                x_mm,
                y_mm,
                w_mm,
                h_mm,
            )

        shapes: list[dict[str, object]] = []

        if "side_left" in visible_parts:
            side_y_mm = 0.0 if joint_type == "type1" else inner_y_mm
            side_h_mm = height_mm if joint_type == "type1" else inner_h_mm
            shapes.append({"key": "side_left", "rect": mm_rect(0.0, side_y_mm, t_carcass, side_h_mm), "fill": "#ede4d6", "pen": "#4f4439"})

        if "side_right" in visible_parts:
            side_y_mm = 0.0 if joint_type == "type1" else inner_y_mm
            side_h_mm = height_mm if joint_type == "type1" else inner_h_mm
            shapes.append({"key": "side_right", "rect": mm_rect(width_mm - t_carcass, side_y_mm, t_carcass, side_h_mm), "fill": "#ede4d6", "pen": "#4f4439"})

        if "top" in visible_parts:
            top_x_mm = t_carcass if joint_type == "type1" else 0.0
            top_w_mm = max(0.0, width_mm - 2.0 * t_carcass) if joint_type == "type1" else width_mm
            shapes.append({"key": "top", "rect": mm_rect(top_x_mm, top_offset_mm, top_w_mm, t_carcass), "fill": "#ede4d6", "pen": "#4f4439"})

        if "bottom" in visible_parts:
            bottom_x_mm = t_carcass if joint_type == "type1" else 0.0
            bottom_w_mm = max(0.0, width_mm - 2.0 * t_carcass) if joint_type == "type1" else width_mm
            bottom_y_mm = max(0.0, height_mm - t_carcass - bottom_offset_mm)
            shapes.append({"key": "bottom", "rect": mm_rect(bottom_x_mm, bottom_y_mm, bottom_w_mm, t_carcass), "fill": "#ede4d6", "pen": "#4f4439"})

        divider_count = int(getattr(module, "divider_count", 0) or 0)
        if "divider" in visible_parts and divider_count > 0:
            clear_w_mm = max(0.0, inner_w_mm - divider_count * t_carcass)
            segment_w_mm = clear_w_mm / (divider_count + 1) if (divider_count + 1) > 0 else clear_w_mm
            for idx in range(1, divider_count + 1):
                x_mm = inner_x_mm + segment_w_mm * idx + t_carcass * (idx - 1)
                shapes.append({"key": f"divider_{idx}", "rect": mm_rect(x_mm, inner_y_mm, t_carcass, inner_h_mm), "fill": "#f5efe5", "pen": "#5a4f45"})

        shelf_count = int(getattr(module, "shelf_count", 0) or 0)
        if "shelf" in visible_parts and shelf_count > 0:
            clear_w_mm = inner_w_mm - max(0, divider_count) * t_carcass
            segment_w_mm = clear_w_mm / (divider_count + 1) if divider_count >= 0 else clear_w_mm
            mount = str(getattr(module, "shelf_mount", "right") or "right").strip().lower()
            shelf_x_mm = inner_x_mm if mount == "left" else inner_x_mm + max(0, divider_count) * t_carcass + max(0, divider_count) * segment_w_mm
            step_h_mm = inner_h_mm / (shelf_count + 1) if (shelf_count + 1) > 0 else inner_h_mm
            for idx in range(1, shelf_count + 1):
                y_mm = inner_y_mm + step_h_mm * idx - t_carcass / 2.0
                shapes.append({"key": f"shelf_{idx}", "rect": mm_rect(shelf_x_mm, y_mm, max(0.0, segment_w_mm), t_carcass), "fill": "#faf6ef", "pen": "#5a4f45"})

        if "back" in visible_parts:
            shapes.append({"key": "back", "rect": mm_rect(max(0.0, width_mm - t_back), inner_y_mm, t_back, inner_h_mm), "fill": "#d7cfc2", "pen": "#7c7065"})

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
            shapes.append(
                {
                    "key": "front",
                    "rect": mm_rect(x_mm, y_mm, w_mm, h_mm),
                    "fill": "#f0dfc8",
                    "fill_alpha": 72,
                    "pen": "#8f6a46",
                }
            )

            facade_mode = str(getattr(module, "facade_mode", "doors") or "doors").strip().lower()
            drawer_count = max(1, int(getattr(module, "drawer_count", 1) or 1))
            hinge_side = str(getattr(module, "door_hinge_side", "left") or "left").strip().lower()
            if hinge_side not in ("left", "right"):
                hinge_side = "left"

            settings = load_drawing_settings()
            auto_double_front_width = max(100.0, float(getattr(settings, "auto_double_front_width_mm", 600.0) or 600.0))
            try:
                gap_between_vertical = max(0.0, float(getattr(module, "front_gap_between_vertical_mm", 0.0) or 0.0))
            except Exception:
                gap_between_vertical = 0.0

            front_left = x_mm
            front_top = y_mm
            front_width = max(1.0, w_mm)
            front_height = max(1.0, h_mm)
            is_double_door = facade_mode == "doors" and front_width >= auto_double_front_width

            if facade_mode == "drawers" and drawer_count > 1:
                total_gap = gap_between_vertical * max(0, drawer_count - 1)
                free_h = max(0.0, front_height - total_gap)
                seg_h = free_h / drawer_count if drawer_count > 0 else front_height
                cursor_y = front_top

                for idx in range(1, drawer_count):
                    cursor_y += seg_h
                    split_y = cursor_y + gap_between_vertical * 0.5
                    shapes.append(
                        {
                            "key": f"front_drawer_split_{idx}",
                            "rect": mm_rect(front_left, split_y - 0.75, front_width, 1.5),
                            "fill": "#8f6a46",
                            "fill_alpha": 255,
                            "pen": "#8f6a46",
                        }
                    )
                    cursor_y += gap_between_vertical
            elif is_double_door:
                mid_x = front_left + front_width / 2.0
                shapes.append(
                    {
                        "key": "front_split_line",
                        "rect": mm_rect(mid_x - 0.75, front_top, 1.5, front_height),
                        "fill": "#8f6a46",
                        "fill_alpha": 255,
                        "pen": "#8f6a46",
                    }
                )
                handle_gap = min(40.0, max(18.0, front_width * 0.08))
                handle_top = front_top + front_height * 0.4
                handle_h = max(40.0, front_height * 0.2)
                for side_idx, handle_x in enumerate((mid_x - handle_gap, mid_x + handle_gap), start=1):
                    shapes.append(
                        {
                            "key": f"front_handle_{side_idx}",
                            "rect": mm_rect(handle_x - 1.0, handle_top, 2.0, handle_h),
                            "fill": "#6b5d4d",
                            "fill_alpha": 255,
                            "pen": "#6b5d4d",
                        }
                    )
            elif facade_mode == "doors":
                handle_offset = min(40.0, max(18.0, front_width * 0.08))
                handle_x = front_left + front_width - handle_offset if hinge_side == "left" else front_left + handle_offset
                handle_top = front_top + front_height * 0.4
                handle_h = max(40.0, front_height * 0.2)
                shapes.append(
                    {
                        "key": "front_handle_1",
                        "rect": mm_rect(handle_x - 1.0, handle_top, 2.0, handle_h),
                        "fill": "#6b5d4d",
                        "fill_alpha": 255,
                        "pen": "#6b5d4d",
                    }
                )

        return shapes

    def _saved_module_payload_from_mime(self, mime: QMimeData | None) -> dict[str, object]:
        if mime is None or not mime.hasFormat(SAVED_MODULE_MIME):
            return {}
        try:
            raw = bytes(mime.data(SAVED_MODULE_MIME)).decode("utf-8").strip()
        except Exception:
            return {}

        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}

        if isinstance(payload, dict):
            return payload

        return {"name": raw}

    def drop_indicator_x(self) -> float | None:
        return None if self._drop_indicator_x is None else float(self._drop_indicator_x)

    def ghost_scene_rect(self) -> QRectF | None:
        if self._ghost_rect is None:
            return None
        return QRectF(self._ghost_rect)

    def _rerender_cached_scene(self) -> None:
        if self._last_assembly is None:
            return
        self.render_assembly(
            self._last_assembly,
            self._last_resolved_items,
            selected_index=self._last_selected_index,
        )

    def clear_hover_preview(self) -> None:
        self._drop_indicator_x = None
        self._ghost_rect = None
        self._ghost_label = ""

    def _fit_scene_to_view(self) -> None:
        scene_rect = self.scene.sceneRect()
        if scene_rect.isNull() or scene_rect.isEmpty():
            return
        self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _tight_scene_rect(self, fallback: QRectF, x_margin: float = 28.0, y_margin: float = 28.0) -> QRectF:
        bounds = self.scene.itemsBoundingRect()
        if bounds.isNull() or bounds.isEmpty():
            bounds = QRectF(fallback)
        return bounds.adjusted(-x_margin, -y_margin, x_margin, y_margin)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_scene_to_view()

    def _update_drag_preview(self, x_mm: float | None, ghost_rect: QRectF | None = None, ghost_label: str = "") -> None:
        if x_mm is None:
            new_value = None
        else:
            new_value = max(0.0, min(float(x_mm), float(self._last_wall_width)))

        same_rect = (
            (self._ghost_rect is None and ghost_rect is None)
            or (self._ghost_rect is not None and ghost_rect is not None and self._ghost_rect == ghost_rect)
        )
        if self._drop_indicator_x == new_value and same_rect and self._ghost_label == str(ghost_label or ""):
            return

        self._drop_indicator_x = new_value
        self._ghost_rect = QRectF(ghost_rect) if ghost_rect is not None else None
        self._ghost_label = str(ghost_label or "")
        self._rerender_cached_scene()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        payload = self._saved_module_payload_from_mime(event.mimeData())
        if payload:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._set_saved_module_drag_preview(payload, float(scene_pos.x()))
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        payload = self._saved_module_payload_from_mime(event.mimeData())
        if payload:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._set_saved_module_drag_preview(payload, float(scene_pos.x()))
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._update_drag_preview(None)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        payload = self._saved_module_payload_from_mime(event.mimeData())
        module_name = str(payload.get("name", "") or "").strip()
        if not module_name:
            super().dropEvent(event)
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        self.sig_saved_module_dropped.emit(module_name, float(scene_pos.x()))
        self._update_drag_preview(None)
        event.acceptProposedAction()

    def _item_index_at_scene_pos(self, scene_pos: QPointF) -> int:
        for index in range(len(self._item_rects) - 1, -1, -1):
            if self._item_rects[index].contains(scene_pos):
                return index
        return -1

    @staticmethod
    def _index_at_scene_pos(scene_pos: QPointF, rects: list[QRectF]) -> int:
        for index in range(len(rects) - 1, -1, -1):
            if rects[index].contains(scene_pos):
                return index
        return -1

    def _target_index_for_reorder(self, drag_index: int, scene_x: float) -> int:
        rect_source = self._top_item_rects if self._view_mode == "top" else self._item_rects
        others = [rect for idx, rect in enumerate(rect_source) if idx != drag_index]
        target_index = 0
        for rect in others:
            if float(scene_x) > float(rect.center().x()):
                target_index += 1
        return target_index

    def item_scene_rect(self, index: int) -> QRectF | None:
        if 0 <= int(index) < len(self._item_rects):
            return QRectF(self._item_rects[int(index)])
        return None

    def top_item_scene_rect(self, index: int) -> QRectF | None:
        if 0 <= int(index) < len(self._top_item_rects):
            return QRectF(self._top_item_rects[int(index)])
        return None

    @staticmethod
    def _wall_width_for_front_side(wall: WallLayoutDef) -> float:
        side = str(getattr(wall, "front_view_wall_side", "A") or "A").strip().upper()
        if side == "B":
            return float(getattr(wall, "wall_b_width_mm", 2600.0) or 2600.0)
        if side == "C":
            return float(getattr(wall, "wall_c_width_mm", 2600.0) or 2600.0)
        return float(getattr(wall, "wall_a_width_mm", 4000.0) or 4000.0)

    @staticmethod
    def _wall_obstacle_fill(kind: str) -> QColor:
        kind_key = str(kind or "").strip().lower()
        if kind_key == "window":
            return QColor("#edf7ff")
        if kind_key == "door":
            return QColor("#fff4e6")
        if kind_key == "pipe":
            return QColor("#efefef")
        if kind_key == "recess":
            return QColor("#f5f5f5")
        if kind_key == "socket":
            return QColor("#fff8e3")
        if kind_key == "plumbing":
            return QColor("#ebfbf7")
        if kind_key == "radiator":
            return QColor("#ffece7")
        if kind_key == "sill":
            return QColor("#eef3f7")
        return QColor("#edf4fb")

    def _linked_wall_for_assembly(self, assembly: FurnitureAssemblyDef) -> WallLayoutDef | None:
        wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
        if not wall_name:
            return None
        return self._wall_store.get(wall_name)

    def _front_y_for_module(self, module_height_mm: float, cabinet_kind: str) -> float:
        wall_height = max(1.0, float(self._last_assembly.height_mm if self._last_assembly is not None else 1.0))
        linked_wall = self._linked_wall_for_assembly(self._last_assembly) if self._last_assembly is not None else None
        module_height_mm = max(0.0, float(module_height_mm or 0.0))
        cabinet_kind = str(cabinet_kind or "lower").strip().lower()

        if linked_wall is None:
            if cabinet_kind == "upper":
                return 0.0
            return max(0.0, wall_height - module_height_mm)

        upper_clearance_mm = max(0.0, float(getattr(linked_wall, "upper_clearance_mm", 0.0) or 0.0))
        base_plinth_mm = max(0.0, float(getattr(linked_wall, "base_plinth_mm", 0.0) or 0.0))

        if cabinet_kind == "upper":
            return max(0.0, min(upper_clearance_mm, wall_height - module_height_mm))

        return max(0.0, wall_height - base_plinth_mm - module_height_mm)

    def _draw_linked_wall_guides(
        self,
        linked_wall: WallLayoutDef,
        wall_width: float,
        wall_height: float,
    ) -> None:
        base_plinth = max(0.0, min(float(getattr(linked_wall, "base_plinth_mm", 0.0) or 0.0), wall_height))
        upper_clearance = max(0.0, min(float(getattr(linked_wall, "upper_clearance_mm", 0.0) or 0.0), wall_height))
        base_left = max(0.0, min(float(getattr(linked_wall, "base_offset_left_mm", 0.0) or 0.0), wall_width))
        base_right = max(0.0, min(float(getattr(linked_wall, "base_offset_right_mm", 0.0) or 0.0), wall_width))
        upper_left = max(0.0, min(float(getattr(linked_wall, "upper_offset_left_mm", 0.0) or 0.0), wall_width))
        upper_right = max(0.0, min(float(getattr(linked_wall, "upper_offset_right_mm", 0.0) or 0.0), wall_width))

        guide_pen = QPen(QColor("#c7b784"))
        guide_pen.setWidth(1)
        guide_pen.setStyle(Qt.PenStyle.DashLine)

        if base_plinth > 0.0:
            y = wall_height - base_plinth
            item = self.scene.addLine(0.0, y, wall_width, y, guide_pen)
            item.setData(0, "assembly_wall_guide__base_plinth")
            item.setZValue(-18.0)

        if upper_clearance > 0.0:
            y = upper_clearance
            item = self.scene.addLine(0.0, y, wall_width, y, guide_pen)
            item.setData(0, "assembly_wall_guide__upper_clearance")
            item.setZValue(-18.0)

        if base_left > 0.0:
            item = self.scene.addLine(base_left, 0.0, base_left, wall_height, guide_pen)
            item.setData(0, "assembly_wall_guide__base_left")
            item.setZValue(-18.0)

        if base_right > 0.0:
            x = wall_width - base_right
            item = self.scene.addLine(x, 0.0, x, wall_height, guide_pen)
            item.setData(0, "assembly_wall_guide__base_right")
            item.setZValue(-18.0)

        if upper_left > 0.0:
            item = self.scene.addLine(upper_left, 0.0, upper_left, wall_height, guide_pen)
            item.setData(0, "assembly_wall_guide__upper_left")
            item.setZValue(-18.0)

        if upper_right > 0.0:
            x = wall_width - upper_right
            item = self.scene.addLine(x, 0.0, x, wall_height, guide_pen)
            item.setData(0, "assembly_wall_guide__upper_right")
            item.setZValue(-18.0)

    def _draw_linked_wall_zones(
        self,
        linked_wall: WallLayoutDef,
        wall_width: float,
        wall_height: float,
    ) -> None:
        base_plinth = max(0.0, min(float(getattr(linked_wall, "base_plinth_mm", 0.0) or 0.0), wall_height))
        upper_clearance = max(0.0, min(float(getattr(linked_wall, "upper_clearance_mm", 0.0) or 0.0), wall_height))
        base_left = max(0.0, min(float(getattr(linked_wall, "base_offset_left_mm", 0.0) or 0.0), wall_width))
        base_right = max(0.0, min(float(getattr(linked_wall, "base_offset_right_mm", 0.0) or 0.0), wall_width))
        upper_left = max(0.0, min(float(getattr(linked_wall, "upper_offset_left_mm", 0.0) or 0.0), wall_width))
        upper_right = max(0.0, min(float(getattr(linked_wall, "upper_offset_right_mm", 0.0) or 0.0), wall_width))

        base_zone_left = min(base_left, wall_width)
        base_zone_right = max(base_zone_left, wall_width - base_right)
        base_zone_width = max(0.0, base_zone_right - base_zone_left)
        base_zone_top = max(0.0, wall_height - max(base_plinth, 1200.0))
        base_zone_height = max(0.0, wall_height - base_zone_top)

        if base_zone_width > 1.0 and base_zone_height > 1.0:
            base_zone_item = self.scene.addRect(
                QRectF(base_zone_left, base_zone_top, base_zone_width, base_zone_height),
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(150, 162, 118, 10)),
            )
            base_zone_item.setData(0, "assembly_zone__base")
            base_zone_item.setZValue(-26.0)

        upper_zone_left = min(upper_left, wall_width)
        upper_zone_right = max(upper_zone_left, wall_width - upper_right)
        upper_zone_width = max(0.0, upper_zone_right - upper_zone_left)
        upper_zone_top = min(max(upper_clearance, 0.0), wall_height)
        upper_zone_bottom = min(max(upper_zone_top + 720.0, upper_zone_top), wall_height)
        upper_zone_height = max(0.0, upper_zone_bottom - upper_zone_top)

        if upper_zone_width > 1.0 and upper_zone_height > 1.0:
            upper_zone_item = self.scene.addRect(
                QRectF(upper_zone_left, upper_zone_top, upper_zone_width, upper_zone_height),
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(164, 177, 193, 10)),
            )
            upper_zone_item.setData(0, "assembly_zone__upper")
            upper_zone_item.setZValue(-25.0)

    def _draw_linked_wall_context(
        self,
        assembly: FurnitureAssemblyDef,
        wall_width: float,
        wall_height: float,
    ) -> WallLayoutDef | None:
        linked_wall = self._linked_wall_for_assembly(assembly)

        if linked_wall is None:
            return None

        wall_pen = QPen(QColor("#b8aea2"))
        wall_pen.setWidth(1)
        wall_brush = QBrush(QColor("#fffdfa"))
        wall_item = self.scene.addRect(QRectF(0.0, 0.0, wall_width, wall_height), wall_pen, wall_brush)
        wall_item.setData(0, "assembly_wall_frame")
        wall_item.setZValue(-30.0)

        self._draw_linked_wall_zones(linked_wall, wall_width, wall_height)
        self._draw_linked_wall_guides(linked_wall, wall_width, wall_height)

        front_side = str(getattr(linked_wall, "front_view_wall_side", "A") or "A").strip().upper()
        front_width_mm = max(1.0, self._wall_width_for_front_side(linked_wall))
        width_scale = wall_width / front_width_mm

        for index, obstacle in enumerate(getattr(linked_wall, "obstacles", []) or []):
            side = str(getattr(obstacle, "wall_side", "A") or "A").strip().upper()
            if side != front_side:
                continue

            x_mm = max(0.0, float(getattr(obstacle, "x_mm", 0.0) or 0.0))
            bottom_mm = max(0.0, float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0))
            width_mm = max(1.0, float(getattr(obstacle, "width_mm", 1.0) or 1.0))
            height_mm = max(1.0, float(getattr(obstacle, "height_mm", 1.0) or 1.0))

            x = max(0.0, min(x_mm * width_scale, wall_width - 1.0))
            width = min(width_mm * width_scale, max(1.0, wall_width - x))
            max_height = max(1.0, wall_height - bottom_mm)
            height = min(height_mm, max_height)
            y = max(0.0, wall_height - bottom_mm - height)

            obstacle_pen = QPen(QColor("#c1b5aa"))
            obstacle_pen.setWidth(1)
            obstacle_fill = self._wall_obstacle_fill(str(getattr(obstacle, "kind", "") or ""))
            obstacle_fill.setAlpha(82)
            obstacle_item = self.scene.addRect(QRectF(x, y, width, height), obstacle_pen, QBrush(obstacle_fill))
            obstacle_item.setData(0, f"assembly_wall_obstacle__{index}")
            obstacle_item.setZValue(-15.0)

        if wall_width >= 1200.0 and wall_height >= 800.0:
            side_badge = self.scene.addText(front_side)
            side_badge.setPos(8.0, 4.0)
            side_badge.setData(0, "assembly_wall_side")
            self._style_readable_text(side_badge, "#6b7280", point_size=10, bold=True, z_value=20.0)

        return linked_wall

    @staticmethod
    def _top_view_module_height_mm(depth_mm: float) -> float:
        # Keep top-view footprint proportional to the real module depth.
        return max(10.0, float(depth_mm))

    def _top_view_base_y(self, origin_y: float = 0.0) -> float:
        return float(origin_y) + 22.0

    def _max_wall_depth_offset_for_index(self, index: int) -> float:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0
        assembly_depth = max(0.0, float(getattr(self._last_assembly, "depth_mm", 0.0) or 0.0))
        resolved = self._last_resolved_items[index]
        return max(0.0, assembly_depth - float(getattr(resolved, "depth_mm", 0.0) or 0.0))

    def _wall_depth_offset_for_index(self, index: int) -> float:
        if self._last_assembly is None or index < 0 or index >= len(getattr(self._last_assembly, "items", []) or []):
            return 0.0
        raw_value = getattr(self._last_assembly.items[index], "wall_depth_offset_mm", 0.0)
        try:
            value = float(raw_value or 0.0)
        except Exception:
            value = 0.0
        max_offset = self._max_wall_depth_offset_for_index(index)
        return max(0.0, min(value, max_offset))

    def _top_snap_offset_candidate_values(
        self,
        index: int,
        current_wall_offset_mm: float | None = None,
    ) -> list[float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return [0.0]

        base_x = self._base_x_for_module_index(index)
        current_item = self._last_resolved_items[index]
        current_width = float(current_item.width_mm)
        current_depth = float(current_item.depth_mm)
        current_top = self._wall_depth_offset_for_index(index) if current_wall_offset_mm is None else float(current_wall_offset_mm)
        current_bottom = current_top + current_depth
        candidates = [0.0]

        for other_index, other in enumerate(self._last_resolved_items):
            if other_index == index:
                continue

            other_left = float(other.x_mm)
            other_right = float(other.x_mm + other.width_mm)
            other_top = self._wall_depth_offset_for_index(other_index)
            other_bottom = other_top + float(other.depth_mm)

            depth_overlap = min(current_bottom, other_bottom) - max(current_top, other_top)
            shares_band = depth_overlap > max(20.0, min(current_depth, float(other.depth_mm)) * 0.25)

            if shares_band:
                candidates.append(other_right - base_x)
                candidates.append(other_left - current_width - base_x)
            else:
                # For modules placed in different depth bands, allow clean left/right alignment.
                candidates.append(other_left - base_x)
                candidates.append(other_right - current_width - base_x)

        unique_candidates: list[float] = []
        seen_keys: set[int] = set()
        for candidate in candidates:
            rounded_key = int(round(float(candidate) * 10.0))
            if rounded_key in seen_keys:
                continue
            seen_keys.add(rounded_key)
            unique_candidates.append(float(candidate))
        return unique_candidates

    def _top_snap_wall_offset_candidate_values(self, index: int) -> list[float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return [0.0]

        current_item = self._last_resolved_items[index]
        current_depth = float(current_item.depth_mm)
        candidates = [0.0]

        for other_index, other in enumerate(self._last_resolved_items):
            if other_index == index:
                continue

            other_offset = self._wall_depth_offset_for_index(other_index)
            other_depth = float(other.depth_mm)
            candidates.append(other_offset)
            candidates.append(other_offset + other_depth - current_depth)

        unique_candidates: list[float] = []
        seen_keys: set[int] = set()
        for candidate in candidates:
            rounded_key = int(round(float(candidate) * 10.0))
            if rounded_key in seen_keys:
                continue
            seen_keys.add(rounded_key)
            unique_candidates.append(float(candidate))
        return unique_candidates

    def _draw_top_view_context(
        self,
        assembly: FurnitureAssemblyDef,
        linked_wall: WallLayoutDef | None,
        resolved_items,
        selected_index: int,
        wall_width: float,
        origin_y: float = 0.0,
        show_label: bool = True,
    ) -> tuple[float, float]:
        top_origin_y = float(origin_y)
        top_wall_height = 10.0
        top_wall_pen = QPen(QColor("#4d4d4d"))
        top_wall_pen.setWidth(2)
        top_wall_brush = QBrush(QColor("#f7f7f7"))

        top_wall_rect = QRectF(0.0, top_origin_y, wall_width, top_wall_height)
        top_wall_item = self.scene.addRect(top_wall_rect, top_wall_pen, top_wall_brush)
        top_wall_item.setData(0, "assembly_top_wall")
        top_wall_item.setZValue(-20.0)

        if show_label:
            top_label = self.scene.addText("Rzut z gory")
            top_label.setPos(0.0, top_origin_y - 30.0)
            top_label.setData(0, "assembly_top_label")
            self._style_readable_text(top_label, "#666666", point_size=9, z_value=18.0)

        module_base_y = self._top_view_base_y(top_origin_y)
        top_depth_limit = max(100.0, float(getattr(assembly, "depth_mm", 100.0) or 100.0))
        deepest = 0.0
        self._top_item_rects = []

        depth_limit_pen = QPen(QColor("#d6dde8"))
        depth_limit_pen.setWidth(1)
        depth_limit_pen.setStyle(Qt.PenStyle.DashLine)
        depth_limit_y = module_base_y + top_depth_limit
        depth_limit_item = self.scene.addLine(0.0, depth_limit_y, wall_width, depth_limit_y, depth_limit_pen)
        depth_limit_item.setData(0, "assembly_top_depth_limit")
        depth_limit_item.setZValue(-18.0)

        for index, item in enumerate(resolved_items or []):
            footprint_h = self._top_view_module_height_mm(float(item.depth_mm))
            wall_offset = self._wall_depth_offset_for_index(index)
            deepest = max(deepest, wall_offset + footprint_h)
            rect = QRectF(float(item.x_mm), module_base_y + wall_offset, float(item.width_mm), footprint_h)
            self._top_item_rects.append(QRectF(rect))

            if index == selected_index:
                brush = QBrush(QColor("#d9ecff"))
                pen = QPen(QColor("#1f6ed4"))
            else:
                brush = QBrush(QColor("#eef5fb"))
                pen = QPen(QColor("#6c8fb2"))

            pen.setWidth(2)
            top_item = self.scene.addRect(rect, pen, brush)
            top_item.setData(0, f"assembly_top_module__{index}")
            top_item.setZValue(2.0)

        return top_origin_y, module_base_y + max(deepest, top_depth_limit)

    def _insertion_x_for_index(self, index: int, skip_index: int | None = None, fallback_x: float | None = None) -> float:
        rect_source = self._top_item_rects if self._view_mode == "top" else self._item_rects
        rects = [QRectF(rect) for idx, rect in enumerate(rect_source) if idx != skip_index]
        if not rects:
            if fallback_x is None:
                return 0.0
            return max(0.0, min(float(fallback_x), float(self._last_wall_width)))

        safe_index = max(0, min(int(index), len(rects)))
        if safe_index <= 0:
            return float(rects[0].left())
        if safe_index >= len(rects):
            return float(rects[-1].right())
        return float(rects[safe_index].left())

    def _set_saved_module_drag_preview(self, payload: dict[str, object], scene_x: float) -> None:
        name = str(payload.get("name", "") or "").strip()
        try:
            width_mm = max(1.0, float(payload.get("width_mm", 1.0) or 1.0))
        except Exception:
            width_mm = 1.0
        try:
            height_mm = max(1.0, float(payload.get("height_mm", 1.0) or 1.0))
        except Exception:
            height_mm = 1.0

        cabinet_kind = str(payload.get("cabinet_kind", "lower") or "lower").strip().lower()
        target_index = self._target_index_for_reorder(-1, float(scene_x))
        insert_x = self._insertion_x_for_index(target_index, fallback_x=float(scene_x))
        if self._view_mode == "top":
            depth_mm = max(100.0, float(payload.get("depth_mm", payload.get("height_mm", 100.0)) or 100.0))
            top_h = self._top_view_module_height_mm(depth_mm)
            ghost_rect = QRectF(float(insert_x), self._top_view_base_y(), float(width_mm), float(top_h))
        else:
            y_mm = self._front_y_for_module(height_mm, cabinet_kind)
            ghost_rect = QRectF(float(insert_x), float(y_mm), float(width_mm), float(height_mm))
        self._update_drag_preview(insert_x, ghost_rect=ghost_rect, ghost_label=name)

    def _set_reorder_drag_preview(self, drag_index: int, scene_x: float) -> None:
        rect_source = self._top_item_rects if self._view_mode == "top" else self._item_rects
        if drag_index < 0 or drag_index >= len(rect_source):
            self._update_drag_preview(None)
            return
        source_rect = QRectF(rect_source[drag_index])
        target_index = self._target_index_for_reorder(drag_index, float(scene_x))
        insert_x = self._insertion_x_for_index(target_index, skip_index=drag_index, fallback_x=float(scene_x))
        ghost_rect = QRectF(float(insert_x), float(source_rect.top()), float(source_rect.width()), float(source_rect.height()))
        self._update_drag_preview(insert_x, ghost_rect=ghost_rect, ghost_label="")

    def _horizontal_reference_mode_for_index(self, index: int) -> str:
        if self._last_assembly is None:
            return "wall_left"
        items = list(getattr(self._last_assembly, "items", []) or [])
        if index < 0 or index >= len(items):
            return "wall_left"

        mode = normalize_assembly_offset_ref_mode(getattr(items[index], "offset_ref_mode", "wall_left"))
        if mode == "previous_module" and (index <= 0 or index - 1 >= len(self._last_resolved_items)):
            return "wall_left"
        return mode

    def _horizontal_reference_label_for_index(self, index: int) -> str:
        mode = self._horizontal_reference_mode_for_index(index)
        if mode == "previous_module" and self._last_assembly is not None and index > 0 and index - 1 < len(self._last_assembly.items):
            previous_name = self._last_assembly.items[index - 1].display_name()
            return f'od poprzedniego modulu: "{previous_name}"'
        return "od lewej sciany"

    def _base_x_for_module_index(self, index: int) -> float:
        if self._horizontal_reference_mode_for_index(index) != "previous_module":
            return 0.0
        if index - 1 >= len(self._last_resolved_items):
            return 0.0
        previous = self._last_resolved_items[index - 1]
        gap_mm = max(0.0, float(getattr(self._last_assembly, "gap_mm", 0.0) or 0.0))
        return float(previous.x_mm) + float(previous.width_mm) + gap_mm

    def _min_offset_for_module_index(self, index: int) -> float:
        if self._horizontal_reference_mode_for_index(index) != "previous_module":
            return 0.0
        base_x = self._base_x_for_module_index(index)
        return min(0.0, -float(base_x))

    def _max_offset_for_module_index(self, index: int) -> float:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0
        resolved = self._last_resolved_items[index]
        base_x = self._base_x_for_module_index(index)
        return max(0.0, float(self._last_wall_width) - base_x - float(resolved.width_mm))

    def _snap_threshold_for_horizontal_offset(self) -> float:
        return 10.0

    def _snap_threshold_for_vertical_position(self) -> float:
        return 12.0

    def _snap_offset_candidate_values(self, index: int, current_top_y: float | None = None) -> list[float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return [0.0]

        base_x = self._base_x_for_module_index(index)
        current_item = self._last_resolved_items[index]
        current_width = float(current_item.width_mm)
        current_height = float(current_item.height_mm)
        current_top = float(current_item.y_mm if current_top_y is None else current_top_y)
        current_bottom = current_top + current_height
        candidates = [0.0]

        for other_index, other in enumerate(self._last_resolved_items):
            if other_index == index:
                continue

            other_left = float(other.x_mm)
            other_right = float(other.x_mm + other.width_mm)
            other_top = float(other.y_mm)
            other_bottom = float(other.y_mm + other.height_mm)

            vertical_overlap = min(current_bottom, other_bottom) - max(current_top, other_top)
            shares_row = vertical_overlap > max(40.0, min(current_height, float(other.height_mm)) * 0.25)

            # For modules in the same row, prefer true side attachment with 0 mm gap.
            if shares_row:
                candidates.append(other_right - base_x)
                candidates.append(other_left - current_width - base_x)
            else:
                # For modules stacked above/below each other, align them by left or right edge.
                candidates.append(other_left - base_x)
                candidates.append(other_right - current_width - base_x)

        unique_candidates: list[float] = []
        seen_keys: set[int] = set()
        for candidate in candidates:
            rounded_key = int(round(float(candidate) * 10.0))
            if rounded_key in seen_keys:
                continue
            seen_keys.add(rounded_key)
            unique_candidates.append(float(candidate))
        return unique_candidates

    def _snap_y_candidate_values(self, index: int, current_left_x: float | None = None) -> list[float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return [0.0]

        current_item = self._last_resolved_items[index]
        current_left = float(current_item.x_mm if current_left_x is None else current_left_x)
        current_width = float(current_item.width_mm)
        current_height = float(current_item.height_mm)
        current_right = current_left + current_width
        candidates = [self._auto_y_for_index(index)]

        for other_index, other in enumerate(self._last_resolved_items):
            if other_index == index:
                continue

            other_left = float(other.x_mm)
            other_right = float(other.x_mm + other.width_mm)
            other_top = float(other.y_mm)
            other_bottom = float(other.y_mm + other.height_mm)

            horizontal_overlap = min(current_right, other_right) - max(current_left, other_left)
            shares_column = horizontal_overlap > max(40.0, min(current_width, float(other.width_mm)) * 0.25)
            if not shares_column:
                continue

            # In one visual column, prefer true stacking instead of overlapping alignments.
            candidates.append(other_bottom)
            candidates.append(other_top - current_height)

        unique_candidates: list[float] = []
        seen_keys: set[int] = set()
        for candidate in candidates:
            rounded_key = int(round(float(candidate) * 10.0))
            if rounded_key in seen_keys:
                continue
            seen_keys.add(rounded_key)
            unique_candidates.append(float(candidate))
        return unique_candidates

    def _is_horizontal_snap_value(self, index: int, offset_value: float, current_top_y: float | None = None) -> bool:
        min_offset = self._min_offset_for_module_index(index)
        max_offset = self._max_offset_for_module_index(index)
        for candidate in self._snap_offset_candidate_values(index, current_top_y=current_top_y):
            clamped = max(min_offset, min(float(candidate), max_offset))
            if abs(float(offset_value) - clamped) <= 0.1:
                return True
        return False

    def _is_vertical_snap_value(self, index: int, y_value: float, current_left_x: float | None = None) -> bool:
        max_y = self._max_y_for_index(index)
        for candidate in self._snap_y_candidate_values(index, current_left_x=current_left_x):
            clamped = max(0.0, min(float(candidate), max_y))
            if abs(float(y_value) - clamped) <= 0.1:
                return True
        return False

    def _snapped_offset_for_scene_x(
        self,
        index: int,
        scene_x: float,
        current_top_y: float | None = None,
        drag_left_offset: float | None = None,
    ) -> tuple[float, float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0, 0.0

        base_x = self._base_x_for_module_index(index)
        min_offset = self._min_offset_for_module_index(index)
        max_offset = self._max_offset_for_module_index(index)
        active_drag_left_offset = float(self._drag_left_offset if drag_left_offset is None else drag_left_offset)
        left_x = float(scene_x) - active_drag_left_offset
        offset_mm = max(min_offset, min(left_x - base_x, max_offset))
        snap_threshold_mm = self._snap_threshold_for_horizontal_offset()
        candidates = [
            max(min_offset, min(float(candidate), max_offset))
            for candidate in self._snap_offset_candidate_values(index, current_top_y=current_top_y)
        ]
        if candidates:
            closest = min(candidates, key=lambda candidate: abs(offset_mm - candidate))
            if abs(offset_mm - closest) <= snap_threshold_mm:
                offset_mm = closest
        return offset_mm, base_x + offset_mm

    def _snapped_top_offset_for_scene_x(
        self,
        index: int,
        scene_x: float,
        current_wall_offset_mm: float | None = None,
        drag_left_offset: float | None = None,
    ) -> tuple[float, float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0, 0.0

        base_x = self._base_x_for_module_index(index)
        min_offset = self._min_offset_for_module_index(index)
        max_offset = self._max_offset_for_module_index(index)
        active_drag_left_offset = float(self._drag_left_offset if drag_left_offset is None else drag_left_offset)
        left_x = float(scene_x) - active_drag_left_offset
        offset_mm = max(min_offset, min(left_x - base_x, max_offset))
        snap_threshold_mm = self._snap_threshold_for_horizontal_offset()
        candidates = [
            max(min_offset, min(float(candidate), max_offset))
            for candidate in self._top_snap_offset_candidate_values(index, current_wall_offset_mm=current_wall_offset_mm)
        ]
        if candidates:
            closest = min(candidates, key=lambda candidate: abs(offset_mm - candidate))
            if abs(offset_mm - closest) <= snap_threshold_mm:
                offset_mm = closest
        return offset_mm, base_x + offset_mm

    def _auto_y_for_index(self, index: int) -> float:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0
        resolved = self._last_resolved_items[index]
        cabinet_kind = str(getattr(resolved.module, "cabinet_kind", "lower") or "lower")
        return self._front_y_for_module(float(resolved.height_mm), cabinet_kind)

    def _max_y_for_index(self, index: int) -> float:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0
        resolved = self._last_resolved_items[index]
        wall_height = max(1.0, float(self._last_assembly.height_mm if self._last_assembly is not None else 1.0))
        return max(0.0, wall_height - float(resolved.height_mm))

    def _snapped_top_wall_offset_for_scene_y(
        self,
        index: int,
        scene_y: float,
        drag_top_offset: float | None = None,
    ) -> tuple[float, float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0, self._top_view_base_y()

        active_drag_top_offset = float(self._drag_top_offset if drag_top_offset is None else drag_top_offset)
        base_y = self._top_view_base_y()
        max_offset = self._max_wall_depth_offset_for_index(index)
        top_y = float(scene_y) - active_drag_top_offset
        wall_offset = max(0.0, min(top_y - base_y, max_offset))
        candidates = [
            max(0.0, min(float(candidate), max_offset))
            for candidate in self._top_snap_wall_offset_candidate_values(index)
        ]
        if candidates:
            closest = min(candidates, key=lambda candidate: abs(wall_offset - candidate))
            if abs(wall_offset - closest) <= self._snap_threshold_for_vertical_position():
                wall_offset = closest
        return wall_offset, base_y + wall_offset

    def _snapped_y_for_scene_y(
        self,
        index: int,
        scene_y: float,
        current_left_x: float | None = None,
        drag_top_offset: float | None = None,
    ) -> tuple[float, float]:
        if index < 0 or index >= len(self._last_resolved_items):
            return 0.0, 0.0

        active_drag_top_offset = float(self._drag_top_offset if drag_top_offset is None else drag_top_offset)
        max_y = self._max_y_for_index(index)
        top_y = max(0.0, min(float(scene_y) - active_drag_top_offset, max_y))
        candidates = [
            max(0.0, min(float(candidate), max_y))
            for candidate in self._snap_y_candidate_values(index, current_left_x=current_left_x)
        ]
        if candidates:
            closest = min(candidates, key=lambda candidate: abs(top_y - candidate))
            if abs(top_y - closest) <= self._snap_threshold_for_vertical_position():
                top_y = closest
        return top_y, top_y

    def _build_offset_editor(self, value_mm: float, min_value_mm: float, max_value_mm: float) -> QDoubleSpinBox:
        editor = QDoubleSpinBox()
        editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        editor.setDecimals(1)
        editor.setKeyboardTracking(False)
        editor.setSingleStep(10.0)
        editor.setSuffix(" mm")
        editor.setRange(float(min_value_mm), max(float(min_value_mm), float(max_value_mm)))
        editor.setValue(float(value_mm))
        editor.setFixedWidth(120)
        editor.setMinimumHeight(28)
        editor.setStyleSheet(
            "QDoubleSpinBox {"
            " background: #ffffff;"
            " border: 1px solid #2b6cb0;"
            " border-radius: 5px;"
            " padding: 2px 6px;"
            " font-size: 11px;"
            " font-weight: 600;"
            "}"
        )
        return editor

    def _draw_selected_offset_overlay(self, selected_index: int) -> None:
        if selected_index < 0 or selected_index >= len(self._item_rects):
            return
        if selected_index >= len(self._last_resolved_items):
            return

        rect = self._item_rects[selected_index]
        base_x = self._base_x_for_module_index(selected_index)
        offset_mm = float(getattr(self._last_assembly.items[selected_index], "offset_mm", 0.0) or 0.0)
        min_offset = self._min_offset_for_module_index(selected_index)
        max_offset = self._max_offset_for_module_index(selected_index)
        current_offset_value = float(self._front_drag_offset_mm if self._front_drag_offset_mm is not None else offset_mm)
        y_value = self._front_drag_y_mm if self._front_drag_y_mm is not None else float(rect.top())
        current_left = float(base_x + current_offset_value)
        current_top = float(y_value)
        current_right = current_left + float(rect.width())
        current_bottom = current_top + float(rect.height())
        snapped = self._is_horizontal_snap_value(selected_index, current_offset_value, current_top_y=y_value)
        y_snapped = self._is_vertical_snap_value(selected_index, float(y_value), current_left_x=current_left)
        vertical_mode = "bottom" if str(getattr(self, "_vertical_reference_mode", "top") or "top").strip().lower() == "bottom" else "top"

        line_y = max(24.0, current_top - 34.0)
        accent_color = QColor("#1f9d55") if snapped else QColor("#2b6cb0")
        guide_color = QColor("#8fd1aa") if snapped else QColor("#8db7e8")

        line_pen = QPen(accent_color)
        line_pen.setWidth(2)
        guide_pen = QPen(guide_color)
        guide_pen.setWidth(1)
        guide_pen.setStyle(Qt.PenStyle.DashLine)

        left_marker = self.scene.addLine(base_x, line_y - 16.0, base_x, line_y + 16.0, guide_pen)
        left_marker.setData(0, f"assembly_offset_base__{selected_index}")
        right_marker = self.scene.addLine(current_left, line_y - 16.0, current_left, line_y + 16.0, guide_pen)
        right_marker.setData(0, f"assembly_offset_edge__{selected_index}")

        if abs(current_left - base_x) > 0.5:
            distance_line = self.scene.addLine(base_x, line_y, current_left, line_y, line_pen)
            distance_line.setData(0, f"assembly_offset_line__{selected_index}")
        else:
            snap_marker = self.scene.addLine(current_left, line_y - 10.0, current_left, line_y + 10.0, line_pen)
            snap_marker.setData(0, f"assembly_offset_snap__{selected_index}")

        label_value = self._front_drag_offset_mm if self._front_drag_offset_mm is not None else offset_mm
        if abs(current_left - base_x) > 0.5:
            label_center_x = (base_x + current_left) * 0.5
        else:
            label_center_x = min(current_right - 24.0, current_left + 28.0)

        editor = self._build_offset_editor(label_value, min_offset, max_offset)
        editor.setStyleSheet(
            "QDoubleSpinBox {"
            f" background: {'#f2fff7' if snapped else '#ffffff'};"
            f" border: 1px solid {accent_color.name()};"
            " border-radius: 5px;"
            " padding: 2px 6px;"
            " font-size: 11px;"
            " font-weight: 600;"
            "}"
        )
        editor.valueChanged.connect(lambda value, idx=selected_index: self.sig_module_offset_changed.emit(idx, float(value)))

        proxy = self.scene.addWidget(editor)
        proxy.setData(0, f"assembly_offset_editor__{selected_index}")
        proxy.setZValue(30.0)
        proxy.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        editor_x = max(8.0, min(label_center_x - float(editor.width()) * 0.5, max(8.0, self._last_wall_width - float(editor.width()) - 8.0)))
        proxy.setPos(editor_x, line_y - 42.0)

        ref_text = self._horizontal_reference_label_for_index(selected_index)
        ref_label = self.scene.addText(ref_text)
        ref_label.setData(0, f"assembly_offset_ref__{selected_index}")
        ref_label.setDefaultTextColor(QColor("#6b7280"))
        ref_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        ref_label.setPos(editor_x + 8.0, line_y - 14.0)
        ref_label.setZValue(30.0)

        vertical_x = current_right + 26.0
        if vertical_x > self._last_wall_width - 12.0:
            vertical_x = max(12.0, current_left - 26.0)

        vertical_accent = QColor("#1f9d55") if y_snapped else QColor("#7c3aed")
        vertical_guide = QColor("#b9a4f6") if not y_snapped else QColor("#8fd1aa")
        vertical_pen = QPen(vertical_accent)
        vertical_pen.setWidth(2)
        vertical_guide_pen = QPen(vertical_guide)
        vertical_guide_pen.setWidth(1)
        vertical_guide_pen.setStyle(Qt.PenStyle.DashLine)

        v_top_marker = self.scene.addLine(vertical_x - 14.0, current_top, vertical_x + 14.0, current_top, vertical_guide_pen)
        v_top_marker.setData(0, f"assembly_position_top__{selected_index}")
        v_zero_marker = self.scene.addLine(vertical_x - 14.0, 0.0, vertical_x + 14.0, 0.0, vertical_guide_pen)
        v_zero_marker.setData(0, f"assembly_position_zero__{selected_index}")
        if current_top > 0.5:
            v_line = self.scene.addLine(vertical_x, 0.0, vertical_x, current_top, vertical_pen)
            v_line.setData(0, f"assembly_position_line__{selected_index}")
        else:
            v_snap = self.scene.addLine(vertical_x - 8.0, 0.0, vertical_x + 8.0, 0.0, vertical_pen)
            v_snap.setData(0, f"assembly_position_snap__{selected_index}")

        max_y = self._max_y_for_index(selected_index)
        y_editor_value = max(0.0, max_y - y_value) if vertical_mode == "bottom" else y_value
        y_editor = self._build_offset_editor(y_editor_value, 0.0, max_y)
        y_editor.setStyleSheet(
            "QDoubleSpinBox {"
            f" background: {'#f2fff7' if y_snapped else '#ffffff'};"
            f" border: 1px solid {vertical_accent.name()};"
            " border-radius: 5px;"
            " padding: 2px 6px;"
            " font-size: 11px;"
            " font-weight: 600;"
            "}"
        )
        y_editor.valueChanged.connect(
            lambda value, idx=selected_index, cur_x=label_value, max_local=max_y, mode=vertical_mode:
            self.sig_module_position_changed.emit(
                idx,
                float(cur_x),
                float(max_local - float(value)) if mode == "bottom" else float(value),
            )
        )
        y_proxy = self.scene.addWidget(y_editor)
        y_proxy.setData(0, f"assembly_position_editor__{selected_index}")
        y_proxy.setZValue(30.0)
        y_proxy.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        y_proxy.setPos(vertical_x - float(y_editor.width()) * 0.5, max(8.0, min((0.0 + current_top) * 0.5 - 14.0, current_bottom - 20.0)))

        y_ref = self.scene.addText("od dolu" if vertical_mode == "bottom" else "od gory")
        y_ref.setData(0, f"assembly_position_ref__{selected_index}")
        y_ref.setDefaultTextColor(QColor("#6b7280"))
        y_ref.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        y_ref.setPos(vertical_x - 18.0, max(8.0, min((0.0 + current_top) * 0.5 + 16.0, current_bottom + 6.0)))
        y_ref.setZValue(30.0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self._view_mode == "top":
                top_index = self._index_at_scene_pos(scene_pos, self._top_item_rects)
                if top_index >= 0:
                    rect = self._top_item_rects[top_index]
                    self._drag_index = top_index
                    self._drag_started = False
                    self._drag_mode = "position_top"
                    self._drag_start_scene = QPointF(scene_pos)
                    self._drag_left_offset = float(scene_pos.x() - rect.left())
                    self._drag_top_offset = float(scene_pos.y() - rect.top())
                    self._front_drag_offset_mm = None
                    self._front_drag_y_mm = None
                    self.sig_module_selected.emit(top_index)
                    event.accept()
                    return
            else:
                front_index = self._index_at_scene_pos(scene_pos, self._item_rects)
                if front_index >= 0:
                    rect = self._item_rects[front_index]
                    self._drag_index = front_index
                    self._drag_started = False
                    self._drag_mode = "position"
                    self._drag_start_scene = QPointF(scene_pos)
                    self._drag_left_offset = float(scene_pos.x() - rect.left())
                    self._drag_top_offset = float(scene_pos.y() - rect.top())
                    self._front_drag_offset_mm = None
                    self._front_drag_y_mm = None
                    self.sig_module_selected.emit(front_index)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_index >= 0 and bool(event.buttons() & Qt.MouseButton.LeftButton):
            scene_pos = self.mapToScene(event.position().toPoint())
            delta = scene_pos - self._drag_start_scene
            if abs(delta.x()) >= 5.0 or abs(delta.y()) >= 5.0:
                self._drag_started = True
                if self._drag_mode == "reorder":
                    self._set_reorder_drag_preview(self._drag_index, float(scene_pos.x()))
                elif self._drag_mode == "position_top":
                    wall_offset_mm, top_y = self._snapped_top_wall_offset_for_scene_y(
                        self._drag_index,
                        float(scene_pos.y()),
                        drag_top_offset=self._drag_top_offset,
                    )
                    offset_mm, left_x = self._snapped_top_offset_for_scene_x(
                        self._drag_index,
                        float(scene_pos.x()),
                        current_wall_offset_mm=wall_offset_mm,
                        drag_left_offset=self._drag_left_offset,
                    )
                    wall_offset_mm, top_y = self._snapped_top_wall_offset_for_scene_y(
                        self._drag_index,
                        float(scene_pos.y()),
                        drag_top_offset=self._drag_top_offset,
                    )
                    if 0 <= self._drag_index < len(self._top_item_rects):
                        source_rect = self._top_item_rects[self._drag_index]
                        ghost_rect = QRectF(float(left_x), float(top_y), float(source_rect.width()), float(source_rect.height()))
                        self._update_drag_preview(left_x, ghost_rect=ghost_rect, ghost_label="")
                else:
                    left_guess = float(scene_pos.x()) - float(self._drag_left_offset)
                    y_mm, top_y = self._snapped_y_for_scene_y(
                        self._drag_index,
                        float(scene_pos.y()),
                        current_left_x=left_guess,
                    )
                    offset_mm, left_x = self._snapped_offset_for_scene_x(
                        self._drag_index,
                        float(scene_pos.x()),
                        current_top_y=top_y,
                    )
                    y_mm, top_y = self._snapped_y_for_scene_y(
                        self._drag_index,
                        float(scene_pos.y()),
                        current_left_x=left_x,
                    )
                    offset_mm, left_x = self._snapped_offset_for_scene_x(
                        self._drag_index,
                        float(scene_pos.x()),
                        current_top_y=top_y,
                    )
                    self._front_drag_offset_mm = offset_mm
                    self._front_drag_y_mm = y_mm
                    if 0 <= self._drag_index < len(self._item_rects):
                        source_rect = self._item_rects[self._drag_index]
                        ghost_rect = QRectF(float(left_x), float(top_y), float(source_rect.width()), float(source_rect.height()))
                        self._update_drag_preview(left_x, ghost_rect=ghost_rect, ghost_label="")
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_index >= 0 and event.button() == Qt.MouseButton.LeftButton:
            drag_index = int(self._drag_index)
            drag_mode = str(self._drag_mode or "")
            scene_pos = self.mapToScene(event.position().toPoint())
            delta = scene_pos - self._drag_start_scene
            started = bool(self._drag_started or abs(delta.x()) >= 5.0 or abs(delta.y()) >= 5.0)

            committed_offset_mm = 0.0
            committed_y_mm = 0.0
            target_index = 0
            if started:
                if drag_mode == "reorder":
                    target_index = self._target_index_for_reorder(drag_index, float(scene_pos.x()))
                elif drag_mode == "position_top":
                    committed_y_mm, _top_y = self._snapped_top_wall_offset_for_scene_y(
                        drag_index,
                        float(scene_pos.y()),
                        drag_top_offset=self._drag_top_offset,
                    )
                    committed_offset_mm, _left_x = self._snapped_top_offset_for_scene_x(
                        drag_index,
                        float(scene_pos.x()),
                        current_wall_offset_mm=committed_y_mm,
                        drag_left_offset=self._drag_left_offset,
                    )
                    committed_y_mm, _top_y = self._snapped_top_wall_offset_for_scene_y(
                        drag_index,
                        float(scene_pos.y()),
                        drag_top_offset=self._drag_top_offset,
                    )
                else:
                    left_guess = float(scene_pos.x()) - float(self._drag_left_offset)
                    committed_y_mm, top_y = self._snapped_y_for_scene_y(
                        drag_index,
                        float(scene_pos.y()),
                        current_left_x=left_guess,
                        drag_top_offset=self._drag_top_offset,
                    )
                    committed_offset_mm, left_x = self._snapped_offset_for_scene_x(
                        drag_index,
                        float(scene_pos.x()),
                        current_top_y=top_y,
                        drag_left_offset=self._drag_left_offset,
                    )
                    committed_y_mm, top_y = self._snapped_y_for_scene_y(
                        drag_index,
                        float(scene_pos.y()),
                        current_left_x=left_x,
                        drag_top_offset=self._drag_top_offset,
                    )
                    committed_offset_mm, _ = self._snapped_offset_for_scene_x(
                        drag_index,
                        float(scene_pos.x()),
                        current_top_y=top_y,
                        drag_left_offset=self._drag_left_offset,
                    )

            self._drag_index = -1
            self._drag_started = False
            self._drag_mode = ""
            self._drag_start_scene = QPointF()
            self._drag_left_offset = 0.0
            self._drag_top_offset = 0.0
            self._front_drag_offset_mm = None
            self._front_drag_y_mm = None
            self._update_drag_preview(None)

            if started:
                if drag_mode == "reorder":
                    self.sig_module_reordered.emit(drag_index, target_index)
                elif drag_mode == "position_top":
                    self.sig_module_top_position_changed.emit(drag_index, committed_offset_mm, committed_y_mm)
                    self.sig_module_selected.emit(drag_index)
                else:
                    self.sig_module_position_changed.emit(drag_index, committed_offset_mm, committed_y_mm)
                    self.sig_module_selected.emit(drag_index)
            else:
                self.sig_module_selected.emit(drag_index)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def render_assembly(
        self,
        assembly: FurnitureAssemblyDef,
        resolved_items,
        selected_index: int = -1,
    ) -> None:
        self._last_assembly = assembly
        self._last_resolved_items = list(resolved_items or [])
        self._last_selected_index = int(selected_index)

        self.scene.clear()
        self._item_rects = []
        self._top_item_rects = []

        wall_width = max(100.0, float(getattr(assembly, "width_mm", 100.0) or 100.0))
        wall_height = max(100.0, float(getattr(assembly, "height_mm", 100.0) or 100.0))
        self._last_wall_width = wall_width
        self._front_view_rect = QRectF(0.0, 0.0, wall_width, wall_height)

        used_width = 0.0
        if resolved_items:
            used_width = max(float(item.x_mm + item.width_mm) for item in resolved_items)

        scene_width = max(wall_width, used_width, 100.0)
        if self._view_mode == "top":
            linked_wall = self._linked_wall_for_assembly(assembly)
            _top_origin_y, top_bottom_y = self._draw_top_view_context(
                assembly,
                linked_wall,
                resolved_items,
                selected_index,
                wall_width,
                origin_y=0.0,
                show_label=False,
            )

            if self._drop_indicator_x is not None:
                indicator_pen = QPen(QColor("#1f6ed4"))
                indicator_pen.setWidth(2)
                indicator_pen.setStyle(Qt.PenStyle.DashLine)
                x_mm = max(0.0, min(float(self._drop_indicator_x), wall_width))
                self.scene.addLine(x_mm, 0.0, x_mm, top_bottom_y + 12.0, indicator_pen)

            if self._ghost_rect is not None:
                ghost_pen = QPen(QColor("#1f6ed4"))
                ghost_pen.setWidth(2)
                ghost_pen.setStyle(Qt.PenStyle.DashLine)
                ghost_brush = QBrush(QColor(31, 110, 212, 45))
                self.scene.addRect(QRectF(self._ghost_rect), ghost_pen, ghost_brush)
                if self._ghost_label:
                    ghost_text = self.scene.addText(self._ghost_label)
                    ghost_text.setDefaultTextColor(QColor("#1f6ed4"))
                    ghost_text.setPos(self._ghost_rect.left() + 8.0, self._ghost_rect.top() + 8.0)

            fallback_rect = QRectF(-20.0, -10.0, scene_width + 40.0, max(top_bottom_y + 36.0, 120.0))
            self.scene.setSceneRect(self._tight_scene_rect(fallback_rect, x_margin=24.0, y_margin=20.0))
            self._fit_scene_to_view()
            return

        scene_height = max(wall_height, 100.0)
        linked_wall = self._draw_linked_wall_context(assembly, wall_width, wall_height)
        if linked_wall is None and resolved_items:
            scene_width = max(
                100.0,
                max(float(item.x_mm + item.width_mm) for item in resolved_items) + 80.0,
            )
            scene_height = max(
                220.0,
                max(float(item.y_mm + item.height_mm) for item in resolved_items) + 80.0,
            )

        if not resolved_items:
            if linked_wall is not None:
                note = self.scene.addText("Dodaj zapisany modul na powiazana sciane.")
            else:
                note = self.scene.addText("Dodaj zapisany modul do kompletu.")
            note.setDefaultTextColor(QColor("#666666"))
            note.setPos(24.0, 24.0)
        else:
            for index, item in enumerate(resolved_items):
                rect = QRectF(item.x_mm, item.y_mm, item.width_mm, item.height_mm)
                self._item_rects.append(QRectF(rect))
                overflow = (item.x_mm + item.width_mm) > wall_width + 0.01

                if overflow:
                    brush = QBrush(QColor("#ffd9d9"))
                    pen = QPen(QColor("#cc3333"))
                elif bool(getattr(item, "has_collision", False)):
                    brush = QBrush(QColor("#ffe6e6"))
                    pen = QPen(QColor("#c62828"))
                elif index == selected_index:
                    brush = QBrush(QColor("#fff4df"))
                    pen = QPen(QColor("#9a5b17"))
                else:
                    brush = QBrush(QColor("#fffdf8"))
                    pen = QPen(QColor("#cbbda8"))

                pen.setWidth(4 if index == selected_index else 1)
                module_item = self.scene.addRect(rect, pen, brush)
                module_item.setData(0, f"assembly_module__{index}")
                module_item.setZValue(0.4 if index == selected_index else 0.2)

                for shape in self._build_module_front_shapes(item.module, rect):
                    shape_key = str(shape.get("key", "") or "")
                    shape_rect = shape.get("rect")
                    if not isinstance(shape_rect, QRectF):
                        continue

                    shape_pen = QPen(QColor(str(shape.get("pen", "#1f1f1f"))))
                    shape_pen.setWidth(2 if index == selected_index else 1)
                    if bool(shape.get("dash", False)):
                        shape_pen.setStyle(Qt.PenStyle.DashLine)

                    fill_value = shape.get("fill")
                    if fill_value:
                        shape_color = QColor(str(fill_value))
                        try:
                            fill_alpha = int(shape.get("fill_alpha", 255) or 255)
                        except Exception:
                            fill_alpha = 255
                        shape_color.setAlpha(max(0, min(fill_alpha, 255)))
                        shape_brush = QBrush(shape_color)
                    else:
                        shape_brush = QBrush(Qt.BrushStyle.NoBrush)

                    shape_item = self.scene.addRect(shape_rect, shape_pen, shape_brush)
                    shape_item.setData(0, f"assembly_module__{index}__{shape_key or 'shape'}")
                    if shape_key == "back":
                        shape_item.setZValue(0.6)
                    elif shape_key == "front":
                        shape_item.setZValue(3.8 if index == selected_index else 3.2)
                    elif shape_key.startswith("shelf_") or shape_key.startswith("divider_"):
                        shape_item.setZValue(3.4 if index == selected_index else 2.8)
                    elif shape_key.startswith("front_drawer_split_") or shape_key == "front_split_line" or shape_key.startswith("front_handle_"):
                        shape_item.setZValue(4.2 if index == selected_index else 3.6)
                    else:
                        shape_item.setZValue(2.6 if index == selected_index else 2.2)

                    if index != selected_index and shape_key != "front":
                        try:
                            shape_item.setOpacity(0.88)
                        except Exception:
                            pass
                    elif index != selected_index and shape_key == "front":
                        try:
                            shape_item.setOpacity(0.96)
                        except Exception:
                            pass

                show_title = index == selected_index
                if show_title:
                    title = self.scene.addText(item.display_name)
                    title.setData(0, f"assembly_module_title__{index}")
                    title.setPos(rect.left() + 10.0, rect.top() + 8.0)
                    self._style_readable_text(title, "#2f241b", point_size=13, bold=True, z_value=26.0)

                    meta = self.scene.addText(
                        f"{item.width_mm:.0f} x {item.height_mm:.0f} x {item.depth_mm:.0f} mm"
                    )
                    meta.setData(0, f"assembly_module_meta__{index}")
                    meta.setPos(rect.left() + 10.0, rect.top() + 30.0)
                    self._style_readable_text(meta, "#6b5d4d", point_size=10, bold=False, z_value=26.0)

                if overflow:
                    warn = self.scene.addText("Poza obrysem kompletu")
                    warn.setPos(rect.left() + 8.0, rect.bottom() - 22.0)
                    warn.setData(0, f"assembly_warning__overflow__{index}")
                    self._style_readable_text(warn, "#b00020", point_size=9, bold=True, z_value=26.0)
                elif bool(getattr(item, "has_collision", False)):
                    warn = self.scene.addText("Kolizja z innym modulem")
                    warn.setPos(rect.left() + 8.0, rect.bottom() - 22.0)
                    warn.setData(0, f"assembly_warning__collision__{index}")
                    self._style_readable_text(warn, "#b00020", point_size=9, bold=True, z_value=26.0)

        show_drag_overlay = (
            self._view_mode == "front"
            and selected_index >= 0
            and self._drag_mode == "position"
            and self._drag_index == selected_index
            and self._drag_started
            and (self._front_drag_offset_mm is not None or self._front_drag_y_mm is not None)
        )
        if show_drag_overlay:
            self._draw_selected_offset_overlay(selected_index)

        if self._drop_indicator_x is not None:
            indicator_pen = QPen(QColor("#1f6ed4"))
            indicator_pen.setWidth(2)
            indicator_pen.setStyle(Qt.PenStyle.DashLine)
            x_mm = max(0.0, min(float(self._drop_indicator_x), wall_width))
            self.scene.addLine(x_mm, 0.0, x_mm, wall_height, indicator_pen)

        if self._ghost_rect is not None:
            ghost_pen = QPen(QColor("#1f6ed4"))
            ghost_pen.setWidth(2)
            ghost_pen.setStyle(Qt.PenStyle.DashLine)
            ghost_brush = QBrush(QColor(31, 110, 212, 45))
            self.scene.addRect(QRectF(self._ghost_rect), ghost_pen, ghost_brush)
            if self._ghost_label:
                ghost_text = self.scene.addText(self._ghost_label)
                ghost_text.setPos(self._ghost_rect.left() + 8.0, self._ghost_rect.top() + 8.0)
                self._style_readable_text(ghost_text, "#1f6ed4", point_size=10, bold=True, z_value=28.0)

        if linked_wall is not None:
            max_right = max(
                wall_width + 30.0,
                max((float(item.x_mm + item.width_mm) for item in resolved_items), default=0.0) + 60.0,
            )
            max_bottom = max(
                wall_height + 30.0,
                max((float(item.y_mm + item.height_mm) for item in resolved_items), default=0.0) + 60.0,
            )
            self.scene.setSceneRect(QRectF(-30.0, -44.0, max_right + 30.0, max_bottom + 74.0))
        else:
            fallback_rect = QRectF(-30.0, -40.0, scene_width + 60.0, scene_height + 100.0)
            self.scene.setSceneRect(self._tight_scene_rect(fallback_rect, x_margin=28.0, y_margin=32.0))
        self._fit_scene_to_view()


class TabSciana(QWidget):
    sig_open_order_requested = pyqtSignal(dict)

    def __init__(
        self,
        parent: QWidget | None = None,
        module_store: ModuleStoreJson | None = None,
        wall_store: WallStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
        assembly_store: AssemblyStoreJson | None = None,
    ) -> None:
        super().__init__(parent)

        self._catalog = CatalogStoreJson()
        self._store = module_store if module_store is not None else ModuleStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._assembly = FurnitureAssemblyDef()
        self._resolved_items = []
        self._is_pushing_ui = False
        self._is_syncing_offset_ui = False
        self._is_syncing_view_ui = False
        self._order_status_context = ""
        self._site_address_context = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(splitter, 1)

        self.left_zone = self._build_left_zone()
        self.center_zone = self._build_center_zone()
        self.right_zone = self._build_right_zone()
        self.preview.sig_saved_module_dropped.connect(self._on_saved_module_dropped)
        self.preview.sig_module_selected.connect(self._on_preview_module_selected)
        self.preview.sig_module_reordered.connect(self._on_preview_module_reordered)
        self.preview.sig_module_offset_changed.connect(self._on_preview_module_offset_changed)
        self.preview.sig_module_position_changed.connect(self._on_preview_module_position_changed)
        self.preview_top.sig_saved_module_dropped.connect(self._on_saved_module_dropped)
        self.preview_top.sig_module_selected.connect(self._on_preview_module_selected)
        self.preview_top.sig_module_top_position_changed.connect(self._on_preview_top_position_changed)

        splitter.addWidget(self.left_zone)
        splitter.addWidget(self.center_zone)
        splitter.addWidget(self.right_zone)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([330, 1080, 300])

        self._reload_profiles()
        self._reload_material_choices()
        self._reload_worker_choices()
        self._reload_saved_walls()
        self._reload_saved_modules()
        self._on_active_view_changed()
        self.preview.set_vertical_reference_mode(self._selected_vertical_reference_mode())
        self.preview_top.set_vertical_reference_mode(self._selected_vertical_reference_mode())
        self._push_assembly_to_ui()
        self._rebuild_assembly()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_material_choices()
        self._reload_worker_choices(current_worker=str(getattr(self._assembly, "worker_name", "") or ""))
        self._reload_saved_walls()
        self._push_assembly_to_ui()
        self._refresh_summary()

    def _build_left_zone(self) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("STREFA LEWA")
        title.setStyleSheet("font-weight:700;")
        layout.addWidget(title)

        self.box_setup = QGroupBox("Ustawienia", panel)
        form = QFormLayout(self.box_setup)

        self.ed_name = QLineEdit()

        self.sp_width = QDoubleSpinBox()
        self.sp_width.setRange(500.0, 20000.0)
        self.sp_width.setDecimals(1)
        self.sp_width.setSuffix(" mm")

        self.sp_height = QDoubleSpinBox()
        self.sp_height.setRange(500.0, 5000.0)
        self.sp_height.setDecimals(1)
        self.sp_height.setSuffix(" mm")

        self.sp_depth = QDoubleSpinBox()
        self.sp_depth.setRange(100.0, 2000.0)
        self.sp_depth.setDecimals(1)
        self.sp_depth.setSuffix(" mm")

        self.sp_gap = QDoubleSpinBox()
        self.sp_gap.setRange(0.0, 200.0)
        self.sp_gap.setDecimals(1)
        self.sp_gap.setSuffix(" mm")

        self.cb_profile = QComboBox()
        self.cb_wall = QComboBox()
        self.btn_refresh_walls = QPushButton("Odswiez sciany")
        self.chk_force_hardware = QCheckBox("Narzuc okucia z profilu zestawu")
        self.chk_force_hardware.setChecked(True)
        self.cb_material_carcass = QComboBox()
        self.cb_material_front = QComboBox()
        self.cb_material_back = QComboBox()
        self.ed_client = QLineEdit()
        self.ed_client.setReadOnly(True)
        self.ed_order = QLineEdit()
        self.ed_order.setReadOnly(True)
        self.cb_worker = QComboBox()

        wall_row = QWidget(self.box_setup)
        wall_row_layout = QHBoxLayout(wall_row)
        wall_row_layout.setContentsMargins(0, 0, 0, 0)
        wall_row_layout.setSpacing(6)
        wall_row_layout.addWidget(self.cb_wall, 1)
        wall_row_layout.addWidget(self.btn_refresh_walls, 0)

        form.addRow("Nazwa", self.ed_name)
        form.addRow("Powiazana sciana", wall_row)
        form.addRow("Klient", self.ed_client)
        form.addRow("Zamowienie", self.ed_order)
        form.addRow("Pracownik", self.cb_worker)
        form.addRow("Szerokosc kompletu", self.sp_width)
        form.addRow("Wysokosc kompletu", self.sp_height)
        form.addRow("Glebokosc bazowa", self.sp_depth)
        form.addRow("Przerwa miedzy modulami", self.sp_gap)
        form.addRow("Profil zestawu", self.cb_profile)
        form.addRow("", self.chk_force_hardware)

        store_btns = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz")
        self.btn_load = QPushButton("Wczytaj")
        self.btn_overwrite = QPushButton("Nadpisz")
        store_btns.addWidget(self.btn_save)
        store_btns.addWidget(self.btn_load)
        store_btns.addWidget(self.btn_overwrite)
        form.addRow("", self._wrap_row_widget(self.box_setup, store_btns))

        self.btn_back_to_order = QPushButton("Powrot do zamowienia")
        form.addRow("", self.btn_back_to_order)

        self.lab_store_status = QLabel("")
        self.lab_store_status.setWordWrap(True)
        self.lab_store_status.setStyleSheet("color:#666666;")
        form.addRow("", self.lab_store_status)

        for field in (
            self.sp_width,
            self.sp_height,
            self.sp_depth,
            self.sp_gap,
            self.cb_profile,
            self.chk_force_hardware,
        ):
            self._hide_form_row(form, field)

        layout.addWidget(self.box_setup)

        self.box_materials = QGroupBox("", panel)
        materials_form = QFormLayout(self.box_materials)
        materials_form.addRow("Korpus", self.cb_material_carcass)
        materials_form.addRow("Front", self.cb_material_front)
        materials_form.addRow("Plecy", self.cb_material_back)

        self.block_materials = CollapsibleBlock("Materialy kompletu", panel)
        self.block_materials.content_layout().addWidget(self.box_materials)
        self.block_materials.set_expanded(False)
        layout.addWidget(self.block_materials)

        box_store = QGroupBox("", panel)
        store_layout = QVBoxLayout(box_store)
        store_row = QHBoxLayout()
        self.btn_refresh_saved = QPushButton("Odswiez")
        store_row.addStretch(1)
        store_row.addWidget(self.btn_refresh_saved, 0)
        store_layout.addLayout(store_row)

        filter_row = QHBoxLayout()
        self.cb_saved_quick_group = QComboBox(box_store)
        for key, label in QUICK_LIBRARY_LABELS.items():
            self.cb_saved_quick_group.addItem(label, key)
        filter_row.addWidget(QLabel("Typ:", box_store), 0)
        filter_row.addWidget(self.cb_saved_quick_group, 1)
        store_layout.addLayout(filter_row)

        self.ed_saved_search = QLineEdit(box_store)
        self.ed_saved_search.setPlaceholderText("Szukaj modulu...")
        store_layout.addWidget(self.ed_saved_search)

        self.cb_active_view = QComboBox(box_store)
        self.cb_active_view.addItem("Widok z przodu", "front")
        self.cb_active_view.addItem("Rzut z gory", "top")
        self.cb_active_view.hide()

        self.tree_saved_modules = SavedModulesTreeWidget(box_store)
        store_layout.addWidget(self.tree_saved_modules, 1)

        self.btn_add_saved = QPushButton("Dodaj do kompletu")
        self.btn_add_saved.setEnabled(False)
        store_layout.addWidget(self.btn_add_saved)

        self.lab_saved_hint = QLabel("Moduly sa pobierane z bazy zakladki Modul. Mozesz kliknac i przeciagnac modul na sciane.")
        self.lab_saved_hint.setWordWrap(True)
        self.lab_saved_hint.setStyleSheet("color:#666666;")
        store_layout.addWidget(self.lab_saved_hint)

        self.block_store = CollapsibleBlock("Dodaj zapisany modul", panel)
        self.block_store.content_layout().addWidget(box_store)
        self.block_store.set_expanded(True)
        layout.addWidget(self.block_store)

        layout.addStretch(1)

        self.ed_name.textChanged.connect(self._on_assembly_changed)
        self.cb_wall.currentIndexChanged.connect(self._on_selected_wall_changed)
        self.cb_worker.currentIndexChanged.connect(self._on_assembly_changed)
        self.btn_refresh_walls.clicked.connect(self._on_refresh_walls_clicked)
        self.btn_save.clicked.connect(self._on_save_new)
        self.btn_load.clicked.connect(self._on_load)
        self.btn_overwrite.clicked.connect(self._on_overwrite)
        self.btn_back_to_order.clicked.connect(self._on_back_to_order)
        self.sp_width.valueChanged.connect(self._on_assembly_changed)
        self.sp_height.valueChanged.connect(self._on_assembly_changed)
        self.sp_depth.valueChanged.connect(self._on_assembly_changed)
        self.sp_gap.valueChanged.connect(self._on_assembly_changed)
        self.cb_profile.currentIndexChanged.connect(self._on_assembly_changed)
        self.chk_force_hardware.toggled.connect(self._on_assembly_changed)
        self.cb_material_carcass.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_material_front.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_material_back.currentIndexChanged.connect(self._on_assembly_changed)
        self.btn_refresh_saved.clicked.connect(self._reload_saved_modules)
        self.cb_saved_quick_group.currentIndexChanged.connect(self._reload_saved_modules)
        self.ed_saved_search.textChanged.connect(self._reload_saved_modules)
        self.btn_add_saved.clicked.connect(self._on_add_saved_module)
        self.tree_saved_modules.currentItemChanged.connect(self._on_saved_module_selection_changed)
        self.cb_active_view.currentIndexChanged.connect(self._on_active_view_changed)

        return panel

    def _hide_form_row(self, form: QFormLayout, field: QWidget) -> None:
        label = form.labelForField(field)
        if label is not None:
            label.hide()
        field.hide()

    def _show_form_row(self, form: QFormLayout, field: QWidget) -> None:
        label = form.labelForField(field)
        if label is not None:
            label.show()
        field.show()

    def _wrap_row_widget(self, parent: QWidget, layout: QHBoxLayout) -> QWidget:
        holder = QWidget(parent)
        holder.setLayout(layout)
        return holder

    def _on_active_view_changed(self) -> None:
        mode = str(self.cb_active_view.currentData() or "front").strip().lower()
        show_front = mode != "top"
        self.front_box.setVisible(show_front)
        self.top_box.setVisible(not show_front)
        if show_front:
            self.center_views_splitter.setSizes([1000, 0])
        else:
            self.center_views_splitter.setSizes([0, 1000])
        self._sync_view_toggle_buttons(mode)
        if hasattr(self, "offset_form") and hasattr(self, "cb_selected_y_ref"):
            if show_front:
                self._show_form_row(self.offset_form, self.cb_selected_y_ref)
            else:
                self._hide_form_row(self.offset_form, self.cb_selected_y_ref)
        self._refresh_selected_offset_label()
        self._refresh_selected_y_label()
        self._sync_selected_offset_editor()
        self._refresh_preview_info_bar()

    def _set_active_view_mode(self, mode: str) -> None:
        target_mode = "top" if str(mode or "").strip().lower() == "top" else "front"
        idx = self.cb_active_view.findData(target_mode)
        if idx < 0:
            return
        if self.cb_active_view.currentIndex() == idx:
            self._on_active_view_changed()
            return
        self.cb_active_view.setCurrentIndex(idx)

    def _sync_view_toggle_buttons(self, mode: str) -> None:
        if not hasattr(self, "btn_view_front") or not hasattr(self, "btn_view_top"):
            return
        self._is_syncing_view_ui = True
        try:
            is_top = str(mode or "").strip().lower() == "top"
            self.btn_view_front.setChecked(not is_top)
            self.btn_view_top.setChecked(is_top)
        finally:
            self._is_syncing_view_ui = False

    def _on_view_toggle_clicked(self, mode: str) -> None:
        if self._is_syncing_view_ui:
            return
        self._set_active_view_mode(mode)

    def _format_module_family_label(self, family: str) -> str:
        family = str(family or "").strip()
        if family == "kitchen_upper":
            return "Wiszacy"
        if family == "kitchen_lower":
            return "Dolny"
        if family == "kitchen_tall":
            return "Wysoki"
        return family or "-"

    def _selected_vertical_reference_mode(self) -> str:
        if not hasattr(self, "cb_selected_y_ref"):
            return "top"
        return "bottom" if str(self.cb_selected_y_ref.currentData() or "top").strip().lower() == "bottom" else "top"

    def _is_top_view_active(self) -> bool:
        if not hasattr(self, "cb_active_view"):
            return False
        return str(self.cb_active_view.currentData() or "front").strip().lower() == "top"

    def _selected_horizontal_reference_mode(self) -> str:
        if not hasattr(self, "cb_selected_x_ref"):
            return "wall_left"
        return normalize_assembly_offset_ref_mode(self.cb_selected_x_ref.currentData() or "wall_left")

    def _effective_horizontal_reference_mode_for_index(self, index: int) -> str:
        if index < 0 or index >= len(self._assembly.items):
            return "wall_left"
        mode = normalize_assembly_offset_ref_mode(getattr(self._assembly.items[index], "offset_ref_mode", "wall_left"))
        if mode == "previous_module" and index <= 0:
            return "wall_left"
        return mode

    def _horizontal_reference_info_text(self, index: int, mode: str | None = None) -> str:
        effective_mode = normalize_assembly_offset_ref_mode(mode or self._effective_horizontal_reference_mode_for_index(index))
        if effective_mode == "previous_module" and index > 0 and index - 1 < len(self._assembly.items):
            previous_name = self._assembly.items[index - 1].display_name()
            return f'Poprzedni modul: "{previous_name}"'
        return "Lewa krawedz sciany"

    def _vertical_offset_bottom_mm(self, index: int, top_y_mm: float) -> float:
        if index < 0 or index >= len(self._resolved_items):
            return 0.0
        max_y = self.preview._max_y_for_index(index)
        return max(0.0, max_y - max(0.0, float(top_y_mm or 0.0)))

    def _vertical_offset_value_for_ui(self, index: int, top_y_mm: float) -> float:
        if self._selected_vertical_reference_mode() == "bottom":
            return self._vertical_offset_bottom_mm(index, top_y_mm)
        return max(0.0, float(top_y_mm or 0.0))

    def _y_from_vertical_offset_ui_value(self, index: int, ui_value_mm: float) -> float:
        max_y = self.preview._max_y_for_index(index)
        value = max(0.0, min(float(ui_value_mm or 0.0), max_y))
        if self._selected_vertical_reference_mode() == "bottom":
            return max(0.0, max_y - value)
        return value

    def _refresh_selected_y_label(self) -> None:
        if not hasattr(self, "offset_form") or not hasattr(self, "sp_selected_y"):
            return
        label = self.offset_form.labelForField(self.sp_selected_y)
        if label is None:
            return
        if self._is_top_view_active():
            label.setText("Od sciany")
            return
        label.setText("Od dolu" if self._selected_vertical_reference_mode() == "bottom" else "Od gory")

    def _refresh_selected_offset_label(self) -> None:
        if not hasattr(self, "offset_form") or not hasattr(self, "sp_selected_offset"):
            return
        label = self.offset_form.labelForField(self.sp_selected_offset)
        if label is None:
            return
        if self._is_top_view_active():
            if self._selected_horizontal_reference_mode() == "previous_module":
                label.setText("Od poprzedniego")
            else:
                label.setText("Po dlugosci")
            return
        label.setText("Offset")

    def _refresh_preview_info_bar(self) -> None:
        if not hasattr(self, "lab_preview_context") or not hasattr(self, "lab_active_module_info"):
            return

        mode = str(self.cb_active_view.currentData() or "front").strip().lower()
        mode_label = "Widok z przodu" if mode != "top" else "Rzut z gory"
        wall_name = str(getattr(self._assembly, "wall_name", "") or "").strip()
        used_width = 0.0
        if self._resolved_items:
            used_width = max(float(item.x_mm + item.width_mm) for item in self._resolved_items)
        wall_width = float(getattr(self._assembly, "width_mm", 0.0) or 0.0)
        wall_height = float(getattr(self._assembly, "height_mm", 0.0) or 0.0)

        if wall_name:
            preview_text = f"Sciana: {wall_name} | {mode_label} | {wall_width:.0f} x {wall_height:.0f} mm | Zajete: {used_width:.0f} mm"
        else:
            preview_text = f"Komplet roboczy | {mode_label} | Zajete: {used_width:.0f} mm"
        self.lab_preview_context.setText(preview_text)

        selected_index = self._selected_index()
        if 0 <= selected_index < len(self._resolved_items):
            item = self._resolved_items[selected_index]
            family_label = self._format_module_family_label(str(getattr(item, "family_label", "") or ""))
            if mode == "top":
                wall_offset_mm = self.preview_top._wall_depth_offset_for_index(selected_index)
                position_summary = (
                    f"Po dlugosci sciany {float(getattr(item, 'x_mm', 0.0) or 0.0):.1f} mm"
                    f" | Od sciany {wall_offset_mm:.1f} mm"
                )
            else:
                top_y_mm = float(getattr(item, "y_mm", 0.0) or 0.0)
                bottom_y_mm = self._vertical_offset_bottom_mm(selected_index, top_y_mm)
                position_summary = (
                    f"Offset {float(getattr(item, 'offset_mm', 0.0) or 0.0):.1f} mm"
                    f" | Od gory {top_y_mm:.1f} mm"
                    f" | Od dolu {bottom_y_mm:.1f} mm"
                )
            collision_html = ""
            if bool(getattr(item, "has_collision", False)):
                collision_html = ' <span style="color:#b00020; font-weight:700;">Kolizja</span>'
            self.lab_active_module_info.setText(
                f'<span style="font-weight:700; color:#2f241b;">Aktywny modul: {html.escape(item.display_name)}</span> '
                f'<span style="color:#6b5d4d;">({html.escape(family_label)})</span><br>'
                f'<span style="color:#3e342b;">{item.width_mm:.0f} x {item.height_mm:.0f} x {item.depth_mm:.0f} mm</span>'
                f' <span style="color:#b3a89a;">|</span> '
                f'<span style="color:#5b5148;">{position_summary}</span>'
                f"{collision_html}"
            )
        elif self._resolved_items:
            self.lab_active_module_info.setText("Kliknij modul w podgladzie albo w tabeli po prawej, aby zobaczyc jego szczegoly.")
        else:
            self.lab_active_module_info.setText("Dodaj zapisany modul, aby zaczac ukladanie kompletu.")

    def _build_center_zone(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("STREFA SRODKOWA")
        title.setStyleSheet("font-weight:700;")
        layout.addWidget(title)

        self.preview_info_box = QWidget(panel)
        self.preview_info_box.setStyleSheet(
            "QWidget {"
            " background: #fbfaf7;"
            " border: 1px solid #d9d1c5;"
            " border-radius: 6px;"
            "}"
        )
        info_layout = QVBoxLayout(self.preview_info_box)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(6)

        info_top_row = QHBoxLayout()
        info_top_row.setContentsMargins(0, 0, 0, 0)
        info_top_row.setSpacing(8)

        self.lab_preview_context = QLabel("Komplet roboczy | Widok z przodu")
        self.lab_preview_context.setStyleSheet("font-weight:700; color:#2f241b; border:0;")
        info_top_row.addWidget(self.lab_preview_context, 1)

        view_switch = QWidget(self.preview_info_box)
        view_switch.setStyleSheet("QWidget { background: transparent; border: 0; }")
        view_switch_layout = QHBoxLayout(view_switch)
        view_switch_layout.setContentsMargins(0, 0, 0, 0)
        view_switch_layout.setSpacing(6)

        self.btn_view_front = QPushButton("Przod", view_switch)
        self.btn_view_front.setCheckable(True)
        self.btn_view_front.setStyleSheet(
            "QPushButton {"
            " padding: 4px 10px;"
            " border: 1px solid #d5c8b7;"
            " border-radius: 5px;"
            " background: #fffdfa;"
            "}"
            "QPushButton:checked {"
            " background: #8f6a46;"
            " color: #ffffff;"
            " border-color: #8f6a46;"
            " font-weight: 700;"
            "}"
        )
        self.btn_view_top = QPushButton("Gora", view_switch)
        self.btn_view_top.setCheckable(True)
        self.btn_view_top.setStyleSheet(self.btn_view_front.styleSheet())
        view_switch_layout.addWidget(QLabel("Widok:", view_switch), 0)
        view_switch_layout.addWidget(self.btn_view_front, 0)
        view_switch_layout.addWidget(self.btn_view_top, 0)
        info_top_row.addWidget(view_switch, 0)
        info_layout.addLayout(info_top_row)

        self.lab_active_module_info = QLabel("Dodaj zapisany modul, aby zaczac ukladanie kompletu.")
        self.lab_active_module_info.setWordWrap(True)
        self.lab_active_module_info.setStyleSheet("color:#5d5246; border:0;")
        info_layout.addWidget(self.lab_active_module_info)
        layout.addWidget(self.preview_info_box, 0)

        self.front_box = QGroupBox("Widok z przodu", panel)
        front_layout = QVBoxLayout(self.front_box)
        front_layout.setContentsMargins(8, 8, 8, 8)
        front_layout.setSpacing(4)

        self.preview = AssemblyPreviewView(self.front_box, wall_store=self._wall_store, view_mode="front")
        self.preview.setMinimumHeight(420)
        self.preview.setStyleSheet("QGraphicsView { background: #fffefb; border: 1px solid #ddd4c8; }")
        front_layout.addWidget(self.preview, 1)
        self.front_box.setMinimumHeight(380)

        self.top_box = QGroupBox("Rzut z gory", panel)
        top_layout = QVBoxLayout(self.top_box)
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setSpacing(4)

        self.preview_top = AssemblyPreviewView(self.top_box, wall_store=self._wall_store, view_mode="top")
        self.preview_top.setMinimumHeight(170)
        self.preview_top.setStyleSheet("QGraphicsView { background: #fffefb; border: 1px solid #ddd4c8; }")
        top_layout.addWidget(self.preview_top, 1)
        self.top_box.setMinimumHeight(180)

        self.center_views_splitter = QSplitter(Qt.Orientation.Vertical, panel)
        self.center_views_splitter.setChildrenCollapsible(False)
        self.center_views_splitter.addWidget(self.front_box)
        self.center_views_splitter.addWidget(self.top_box)
        self.center_views_splitter.setStretchFactor(0, 4)
        self.center_views_splitter.setStretchFactor(1, 2)
        self.center_views_splitter.setSizes([560, 240])

        layout.addWidget(self.center_views_splitter, 1)

        self.btn_view_front.clicked.connect(lambda: self._on_view_toggle_clicked("front"))
        self.btn_view_top.clicked.connect(lambda: self._on_view_toggle_clicked("top"))
        return panel

    def _build_right_zone(self) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("STREFA PRAWA")
        title.setStyleSheet("font-weight:700;")
        layout.addWidget(title)

        self.right_scroll_area = QScrollArea(panel)
        self.right_scroll_area.setWidgetResizable(True)
        self.right_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_scroll_area.setStyleSheet("QScrollArea { border: 0; background: transparent; }")
        layout.addWidget(self.right_scroll_area, 1)

        scroll_content = QWidget(self.right_scroll_area)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        box_items = QGroupBox("Lista modulow", scroll_content)
        items_layout = QVBoxLayout(box_items)

        self.tbl_items = QTableWidget(0, 3, box_items)
        self.tbl_items.setHorizontalHeaderLabels(["Modul", "Typ", "Koszt"])
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.horizontalHeader().setStretchLastSection(False)
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.setAlternatingRowColors(True)
        items_layout.addWidget(self.tbl_items)

        btn_row = QHBoxLayout()
        self.btn_move_up = QPushButton("W lewo")
        self.btn_move_down = QPushButton("W prawo")
        self.btn_remove = QPushButton("Usun")
        btn_row.addWidget(self.btn_move_up)
        btn_row.addWidget(self.btn_move_down)
        btn_row.addWidget(self.btn_remove)
        items_layout.addLayout(btn_row)
        scroll_layout.addWidget(box_items, 0)

        box_offset = QGroupBox("", scroll_content)
        box_offset_layout = QVBoxLayout(box_offset)
        box_offset_layout.setContentsMargins(0, 0, 0, 0)
        box_offset_layout.setSpacing(6)
        self.lab_selected_module_meta = QLabel("Wybierz modul z listy albo kliknij go w podgladzie.")
        self.lab_selected_module_meta.setWordWrap(True)
        self.lab_selected_module_meta.setStyleSheet("color:#4b5563;")
        box_offset_layout.addWidget(self.lab_selected_module_meta)
        self.offset_form = QFormLayout()
        self.cb_selected_x_ref = QComboBox(box_offset)
        self.cb_selected_x_ref.addItem("Od lewej sciany", "wall_left")
        self.cb_selected_x_ref.addItem("Od poprzedniego modulu", "previous_module")
        self.lab_offset_ref = QLabel("-")
        self.sp_selected_offset = QDoubleSpinBox(box_offset)
        self.sp_selected_offset.setRange(-20000.0, 20000.0)
        self.sp_selected_offset.setDecimals(1)
        self.sp_selected_offset.setSuffix(" mm")
        self.cb_selected_y_ref = QComboBox(box_offset)
        self.cb_selected_y_ref.addItem("Od gory", "top")
        self.cb_selected_y_ref.addItem("Od dolu", "bottom")
        self.sp_selected_y = QDoubleSpinBox(box_offset)
        self.sp_selected_y.setRange(0.0, 20000.0)
        self.sp_selected_y.setDecimals(1)
        self.sp_selected_y.setSuffix(" mm")
        self.offset_form.addRow("Pozioma baza", self.cb_selected_x_ref)
        self.offset_form.addRow("Odniesienie", self.lab_offset_ref)
        self.offset_form.addRow("Pionowa baza", self.cb_selected_y_ref)
        self.offset_form.addRow("Offset", self.sp_selected_offset)
        self.offset_form.addRow("Od gory", self.sp_selected_y)
        box_offset_layout.addLayout(self.offset_form)
        self.block_offset = CollapsibleBlock("Aktywny modul", scroll_content)
        self.block_offset.content_layout().addWidget(box_offset)
        self.block_offset.set_expanded(True)
        scroll_layout.addWidget(self.block_offset, 0)

        self.lab_layout_alert = QLabel("", scroll_content)
        self.lab_layout_alert.setWordWrap(True)
        self.lab_layout_alert.hide()
        scroll_layout.addWidget(self.lab_layout_alert, 0)

        box_summary = QGroupBox("", scroll_content)
        summary_layout = QVBoxLayout(box_summary)
        self.lab_summary = QLabel("-")
        self.lab_summary.setWordWrap(True)
        summary_layout.addWidget(self.lab_summary)
        self.block_summary = CollapsibleBlock("Podsumowanie kompletu", scroll_content)
        self.block_summary.content_layout().addWidget(box_summary)
        self.block_summary.set_expanded(True)
        scroll_layout.addWidget(self.block_summary, 0)
        scroll_layout.addStretch(1)
        self.right_scroll_area.setWidget(scroll_content)

        self.tbl_items.itemSelectionChanged.connect(self._refresh_preview_only)
        self.btn_remove.clicked.connect(self._on_remove_selected_item)
        self.btn_move_up.clicked.connect(lambda: self._move_selected_item(-1))
        self.btn_move_down.clicked.connect(lambda: self._move_selected_item(1))
        self.cb_selected_x_ref.currentIndexChanged.connect(self._on_selected_x_reference_changed)
        self.cb_selected_y_ref.currentIndexChanged.connect(self._on_selected_y_reference_changed)
        self.sp_selected_offset.valueChanged.connect(self._on_selected_offset_changed)
        self.sp_selected_y.valueChanged.connect(self._on_selected_y_changed)

        return panel

    def _reload_profiles(self) -> None:
        current_key = str(self.cb_profile.currentData() or "")
        profiles = self._catalog.list_material_profiles()

        self.cb_profile.blockSignals(True)
        self.cb_profile.clear()
        for profile in profiles:
            self.cb_profile.addItem(f"{profile.name_pl} ({profile.key})", profile.key)

        idx = self.cb_profile.findData(current_key)
        if idx < 0:
            idx = self.cb_profile.findData(getattr(self._assembly, "material_profile_key", "STD_WHITE"))
        if idx < 0 and self.cb_profile.count() > 0:
            idx = 0
        if idx >= 0:
            self.cb_profile.setCurrentIndex(idx)
        self.cb_profile.blockSignals(False)

    def _material_label(self, material) -> str:
        label = f"{material.key} ({material.thickness_mm:g} mm) - {material.name_pl}"
        extras: list[str] = []
        manufacturer = str(getattr(material, "manufacturer", "") or "").strip()
        material_type = str(getattr(material, "material_type", "") or "").strip()
        if manufacturer:
            extras.append(manufacturer)
        if material_type:
            extras.append(material_type)
        if extras:
            label += f" [{', '.join(extras)}]"
        price = float(getattr(material, "price_pln_per_m2", 0.0) or 0.0)
        if price > 0.0:
            label += f" - {price:.2f} zl/m2"
        return label

    def _reload_material_choices(self) -> None:
        current_values = {
            "carcass": str(self.cb_material_carcass.currentData() or ""),
            "front": str(self.cb_material_front.currentData() or ""),
            "back": str(self.cb_material_back.currentData() or ""),
        }
        materials = self._catalog.list_materials() or []

        def fill(cb: QComboBox, current_value: str) -> None:
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("[bez nadpisania]", "")
            for material in materials:
                cb.addItem(self._material_label(material), material.key)
            idx = cb.findData(current_value)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

        fill(self.cb_material_carcass, current_values["carcass"])
        fill(self.cb_material_front, current_values["front"])
        fill(self.cb_material_back, current_values["back"])

    def _reload_worker_choices(self, current_worker: str = "") -> None:
        current_worker = str(current_worker or "").strip()
        worker_names = [str(name or "").strip() for name in self._worker_store.list_names() if str(name or "").strip()]

        self.cb_worker.blockSignals(True)
        self.cb_worker.clear()
        self.cb_worker.addItem("[brak]", "")
        for worker_name in worker_names:
            self.cb_worker.addItem(worker_name, worker_name)
        if current_worker and self.cb_worker.findData(current_worker) < 0:
            self.cb_worker.addItem(current_worker, current_worker)
        idx = self.cb_worker.findData(current_worker)
        if idx < 0:
            idx = 0
        self.cb_worker.setCurrentIndex(idx)
        self.cb_worker.blockSignals(False)

    def _wall_width_for_side(self, wall: WallLayoutDef, side: str) -> float:
        side_key = str(side or "A").strip().upper()
        if side_key == "B":
            return float(getattr(wall, "wall_b_width_mm", 2600.0) or 2600.0)
        if side_key == "C":
            return float(getattr(wall, "wall_c_width_mm", 2600.0) or 2600.0)
        return float(getattr(wall, "wall_a_width_mm", 4000.0) or 4000.0)

    def _reload_saved_walls(self) -> None:
        current_name = str(getattr(self._assembly, "wall_name", "") or str(self.cb_wall.currentData() or ""))
        layouts = self._wall_store.list_layouts() if hasattr(self._wall_store, "list_layouts") else []

        self.cb_wall.blockSignals(True)
        self.cb_wall.clear()
        self.cb_wall.addItem("(bez powiazania)", "")

        for wall in layouts:
            wall_name = str(getattr(wall, "name", "") or "")
            client = str(getattr(wall, "client_name", "") or "-")
            order = str(getattr(wall, "order_name", "") or "-")
            self.cb_wall.addItem(f"{wall_name} | {client} | {order}", wall_name)

        idx = self.cb_wall.findData(current_name)
        if idx < 0:
            idx = 0
        self.cb_wall.setCurrentIndex(idx)
        self.cb_wall.blockSignals(False)

    def _selected_wall_name(self) -> str:
        return str(self.cb_wall.currentData() or "").strip()

    def _apply_selected_wall_context(self, sync_dims: bool) -> None:
        wall_name = self._selected_wall_name()
        if not wall_name:
            self._assembly.wall_name = ""
            self._assembly.client_name = ""
            self._assembly.order_name = ""
            self._assembly.worker_name = ""
            self._order_status_context = ""
            self._site_address_context = ""
            self.ed_client.setText("")
            self.ed_order.setText("")
            self._reload_worker_choices()
            return

        wall = self._wall_store.get(wall_name)
        if wall is None:
            self._assembly.wall_name = ""
            self._assembly.client_name = ""
            self._assembly.order_name = ""
            self._assembly.worker_name = ""
            self._order_status_context = ""
            self._site_address_context = ""
            self.ed_client.setText("")
            self.ed_order.setText("")
            self._reload_worker_choices()
            return

        self._assembly.wall_name = wall_name
        self._assembly.client_name = str(getattr(wall, "client_name", "") or "")
        self._assembly.order_name = str(getattr(wall, "order_name", "") or "")
        self._assembly.worker_name = str(getattr(wall, "worker_name", "") or "")
        order_def = self._order_store.get(self._assembly.order_name) if self._assembly.order_name else None
        self._order_status_context = str(getattr(order_def, "status", "") or "")
        self._site_address_context = str(getattr(order_def, "site_address", "") or "")
        self.ed_client.setText(self._assembly.client_name)
        self.ed_order.setText(self._assembly.order_name)
        self._reload_worker_choices(current_worker=self._assembly.worker_name)

        if sync_dims:
            front_side = str(getattr(wall, "front_view_wall_side", "A") or "A")
            self.sp_width.setValue(self._wall_width_for_side(wall, front_side))
            self.sp_height.setValue(float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
            self.sp_depth.setValue(float(getattr(wall, "base_depth_mm", 560.0) or 560.0))

    def _reload_saved_modules(self) -> None:
        current_name = self._selected_saved_module_name()
        grouped = self._store.list_grouped_names() if hasattr(self._store, "list_grouped_names") else {}
        selected_quick_group = str(self.cb_saved_quick_group.currentData() or "all").strip().lower() if hasattr(self, "cb_saved_quick_group") else "all"
        search_text = str(self.ed_saved_search.text() or "").strip().lower() if hasattr(self, "ed_saved_search") else ""

        self.tree_saved_modules.blockSignals(True)
        self.tree_saved_modules.clear()

        first_child: QTreeWidgetItem | None = None
        selected_child: QTreeWidgetItem | None = None

        for base_group, names in grouped.items():
            visible_children: list[QTreeWidgetItem] = []
            group_item = QTreeWidgetItem([module_base_group_label_pl(base_group)])
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

            for name in names:
                module = self._store.get(name)
                if not self._saved_module_matches_library_filter(module, name, selected_quick_group, search_text):
                    continue
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, name)
                child.setData(0, SAVED_MODULE_NAME_ROLE, name)
                child.setData(0, SAVED_MODULE_WIDTH_ROLE, float(getattr(module, "width_mm", 0.0) or 0.0))
                child.setData(0, SAVED_MODULE_HEIGHT_ROLE, float(getattr(module, "height_mm", 0.0) or 0.0))
                child.setData(0, SAVED_MODULE_KIND_ROLE, str(getattr(module, "cabinet_kind", "lower") or "lower"))
                quick_label = _saved_module_quick_group_label(_saved_module_quick_group_key(module))
                child.setToolTip(
                    0,
                    f"{quick_label} | {float(getattr(module, 'width_mm', 0.0) or 0.0):.0f} x "
                    f"{float(getattr(module, 'height_mm', 0.0) or 0.0):.0f} x "
                    f"{float(getattr(module, 'depth_mm', 0.0) or 0.0):.0f} mm",
                )
                group_item.addChild(child)
                visible_children.append(child)
                if first_child is None:
                    first_child = child
                if name == current_name:
                    selected_child = child

            if visible_children:
                self.tree_saved_modules.addTopLevelItem(group_item)

        self.tree_saved_modules.expandAll()
        if selected_child is not None:
            self.tree_saved_modules.setCurrentItem(selected_child)
        elif first_child is not None:
            self.tree_saved_modules.setCurrentItem(first_child)

        self.tree_saved_modules.blockSignals(False)
        self._on_saved_module_selection_changed(self.tree_saved_modules.currentItem(), None)

    def _saved_module_matches_library_filter(
        self,
        module: ModuleDef | None,
        module_name: str,
        quick_group: str,
        search_text: str,
    ) -> bool:
        quick_group = str(quick_group or "all").strip().lower() or "all"
        search_text = str(search_text or "").strip().lower()

        module_quick_group = _saved_module_quick_group_key(module)
        if quick_group != "all" and module_quick_group != quick_group:
            return False

        if not search_text:
            return True

        haystack = " ".join(
            [
                str(module_name or ""),
                str(getattr(module, "module_family", "") or ""),
                str(getattr(module, "base_group", "") or ""),
                str(getattr(module, "cabinet_kind", "") or ""),
                _saved_module_quick_group_label(module_quick_group),
            ]
        ).lower()
        return search_text in haystack

    def _selected_saved_module_name(self) -> str:
        item = self.tree_saved_modules.currentItem()
        if item is None:
            return ""
        return str(item.data(0, SAVED_MODULE_NAME_ROLE) or "").strip()

    def _on_saved_module_selection_changed(
        self,
        item: QTreeWidgetItem | None,
        _prev: QTreeWidgetItem | None,
    ) -> None:
        has_module = bool(item and str(item.data(0, SAVED_MODULE_NAME_ROLE) or "").strip())
        self.btn_add_saved.setEnabled(has_module)

    def _push_assembly_to_ui(self) -> None:
        self._is_pushing_ui = True
        try:
            self.ed_name.setText(str(getattr(self._assembly, "name", "Komplet 1") or "Komplet 1"))
            self.ed_client.setText(str(getattr(self._assembly, "client_name", "") or ""))
            self.ed_order.setText(str(getattr(self._assembly, "order_name", "") or ""))
            self._reload_worker_choices(current_worker=str(getattr(self._assembly, "worker_name", "") or ""))
            self.sp_width.setValue(float(getattr(self._assembly, "width_mm", 3000.0) or 3000.0))
            self.sp_height.setValue(float(getattr(self._assembly, "height_mm", 2500.0) or 2500.0))
            self.sp_depth.setValue(float(getattr(self._assembly, "depth_mm", 560.0) or 560.0))
            self.sp_gap.setValue(float(getattr(self._assembly, "gap_mm", 0.0) or 0.0))
            self.chk_force_hardware.setChecked(bool(getattr(self._assembly, "force_hardware_from_profile", True)))

            wall_name = str(getattr(self._assembly, "wall_name", "") or "")
            wall_idx = self.cb_wall.findData(wall_name)
            if wall_idx < 0:
                wall_idx = 0
            self.cb_wall.setCurrentIndex(wall_idx)

            profile_key = str(getattr(self._assembly, "material_profile_key", "STD_WHITE") or "STD_WHITE")
            idx = self.cb_profile.findData(profile_key)
            if idx < 0 and self.cb_profile.count() > 0:
                idx = 0
            if idx >= 0:
                self.cb_profile.setCurrentIndex(idx)

            material_overrides = dict(getattr(self._assembly, "material_overrides", {}) or {})

            def set_material_combo(cb: QComboBox, group_key: str) -> None:
                value = str(material_overrides.get(group_key, "") or "").strip()
                idx_local = cb.findData(value)
                cb.setCurrentIndex(idx_local if idx_local >= 0 else 0)

            set_material_combo(self.cb_material_carcass, "carcass")
            set_material_combo(self.cb_material_front, "front")
            set_material_combo(self.cb_material_back, "back")
        finally:
            self._is_pushing_ui = False

    def _pull_ui_to_assembly(self) -> None:
        profile_key = str(self.cb_profile.currentData() or "STD_WHITE")
        self._assembly.name = str(self.ed_name.text().strip() or "Komplet 1")
        self._assembly.wall_name = self._selected_wall_name()
        self._assembly.client_name = str(self.ed_client.text().strip())
        self._assembly.order_name = str(self.ed_order.text().strip())
        self._assembly.worker_name = str(self.cb_worker.currentData() or "").strip()
        self._assembly.width_mm = float(self.sp_width.value())
        self._assembly.height_mm = float(self.sp_height.value())
        self._assembly.depth_mm = float(self.sp_depth.value())
        self._assembly.gap_mm = 0.0
        self._assembly.material_profile_key = profile_key
        self._assembly.force_hardware_from_profile = bool(self.chk_force_hardware.isChecked())
        self._assembly.material_overrides = {
            group_key: material_key
            for group_key, material_key in (
                ("carcass", str(self.cb_material_carcass.currentData() or "").strip()),
                ("front", str(self.cb_material_front.currentData() or "").strip()),
                ("back", str(self.cb_material_back.currentData() or "").strip()),
            )
            if material_key
        }

    def _on_assembly_changed(self) -> None:
        if self._is_pushing_ui:
            return
        self._pull_ui_to_assembly()
        self._rebuild_assembly()

    def _on_selected_wall_changed(self) -> None:
        if self._is_pushing_ui:
            return
        self._is_pushing_ui = True
        try:
            self._apply_selected_wall_context(sync_dims=True)
        finally:
            self._is_pushing_ui = False
        self._pull_ui_to_assembly()
        self._rebuild_assembly()

    def _on_refresh_walls_clicked(self) -> None:
        current_name = self._selected_wall_name()
        self._reload_saved_walls()
        idx = self.cb_wall.findData(current_name)
        if idx >= 0:
            self.cb_wall.setCurrentIndex(idx)
        self._on_selected_wall_changed()

    def _set_store_status(self, message_pl: str, ok: bool = True) -> None:
        self.lab_store_status.setText(str(message_pl or ""))
        self.lab_store_status.setStyleSheet("color:#0f6a2f;" if ok else "color:#a61b1b;")

    def _ensure_name_for_save(self) -> str:
        name = str(self.ed_name.text().strip() or getattr(self._assembly, "name", "") or "Komplet 1")
        self.ed_name.setText(name)
        return name

    def _assembly_snapshot_for_store(self) -> FurnitureAssemblyDef:
        self._pull_ui_to_assembly()
        return FurnitureAssemblyDef.from_dict(self._assembly.to_dict())

    def current_order_context(self) -> dict[str, str]:
        self._pull_ui_to_assembly()
        order_name = str(getattr(self._assembly, "order_name", "") or "").strip()
        client_name = str(getattr(self._assembly, "client_name", "") or "").strip()
        worker_name = str(getattr(self._assembly, "worker_name", "") or "").strip()

        order_status = ""
        site_address = ""
        if order_name:
            order_def = self._order_store.get(order_name)
            if order_def is not None:
                order_status = str(getattr(order_def, "status", "") or "").strip()
                site_address = str(getattr(order_def, "site_address", "") or "").strip()
                if not client_name:
                    client_name = str(getattr(order_def, "client_name", "") or "").strip()
                if not worker_name:
                    worker_name = str(getattr(order_def, "worker_name", "") or "").strip()
            else:
                order_status = str(self._order_status_context or "").strip()
                site_address = str(self._site_address_context or "").strip()

        return {
            "client_name": client_name,
            "order_name": order_name,
            "worker_name": worker_name,
            "order_status": order_status,
            "site_address": site_address,
        }

    def _on_save_new(self) -> None:
        name = self._ensure_name_for_save()
        assembly = self._assembly_snapshot_for_store()
        assembly.name = name
        result = self._assembly_store.save_new(assembly)
        self._set_store_status(result.message_pl, ok=result.ok)

    def _on_back_to_order(self) -> None:
        self.sig_open_order_requested.emit(self.current_order_context())

    def _on_overwrite(self) -> None:
        name = self._ensure_name_for_save()
        assembly = self._assembly_snapshot_for_store()
        assembly.name = name
        result = self._assembly_store.overwrite(assembly)
        self._set_store_status(result.message_pl, ok=result.ok)

    def _on_load(self) -> None:
        dlg = LoadAssemblyDialog(self, self._assembly_store)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        assembly = dlg.selected_assembly()
        if assembly is None:
            self._set_store_status("Nie udalo sie wczytac kompletu.", ok=False)
            return

        self._apply_loaded_assembly(assembly)
        self._set_store_status(f'Wczytano komplet: "{getattr(self._assembly, "name", "") or ""}".', ok=True)

    def _apply_loaded_assembly(self, assembly: FurnitureAssemblyDef) -> None:
        self._assembly = FurnitureAssemblyDef.from_dict(assembly.to_dict())
        self._assembly.gap_mm = 0.0
        self._reload_saved_walls()
        self._reload_worker_choices(current_worker=str(getattr(self._assembly, "worker_name", "") or ""))
        self._push_assembly_to_ui()
        self._rebuild_assembly()

    def load_assembly_from_store_name(self, name: str) -> bool:
        assembly_name = str(name or "").strip()
        if not assembly_name:
            self._set_store_status("Nie podano nazwy kompletu.", ok=False)
            return False

        assembly = self._assembly_store.get(assembly_name)
        if assembly is None:
            self._set_store_status(f'Nie ma kompletu "{assembly_name}" w bazie.', ok=False)
            return False

        self._apply_loaded_assembly(assembly)
        self._set_store_status(f'Wczytano komplet: "{assembly_name}".', ok=True)
        return True

    def start_new_assembly(self) -> None:
        self._assembly = FurnitureAssemblyDef()
        self._order_status_context = ""
        self._site_address_context = ""
        self._reload_saved_walls()
        self._reload_worker_choices(current_worker="")
        self._push_assembly_to_ui()
        self._rebuild_assembly()
        self._set_store_status("Gotowy nowy komplet.", ok=True)

    def start_new_assembly_from_wall_context(self, context: dict | None = None) -> None:
        payload = context if isinstance(context, dict) else {}
        order_name = str(payload.get("order_name", "") or "").strip()
        order_def = self._order_store.get(order_name) if order_name else None
        self._assembly = FurnitureAssemblyDef(
            wall_name=str(payload.get("wall_name", "") or "").strip(),
            client_name=str(payload.get("client_name", "") or "").strip(),
            order_name=order_name,
            worker_name=str(payload.get("worker_name", "") or "").strip(),
            width_mm=float(payload.get("width_mm", 3000.0) or 3000.0),
            height_mm=float(payload.get("height_mm", 2500.0) or 2500.0),
            depth_mm=float(payload.get("depth_mm", 560.0) or 560.0),
        )
        self._order_status_context = str(
            payload.get("order_status", "") or getattr(order_def, "status", "") or ""
        ).strip()
        self._site_address_context = str(
            payload.get("site_address", "") or getattr(order_def, "site_address", "") or ""
        ).strip()

        self._reload_saved_walls()
        self._reload_worker_choices(current_worker=str(getattr(self._assembly, "worker_name", "") or ""))
        self._push_assembly_to_ui()

        wall_name = str(getattr(self._assembly, "wall_name", "") or "").strip()
        if wall_name:
            wall_idx = self.cb_wall.findData(wall_name)
            if wall_idx >= 0:
                self._is_pushing_ui = True
                try:
                    self.cb_wall.setCurrentIndex(wall_idx)
                    self._apply_selected_wall_context(sync_dims=True)
                finally:
                    self._is_pushing_ui = False

        self._pull_ui_to_assembly()
        self._rebuild_assembly()

        if self._assembly.wall_name:
            self._set_store_status(f'Gotowy nowy komplet dla sciany "{self._assembly.wall_name}".', ok=True)
        elif self._assembly.client_name or self._assembly.order_name or self._assembly.worker_name:
            self._set_store_status("Gotowy nowy komplet z danymi sciany.", ok=True)
        else:
            self._set_store_status("Gotowy nowy komplet.", ok=True)

    def _next_instance_name(self, base_name: str) -> str:
        existing_names = {item.display_name() for item in (self._assembly.items or [])}
        if base_name not in existing_names:
            return base_name

        index = 2
        while True:
            candidate = f"{base_name} #{index}"
            if candidate not in existing_names:
                return candidate
            index += 1

    def _offset_for_drop_position(self, module: ModuleDef, insert_index: int, drop_x_mm: float) -> float:
        width_mm = max(0.0, float(getattr(module, "width_mm", 0.0) or 0.0))
        wall_width = max(0.0, float(getattr(self._assembly, "width_mm", 0.0) or 0.0))

        desired_left = max(0.0, float(drop_x_mm or 0.0) - width_mm * 0.5)
        min_left = 0.0
        max_left = max(0.0, wall_width - width_mm)
        desired_left = max(min_left, min(desired_left, max_left))
        offset_mm = desired_left

        snap_candidates = [0.0]
        for other in self._resolved_items:
            snap_candidates.append(float(other.x_mm))
            snap_candidates.append(float(other.x_mm + other.width_mm))

        if snap_candidates:
            closest = min(snap_candidates, key=lambda candidate: abs(offset_mm - float(candidate)))
            if abs(offset_mm - float(closest)) <= 12.0:
                offset_mm = float(closest)
        return offset_mm

    def _add_saved_module_by_name(
        self,
        source_name: str,
        insert_index: int | None = None,
        initial_offset_mm: float | None = None,
    ) -> bool:
        source_name = str(source_name or "").strip()
        if not source_name:
            self._set_store_status("Nie wybrano modulu do dodania.", ok=False)
            return False

        module = self._store.get(source_name)
        if module is None:
            self._set_store_status(f'Nie ma modulu "{source_name}" w bazie.', ok=False)
            return False

        cloned = ModuleDef.from_dict(module.to_dict()) if hasattr(module, "to_dict") else ModuleDef()
        if not getattr(cloned, "parts", None):
            cloned.parts = build_module_parts(cloned, self._catalog)

        item = AssemblyModuleItemDef(
            source_name=source_name,
            instance_name=self._next_instance_name(source_name),
            offset_ref_mode="wall_left",
            offset_mm=0.0,
            wall_depth_offset_mm=0.0,
            module=cloned,
        )

        items = self._assembly.items
        target_index = len(items) if insert_index is None else int(insert_index)
        target_index = max(0, min(target_index, len(items)))
        if initial_offset_mm is None:
            if target_index > 0 and target_index - 1 < len(self._resolved_items):
                previous = self._resolved_items[target_index - 1]
                gap_mm = max(0.0, float(getattr(self._assembly, "gap_mm", 0.0) or 0.0))
                initial_offset_mm = float(previous.x_mm) + float(previous.width_mm) + gap_mm
            else:
                initial_offset_mm = 0.0
        wall_width = max(0.0, float(getattr(self._assembly, "width_mm", 0.0) or 0.0))
        max_left = max(0.0, wall_width - float(getattr(cloned, "width_mm", 0.0) or 0.0))
        initial_offset_mm = max(0.0, min(float(initial_offset_mm or 0.0), max_left))
        item.offset_mm = float(initial_offset_mm or 0.0)
        items.insert(target_index, item)
        self._rebuild_assembly(select_index=target_index)
        self._set_store_status(f'Dodano modul "{source_name}" do kompletu.', ok=True)
        return True

    def _insert_index_for_drop_x_mm(self, drop_x_mm: float) -> int:
        if not self._resolved_items:
            return len(self._assembly.items)

        x_mm = max(0.0, float(drop_x_mm or 0.0))
        for index, resolved in enumerate(self._resolved_items):
            center_x = float(resolved.x_mm) + float(resolved.width_mm) * 0.5
            if x_mm < center_x:
                return index
        return len(self._resolved_items)

    def _on_add_saved_module(self) -> None:
        source_name = self._selected_saved_module_name()
        self._add_saved_module_by_name(source_name)

    def _on_saved_module_dropped(self, source_name: str, drop_x_mm: float) -> None:
        insert_index = self._insert_index_for_drop_x_mm(drop_x_mm)
        module = self._store.get(source_name)
        initial_offset_mm = 0.0
        if module is not None:
            initial_offset_mm = self._offset_for_drop_position(module, insert_index, drop_x_mm)
        self._add_saved_module_by_name(source_name, insert_index=insert_index, initial_offset_mm=initial_offset_mm)

    def _on_preview_module_selected(self, index: int) -> None:
        if 0 <= int(index) < self.tbl_items.rowCount():
            self.tbl_items.selectRow(int(index))
            self._sync_selected_offset_editor()
            self._refresh_preview_only()

    def _on_preview_module_reordered(self, old_index: int, target_index: int) -> None:
        old_index = int(old_index)
        target_index = int(target_index)
        items = self._assembly.items
        if old_index < 0 or old_index >= len(items):
            return

        target_index = max(0, min(target_index, len(items) - 1))
        item = items.pop(old_index)
        items.insert(target_index, item)
        self._rebuild_assembly(select_index=target_index)
        self._set_store_status(f'Przeniesiono modul "{item.display_name()}".', ok=True)

    def _on_preview_module_offset_changed(self, index: int, offset_mm: float) -> None:
        index = int(index)
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview._min_offset_for_module_index(index)
        max_offset = self.preview._max_offset_for_module_index(index)
        self._assembly.items[index].offset_mm = max(min_offset, min(float(offset_mm or 0.0), max_offset))
        self._rebuild_assembly(select_index=index)

    def _on_preview_module_position_changed(self, index: int, offset_mm: float, y_mm: float) -> None:
        index = int(index)
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview._min_offset_for_module_index(index)
        max_offset = self.preview._max_offset_for_module_index(index)
        max_y = self.preview._max_y_for_index(index)
        self._assembly.items[index].offset_mm = max(min_offset, min(float(offset_mm or 0.0), max_offset))
        self._assembly.items[index].position_y_mm = max(0.0, min(float(y_mm or 0.0), max_y))
        self._rebuild_assembly(select_index=index)

    def _on_preview_top_position_changed(self, index: int, offset_mm: float, wall_offset_mm: float) -> None:
        index = int(index)
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview_top._min_offset_for_module_index(index)
        max_offset = self.preview_top._max_offset_for_module_index(index)
        max_wall_offset = self.preview_top._max_wall_depth_offset_for_index(index)
        self._assembly.items[index].offset_mm = max(min_offset, min(float(offset_mm or 0.0), max_offset))
        self._assembly.items[index].wall_depth_offset_mm = max(0.0, min(float(wall_offset_mm or 0.0), max_wall_offset))
        self._rebuild_assembly(select_index=index)

    def _selected_index(self) -> int:
        rows = self.tbl_items.selectionModel().selectedRows() if self.tbl_items.selectionModel() is not None else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _sync_selected_offset_editor(self) -> None:
        index = self._selected_index()
        enabled = 0 <= index < len(self._assembly.items)
        self.lab_selected_module_meta.setEnabled(enabled)
        self.cb_selected_x_ref.setEnabled(enabled)
        self.lab_offset_ref.setEnabled(enabled)
        self.cb_selected_y_ref.setEnabled(enabled and not self._is_top_view_active())
        self.sp_selected_offset.setEnabled(enabled)
        self.sp_selected_y.setEnabled(enabled)

        self._is_syncing_offset_ui = True
        try:
            if not enabled:
                self.lab_selected_module_meta.setText("Wybierz modul z listy albo kliknij go w podgladzie.")
                self.cb_selected_x_ref.setCurrentIndex(0)
                self.lab_offset_ref.setText("-")
                self.cb_selected_y_ref.setCurrentIndex(0)
                self.sp_selected_offset.setRange(0.0, 0.0)
                self.sp_selected_offset.setValue(0.0)
                self.sp_selected_y.setRange(0.0, 0.0)
                self.sp_selected_y.setValue(0.0)
                self._refresh_selected_offset_label()
                self._refresh_selected_y_label()
                return

            effective_mode = self._effective_horizontal_reference_mode_for_index(index)
            self._assembly.items[index].offset_ref_mode = effective_mode
            x_ref_idx = self.cb_selected_x_ref.findData(effective_mode)
            if x_ref_idx >= 0:
                self.cb_selected_x_ref.setCurrentIndex(x_ref_idx)
            self.lab_offset_ref.setText(self._horizontal_reference_info_text(index, effective_mode))
            self._refresh_selected_offset_label()

            if index < len(self._resolved_items):
                resolved = self._resolved_items[index]
                family_label = self._format_module_family_label(str(getattr(resolved, "family_label", "") or ""))
                collision_html = ""
                if bool(getattr(resolved, "has_collision", False)):
                    collision_html = ' <span style="color:#b00020; font-weight:700;">Kolizja</span>'
                self.lab_selected_module_meta.setText(
                    f'<span style="font-weight:700; color:#111827;">{html.escape(resolved.display_name)}</span>'
                    f' <span style="color:#6b7280;">({html.escape(family_label)})</span><br>'
                    f'<span style="color:#334155;">{resolved.width_mm:.0f} x {resolved.height_mm:.0f} x {resolved.depth_mm:.0f} mm</span>'
                    f"{collision_html}"
                )
            else:
                self.lab_selected_module_meta.setText("Wybierz modul z listy albo kliknij go w podgladzie.")

            min_offset = self.preview._min_offset_for_module_index(index)
            max_offset = self.preview._max_offset_for_module_index(index)
            offset_mm = float(getattr(self._assembly.items[index], "offset_mm", 0.0) or 0.0)
            clamped_offset = max(min_offset, min(offset_mm, max_offset))
            self.sp_selected_offset.setRange(float(min_offset), max(float(min_offset), float(max_offset)))
            self.sp_selected_offset.setValue(clamped_offset)
            if self._is_top_view_active():
                max_wall_offset = self.preview_top._max_wall_depth_offset_for_index(index)
                current_wall_offset = self.preview_top._wall_depth_offset_for_index(index)
                self.sp_selected_y.setRange(0.0, max(0.0, float(max_wall_offset)))
                self._refresh_selected_y_label()
                self.sp_selected_y.setValue(min(current_wall_offset, max_wall_offset))
            else:
                max_y = self.preview._max_y_for_index(index)
                current_y = getattr(self._assembly.items[index], "position_y_mm", None)
                if current_y in (None, ""):
                    y_value = self.preview._auto_y_for_index(index)
                else:
                    y_value = max(0.0, float(current_y or 0.0))
                self.sp_selected_y.setRange(0.0, max(0.0, float(max_y)))
                self._refresh_selected_y_label()
                self.sp_selected_y.setValue(min(self._vertical_offset_value_for_ui(index, y_value), max_y))
        finally:
            self._is_syncing_offset_ui = False

    def _on_selected_y_reference_changed(self) -> None:
        if self._is_syncing_offset_ui:
            return
        self._refresh_selected_y_label()
        vertical_mode = self._selected_vertical_reference_mode()
        self.preview.set_vertical_reference_mode(vertical_mode)
        self.preview_top.set_vertical_reference_mode(vertical_mode)
        self._sync_selected_offset_editor()
        self._refresh_preview_info_bar()

    def _on_selected_x_reference_changed(self) -> None:
        if self._is_syncing_offset_ui:
            return
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return

        current_x = 0.0
        if index < len(self._resolved_items):
            current_x = float(getattr(self._resolved_items[index], "x_mm", 0.0) or 0.0)

        item = self._assembly.items[index]
        item.offset_ref_mode = self._selected_horizontal_reference_mode()
        min_offset = self.preview._min_offset_for_module_index(index)
        max_offset = self.preview._max_offset_for_module_index(index)
        base_x = self.preview._base_x_for_module_index(index)
        item.offset_mm = max(min_offset, min(current_x - base_x, max_offset))
        self._refresh_selected_offset_label()
        self._rebuild_assembly(select_index=index)

    def _on_selected_offset_changed(self, value: float) -> None:
        if self._is_syncing_offset_ui:
            return
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview._min_offset_for_module_index(index)
        max_offset = self.preview._max_offset_for_module_index(index)
        self._assembly.items[index].offset_mm = max(min_offset, min(float(value or 0.0), max_offset))
        self._rebuild_assembly(select_index=index)

    def _on_selected_y_changed(self, value: float) -> None:
        if self._is_syncing_offset_ui:
            return
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        if self._is_top_view_active():
            max_wall_offset = self.preview_top._max_wall_depth_offset_for_index(index)
            self._assembly.items[index].wall_depth_offset_mm = max(0.0, min(float(value or 0.0), max_wall_offset))
        else:
            self._assembly.items[index].position_y_mm = self._y_from_vertical_offset_ui_value(index, float(value or 0.0))
        self._rebuild_assembly(select_index=index)

    def _on_remove_selected_item(self) -> None:
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        self._assembly.items.pop(index)
        self._rebuild_assembly(select_index=min(index, len(self._assembly.items) - 1))

    def _move_selected_item(self, direction: int) -> None:
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        new_index = index + int(direction)
        if new_index < 0 or new_index >= len(self._assembly.items):
            return
        items = self._assembly.items
        items[index], items[new_index] = items[new_index], items[index]
        self._rebuild_assembly(select_index=new_index)

    def _rebuild_assembly(self, select_index: int | None = None) -> None:
        self._pull_ui_to_assembly()
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)
        linked_wall = None
        wall_name = str(getattr(self._assembly, "wall_name", "") or "").strip()
        if wall_name:
            linked_wall = self._wall_store.get(wall_name)
        self._resolved_items = resolve_assembly_items(
            self._assembly,
            self._catalog,
            auto_double_front_width_mm=auto_double_width,
            linked_wall=linked_wall,
        )
        self.preview.clear_hover_preview()
        self.preview_top.clear_hover_preview()
        self._refresh_items_table(select_index=select_index)
        self._refresh_summary()
        self._refresh_preview_only()

    def _refresh_items_table(self, select_index: int | None = None) -> None:
        self.tbl_items.setRowCount(len(self._resolved_items))
        for row, item in enumerate(self._resolved_items):
            family = str(getattr(item.module, "module_family", "") or "-")
            total = f"{item.cost_breakdown.grand_total_pln:.2f} zl"
            family_label = self._format_module_family_label(family)

            name_item = QTableWidgetItem(item.display_name)
            family_item = QTableWidgetItem(family_label)
            cost_item = QTableWidgetItem(total)
            cost_item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.tbl_items.setItem(row, 0, name_item)
            self.tbl_items.setItem(row, 1, family_item)
            self.tbl_items.setItem(row, 2, cost_item)

        if select_index is None:
            select_index = self._selected_index()

        if 0 <= select_index < self.tbl_items.rowCount():
            self.tbl_items.selectRow(select_index)
        elif self.tbl_items.rowCount() > 0:
            self.tbl_items.selectRow(0)

        has_selection = self.tbl_items.rowCount() > 0 and self._selected_index() >= 0
        self.btn_remove.setEnabled(has_selection)
        self.btn_move_up.setEnabled(has_selection)
        self.btn_move_down.setEnabled(has_selection)
        self._sync_selected_offset_editor()

    def _refresh_preview_only(self) -> None:
        vertical_mode = self._selected_vertical_reference_mode()
        self.preview.set_vertical_reference_mode(vertical_mode)
        self.preview_top.set_vertical_reference_mode(vertical_mode)
        self.preview.render_assembly(
            self._assembly,
            self._resolved_items,
            selected_index=self._selected_index(),
        )
        self.preview_top.render_assembly(
            self._assembly,
            self._resolved_items,
            selected_index=self._selected_index(),
        )
        self._refresh_preview_info_bar()

    def _selected_order_details(self) -> tuple[str, str]:
        order_name = str(getattr(self._assembly, "order_name", "") or "").strip()
        if not order_name:
            return "", ""
        order_def = self._order_store.get(order_name)
        if order_def is None:
            return "", ""
        status = str(getattr(order_def, "status", "") or "").strip()
        site_address = str(getattr(order_def, "site_address", "") or "").strip()
        return status, site_address

    def _refresh_summary(self) -> None:
        used_width = 0.0
        if self._resolved_items:
            used_width = max(float(item.x_mm + item.width_mm) for item in self._resolved_items)

        wall_width = float(getattr(self._assembly, "width_mm", 0.0) or 0.0)
        free_width = wall_width - used_width

        material_total = sum(item.cost_breakdown.material_total_pln for item in self._resolved_items)
        edgeband_total = sum(item.cost_breakdown.edgeband_total_pln for item in self._resolved_items)
        hardware_total = sum(item.cost_breakdown.hardware_total_pln for item in self._resolved_items)
        grand_total = sum(item.cost_breakdown.grand_total_pln for item in self._resolved_items)
        collision_count = sum(1 for item in self._resolved_items if bool(getattr(item, "has_collision", False)))

        profile_key = str(getattr(self._assembly, "material_profile_key", "STD_WHITE") or "STD_WHITE")
        force_hw_txt = "tak" if bool(getattr(self._assembly, "force_hardware_from_profile", True)) else "nie"
        wall_name = str(getattr(self._assembly, "wall_name", "") or "-")
        client_name = str(getattr(self._assembly, "client_name", "") or "-")
        order_name = str(getattr(self._assembly, "order_name", "") or "-")
        order_status, site_address = self._selected_order_details()

        lines = [
            f"Nazwa: {self._assembly.name}",
            f"Powiazana sciana: {wall_name}",
            f"Klient: {client_name}",
            f"Zamowienie: {order_name}",
            f"Pracownik: {str(getattr(self._assembly, 'worker_name', '') or '-')}",
            f"Liczba modulow: {len(self._resolved_items)}",
            f"Zajeta szerokosc: {used_width:.0f} / {wall_width:.0f} mm",
        ]

        material_overrides = dict(getattr(self._assembly, "material_overrides", {}) or {})
        override_chunks = []
        for group_key, label in (("carcass", "Korpus"), ("front", "Front"), ("back", "Plecy")):
            selected = str(material_overrides.get(group_key, "") or "").strip()
            if selected:
                override_chunks.append(f"{label}: {selected}")
        if override_chunks:
            lines.append(f"Materialy zestawu: {', '.join(override_chunks)}")

        if free_width >= 0.0:
            lines.append(f"Wolne miejsce: {free_width:.0f} mm")
        else:
            lines.append(f"Przekroczenie szerokosci: {abs(free_width):.0f} mm")

        lines.append(f"Profil zestawu: {profile_key}")
        if order_status:
            lines.append(f"Status zamowienia: {order_status}")
        if site_address:
            lines.append(f"Adres realizacji: {site_address}")

        lines.extend(
            [
                "",
                f"Materialy: {material_total:.2f} zl",
                f"Okleina: {edgeband_total:.2f} zl",
                f"Okucia: {hardware_total:.2f} zl",
                f"RAZEM: {grand_total:.2f} zl",
            ]
        )

        self.lab_summary.setText("\n".join(lines))
        if collision_count > 0:
            self.lab_layout_alert.setText(f"Kolizja: {collision_count} modul(y) nachodza na siebie.")
            self.lab_layout_alert.setStyleSheet("color:#b00020; font-weight:700;")
            self.lab_layout_alert.show()
        elif free_width < 0.0:
            self.lab_layout_alert.setText("Uwaga: modul(y) wychodza poza obrys kompletu.")
            self.lab_layout_alert.setStyleSheet("color:#b00020; font-weight:700;")
            self.lab_layout_alert.show()
        else:
            self.lab_layout_alert.clear()
            self.lab_layout_alert.hide()
