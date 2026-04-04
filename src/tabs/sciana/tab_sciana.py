from __future__ import annotations

import html
import json
from pathlib import Path

from PyQt6.QtCore import QItemSelectionModel, QMimeData, QPointF, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QFont, QKeySequence, QMouseEvent, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
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
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QProgressBar,
)

from src.app.app_settings import load_drawing_settings, load_ui_string_list, save_ui_string_list
from src.core.module_parts_service import build_module_parts, normalize_rail_offsets_mm
from src.domain.assembly_models import (
    AssemblyModuleItemDef,
    FurnitureAssemblyDef,
    normalize_assembly_offset_ref_mode,
    new_assembly_id,
)
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.domain.module_base_group import module_base_group_label_pl, normalize_module_base_group
from src.domain.module_models import ModuleDef, normalize_module_type, new_module_id
from src.domain.wall_models import WallLayoutDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.shopping_list_store_json import ShoppingListStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.tabs.sciana.dialog_load_assembly import LoadAssemblyDialog
from src.ui.collapsible_block import CollapsibleBlock
from src.ui.ui_polish import mark_ui_card, set_ui_variant
from src.ui.theme_utils import get_muted_color


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

FRONT_VARIANT_LABELS = {
    "all": "Wszystkie",
    "doors": "Drzwi",
    "drawers": "Szuflady",
    "mixed": "Mieszane",
    "open": "Otwarte",
}

WIDTH_VARIANT_LABELS = {
    "all": "Wszystkie",
    "narrow": "Do 45 cm",
    "60": "Ok. 60 cm",
    "80": "Ok. 80 cm",
    "90": "Ok. 90 cm",
    "wide": "100+ cm",
    "other": "Inne szer.",
}

BUSINESS_LIBRARY_LABELS = {
    "all": "Wszystkie",
    "kitchen": "Kuchnia",
    "wardrobe": "Szafy / garderoby",
    "bathroom": "Lazienka",
    "other": "Inne",
}

PRESET_VARIANT_LABELS = {
    "all": "Wszystkie",
    "standard": "Standardy",
    "custom": "Niestandardowe",
}

NAMED_LIBRARY_SET_LABELS = {
    "": "[bez zestawu]",
    "kitchen_upper_standard": "Kuchnia - gorne standard",
    "kitchen_drawers_80": "Kuchnia - szuflady 80",
    "wardrobe_standard": "Szafa - standard",
    "bathroom_basic": "Lazienka - basic",
}

NAMED_LIBRARY_SET_VALUES = {
    "kitchen_upper_standard": {
        "quick_group": "upper",
        "front_variant": "all",
        "width_variant": "all",
        "business_group": "kitchen",
        "preset_variant": "standard",
        "search": "",
    },
    "kitchen_drawers_80": {
        "quick_group": "all",
        "front_variant": "drawers",
        "width_variant": "80",
        "business_group": "kitchen",
        "preset_variant": "standard",
        "search": "",
    },
    "wardrobe_standard": {
        "quick_group": "tall",
        "front_variant": "all",
        "width_variant": "all",
        "business_group": "wardrobe",
        "preset_variant": "standard",
        "search": "",
    },
    "bathroom_basic": {
        "quick_group": "lower",
        "front_variant": "all",
        "width_variant": "all",
        "business_group": "bathroom",
        "preset_variant": "all",
        "search": "",
    },
}

HARDWARE_VENDOR_LABELS = {
    "": "[z profilu]",
    "generic": "Ogolne",
    "blum": "Blum",
    "hettich": "Hettich",
}

DECOR_PRESET_LABELS = {
    "": "[bez dekoru handlowego]",
    "white": "Bialy",
    "cashmere": "Cashmere",
    "oak": "Dab naturalny",
    "graphite": "Grafit",
    "black": "Czarny",
    "custom": "Indywidualny",
}

DECOR_PRESET_VALUES = {
    "white": {"carcass": "Bialy", "front": "Bialy"},
    "cashmere": {"carcass": "Cashmere", "front": "Cashmere"},
    "oak": {"carcass": "Dab naturalny", "front": "Dab naturalny"},
    "graphite": {"carcass": "Grafit", "front": "Grafit"},
    "black": {"carcass": "Czarny", "front": "Czarny"},
}

COMPANY_COLLECTION_LABELS = {
    "": "[bez kolekcji firmowej]",
    "basic_white": "Basic bialy",
    "premium_cashmere": "Premium cashmere",
    "wardrobe_graphite": "Szafa grafit",
    "display_black": "Witryna czarna",
}

COMPANY_COLLECTION_VALUES = {
    "basic_white": {
        "material_preset": "STD_WHITE",
        "hardware_vendor": "generic",
        "decor_preset": "white",
    },
    "premium_cashmere": {
        "material_preset": "OAK_PREMIUM",
        "hardware_vendor": "blum",
        "decor_preset": "cashmere",
    },
    "wardrobe_graphite": {
        "material_preset": "WARDROBE_GRAPHITE",
        "hardware_vendor": "hettich",
        "decor_preset": "graphite",
    },
    "display_black": {
        "material_preset": "DISPLAY_GLASS",
        "hardware_vendor": "blum",
        "decor_preset": "black",
    },
}


class AssemblyItemsTable(QTableWidget):
    def selectRow(self, row: int) -> None:  # type: ignore[override]
        self.clearSelection()
        super().selectRow(int(row))

_IMAGE_ATTACHMENT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


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


def _saved_module_front_variant_key(module: ModuleDef | None) -> str:
    if module is None:
        return "open"

    facade_mode = str(getattr(module, "facade_mode", "doors") or "doors").strip().lower()
    visible_parts = {str(part or "").strip().lower() for part in (getattr(module, "visible_parts", set()) or set())}

    if facade_mode == "drawers":
        return "drawers"
    if facade_mode == "mixed":
        return "mixed"
    if facade_mode in ("open", "open_shelves", "none"):
        return "open"
    if "front" not in visible_parts and facade_mode not in ("doors", "drawers", "mixed"):
        return "open"
    return "doors"


def _saved_module_front_variant_label(key: str) -> str:
    return FRONT_VARIANT_LABELS.get(str(key or "").strip().lower(), FRONT_VARIANT_LABELS["open"])


def _saved_module_width_variant_key(module: ModuleDef | None) -> str:
    width_mm = float(getattr(module, "width_mm", 0.0) or 0.0) if module is not None else 0.0
    if width_mm <= 450.0:
        return "narrow"
    if 550.0 <= width_mm <= 650.0:
        return "60"
    if 750.0 <= width_mm <= 850.0:
        return "80"
    if 850.0 < width_mm <= 950.0:
        return "90"
    if width_mm >= 1000.0:
        return "wide"
    return "other"


def _saved_module_width_variant_label(key: str) -> str:
    return WIDTH_VARIANT_LABELS.get(str(key or "").strip().lower(), WIDTH_VARIANT_LABELS["other"])


def _saved_module_business_group_key(module: ModuleDef | None) -> str:
    if module is None:
        return "other"

    base_group = normalize_module_base_group(str(getattr(module, "base_group", "") or ""))
    if base_group in BUSINESS_LIBRARY_LABELS:
        return base_group

    name_blob = " ".join(
        [
            str(getattr(module, "name", "") or ""),
            str(getattr(module, "module_family", "") or ""),
            str(getattr(module, "base_group", "") or ""),
        ]
    ).strip().lower()

    if any(token in name_blob for token in ("wardrobe", "garder", "szafa")):
        return "wardrobe"
    if any(token in name_blob for token in ("bath", "lazien")):
        return "bathroom"
    if any(token in name_blob for token in ("kitchen", "kuch")):
        return "kitchen"
    return "other"


def _saved_module_business_group_label(key: str) -> str:
    return BUSINESS_LIBRARY_LABELS.get(str(key or "").strip().lower(), BUSINESS_LIBRARY_LABELS["other"])


def _saved_module_preset_variant_key(module: ModuleDef | None) -> str:
    if module is None:
        return "custom"

    name_blob = " ".join(
        [
            str(getattr(module, "name", "") or ""),
            str(getattr(module, "module_family", "") or ""),
            str(getattr(module, "base_group", "") or ""),
        ]
    ).strip().lower()

    width_variant = _saved_module_width_variant_key(module)
    business_group = _saved_module_business_group_key(module)
    if any(token in name_blob for token in ("std", "standard", "fast")):
        return "standard"
    if business_group in {"kitchen", "wardrobe", "bathroom"} and width_variant in {"60", "80", "90"}:
        return "standard"
    return "custom"


def _saved_module_preset_variant_label(key: str) -> str:
    return PRESET_VARIANT_LABELS.get(str(key or "").strip().lower(), PRESET_VARIANT_LABELS["custom"])


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
    sig_module_selection_requested = pyqtSignal(int, bool)
    sig_module_selection_group_requested = pyqtSignal(object, bool)
    sig_module_reordered = pyqtSignal(int, int)
    sig_module_offset_changed = pyqtSignal(int, float)
    sig_module_position_changed = pyqtSignal(int, float, float)
    sig_module_top_position_changed = pyqtSignal(int, float, float)
    sig_apply_module_height_to_selected = pyqtSignal(int)
    sig_apply_module_width_to_selected = pyqtSignal(int)
    sig_apply_module_depth_to_selected = pyqtSignal(int)
    sig_apply_module_front_material_to_selected = pyqtSignal(int)
    sig_apply_module_carcass_material_to_selected = pyqtSignal(int)
    sig_apply_module_back_material_to_selected = pyqtSignal(int)
    sig_duplicate_selected_requested = pyqtSignal()
    sig_duplicate_selected_direction_requested = pyqtSignal(str)
    sig_duplicate_selected_repeat_requested = pyqtSignal(int)
    sig_duplicate_preview_requested = pyqtSignal(str)
    sig_align_selected_requested = pyqtSignal(str)
    sig_distribute_selected_requested = pyqtSignal()
    sig_toggle_snap_grid_requested = pyqtSignal()
    sig_snap_step_requested = pyqtSignal(int)
    sig_remove_selected_requested = pyqtSignal()
    sig_move_selected_requested = pyqtSignal(int)

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
        self._last_selected_indexes: list[int] = []
        self._last_wall_width = 100.0
        self._ghost_rect: QRectF | None = None
        self._ghost_label = ""
        self._selection_box_rect: QRectF | None = None
        self._selection_preserve = False
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
            selected_indexes=self._last_selected_indexes,
        )

    def clear_hover_preview(self) -> None:
        self._drop_indicator_x = None
        self._ghost_rect = None
        self._ghost_label = ""

    def _update_selection_box_preview(self, rect: QRectF | None, preserve_selection: bool = False) -> None:
        normalized_rect = QRectF(rect).normalized() if rect is not None else None
        same_rect = (
            (self._selection_box_rect is None and normalized_rect is None)
            or (self._selection_box_rect is not None and normalized_rect is not None and self._selection_box_rect == normalized_rect)
        )
        if same_rect and self._selection_preserve == bool(preserve_selection):
            return
        self._selection_box_rect = normalized_rect
        self._selection_preserve = bool(preserve_selection)
        self._rerender_cached_scene()

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

    def _indexes_in_scene_rect(self, selection_rect: QRectF) -> list[int]:
        rects = self._top_item_rects if self._view_mode == "top" else self._item_rects
        normalized = QRectF(selection_rect).normalized()
        indexes: list[int] = []
        for index, rect in enumerate(rects):
            if normalized.intersects(rect) or normalized.contains(rect.center()):
                indexes.append(index)
        return indexes

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
        # snap do lewej i prawej krawedzi sciany
        wall_width = max(0.0, float(self._last_assembly.width_mm if self._last_assembly is not None else 0.0))
        candidates = [0.0, max(0.0, wall_width - current_width) - base_x]

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
        selected_indexes: set[int],
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

            if index in selected_indexes:
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
            preserve_selection = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            range_selection = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if self._view_mode == "top":
                top_index = self._index_at_scene_pos(scene_pos, self._top_item_rects)
                if top_index >= 0:
                    if range_selection:
                        anchor = int(self._last_selected_index)
                        if anchor < 0 and self._last_selected_indexes:
                            anchor = int(self._last_selected_indexes[0])
                        if anchor < 0:
                            anchor = int(top_index)
                        start = min(anchor, int(top_index))
                        end = max(anchor, int(top_index))
                        self.sig_module_selection_group_requested.emit(list(range(start, end + 1)), preserve_selection)
                        event.accept()
                        return
                    if preserve_selection:
                        self.sig_module_selection_requested.emit(top_index, True)
                        event.accept()
                        return
                    rect = self._top_item_rects[top_index]
                    self._drag_index = top_index
                    self._drag_started = False
                    self._drag_mode = "position_top"
                    self._drag_start_scene = QPointF(scene_pos)
                    self._drag_left_offset = float(scene_pos.x() - rect.left())
                    self._drag_top_offset = float(scene_pos.y() - rect.top())
                    self._front_drag_offset_mm = None
                    self._front_drag_y_mm = None
                    self.sig_module_selection_requested.emit(top_index, False)
                    event.accept()
                    return
            else:
                front_index = self._index_at_scene_pos(scene_pos, self._item_rects)
                if front_index >= 0:
                    if range_selection:
                        anchor = int(self._last_selected_index)
                        if anchor < 0 and self._last_selected_indexes:
                            anchor = int(self._last_selected_indexes[0])
                        if anchor < 0:
                            anchor = int(front_index)
                        start = min(anchor, int(front_index))
                        end = max(anchor, int(front_index))
                        self.sig_module_selection_group_requested.emit(list(range(start, end + 1)), preserve_selection)
                        event.accept()
                        return
                    if preserve_selection:
                        self.sig_module_selection_requested.emit(front_index, True)
                        event.accept()
                        return
                    rect = self._item_rects[front_index]
                    self._drag_index = front_index
                    self._drag_started = False
                    self._drag_mode = "position"
                    self._drag_start_scene = QPointF(scene_pos)
                    self._drag_left_offset = float(scene_pos.x() - rect.left())
                    self._drag_top_offset = float(scene_pos.y() - rect.top())
                    self._front_drag_offset_mm = None
                    self._front_drag_y_mm = None
                    self.sig_module_selection_requested.emit(front_index, False)
                    event.accept()
                    return
            self._drag_index = -1
            self._drag_started = False
            self._drag_mode = "select_box"
            self._drag_start_scene = QPointF(scene_pos)
            self._selection_preserve = preserve_selection
            self._update_selection_box_preview(QRectF(scene_pos, scene_pos), preserve_selection=preserve_selection)
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
        if self._drag_mode == "select_box" and bool(event.buttons() & Qt.MouseButton.LeftButton):
            scene_pos = self.mapToScene(event.position().toPoint())
            delta = scene_pos - self._drag_start_scene
            if abs(delta.x()) >= 5.0 or abs(delta.y()) >= 5.0:
                self._drag_started = True
            selection_rect = QRectF(self._drag_start_scene, scene_pos).normalized()
            self._update_selection_box_preview(selection_rect, preserve_selection=self._selection_preserve)
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
                    self.sig_module_selection_requested.emit(drag_index, False)
                else:
                    self.sig_module_position_changed.emit(drag_index, committed_offset_mm, committed_y_mm)
                    self.sig_module_selection_requested.emit(drag_index, False)
            else:
                self.sig_module_selection_requested.emit(drag_index, False)
            event.accept()
            return
        if self._drag_mode == "select_box" and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            selection_rect = QRectF(self._drag_start_scene, scene_pos).normalized()
            started = bool(self._drag_started or selection_rect.width() >= 5.0 or selection_rect.height() >= 5.0)
            preserve_selection = bool(self._selection_preserve)
            self._drag_started = False
            self._drag_mode = ""
            self._drag_start_scene = QPointF()
            self._selection_preserve = False
            self._update_selection_box_preview(None)

            if started:
                self.sig_module_selection_group_requested.emit(self._indexes_in_scene_rect(selection_rect), preserve_selection)
            elif not preserve_selection:
                self.sig_module_selection_group_requested.emit([], False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        scene_pos = self.mapToScene(event.pos())
        rects = self._top_item_rects if self._view_mode == "top" else self._item_rects
        index = self._index_at_scene_pos(scene_pos, rects)
        if index < 0:
            super().contextMenuEvent(event)
            return

        selected_set = set(int(value) for value in self._last_selected_indexes)
        menu = QMenu(self)
        act_select_only = menu.addAction("Zaznacz tylko ten modul")
        if index in selected_set:
            act_toggle = menu.addAction("Usun ten modul z zaznaczenia")
        else:
            act_toggle = menu.addAction("Dodaj ten modul do zaznaczenia (Ctrl)")
        menu.addSeparator()
        act_duplicate = menu.addAction("Powiel zaznaczone")
        act_duplicate_right = menu.addAction("Powiel w prawo")
        act_duplicate_left = menu.addAction("Powiel w lewo")
        act_duplicate_down = menu.addAction("Powiel w dol")
        act_duplicate_up = menu.addAction("Powiel w gore")
        duplicate_repeat_menu = menu.addMenu("Szybkie powielenie")
        act_duplicate_x2 = duplicate_repeat_menu.addAction("Powiel x2")
        act_duplicate_x3 = duplicate_repeat_menu.addAction("Powiel x3")
        act_duplicate_x5 = duplicate_repeat_menu.addAction("Powiel x5")
        duplicate_preview_menu = menu.addMenu("Pokaz podglad kierunku")
        act_preview_right = duplicate_preview_menu.addAction("Podglad: w prawo")
        act_preview_left = duplicate_preview_menu.addAction("Podglad: w lewo")
        act_preview_down = duplicate_preview_menu.addAction("Podglad: w dol")
        act_preview_up = duplicate_preview_menu.addAction("Podglad: w gore")
        act_remove = menu.addAction("Usun zaznaczone")
        act_move_left = menu.addAction("Przesun zaznaczone w lewo")
        act_move_right = menu.addAction("Przesun zaznaczone w prawo")
        menu.addSeparator()
        act_align_left = menu.addAction("Wyrownaj do lewej")
        act_align_right = menu.addAction("Wyrownaj do prawej")
        act_align_top = menu.addAction("Wyrownaj do gory")
        act_align_bottom = menu.addAction("Wyrownaj do dolu")
        act_distribute = menu.addAction("Rozstaw rownomiernie")
        act_toggle_snap = menu.addAction("Przelacz snap siatki 50 mm")
        snap_step_menu = menu.addMenu("Krok snap")
        act_snap_10 = snap_step_menu.addAction("10 mm")
        act_snap_25 = snap_step_menu.addAction("25 mm")
        act_snap_50 = snap_step_menu.addAction("50 mm")
        act_snap_100 = snap_step_menu.addAction("100 mm")
        menu.addSeparator()
        act_apply_height = menu.addAction("Przepisz wysokosc tego modulu do zaznaczonych")
        act_apply_width = menu.addAction("Przepisz szerokosc tego modulu do zaznaczonych")
        act_apply_depth = menu.addAction("Przepisz glebokosc tego modulu do zaznaczonych")
        menu.addSeparator()
        act_apply_front = menu.addAction("Przepisz material frontu do zaznaczonych")
        act_apply_carcass = menu.addAction("Przepisz material korpusu do zaznaczonych")
        act_apply_back = menu.addAction("Przepisz material plecow do zaznaczonych")

        chosen = menu.exec(self.viewport().mapToGlobal(event.pos()))
        if chosen == act_select_only:
            self.sig_module_selection_requested.emit(index, False)
            event.accept()
            return
        if chosen == act_toggle:
            self.sig_module_selection_requested.emit(index, True)
            event.accept()
            return
        if chosen in {
            act_duplicate,
            act_duplicate_right,
            act_duplicate_left,
            act_duplicate_down,
            act_duplicate_up,
            act_duplicate_x2,
            act_duplicate_x3,
            act_duplicate_x5,
            act_preview_right,
            act_preview_left,
            act_preview_down,
            act_preview_up,
            act_remove,
            act_move_left,
            act_move_right,
            act_align_left,
            act_align_right,
            act_align_top,
            act_align_bottom,
            act_distribute,
            act_toggle_snap,
            act_snap_10,
            act_snap_25,
            act_snap_50,
            act_snap_100,
        }:
            if index not in selected_set:
                preserve_selection = bool(selected_set)
                self.sig_module_selection_requested.emit(index, preserve_selection)
            if chosen == act_duplicate:
                self.sig_duplicate_selected_requested.emit()
                event.accept()
                return
            if chosen == act_duplicate_right:
                self.sig_duplicate_selected_direction_requested.emit("right")
                event.accept()
                return
            if chosen == act_duplicate_left:
                self.sig_duplicate_selected_direction_requested.emit("left")
                event.accept()
                return
            if chosen == act_duplicate_down:
                self.sig_duplicate_selected_direction_requested.emit("down")
                event.accept()
                return
            if chosen == act_duplicate_up:
                self.sig_duplicate_selected_direction_requested.emit("up")
                event.accept()
                return
            if chosen == act_duplicate_x2:
                self.sig_duplicate_selected_repeat_requested.emit(2)
                event.accept()
                return
            if chosen == act_duplicate_x3:
                self.sig_duplicate_selected_repeat_requested.emit(3)
                event.accept()
                return
            if chosen == act_duplicate_x5:
                self.sig_duplicate_selected_repeat_requested.emit(5)
                event.accept()
                return
            if chosen == act_preview_right:
                self.sig_duplicate_preview_requested.emit("right")
                event.accept()
                return
            if chosen == act_preview_left:
                self.sig_duplicate_preview_requested.emit("left")
                event.accept()
                return
            if chosen == act_preview_down:
                self.sig_duplicate_preview_requested.emit("down")
                event.accept()
                return
            if chosen == act_preview_up:
                self.sig_duplicate_preview_requested.emit("up")
                event.accept()
                return
            if chosen == act_remove:
                self.sig_remove_selected_requested.emit()
                event.accept()
                return
            if chosen == act_move_left:
                self.sig_move_selected_requested.emit(-1)
                event.accept()
                return
            if chosen == act_move_right:
                self.sig_move_selected_requested.emit(1)
                event.accept()
                return
            if chosen == act_align_left:
                self.sig_align_selected_requested.emit("left")
                event.accept()
                return
            if chosen == act_align_right:
                self.sig_align_selected_requested.emit("right")
                event.accept()
                return
            if chosen == act_align_top:
                self.sig_align_selected_requested.emit("top")
                event.accept()
                return
            if chosen == act_align_bottom:
                self.sig_align_selected_requested.emit("bottom")
                event.accept()
                return
            if chosen == act_distribute:
                self.sig_distribute_selected_requested.emit()
                event.accept()
                return
            if chosen == act_toggle_snap:
                self.sig_toggle_snap_grid_requested.emit()
                event.accept()
                return
            if chosen == act_snap_10:
                self.sig_snap_step_requested.emit(10)
                event.accept()
                return
            if chosen == act_snap_25:
                self.sig_snap_step_requested.emit(25)
                event.accept()
                return
            if chosen == act_snap_50:
                self.sig_snap_step_requested.emit(50)
                event.accept()
                return
            if chosen == act_snap_100:
                self.sig_snap_step_requested.emit(100)
                event.accept()
                return
        if chosen == act_apply_height:
            self.sig_apply_module_height_to_selected.emit(index)
            event.accept()
            return
        if chosen == act_apply_width:
            self.sig_apply_module_width_to_selected.emit(index)
            event.accept()
            return
        if chosen == act_apply_depth:
            self.sig_apply_module_depth_to_selected.emit(index)
            event.accept()
            return
        if chosen == act_apply_front:
            self.sig_apply_module_front_material_to_selected.emit(index)
            event.accept()
            return
        if chosen == act_apply_carcass:
            self.sig_apply_module_carcass_material_to_selected.emit(index)
            event.accept()
            return
        if chosen == act_apply_back:
            self.sig_apply_module_back_material_to_selected.emit(index)
            event.accept()
            return
        super().contextMenuEvent(event)

    def render_assembly(
        self,
        assembly: FurnitureAssemblyDef,
        resolved_items,
        selected_index: int = -1,
        selected_indexes: list[int] | None = None,
    ) -> None:
        self._last_assembly = assembly
        self._last_resolved_items = list(resolved_items or [])
        self._last_selected_index = int(selected_index)
        self._last_selected_indexes = sorted({int(index) for index in (selected_indexes or ([] if selected_index < 0 else [selected_index]))})

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
        selected_set = set(self._last_selected_indexes)
        if self._view_mode == "top":
            linked_wall = self._linked_wall_for_assembly(assembly)
            _top_origin_y, top_bottom_y = self._draw_top_view_context(
                assembly,
                linked_wall,
                resolved_items,
                selected_index,
                selected_set,
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

            if self._selection_box_rect is not None:
                selection_pen = QPen(QColor("#1f6ed4"))
                selection_pen.setWidth(2)
                selection_pen.setStyle(Qt.PenStyle.DashLine)
                selection_brush = QBrush(QColor(31, 110, 212, 30))
                selection_item = self.scene.addRect(QRectF(self._selection_box_rect), selection_pen, selection_brush)
                selection_item.setData(0, "assembly_selection_box")
                selection_item.setZValue(60.0)

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
                elif index in selected_set:
                    brush = QBrush(QColor("#fff4df"))
                    pen = QPen(QColor("#9a5b17"))
                else:
                    brush = QBrush(QColor("#fffdf8"))
                    pen = QPen(QColor("#cbbda8"))

                pen.setWidth(4 if index in selected_set else 1)
                module_item = self.scene.addRect(rect, pen, brush)
                module_item.setData(0, f"assembly_module__{index}")
                module_item.setZValue(0.4 if index in selected_set else 0.2)

                for shape in self._build_module_front_shapes(item.module, rect):
                    shape_key = str(shape.get("key", "") or "")
                    shape_rect = shape.get("rect")
                    if not isinstance(shape_rect, QRectF):
                        continue

                    shape_pen = QPen(QColor(str(shape.get("pen", "#1f1f1f"))))
                    shape_pen.setWidth(2 if index in selected_set else 1)
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
                        shape_item.setZValue(3.8 if index in selected_set else 3.2)
                    elif shape_key.startswith("shelf_") or shape_key.startswith("divider_"):
                        shape_item.setZValue(3.4 if index in selected_set else 2.8)
                    elif shape_key.startswith("front_drawer_split_") or shape_key == "front_split_line" or shape_key.startswith("front_handle_"):
                        shape_item.setZValue(4.2 if index in selected_set else 3.6)
                    else:
                        shape_item.setZValue(2.6 if index in selected_set else 2.2)

                    if index not in selected_set and shape_key != "front":
                        try:
                            shape_item.setOpacity(0.88)
                        except Exception:
                            pass
                    elif index not in selected_set and shape_key == "front":
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

        if self._selection_box_rect is not None:
            selection_pen = QPen(QColor("#1f6ed4"))
            selection_pen.setWidth(2)
            selection_pen.setStyle(Qt.PenStyle.DashLine)
            selection_brush = QBrush(QColor(31, 110, 212, 30))
            selection_item = self.scene.addRect(QRectF(self._selection_box_rect), selection_pen, selection_brush)
            selection_item.setData(0, "assembly_selection_box")
            selection_item.setZValue(60.0)

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
    sig_open_wycena_requested = pyqtSignal(str)  # assembly name

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
        self._assembly = FurnitureAssemblyDef(assembly_id=new_assembly_id())
        self._resolved_items = []
        self._is_pushing_ui = False
        self._is_syncing_offset_ui = False
        self._is_syncing_bulk_ui = False
        self._is_syncing_view_ui = False
        self._order_status_context = ""
        self._site_address_context = ""
        self._project_references: list[dict[str, str]] = []
        self._project_reference_pixmap = QPixmap()
        self._left_zone_visible = True
        self._left_zone_last_width = 330
        self._right_zone_visible = True
        self._right_zone_last_width = 300
        self._snap_grid_enabled = False
        self._snap_grid_step_mm = 50.0

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.right_zone_toggle = QPushButton("Panel informacyjny >", self)
        self.right_zone_toggle.setStyleSheet("QPushButton { border: none; background: transparent; color: #555; font-weight: 600; padding: 4px; text-align: left; }")
        self.right_zone_toggle.clicked.connect(self._toggle_right_zone)
        # Hide root vertical toggle to reclaim horizontal workspace.
        self.right_zone_toggle.hide()

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(self.main_splitter, 1)

        self.left_zone = self._build_left_zone()
        self.center_zone = self._build_center_zone()
        self.right_zone = self._build_right_zone()
        self.preview.sig_saved_module_dropped.connect(self._on_saved_module_dropped)
        self.preview.sig_module_selection_requested.connect(self._on_preview_module_selection_requested)
        self.preview.sig_module_selection_group_requested.connect(self._on_preview_module_selection_group_requested)
        self.preview.sig_apply_module_height_to_selected.connect(self._on_preview_apply_height_to_selected)
        self.preview.sig_apply_module_width_to_selected.connect(self._on_preview_apply_width_to_selected)
        self.preview.sig_apply_module_depth_to_selected.connect(self._on_preview_apply_depth_to_selected)
        self.preview.sig_apply_module_front_material_to_selected.connect(self._on_preview_apply_front_material_to_selected)
        self.preview.sig_apply_module_carcass_material_to_selected.connect(self._on_preview_apply_carcass_material_to_selected)
        self.preview.sig_apply_module_back_material_to_selected.connect(self._on_preview_apply_back_material_to_selected)
        self.preview.sig_duplicate_selected_requested.connect(self._on_duplicate_selected_item)
        self.preview.sig_duplicate_selected_direction_requested.connect(self._on_duplicate_selected_item_direction)
        self.preview.sig_duplicate_selected_repeat_requested.connect(self._on_duplicate_selected_item_repeat)
        self.preview.sig_duplicate_preview_requested.connect(self._show_duplicate_direction_preview)
        self.preview.sig_align_selected_requested.connect(self._on_align_selected_requested)
        self.preview.sig_distribute_selected_requested.connect(self._on_distribute_selected_horizontally)
        self.preview.sig_toggle_snap_grid_requested.connect(self._toggle_snap_grid)
        self.preview.sig_snap_step_requested.connect(self._set_snap_step)
        self.preview.sig_remove_selected_requested.connect(self._on_remove_selected_item)
        self.preview.sig_move_selected_requested.connect(self._move_selected_item)
        self.preview.sig_module_reordered.connect(self._on_preview_module_reordered)
        self.preview.sig_module_offset_changed.connect(self._on_preview_module_offset_changed)
        self.preview.sig_module_position_changed.connect(self._on_preview_module_position_changed)
        self.preview_top.sig_saved_module_dropped.connect(self._on_saved_module_dropped)
        self.preview_top.sig_module_selection_requested.connect(self._on_preview_module_selection_requested)
        self.preview_top.sig_module_selection_group_requested.connect(self._on_preview_module_selection_group_requested)
        self.preview_top.sig_apply_module_height_to_selected.connect(self._on_preview_apply_height_to_selected)
        self.preview_top.sig_apply_module_width_to_selected.connect(self._on_preview_apply_width_to_selected)
        self.preview_top.sig_apply_module_depth_to_selected.connect(self._on_preview_apply_depth_to_selected)
        self.preview_top.sig_apply_module_front_material_to_selected.connect(self._on_preview_apply_front_material_to_selected)
        self.preview_top.sig_apply_module_carcass_material_to_selected.connect(self._on_preview_apply_carcass_material_to_selected)
        self.preview_top.sig_apply_module_back_material_to_selected.connect(self._on_preview_apply_back_material_to_selected)
        self.preview_top.sig_duplicate_selected_requested.connect(self._on_duplicate_selected_item)
        self.preview_top.sig_duplicate_selected_direction_requested.connect(self._on_duplicate_selected_item_direction)
        self.preview_top.sig_duplicate_selected_repeat_requested.connect(self._on_duplicate_selected_item_repeat)
        self.preview_top.sig_duplicate_preview_requested.connect(self._show_duplicate_direction_preview)
        self.preview_top.sig_align_selected_requested.connect(self._on_align_selected_requested)
        self.preview_top.sig_distribute_selected_requested.connect(self._on_distribute_selected_horizontally)
        self.preview_top.sig_toggle_snap_grid_requested.connect(self._toggle_snap_grid)
        self.preview_top.sig_snap_step_requested.connect(self._set_snap_step)
        self.preview_top.sig_remove_selected_requested.connect(self._on_remove_selected_item)
        self.preview_top.sig_move_selected_requested.connect(self._move_selected_item)
        self.preview_top.sig_module_top_position_changed.connect(self._on_preview_top_position_changed)

        self.main_splitter.addWidget(self.left_zone)
        self.main_splitter.addWidget(self.center_zone)
        self.main_splitter.addWidget(self.right_zone)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([330, 1080, 300])
        self.left_zone.show()

        self._reload_profiles()
        self._reload_quick_material_presets()
        self._reload_material_choices()
        self._reload_selected_module_material_choices()
        self._reload_bulk_module_material_choices()
        self._reload_hardware_vendor_presets()
        self._reload_decor_presets()
        self._reload_company_collections()
        self._reload_worker_choices()
        self._reload_saved_walls()
        self._reload_saved_modules()
        self._on_active_view_changed()
        self.preview.set_vertical_reference_mode(self._selected_vertical_reference_mode())
        self.preview_top.set_vertical_reference_mode(self._selected_vertical_reference_mode())
        self._push_assembly_to_ui()
        self._rebuild_assembly()
        self._shortcut_actions = {
            "save": ("Ctrl+S", self._shortcut_save_assembly),
            "overwrite": ("Ctrl+Shift+S", self._on_overwrite),
            "load": ("Ctrl+L", self._on_load),
            "new": ("Ctrl+N", self.start_new_assembly),
            "focus_search": ("Ctrl+F", self._shortcut_focus_saved_search),
            "duplicate": ("Ctrl+D", self._on_duplicate_selected_item),
            "toggle_snap": ("Ctrl+G", self._toggle_snap_grid),
            "toggle_left": ("Ctrl+Shift+L", self._toggle_left_zone_visibility),
        }
        self._setup_shortcuts_from_settings()
        self._refresh_left_zone_toggle_button()
        self._refresh_snap_button_text()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_profiles()
        self._reload_quick_material_presets()
        self._reload_material_choices()
        self._reload_selected_module_material_choices()
        self._reload_bulk_module_material_choices()
        self._reload_hardware_vendor_presets()
        self._reload_decor_presets()
        self._reload_company_collections()
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
        self.cb_wall.setMinimumContentsLength(26)
        self.cb_wall.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.btn_refresh_walls = QPushButton("Odswiez sciany")
        self.chk_force_hardware = QCheckBox("Narzuc okucia z profilu zestawu")
        self.chk_force_hardware.setChecked(True)
        self.cb_material_carcass = QComboBox()
        self.cb_material_front = QComboBox()
        self.cb_material_back = QComboBox()
        self.cb_company_collection = QComboBox()
        self.cb_company_collection.setMinimumContentsLength(18)
        self.cb_company_collection.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.cb_quick_material_preset = QComboBox()
        self.cb_quick_material_preset.setMinimumContentsLength(18)
        self.cb_quick_material_preset.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.btn_apply_company_collection = QPushButton("Zastosuj")
        self.btn_apply_material_preset = QPushButton("Zastosuj")
        self.btn_clear_material_overrides = QPushButton("Wyczysc nadpisania")
        self.cb_hardware_vendor_preset = QComboBox()
        self.cb_quick_decor_preset = QComboBox()
        self.ed_decor_carcass = QLineEdit()
        self.ed_decor_front = QLineEdit()
        self.btn_clear_decor_labels = QPushButton("Wyczysc dekor")
        self.lab_material_preset_hint = QLabel("")
        self.lab_material_preset_hint.setWordWrap(True)
        self.lab_material_preset_hint.setStyleSheet(f"color:{get_muted_color()};")
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
        set_ui_variant(self.btn_save, "primary")
        set_ui_variant(self.btn_load, "ghost")
        set_ui_variant(self.btn_overwrite, "ghost")
        store_btns.addWidget(self.btn_save)
        store_btns.addWidget(self.btn_load)
        store_btns.addWidget(self.btn_overwrite)
        form.addRow("", self._wrap_row_widget(self.box_setup, store_btns))

        self.btn_back_to_order = QPushButton("Powrot do zamowienia")
        set_ui_variant(self.btn_back_to_order, "ghost")
        form.addRow("", self.btn_back_to_order)

        self.lab_store_status = QLabel("")
        self.lab_store_status.setWordWrap(True)
        self.lab_store_status.setStyleSheet(f"color:{get_muted_color()};")
        form.addRow("", self.lab_store_status)
        set_ui_variant(self.btn_refresh_walls, "ghost")
        set_ui_variant(self.btn_apply_company_collection, "success")
        set_ui_variant(self.btn_apply_material_preset, "success")
        set_ui_variant(self.btn_clear_decor_labels, "danger")
        set_ui_variant(self.btn_clear_material_overrides, "danger")
        for button in (
            self.btn_refresh_walls,
            self.btn_save,
            self.btn_load,
            self.btn_overwrite,
            self.btn_back_to_order,
            self.btn_apply_company_collection,
            self.btn_apply_material_preset,
            self.btn_clear_decor_labels,
            self.btn_clear_material_overrides,
        ):
            button.setMinimumHeight(30)

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
        company_row = QWidget(self.box_materials)
        company_row_layout = QHBoxLayout(company_row)
        company_row_layout.setContentsMargins(0, 0, 0, 0)
        company_row_layout.setSpacing(6)
        company_row_layout.addWidget(self.cb_company_collection, 1)
        company_row_layout.addWidget(self.btn_apply_company_collection, 0)
        preset_row = QWidget(self.box_materials)
        preset_row_layout = QHBoxLayout(preset_row)
        preset_row_layout.setContentsMargins(0, 0, 0, 0)
        preset_row_layout.setSpacing(6)
        preset_row_layout.addWidget(self.cb_quick_material_preset, 1)
        preset_row_layout.addWidget(self.btn_apply_material_preset, 0)
        materials_form.addRow("Kolekcja firmowa", company_row)
        materials_form.addRow("Szybki preset", preset_row)
        materials_form.addRow("Korpus", self.cb_material_carcass)
        materials_form.addRow("Front", self.cb_material_front)
        materials_form.addRow("Plecy", self.cb_material_back)
        materials_form.addRow("Wariant okuc", self.cb_hardware_vendor_preset)
        materials_form.addRow("Dekor kompletu", self.cb_quick_decor_preset)
        materials_form.addRow("Dekor korpusu", self.ed_decor_carcass)
        materials_form.addRow("Dekor frontu", self.ed_decor_front)
        materials_form.addRow("", self.btn_clear_decor_labels)
        materials_form.addRow("", self.btn_clear_material_overrides)
        materials_form.addRow("", self.lab_material_preset_hint)

        self.block_materials = CollapsibleBlock("Materialy kompletu", panel)
        self.block_materials.content_layout().addWidget(self.box_materials)
        self.block_materials.set_expanded(True)
        layout.addWidget(self.block_materials)

        box_store = QGroupBox("", panel)
        store_layout = QVBoxLayout(box_store)
        store_row = QHBoxLayout()
        self.btn_refresh_saved = QPushButton("Odswiez")
        set_ui_variant(self.btn_refresh_saved, "ghost")
        self.btn_refresh_saved.setMinimumHeight(30)
        store_row.addStretch(1)
        store_row.addWidget(self.btn_refresh_saved, 0)
        store_layout.addLayout(store_row)

        named_set_row = QHBoxLayout()
        self.cb_saved_named_set = QComboBox(box_store)
        for key, label in NAMED_LIBRARY_SET_LABELS.items():
            self.cb_saved_named_set.addItem(label, key)
        self.btn_apply_saved_named_set = QPushButton("Zastosuj zestaw")
        set_ui_variant(self.btn_apply_saved_named_set, "success")
        self.btn_apply_saved_named_set.setMinimumHeight(30)
        named_set_row.addWidget(QLabel("Zestaw:", box_store), 0)
        named_set_row.addWidget(self.cb_saved_named_set, 1)
        named_set_row.addWidget(self.btn_apply_saved_named_set, 0)
        store_layout.addLayout(named_set_row)

        filter_row = QHBoxLayout()
        self.cb_saved_quick_group = QComboBox(box_store)
        for key, label in QUICK_LIBRARY_LABELS.items():
            self.cb_saved_quick_group.addItem(label, key)
        filter_row.addWidget(QLabel("Typ:", box_store), 0)
        filter_row.addWidget(self.cb_saved_quick_group, 1)
        store_layout.addLayout(filter_row)

        variant_row = QHBoxLayout()
        self.cb_saved_front_variant = QComboBox(box_store)
        for key, label in FRONT_VARIANT_LABELS.items():
            self.cb_saved_front_variant.addItem(label, key)
        variant_row.addWidget(QLabel("Front:", box_store), 0)
        variant_row.addWidget(self.cb_saved_front_variant, 1)

        self.cb_saved_width_variant = QComboBox(box_store)
        for key, label in WIDTH_VARIANT_LABELS.items():
            self.cb_saved_width_variant.addItem(label, key)
        variant_row.addWidget(QLabel("Szer.:", box_store), 0)
        variant_row.addWidget(self.cb_saved_width_variant, 1)
        store_layout.addLayout(variant_row)

        business_row = QHBoxLayout()
        self.cb_saved_business_group = QComboBox(box_store)
        for key, label in BUSINESS_LIBRARY_LABELS.items():
            self.cb_saved_business_group.addItem(label, key)
        business_row.addWidget(QLabel("Zastos.:", box_store), 0)
        business_row.addWidget(self.cb_saved_business_group, 1)

        self.cb_saved_preset_variant = QComboBox(box_store)
        for key, label in PRESET_VARIANT_LABELS.items():
            self.cb_saved_preset_variant.addItem(label, key)
        business_row.addWidget(QLabel("Preset:", box_store), 0)
        business_row.addWidget(self.cb_saved_preset_variant, 1)
        store_layout.addLayout(business_row)

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
        set_ui_variant(self.btn_add_saved, "primary")
        self.btn_add_saved.setMinimumHeight(30)
        store_layout.addWidget(self.btn_add_saved)

        quick_presets_row = QHBoxLayout()
        self.btn_add_front_only = QPushButton("+ Front")
        self.btn_add_shelf_only = QPushButton("+ Polka")
        self.btn_add_wall_panel = QPushButton("+ Panel")
        set_ui_variant(self.btn_add_front_only, "success")
        set_ui_variant(self.btn_add_shelf_only, "success")
        set_ui_variant(self.btn_add_wall_panel, "ghost")
        for button in (self.btn_add_front_only, self.btn_add_shelf_only, self.btn_add_wall_panel):
            button.setMinimumHeight(30)
            quick_presets_row.addWidget(button, 1)
        store_layout.addLayout(quick_presets_row)

        self.lab_saved_hint = QLabel("Moduly sa pobierane z bazy zakladki Modul. Mozesz kliknac i przeciagnac modul na sciane.")
        self.lab_saved_hint.setWordWrap(True)
        self.lab_saved_hint.setStyleSheet(f"color:{get_muted_color()};")
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
        self.btn_apply_company_collection.clicked.connect(self._apply_selected_company_collection)
        self.cb_quick_material_preset.currentIndexChanged.connect(self._refresh_quick_material_preset_hint)
        self.btn_apply_material_preset.clicked.connect(self._apply_selected_quick_material_preset)
        self.btn_clear_material_overrides.clicked.connect(self._clear_material_overrides)
        self.cb_material_carcass.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_material_front.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_material_back.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_hardware_vendor_preset.currentIndexChanged.connect(self._on_assembly_changed)
        self.cb_quick_decor_preset.currentIndexChanged.connect(self._apply_selected_decor_preset)
        self.ed_decor_carcass.textChanged.connect(self._on_assembly_changed)
        self.ed_decor_front.textChanged.connect(self._on_assembly_changed)
        self.btn_clear_decor_labels.clicked.connect(self._clear_decor_labels)
        self.btn_refresh_saved.clicked.connect(self._reload_saved_modules)
        self.btn_apply_saved_named_set.clicked.connect(self._apply_selected_saved_named_set)
        self.cb_saved_quick_group.currentIndexChanged.connect(self._reload_saved_modules)
        self.cb_saved_front_variant.currentIndexChanged.connect(self._reload_saved_modules)
        self.cb_saved_width_variant.currentIndexChanged.connect(self._reload_saved_modules)
        self.cb_saved_business_group.currentIndexChanged.connect(self._reload_saved_modules)
        self.cb_saved_preset_variant.currentIndexChanged.connect(self._reload_saved_modules)
        self.ed_saved_search.textChanged.connect(self._reload_saved_modules)
        self.ed_saved_search.returnPressed.connect(self._on_add_saved_module)
        self.btn_add_saved.clicked.connect(self._on_add_saved_module)
        self.btn_add_front_only.clicked.connect(lambda: self._add_quick_preset_module("front_only"))
        self.btn_add_shelf_only.clicked.connect(lambda: self._add_quick_preset_module("shelf_only"))
        self.btn_add_wall_panel.clicked.connect(lambda: self._add_quick_preset_module("wall_panel"))
        self.tree_saved_modules.currentItemChanged.connect(self._on_saved_module_selection_changed)
        self.tree_saved_modules.itemDoubleClicked.connect(self._on_saved_module_item_double_clicked)
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

    def _refresh_left_zone_toggle_button(self) -> None:
        if not hasattr(self, "btn_toggle_left_zone"):
            return
        self.btn_toggle_left_zone.setText("Pokaz lewy panel" if not self._left_zone_visible else "Ukryj lewy panel")

    def _refresh_snap_button_text(self) -> None:
        if not hasattr(self, "btn_snap_grid"):
            return
        step_label = int(self._snap_grid_step_mm) if float(self._snap_grid_step_mm).is_integer() else self._snap_grid_step_mm
        self.btn_snap_grid.setChecked(bool(self._snap_grid_enabled))
        state = "ON" if self._snap_grid_enabled else "OFF"
        self.btn_snap_grid.setText(f"Snap {step_label}mm: {state}")
        if hasattr(self, "cb_snap_step"):
            idx = self.cb_snap_step.findData(int(round(float(self._snap_grid_step_mm))))
            if idx >= 0 and self.cb_snap_step.currentIndex() != idx:
                self.cb_snap_step.blockSignals(True)
                self.cb_snap_step.setCurrentIndex(idx)
                self.cb_snap_step.blockSignals(False)

    def _toggle_right_zone(self) -> None:
        self._right_zone_visible = not self._right_zone_visible
        if self._right_zone_visible:
            self.right_zone.setVisible(True)
            self.right_zone_toggle.setText("Panel informacyjny >")
            sizes = list(self.main_splitter.sizes())
            if len(sizes) >= 3:
                sizes[2] = self._right_zone_last_width
                self.main_splitter.setSizes(sizes)
        else:
            sizes = list(self.main_splitter.sizes())
            if len(sizes) >= 3:
                self._right_zone_last_width = sizes[2]
                sizes[2] = 0
                self.main_splitter.setSizes(sizes)
            self.right_zone.setVisible(False)
            self.right_zone_toggle.setText("< Panel informacyjny")

    def _toggle_snap_grid(self, _checked: bool | None = None) -> None:
        self._snap_grid_enabled = not self._snap_grid_enabled
        self._refresh_snap_button_text()
        self._set_store_status(
            f"Snap siatki {'wlaczony' if self._snap_grid_enabled else 'wylaczony'} ({self._snap_grid_step_mm:.0f} mm).",
            ok=True,
        )

    def _set_snap_step(self, step_mm: int) -> None:
        step = max(1, int(step_mm or 50))
        self._snap_grid_step_mm = float(step)
        self._refresh_snap_button_text()
        self._set_store_status(f"Ustawiono krok snap: {step} mm.", ok=True)

    def _on_snap_step_combo_changed(self, _index: int) -> None:
        self._set_snap_step(int(self.cb_snap_step.currentData() or 50))

    def _snap_mm(self, value_mm: float) -> float:
        if not self._snap_grid_enabled:
            return float(value_mm)
        step = max(1.0, float(self._snap_grid_step_mm or 50.0))
        return round(float(value_mm) / step) * step

    def _toggle_left_zone_visibility(self) -> None:
        if not hasattr(self, "main_splitter"):
            return
        sizes = self.main_splitter.sizes()
        if len(sizes) < 3:
            return

        left, center, right = int(sizes[0]), int(sizes[1]), int(sizes[2])
        total_main = max(600, left + center)
        if self._left_zone_visible:
            if left > 0:
                self._left_zone_last_width = max(220, left)
            self._left_zone_visible = False
            self.left_zone.hide()
            self.main_splitter.setSizes([0, total_main, right])
        else:
            target_left = max(220, int(self._left_zone_last_width or 330))
            target_left = min(target_left, max(220, total_main - 300))
            restored_center = max(300, total_main - target_left)
            self._left_zone_visible = True
            self.left_zone.show()
            self.main_splitter.setSizes([target_left, restored_center, right])

        self._refresh_left_zone_toggle_button()

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

        selected_indexes = self._selected_indexes()
        if len(selected_indexes) > 1:
            self.lab_active_module_info.setText(
                f"Zaznaczono {len(selected_indexes)} modulow. Uzyj bloku 'Zaznaczone moduly', aby zmienic je grupowo."
            )
            return

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
        mark_ui_card(self.preview_info_box, elevated=False)
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
        set_ui_variant(self.btn_view_front, "ghost")
        self.btn_view_front.setMinimumHeight(30)
        self.btn_view_top = QPushButton("Gora", view_switch)
        self.btn_view_top.setCheckable(True)
        set_ui_variant(self.btn_view_top, "ghost")
        self.btn_view_top.setMinimumHeight(30)
        view_switch_layout.addWidget(QLabel("Widok:", view_switch), 0)
        view_switch_layout.addWidget(self.btn_view_front, 0)
        view_switch_layout.addWidget(self.btn_view_top, 0)
        self.btn_snap_grid = QPushButton("Snap 50mm: OFF", view_switch)
        self.btn_snap_grid.setCheckable(True)
        self.btn_snap_grid.setChecked(False)
        set_ui_variant(self.btn_snap_grid, "success")
        self.btn_snap_grid.setMinimumHeight(30)
        view_switch_layout.addWidget(self.btn_snap_grid, 0)
        self.cb_snap_step = QComboBox(view_switch)
        self.cb_snap_step.addItem("10 mm", 10)
        self.cb_snap_step.addItem("25 mm", 25)
        self.cb_snap_step.addItem("50 mm", 50)
        self.cb_snap_step.addItem("100 mm", 100)
        self.cb_snap_step.setCurrentIndex(2)
        view_switch_layout.addWidget(self.cb_snap_step, 0)
        self.btn_toggle_left_zone = QPushButton("Ukryj lewy panel", view_switch)
        set_ui_variant(self.btn_toggle_left_zone, "ghost")
        self.btn_toggle_left_zone.setMinimumHeight(30)
        view_switch_layout.addWidget(self.btn_toggle_left_zone, 0)
        info_top_row.addWidget(view_switch, 0)
        info_layout.addLayout(info_top_row)

        quick_actions = QWidget(self.preview_info_box)
        quick_actions.setStyleSheet("QWidget { background: transparent; border: 0; }")
        quick_actions_layout = QHBoxLayout(quick_actions)
        quick_actions_layout.setContentsMargins(0, 0, 0, 0)
        quick_actions_layout.setSpacing(10)

        self.btn_q_save = QPushButton("Zapisz", quick_actions)
        self.btn_q_save.clicked.connect(self._shortcut_save_assembly)
        set_ui_variant(self.btn_q_save, "primary")
        self.btn_q_save.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_save, 0)

        self.btn_q_overwrite = QPushButton("Nadpisz", quick_actions)
        self.btn_q_overwrite.clicked.connect(self._on_overwrite)
        set_ui_variant(self.btn_q_overwrite, "ghost")
        self.btn_q_overwrite.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_overwrite, 0)

        self.btn_q_load = QPushButton("Wczytaj", quick_actions)
        self.btn_q_load.clicked.connect(self._on_load)
        set_ui_variant(self.btn_q_load, "ghost")
        self.btn_q_load.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_load, 0)

        self.btn_q_new = QPushButton("Nowy", quick_actions)
        self.btn_q_new.clicked.connect(self.start_new_assembly)
        set_ui_variant(self.btn_q_new, "ghost")
        self.btn_q_new.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_new, 0)

        self.btn_q_search = QPushButton("Szukaj", quick_actions)
        self.btn_q_search.clicked.connect(self._shortcut_focus_saved_search)
        set_ui_variant(self.btn_q_search, "ghost")
        self.btn_q_search.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_search, 0)

        self.btn_q_duplicate = QPushButton("Duplikuj", quick_actions)
        self.btn_q_duplicate.clicked.connect(self._on_duplicate_selected_item)
        set_ui_variant(self.btn_q_duplicate, "success")
        self.btn_q_duplicate.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_duplicate, 0)

        self.btn_q_snap = QPushButton("Snap", quick_actions)
        self.btn_q_snap.clicked.connect(self._toggle_snap_grid)
        set_ui_variant(self.btn_q_snap, "success")
        self.btn_q_snap.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_snap, 0)

        self.btn_q_shortcuts = QPushButton("Skroty", quick_actions)
        self.btn_q_shortcuts.clicked.connect(self._open_shortcuts_dialog)
        set_ui_variant(self.btn_q_shortcuts, "ghost")
        self.btn_q_shortcuts.setMinimumHeight(30)
        quick_actions_layout.addWidget(self.btn_q_shortcuts, 0)

        self.btn_q_more = QToolButton(quick_actions)
        self.btn_q_more.setText("Wiecej")
        self.btn_q_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        set_ui_variant(self.btn_q_more, "ghost")
        self.btn_q_more.setMinimumHeight(30)
        self._quick_more_menu = QMenu(self.btn_q_more)
        self._quick_more_menu.addAction("Nadpisz", self._on_overwrite)
        self._quick_more_menu.addAction("Wczytaj", self._on_load)
        self._quick_more_menu.addAction("Nowy komplet", self.start_new_assembly)
        self._quick_more_menu.addAction("Szukaj", self._shortcut_focus_saved_search)
        self._quick_more_menu.addAction("Duplikuj", self._on_duplicate_selected_item)
        self._quick_more_menu.addAction("Snap ON/OFF", self._toggle_snap_grid)
        self._quick_more_menu.addAction("Pokaz/ukryj lewy panel", self._toggle_left_zone_visibility)
        self._quick_more_menu.addAction("Skroty", self._open_shortcuts_dialog)
        self.btn_q_more.setMenu(self._quick_more_menu)
        quick_actions_layout.addWidget(self.btn_q_more, 0)

        for btn, min_w, max_w in (
            (self.btn_q_save, 96, 124),
            (self.btn_q_overwrite, 102, 132),
            (self.btn_q_load, 96, 124),
            (self.btn_q_new, 90, 114),
            (self.btn_q_search, 94, 120),
            (self.btn_q_duplicate, 102, 132),
            (self.btn_q_snap, 88, 112),
            (self.btn_q_shortcuts, 98, 126),
        ):
            btn.setMinimumWidth(min_w)
            btn.setMaximumWidth(max_w)
        self.btn_q_more.setMinimumWidth(90)
        self.btn_q_more.setMaximumWidth(120)
        for btn in (
            self.btn_q_save,
            self.btn_q_overwrite,
            self.btn_q_load,
            self.btn_q_new,
            self.btn_q_search,
            self.btn_q_duplicate,
            self.btn_q_snap,
            self.btn_q_shortcuts,
            self.btn_q_more,
        ):
            btn.setMinimumHeight(36)
            btn.setMaximumHeight(36)

        # Desktop-first: keep all key actions visible.
        for btn in (
            self.btn_q_overwrite,
            self.btn_q_load,
            self.btn_q_new,
            self.btn_q_search,
            self.btn_q_duplicate,
            self.btn_q_snap,
            self.btn_q_shortcuts,
        ):
            btn.show()
        self.btn_q_more.hide()

        quick_actions_layout.addStretch(1)
        info_layout.addWidget(quick_actions, 0)

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
        self.btn_snap_grid.clicked.connect(self._toggle_snap_grid)
        self.cb_snap_step.currentIndexChanged.connect(self._on_snap_step_combo_changed)
        self.btn_toggle_left_zone.clicked.connect(self._toggle_left_zone_visibility)
        self.btn_toggle_left_zone.hide()
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

        self.tbl_items = AssemblyItemsTable(0, 3, box_items)
        self.tbl_items.setHorizontalHeaderLabels(["Modul", "Typ", "Koszt"])
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        self.btn_duplicate = QPushButton("Duplikuj")
        self.btn_align_left = QPushButton("Wyrownaj lewo")
        self.btn_align_right = QPushButton("Wyrownaj prawo")
        self.btn_align_top = QPushButton("Wyrownaj gora")
        self.btn_align_bottom = QPushButton("Wyrownaj dol")
        self.btn_distribute = QPushButton("Rozstaw")
        self.btn_remove = QPushButton("Usun")
        set_ui_variant(self.btn_move_up, "ghost")
        set_ui_variant(self.btn_move_down, "ghost")
        set_ui_variant(self.btn_duplicate, "success")
        set_ui_variant(self.btn_align_left, "ghost")
        set_ui_variant(self.btn_align_right, "ghost")
        set_ui_variant(self.btn_align_top, "ghost")
        set_ui_variant(self.btn_align_bottom, "ghost")
        set_ui_variant(self.btn_distribute, "success")
        set_ui_variant(self.btn_remove, "danger")
        for button in (
            self.btn_move_up,
            self.btn_move_down,
            self.btn_duplicate,
            self.btn_align_left,
            self.btn_align_right,
            self.btn_align_top,
            self.btn_align_bottom,
            self.btn_distribute,
            self.btn_remove,
        ):
            button.setMinimumHeight(30)
        btn_row.addWidget(self.btn_move_up)
        btn_row.addWidget(self.btn_move_down)
        btn_row.addWidget(self.btn_duplicate)
        btn_row.addWidget(self.btn_align_left)
        btn_row.addWidget(self.btn_align_right)
        btn_row.addWidget(self.btn_align_top)
        btn_row.addWidget(self.btn_align_bottom)
        btn_row.addWidget(self.btn_distribute)
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
        self.sp_selected_width = QDoubleSpinBox(box_offset)
        self.sp_selected_width.setRange(100.0, 3000.0)
        self.sp_selected_width.setDecimals(1)
        self.sp_selected_width.setSuffix(" mm")
        self.sp_selected_height = QDoubleSpinBox(box_offset)
        self.sp_selected_height.setRange(100.0, 5000.0)
        self.sp_selected_height.setDecimals(1)
        self.sp_selected_height.setSuffix(" mm")
        self.sp_selected_depth = QDoubleSpinBox(box_offset)
        self.sp_selected_depth.setRange(50.0, 2000.0)
        self.sp_selected_depth.setDecimals(1)
        self.sp_selected_depth.setSuffix(" mm")
        self.cb_selected_material_carcass = QComboBox(box_offset)
        self.cb_selected_material_front = QComboBox(box_offset)
        self.cb_selected_material_back = QComboBox(box_offset)
        self.lab_selected_offset = QLabel("Offset", box_offset)
        self.lab_selected_y = QLabel("Od gory", box_offset)
        self.offset_form.addRow("Pozioma baza", self.cb_selected_x_ref)
        self.offset_form.addRow("Odniesienie", self.lab_offset_ref)
        self.offset_form.addRow("Pionowa baza", self.cb_selected_y_ref)
        self.offset_form.addRow(self.lab_selected_offset, self.sp_selected_offset)
        self.offset_form.addRow(self.lab_selected_y, self.sp_selected_y)
        self.offset_form.addRow("Szerokosc", self.sp_selected_width)
        self.offset_form.addRow("Wysokosc", self.sp_selected_height)
        self.offset_form.addRow("Glebokosc", self.sp_selected_depth)
        self.offset_form.addRow("Mat. korpusu", self.cb_selected_material_carcass)
        self.offset_form.addRow("Mat. frontu", self.cb_selected_material_front)
        self.offset_form.addRow("Mat. plecow", self.cb_selected_material_back)
        box_offset_layout.addLayout(self.offset_form)
        self.block_offset = CollapsibleBlock("Aktywny modul", scroll_content)
        self.block_offset.content_layout().addWidget(box_offset)
        self.block_offset.set_expanded(True)
        scroll_layout.addWidget(self.block_offset, 0)

        box_bulk = QGroupBox("", scroll_content)
        box_bulk_layout = QVBoxLayout(box_bulk)
        box_bulk_layout.setContentsMargins(0, 0, 0, 0)
        box_bulk_layout.setSpacing(6)
        self.lab_bulk_modules_meta = QLabel("Zaznacz kilka modulow z listy, aby zmienic je grupowo.")
        self.lab_bulk_modules_meta.setWordWrap(True)
        self.lab_bulk_modules_meta.setStyleSheet("color:#4b5563;")
        box_bulk_layout.addWidget(self.lab_bulk_modules_meta)
        self.bulk_form = QFormLayout()
        self.sp_bulk_height = QDoubleSpinBox(box_bulk)
        self.sp_bulk_height.setRange(0.0, 5000.0)
        self.sp_bulk_height.setDecimals(1)
        self.sp_bulk_height.setSuffix(" mm")
        self.sp_bulk_height.setSpecialValueText("[bez zmiany]")
        self.cb_bulk_material_carcass = QComboBox(box_bulk)
        self.cb_bulk_material_front = QComboBox(box_bulk)
        self.cb_bulk_material_back = QComboBox(box_bulk)
        self.bulk_form.addRow("Wysokosc", self.sp_bulk_height)
        self.bulk_form.addRow("Mat. korpusu", self.cb_bulk_material_carcass)
        self.bulk_form.addRow("Mat. frontu", self.cb_bulk_material_front)
        self.bulk_form.addRow("Mat. plecow", self.cb_bulk_material_back)
        box_bulk_layout.addLayout(self.bulk_form)
        self.btn_apply_bulk_modules = QPushButton("Zastosuj do zaznaczonych", box_bulk)
        set_ui_variant(self.btn_apply_bulk_modules, "success")
        self.btn_apply_bulk_modules.setMinimumHeight(30)
        box_bulk_layout.addWidget(self.btn_apply_bulk_modules)
        self.block_bulk_modules = CollapsibleBlock("Zaznaczone moduly", scroll_content)
        self.block_bulk_modules.content_layout().addWidget(box_bulk)
        self.block_bulk_modules.set_expanded(False)
        scroll_layout.addWidget(self.block_bulk_modules, 0)

        box_references = QGroupBox("", scroll_content)
        references_layout = QVBoxLayout(box_references)
        references_layout.setContentsMargins(0, 0, 0, 0)
        references_layout.setSpacing(6)
        self.tbl_project_refs = QTableWidget(0, 3, box_references)
        self.tbl_project_refs.setHorizontalHeaderLabels(["Plik", "Cel", "Opis"])
        self.tbl_project_refs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_project_refs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_project_refs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_project_refs.verticalHeader().setVisible(False)
        self.tbl_project_refs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_project_refs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_project_refs.horizontalHeader().setStretchLastSection(True)
        self.tbl_project_refs.setAlternatingRowColors(True)
        self.tbl_project_refs.setMinimumHeight(120)
        references_layout.addWidget(self.tbl_project_refs)
        self.lab_project_reference_info = QLabel("Brak referencji z projektu.")
        self.lab_project_reference_info.setWordWrap(True)
        self.lab_project_reference_info.setStyleSheet("color:#4b5563;")
        references_layout.addWidget(self.lab_project_reference_info)
        self.lab_project_reference_preview = QLabel("Brak podgladu referencji.")
        self.lab_project_reference_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_project_reference_preview.setMinimumHeight(170)
        self.lab_project_reference_preview.setStyleSheet(
            "border:1px solid #d8d4ce; background:#fbfaf8; color:#6b7280; padding:6px;"
        )
        references_layout.addWidget(self.lab_project_reference_preview)
        self.block_project_refs = CollapsibleBlock("Referencje z projektu", scroll_content)
        self.block_project_refs.content_layout().addWidget(box_references)
        self.block_project_refs.set_expanded(True)
        scroll_layout.addWidget(self.block_project_refs, 0)

        self.lab_layout_alert = QLabel("", scroll_content)
        self.lab_layout_alert.setWordWrap(True)
        self.lab_layout_alert.hide()
        scroll_layout.addWidget(self.lab_layout_alert, 0)

        box_summary = QGroupBox("", scroll_content)
        summary_layout = QVBoxLayout(box_summary)
        quick_costs = QWidget(box_summary)
        quick_costs_layout = QGridLayout(quick_costs)
        quick_costs_layout.setContentsMargins(0, 0, 0, 0)
        quick_costs_layout.setHorizontalSpacing(8)
        quick_costs_layout.setVerticalSpacing(8)

        def build_cost_card(title: str) -> tuple[QWidget, QLabel]:
            card = QFrame(quick_costs)
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setStyleSheet(
                "QFrame {"
                " border:1px solid #d8d4ce;"
                " border-radius:8px;"
                " background:#fbfaf8;"
                " padding:4px;"
                "}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(2)
            label_title = QLabel(title, card)
            label_title.setStyleSheet("color:#6b5d4d; font-weight:600;")
            label_value = QLabel("0.00 zl", card)
            label_value.setStyleSheet("color:#2f241b; font-weight:700; font-size:15px;")
            card_layout.addWidget(label_title)
            card_layout.addWidget(label_value)
            return card, label_value

        card_materials, self.lab_summary_material_total = build_cost_card("Materialy")
        card_edgeband, self.lab_summary_edgeband_total = build_cost_card("Okleina")
        card_hardware, self.lab_summary_hardware_total = build_cost_card("Okucia")
        card_total, self.lab_summary_grand_total = build_cost_card("Razem")
        quick_costs_layout.addWidget(card_materials, 0, 0)
        quick_costs_layout.addWidget(card_edgeband, 0, 1)
        quick_costs_layout.addWidget(card_hardware, 1, 0)
        quick_costs_layout.addWidget(card_total, 1, 1)
        summary_layout.addWidget(quick_costs)

        # ── PASEK WYPELNIENIA ─────────────────────────────────────
        fill_row = QHBoxLayout()
        fill_row.setSpacing(6)
        fill_row.addWidget(QLabel("Wypelnienie:"))
        self.fill_bar = QProgressBar(scroll_content)
        self.fill_bar.setRange(0, 100)
        self.fill_bar.setValue(0)
        self.fill_bar.setTextVisible(True)
        self.fill_bar.setFixedHeight(16)
        self.fill_bar.setStyleSheet(
            "QProgressBar{border:1px solid #d1d5db;border-radius:8px;background:#f3f4f6;text-align:center;font-size:10px;}"
            "QProgressBar::chunk{border-radius:8px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22c55e,stop:0.75 #f59e0b,stop:1 #ef4444);}"
        )
        fill_row.addWidget(self.fill_bar, 1)
        self.lab_fill_info = QLabel("0 / 0 mm")
        self.lab_fill_info.setStyleSheet("font-size:10px; color:#6b7280;")
        fill_row.addWidget(self.lab_fill_info)
        summary_layout.addLayout(fill_row)

        # ── SZYBKA KALKULACJA HANDLOWA ────────────────────────────
        box_trade = QGroupBox("Kalkulacja handlowa", scroll_content)
        trade_form = QFormLayout(box_trade)
        trade_form.setSpacing(4)
        trade_form.setContentsMargins(8, 6, 8, 6)

        def _sp_trade(suffix: str, max_val: float = 100000.0) -> QDoubleSpinBox:
            sb = QDoubleSpinBox()
            sb.setRange(0.0, max_val)
            sb.setDecimals(2)
            sb.setSingleStep(100.0)
            sb.setSuffix(f" {suffix}")
            sb.setFixedHeight(24)
            return sb

        self.sp_trade_labor = _sp_trade("zl")
        self.sp_trade_transport = _sp_trade("zl")
        self.sp_trade_montage = _sp_trade("zl")
        self.sp_trade_margin = QDoubleSpinBox()
        self.sp_trade_margin.setRange(0.0, 200.0)
        self.sp_trade_margin.setDecimals(1)
        self.sp_trade_margin.setSuffix(" %")
        self.sp_trade_margin.setValue(30.0)
        self.sp_trade_margin.setFixedHeight(24)

        self.lab_trade_netto = QLabel("0.00 zl")
        self.lab_trade_netto.setStyleSheet("font-weight:700; color:#1f2937; font-size:13px;")
        self.lab_trade_brutto = QLabel("0.00 zl")
        self.lab_trade_brutto.setStyleSheet("font-weight:800; color:#0f172a; font-size:14px;")
        self.lab_trade_profit = QLabel("0.00 zl")
        self.lab_trade_profit.setStyleSheet("font-weight:600; color:#15803d;")

        trade_form.addRow("Robocizna:", self.sp_trade_labor)
        trade_form.addRow("Transport:", self.sp_trade_transport)
        trade_form.addRow("Montaz:", self.sp_trade_montage)
        trade_form.addRow("Marza:", self.sp_trade_margin)
        sep_t = QFrame()
        sep_t.setFrameShape(QFrame.Shape.HLine)
        sep_t.setFrameShadow(QFrame.Shadow.Sunken)
        trade_form.addRow(sep_t)
        trade_form.addRow("Netto:", self.lab_trade_netto)
        trade_form.addRow("Brutto (23%):", self.lab_trade_brutto)
        trade_form.addRow("Narost:", self.lab_trade_profit)

        self.btn_open_wycena = QPushButton("Wyslij do Wyceny →")
        self.btn_open_wycena.setToolTip(
            "Otwiera karte Wycena z tym kompletem zaznaczonym na liscie"
        )
        self.btn_open_wycena.setMinimumHeight(28)
        self.btn_open_wycena.setStyleSheet(
            "QPushButton{background:#1d4ed8;color:#fff;border-radius:4px;"
            "font-weight:700;font-size:11px;padding:4px 10px;}"
            "QPushButton:hover{background:#2563eb;}"
            "QPushButton:pressed{background:#1e40af;}"
        )
        self.btn_open_wycena.clicked.connect(self._on_open_in_wycena)
        trade_form.addRow(self.btn_open_wycena)

        self.btn_send_shopping = QPushButton("Wyslij do listy zakupow →")
        self.btn_send_shopping.setToolTip(
            "Agreguje materialy ze wszystkich modulow i dodaje do listy zakupow"
        )
        self.btn_send_shopping.setMinimumHeight(28)
        self.btn_send_shopping.setStyleSheet(
            "QPushButton{background:#15803d;color:#fff;border-radius:4px;"
            "font-weight:700;font-size:11px;padding:4px 10px;}"
            "QPushButton:hover{background:#16a34a;}"
            "QPushButton:pressed{background:#166534;}"
        )
        self.btn_send_shopping.clicked.connect(self._on_send_to_shopping_list)
        trade_form.addRow(self.btn_send_shopping)

        summary_layout.addWidget(box_trade)

        for sp in (self.sp_trade_labor, self.sp_trade_transport, self.sp_trade_montage, self.sp_trade_margin):
            sp.valueChanged.connect(self._refresh_trade_calc)

        self.lab_summary = QLabel("-")
        self.lab_summary.setWordWrap(True)
        summary_layout.addWidget(self.lab_summary)
        self.block_summary = CollapsibleBlock("Podsumowanie kompletu", scroll_content)
        self.block_summary.content_layout().addWidget(box_summary)
        self.block_summary.set_expanded(True)
        scroll_layout.addWidget(self.block_summary, 0)
        scroll_layout.addStretch(1)
        self.right_scroll_area.setWidget(scroll_content)

        self.tbl_items.itemSelectionChanged.connect(self._on_items_selection_changed)
        self.btn_remove.clicked.connect(self._on_remove_selected_item)
        self.btn_move_up.clicked.connect(lambda: self._move_selected_item(-1))
        self.btn_move_down.clicked.connect(lambda: self._move_selected_item(1))
        self.btn_duplicate.clicked.connect(self._on_duplicate_selected_item)
        self.btn_align_left.clicked.connect(lambda: self._on_align_selected_horizontal("left"))
        self.btn_align_right.clicked.connect(lambda: self._on_align_selected_horizontal("right"))
        self.btn_align_top.clicked.connect(lambda: self._on_align_selected_vertical("top"))
        self.btn_align_bottom.clicked.connect(lambda: self._on_align_selected_vertical("bottom"))
        self.btn_distribute.clicked.connect(self._on_distribute_selected_horizontally)
        self.cb_selected_x_ref.currentIndexChanged.connect(self._on_selected_x_reference_changed)
        self.cb_selected_y_ref.currentIndexChanged.connect(self._on_selected_y_reference_changed)
        self.sp_selected_offset.valueChanged.connect(self._on_selected_offset_changed)
        self.sp_selected_y.valueChanged.connect(self._on_selected_y_changed)
        self.sp_selected_width.valueChanged.connect(self._on_selected_dimensions_changed)
        self.sp_selected_height.valueChanged.connect(self._on_selected_dimensions_changed)
        self.sp_selected_depth.valueChanged.connect(self._on_selected_dimensions_changed)
        self.cb_selected_material_carcass.currentIndexChanged.connect(self._on_selected_module_materials_changed)
        self.cb_selected_material_front.currentIndexChanged.connect(self._on_selected_module_materials_changed)
        self.cb_selected_material_back.currentIndexChanged.connect(self._on_selected_module_materials_changed)
        self.btn_apply_bulk_modules.clicked.connect(self._apply_bulk_changes_to_selected)
        self.sp_bulk_height.valueChanged.connect(self._on_bulk_height_changed_auto)
        self.cb_bulk_material_carcass.currentIndexChanged.connect(self._on_bulk_materials_changed_auto)
        self.cb_bulk_material_front.currentIndexChanged.connect(self._on_bulk_materials_changed_auto)
        self.cb_bulk_material_back.currentIndexChanged.connect(self._on_bulk_materials_changed_auto)
        self.tbl_project_refs.itemSelectionChanged.connect(self._on_project_reference_selection_changed)

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

    def _reload_quick_material_presets(self) -> None:
        current_key = str(self.cb_quick_material_preset.currentData() or "")
        assembly_key = str(getattr(self._assembly, "material_profile_key", "STD_WHITE") or "STD_WHITE")
        profiles = self._catalog.list_material_profiles()

        self.cb_quick_material_preset.blockSignals(True)
        self.cb_quick_material_preset.clear()
        self.cb_quick_material_preset.addItem("[bez szybkiego presetu]", "")
        self.cb_quick_material_preset.setItemData(
            0,
            "Pozostawia reczne ustawienie materialow bez gotowego wariantu handlowego.",
            Qt.ItemDataRole.ToolTipRole,
        )
        for profile in profiles:
            label = profile.name_pl
            self.cb_quick_material_preset.addItem(label, profile.key)
            index = self.cb_quick_material_preset.count() - 1
            self.cb_quick_material_preset.setItemData(index, str(getattr(profile, "description", "") or ""), Qt.ItemDataRole.ToolTipRole)

        idx = self.cb_quick_material_preset.findData(current_key)
        if idx < 0:
            idx = self.cb_quick_material_preset.findData(assembly_key)
        if idx < 0:
            idx = 0
        self.cb_quick_material_preset.setCurrentIndex(idx)
        self.cb_quick_material_preset.blockSignals(False)
        self._refresh_quick_material_preset_hint()

    def _reload_hardware_vendor_presets(self) -> None:
        current_vendor = str(self.cb_hardware_vendor_preset.currentData() or "").strip().lower()
        assembly_vendor = str(
            dict(getattr(self._assembly, "hardware_vendor_overrides", {}) or {}).get("hinge", "") or ""
        ).strip().lower()
        vendor_names = sorted(
            {
                str(vendor or "").strip().lower()
                for vendor in (
                    self._catalog.list_hardware_manufacturers("hinge")
                    + self._catalog.list_hardware_manufacturers("drawer_system")
                )
                if str(vendor or "").strip()
            }
        )

        self.cb_hardware_vendor_preset.blockSignals(True)
        self.cb_hardware_vendor_preset.clear()
        for vendor in [""] + vendor_names:
            label = HARDWARE_VENDOR_LABELS.get(vendor, str(vendor).title())
            self.cb_hardware_vendor_preset.addItem(label, vendor)
        idx = self.cb_hardware_vendor_preset.findData(current_vendor)
        if idx < 0:
            idx = self.cb_hardware_vendor_preset.findData(assembly_vendor)
        if idx < 0:
            idx = 0
        self.cb_hardware_vendor_preset.setCurrentIndex(idx)
        self.cb_hardware_vendor_preset.blockSignals(False)

    def _company_collection_matches(
        self,
        collection_key: str,
        profile_key: str,
        hardware_vendor: str,
        decor_key: str,
    ) -> bool:
        values = dict(COMPANY_COLLECTION_VALUES.get(collection_key, {}))
        if not values:
            return False
        return (
            str(values.get("material_preset", "") or "").strip() == str(profile_key or "").strip()
            and str(values.get("hardware_vendor", "") or "").strip().lower() == str(hardware_vendor or "").strip().lower()
            and str(values.get("decor_preset", "") or "").strip() == str(decor_key or "").strip()
        )

    def _matching_company_collection_key(self, profile_key: str, hardware_vendor: str, decor_key: str) -> str:
        normalized_profile = str(profile_key or "").strip()
        normalized_vendor = str(hardware_vendor or "").strip().lower()
        normalized_decor = str(decor_key or "").strip()
        if not normalized_profile and not normalized_vendor and not normalized_decor:
            return ""
        for collection_key in COMPANY_COLLECTION_VALUES:
            if self._company_collection_matches(collection_key, normalized_profile, normalized_vendor, normalized_decor):
                return collection_key
        return ""

    def _reload_company_collections(self) -> None:
        current_key = str(self.cb_company_collection.currentData() or "").strip()
        assembly_key = str(getattr(self._assembly, "company_collection_key", "") or "").strip()
        hardware_vendor = str(
            dict(getattr(self._assembly, "hardware_vendor_overrides", {}) or {}).get("hinge", "") or ""
        ).strip().lower()
        decor_key = str(getattr(self._assembly, "decor_preset_key", "") or "").strip()
        if not decor_key:
            decor_key = self._matching_decor_preset_key(dict(getattr(self._assembly, "decor_labels", {}) or {}))
        matched_key = self._matching_company_collection_key(
            str(getattr(self._assembly, "material_profile_key", "STD_WHITE") or "STD_WHITE"),
            hardware_vendor,
            decor_key,
        )

        self.cb_company_collection.blockSignals(True)
        self.cb_company_collection.clear()
        for key, label in COMPANY_COLLECTION_LABELS.items():
            self.cb_company_collection.addItem(label, key)
        idx = self.cb_company_collection.findData(current_key)
        if idx < 0:
            idx = self.cb_company_collection.findData(assembly_key)
        if idx < 0:
            idx = self.cb_company_collection.findData(matched_key)
        if idx < 0:
            idx = 0
        self.cb_company_collection.setCurrentIndex(idx)
        self.cb_company_collection.blockSignals(False)

    def _matching_decor_preset_key(self, decor_labels: dict[str, str] | None) -> str:
        labels = {
            "carcass": str((decor_labels or {}).get("carcass", "") or "").strip(),
            "front": str((decor_labels or {}).get("front", "") or "").strip(),
        }
        if not labels["carcass"] and not labels["front"]:
            return ""
        for preset_key, values in DECOR_PRESET_VALUES.items():
            if (
                str(values.get("carcass", "") or "").strip() == labels["carcass"]
                and str(values.get("front", "") or "").strip() == labels["front"]
            ):
                return preset_key
        return "custom"

    def _reload_decor_presets(self) -> None:
        decor_labels = dict(getattr(self._assembly, "decor_labels", {}) or {})
        current_key = str(self.cb_quick_decor_preset.currentData() or "").strip()
        assembly_key = str(getattr(self._assembly, "decor_preset_key", "") or "").strip()
        matched_key = self._matching_decor_preset_key(decor_labels)

        self.cb_quick_decor_preset.blockSignals(True)
        self.cb_quick_decor_preset.clear()
        for key, label in DECOR_PRESET_LABELS.items():
            self.cb_quick_decor_preset.addItem(label, key)
        idx = self.cb_quick_decor_preset.findData(current_key)
        if idx < 0:
            idx = self.cb_quick_decor_preset.findData(assembly_key)
        if idx < 0:
            idx = self.cb_quick_decor_preset.findData(matched_key)
        if idx < 0:
            idx = 0
        self.cb_quick_decor_preset.setCurrentIndex(idx)
        self.cb_quick_decor_preset.blockSignals(False)

    def _apply_selected_decor_preset(self) -> None:
        preset_key = str(self.cb_quick_decor_preset.currentData() or "").strip()
        if preset_key == "custom":
            return

        values = dict(DECOR_PRESET_VALUES.get(preset_key, {}))
        self._is_pushing_ui = True
        try:
            self.ed_decor_carcass.setText(str(values.get("carcass", "") or ""))
            self.ed_decor_front.setText(str(values.get("front", "") or ""))
        finally:
            self._is_pushing_ui = False

        self._pull_ui_to_assembly()
        self._refresh_summary()

    def _apply_selected_company_collection(self) -> None:
        collection_key = str(self.cb_company_collection.currentData() or "").strip()
        if not collection_key:
            return

        values = dict(COMPANY_COLLECTION_VALUES.get(collection_key, {}))
        self._is_pushing_ui = True
        try:
            material_idx = self.cb_quick_material_preset.findData(str(values.get("material_preset", "") or "").strip())
            if material_idx >= 0:
                self.cb_quick_material_preset.setCurrentIndex(material_idx)
            hardware_idx = self.cb_hardware_vendor_preset.findData(str(values.get("hardware_vendor", "") or "").strip().lower())
            if hardware_idx >= 0:
                self.cb_hardware_vendor_preset.setCurrentIndex(hardware_idx)
            decor_idx = self.cb_quick_decor_preset.findData(str(values.get("decor_preset", "") or "").strip())
            if decor_idx >= 0:
                self.cb_quick_decor_preset.setCurrentIndex(decor_idx)
        finally:
            self._is_pushing_ui = False

        self._apply_selected_quick_material_preset()
        self._apply_selected_decor_preset()
        self._pull_ui_to_assembly()
        self._rebuild_assembly()

    def _clear_decor_labels(self) -> None:
        self._is_pushing_ui = True
        try:
            self.ed_decor_carcass.clear()
            self.ed_decor_front.clear()
            self.cb_quick_decor_preset.setCurrentIndex(0)
        finally:
            self._is_pushing_ui = False
        self._pull_ui_to_assembly()
        self._refresh_summary()

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

    def _refresh_quick_material_preset_hint(self) -> None:
        preset_key = str(self.cb_quick_material_preset.currentData() or "").strip()
        if not preset_key:
            self.lab_material_preset_hint.setText(
                "Jeden klik ustawia typowy wariant handlowy dla korpusu, frontu i plecow. Dekor kompletu zapisuje kolor/dekor handlowy do wyceny."
            )
            return

        description = ""
        for profile in self._catalog.list_material_profiles():
            if str(getattr(profile, "key", "") or "").strip() == preset_key:
                description = str(getattr(profile, "description", "") or "").strip()
                break
        if not description:
            description = f"Gotowy wariant handlowy: {preset_key}."
        self.lab_material_preset_hint.setText(description)

    def _reload_selected_module_material_choices(self) -> None:
        current_values = {
            "carcass": str(self.cb_selected_material_carcass.currentData() or ""),
            "front": str(self.cb_selected_material_front.currentData() or ""),
            "back": str(self.cb_selected_material_back.currentData() or ""),
        }
        materials = self._catalog.list_materials() or []

        def fill(cb: QComboBox, current_value: str) -> None:
            cb.blockSignals(True)
            cb.clear()
            for material in materials:
                cb.addItem(self._material_label(material), material.key)
            idx = cb.findData(current_value)
            if idx < 0 and current_value:
                cb.addItem(current_value, current_value)
                idx = cb.findData(current_value)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

        fill(self.cb_selected_material_carcass, current_values["carcass"])
        fill(self.cb_selected_material_front, current_values["front"])
        fill(self.cb_selected_material_back, current_values["back"])

    def _reload_bulk_module_material_choices(self) -> None:
        current_values = {
            "carcass": str(self.cb_bulk_material_carcass.currentData() or ""),
            "front": str(self.cb_bulk_material_front.currentData() or ""),
            "back": str(self.cb_bulk_material_back.currentData() or ""),
        }
        materials = self._catalog.list_materials() or []

        def fill(cb: QComboBox, current_value: str) -> None:
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("[bez zmiany]", "")
            for material in materials:
                cb.addItem(self._material_label(material), material.key)
            idx = cb.findData(current_value)
            if idx < 0 and current_value:
                cb.addItem(current_value, current_value)
                idx = cb.findData(current_value)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

        fill(self.cb_bulk_material_carcass, current_values["carcass"])
        fill(self.cb_bulk_material_front, current_values["front"])
        fill(self.cb_bulk_material_back, current_values["back"])

    def _set_material_combo_to_key(self, cb: QComboBox, material_key: str) -> None:
        normalized_key = str(material_key or "").strip()
        idx = cb.findData(normalized_key)
        cb.setCurrentIndex(idx if idx >= 0 else 0)

    def _apply_selected_quick_material_preset(self) -> None:
        preset_key = str(self.cb_quick_material_preset.currentData() or "").strip()
        if not preset_key:
            return

        profile = self._catalog.get_material_profile(preset_key)
        self._is_pushing_ui = True
        try:
            profile_idx = self.cb_profile.findData(profile.key)
            if profile_idx >= 0:
                self.cb_profile.setCurrentIndex(profile_idx)
            self._set_material_combo_to_key(
                self.cb_material_carcass,
                str(profile.material_map.get("carcass", profile.material_map.get("side", "")) or ""),
            )
            self._set_material_combo_to_key(self.cb_material_front, str(profile.material_map.get("front", "") or ""))
            self._set_material_combo_to_key(self.cb_material_back, str(profile.material_map.get("back", "") or ""))
        finally:
            self._is_pushing_ui = False

        self._refresh_quick_material_preset_hint()
        self._pull_ui_to_assembly()
        self._rebuild_assembly()

    def _clear_material_overrides(self) -> None:
        self._is_pushing_ui = True
        try:
            self.cb_material_carcass.setCurrentIndex(0)
            self.cb_material_front.setCurrentIndex(0)
            self.cb_material_back.setCurrentIndex(0)
        finally:
            self._is_pushing_ui = False

        self._pull_ui_to_assembly()
        self._rebuild_assembly()

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
            display_parts = [wall_name]
            if client and client != "-":
                display_parts.append(client)
            display_text = " - ".join(display_parts[:2])
            if order and order != "-":
                display_text = f"{display_text} ({order})"
            self.cb_wall.addItem(display_text, wall_name)
            item_index = self.cb_wall.count() - 1
            self.cb_wall.setItemData(
                item_index,
                f"Sciana: {wall_name}\nKlient: {client}\nZamowienie: {order}",
                Qt.ItemDataRole.ToolTipRole,
            )

        idx = self.cb_wall.findData(current_name)
        if idx < 0:
            idx = 0
        self.cb_wall.setCurrentIndex(idx)
        self.cb_wall.blockSignals(False)

    def _is_visual_attachment_entry(self, entry: dict | None) -> bool:
        if not isinstance(entry, dict):
            return False
        path = str(entry.get("path", "") or "").strip()
        if not path:
            return False
        kind = str(entry.get("kind", "") or "").strip().lower()
        suffix = Path(path).suffix.strip().lower()
        return kind in {"obraz", "referencja"} or suffix in _IMAGE_ATTACHMENT_EXTENSIONS

    def _attachment_target_matches(self, entry: dict | None, allowed_kinds: set[str], candidate_names: set[str]) -> bool:
        if not isinstance(entry, dict):
            return False
        raw_target_kind = str(entry.get("target_kind", "") or "").strip().lower()
        raw_target_name = str(entry.get("target_name", "") or "").strip().lower()
        if raw_target_kind in {"", "zamowienie"}:
            return True
        if raw_target_kind not in allowed_kinds:
            return False
        if not raw_target_name:
            return True
        return raw_target_name in candidate_names

    def _collect_project_references(self) -> list[dict[str, str]]:
        order_name = str(getattr(self._assembly, "order_name", "") or "").strip()
        if not order_name:
            return []
        order_def = self._order_store.get(order_name)
        if order_def is None:
            return []

        candidate_names = {
            str(name or "").strip().lower()
            for name in (
                getattr(self._assembly, "name", ""),
                getattr(self._assembly, "wall_name", ""),
            )
            if str(name or "").strip()
        }
        references: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        for attachment in list(getattr(order_def, "attachments", []) or []):
            if not self._is_visual_attachment_entry(attachment):
                continue
            if not self._attachment_target_matches(attachment, {"komplet", "sciana"}, candidate_names):
                continue
            path = str(attachment.get("path", "") or "").strip()
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            target_kind = str(attachment.get("target_kind", "") or "").strip()
            target_name = str(attachment.get("target_name", "") or "").strip()
            description = str(attachment.get("description", "") or "").strip()
            source_page = str(attachment.get("source_page", "") or "").strip()
            info_chunks = [chunk for chunk in (description, source_page) if chunk]
            references.append(
                {
                    "path": path,
                    "target": f"{target_kind} / {target_name}".strip(" /") or "Zamowienie",
                    "description": " | ".join(info_chunks) if info_chunks else target_kind or "Referencja",
                }
            )
        return references

    def _refresh_project_references(self) -> None:
        if not hasattr(self, "tbl_project_refs"):
            return
        selected_path = self._selected_project_reference_path()
        self._project_references = self._collect_project_references()
        self.tbl_project_refs.setRowCount(len(self._project_references))
        for row, entry in enumerate(self._project_references):
            path_item = QTableWidgetItem(Path(str(entry.get("path", "") or "")).name)
            path_item.setData(Qt.ItemDataRole.UserRole, str(entry.get("path", "") or ""))
            target_item = QTableWidgetItem(str(entry.get("target", "") or "-"))
            description_item = QTableWidgetItem(str(entry.get("description", "") or "-"))
            self.tbl_project_refs.setItem(row, 0, path_item)
            self.tbl_project_refs.setItem(row, 1, target_item)
            self.tbl_project_refs.setItem(row, 2, description_item)
        self.tbl_project_refs.resizeColumnsToContents()

        if self._project_references:
            target_row = 0
            if selected_path:
                for row in range(self.tbl_project_refs.rowCount()):
                    item = self.tbl_project_refs.item(row, 0)
                    if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == selected_path:
                        target_row = row
                        break
            self.tbl_project_refs.selectRow(target_row)
            self.block_project_refs.set_expanded(True)
        else:
            self.tbl_project_refs.clearSelection()
            self._project_reference_pixmap = QPixmap()
            self.lab_project_reference_info.setText("Brak referencji z projektu.")
            self.lab_project_reference_preview.setPixmap(QPixmap())
            self.lab_project_reference_preview.setText("Brak podgladu referencji.")

    def _selected_project_reference_path(self) -> str:
        rows = self.tbl_project_refs.selectionModel().selectedRows() if self.tbl_project_refs.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_project_refs.item(int(rows[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _update_project_reference_preview(self) -> None:
        if self._project_reference_pixmap.isNull():
            self.lab_project_reference_preview.setPixmap(QPixmap())
            return
        target_size = self.lab_project_reference_preview.size()
        scaled = self._project_reference_pixmap.scaled(
            max(40, target_size.width() - 12),
            max(40, target_size.height() - 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lab_project_reference_preview.setPixmap(scaled)

    def _on_project_reference_selection_changed(self) -> None:
        rows = self.tbl_project_refs.selectionModel().selectedRows() if self.tbl_project_refs.selectionModel() is not None else []
        if not rows:
            self._project_reference_pixmap = QPixmap()
            self.lab_project_reference_info.setText("Brak referencji z projektu.")
            self.lab_project_reference_preview.setPixmap(QPixmap())
            self.lab_project_reference_preview.setText("Brak podgladu referencji.")
            return
        row = int(rows[0].row())
        if row < 0 or row >= len(self._project_references):
            return
        entry = self._project_references[row]
        path = str(entry.get("path", "") or "").strip()
        target = str(entry.get("target", "") or "").strip()
        description = str(entry.get("description", "") or "").strip()
        info_parts = [chunk for chunk in (Path(path).name, target, description) if chunk]
        self.lab_project_reference_info.setText(" | ".join(info_parts))
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._project_reference_pixmap = QPixmap()
            self.lab_project_reference_preview.setPixmap(QPixmap())
            self.lab_project_reference_preview.setText("Nie udalo sie odczytac obrazu referencyjnego.")
            return
        self._project_reference_pixmap = pixmap
        self.lab_project_reference_preview.setText("")
        self._update_project_reference_preview()

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
        selected_front_variant = str(self.cb_saved_front_variant.currentData() or "all").strip().lower() if hasattr(self, "cb_saved_front_variant") else "all"
        selected_width_variant = str(self.cb_saved_width_variant.currentData() or "all").strip().lower() if hasattr(self, "cb_saved_width_variant") else "all"
        selected_business_group = str(self.cb_saved_business_group.currentData() or "all").strip().lower() if hasattr(self, "cb_saved_business_group") else "all"
        selected_preset_variant = str(self.cb_saved_preset_variant.currentData() or "all").strip().lower() if hasattr(self, "cb_saved_preset_variant") else "all"
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
                if not self._saved_module_matches_library_filter(
                    module,
                    name,
                    selected_quick_group,
                    selected_front_variant,
                    selected_width_variant,
                    selected_business_group,
                    selected_preset_variant,
                    search_text,
                ):
                    continue
                width_mm = float(getattr(module, "width_mm", 0.0) or 0.0)
                height_mm = float(getattr(module, "height_mm", 0.0) or 0.0)
                depth_mm = float(getattr(module, "depth_mm", 0.0) or 0.0)
                quick_label = _saved_module_quick_group_label(_saved_module_quick_group_key(module))
                front_label = _saved_module_front_variant_label(_saved_module_front_variant_key(module))
                width_label = _saved_module_width_variant_label(_saved_module_width_variant_key(module))
                business_label = _saved_module_business_group_label(_saved_module_business_group_key(module))
                preset_label = _saved_module_preset_variant_label(_saved_module_preset_variant_key(module))
                child = QTreeWidgetItem([f"{name} | {width_mm:.0f}x{height_mm:.0f}x{depth_mm:.0f} | {front_label}"])
                child.setData(0, Qt.ItemDataRole.UserRole, name)
                child.setData(0, SAVED_MODULE_NAME_ROLE, name)
                child.setData(0, SAVED_MODULE_WIDTH_ROLE, width_mm)
                child.setData(0, SAVED_MODULE_HEIGHT_ROLE, height_mm)
                child.setData(0, SAVED_MODULE_KIND_ROLE, str(getattr(module, "cabinet_kind", "lower") or "lower"))
                child.setToolTip(
                    0,
                    f"{business_label} | {preset_label} | {quick_label} | {front_label} | {width_label} | "
                    f"{width_mm:.0f} x {height_mm:.0f} x {depth_mm:.0f} mm",
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

    def _set_combo_to_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _apply_selected_saved_named_set(self) -> None:
        set_key = str(self.cb_saved_named_set.currentData() or "").strip()
        if not set_key:
            return

        values = dict(NAMED_LIBRARY_SET_VALUES.get(set_key, {}))
        for combo, value in (
            (self.cb_saved_quick_group, str(values.get("quick_group", "all") or "all")),
            (self.cb_saved_front_variant, str(values.get("front_variant", "all") or "all")),
            (self.cb_saved_width_variant, str(values.get("width_variant", "all") or "all")),
            (self.cb_saved_business_group, str(values.get("business_group", "all") or "all")),
            (self.cb_saved_preset_variant, str(values.get("preset_variant", "all") or "all")),
        ):
            combo.blockSignals(True)
            self._set_combo_to_data(combo, value)
            combo.blockSignals(False)

        self.ed_saved_search.blockSignals(True)
        self.ed_saved_search.setText(str(values.get("search", "") or ""))
        self.ed_saved_search.blockSignals(False)
        self._reload_saved_modules()

    def _saved_module_matches_library_filter(
        self,
        module: ModuleDef | None,
        module_name: str,
        quick_group: str,
        front_variant: str,
        width_variant: str,
        business_group: str,
        preset_variant: str,
        search_text: str,
    ) -> bool:
        quick_group = str(quick_group or "all").strip().lower() or "all"
        front_variant = str(front_variant or "all").strip().lower() or "all"
        width_variant = str(width_variant or "all").strip().lower() or "all"
        business_group = str(business_group or "all").strip().lower() or "all"
        preset_variant = str(preset_variant or "all").strip().lower() or "all"
        search_text = str(search_text or "").strip().lower()

        module_quick_group = _saved_module_quick_group_key(module)
        module_front_variant = _saved_module_front_variant_key(module)
        module_width_variant = _saved_module_width_variant_key(module)
        module_business_group = _saved_module_business_group_key(module)
        module_preset_variant = _saved_module_preset_variant_key(module)
        if quick_group != "all" and module_quick_group != quick_group:
            return False
        if front_variant != "all" and module_front_variant != front_variant:
            return False
        if width_variant != "all" and module_width_variant != width_variant:
            return False
        if business_group != "all" and module_business_group != business_group:
            return False
        if preset_variant != "all" and module_preset_variant != preset_variant:
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
                _saved_module_front_variant_label(module_front_variant),
                _saved_module_width_variant_label(module_width_variant),
                _saved_module_business_group_label(module_business_group),
                _saved_module_preset_variant_label(module_preset_variant),
                f"{float(getattr(module, 'width_mm', 0.0) or 0.0):.0f}",
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

    def _on_saved_module_item_double_clicked(self, item: QTreeWidgetItem | None, _column: int) -> None:
        source_name = str(item.data(0, SAVED_MODULE_NAME_ROLE) or "").strip() if item is not None else ""
        if not source_name:
            return
        self.tree_saved_modules.setCurrentItem(item)
        self._add_saved_module_by_name(source_name)

    def _shortcut_save_assembly(self) -> None:
        try:
            name = str(getattr(self._assembly, "name", "") or "").strip()
            existing = self._assembly_store.get(name) if name else None
            if existing is not None:
                self._on_overwrite()
            else:
                self._on_save_new()
        except Exception as exc:
            self._show_storage_operation_error("sprawdzic komplet przed zapisem", exc)

    def _shortcut_focus_saved_search(self) -> None:
        self.ed_saved_search.setFocus()
        self.ed_saved_search.selectAll()

    def _shortcut_settings_key(self) -> str:
        return "komplet_shortcuts_v2"

    def _default_shortcut_strings(self) -> list[str]:
        out: list[str] = []
        for action_key, (seq, _handler) in dict(getattr(self, "_shortcut_actions", {}) or {}).items():
            out.append(f"{action_key}={seq}")
        return out

    def _load_shortcut_map(self) -> dict[str, str]:
        raw = load_ui_string_list(self._shortcut_settings_key(), self._default_shortcut_strings())
        parsed: dict[str, str] = {}
        for row in raw:
            text = str(row or "").strip()
            if not text or "=" not in text:
                continue
            key, seq = text.split("=", 1)
            action = str(key or "").strip()
            value = str(seq or "").strip()
            if action:
                parsed[action] = value
        return parsed

    def _save_shortcut_map(self, mapping: dict[str, str]) -> None:
        rows: list[str] = []
        for action_key in dict(getattr(self, "_shortcut_actions", {}) or {}).keys():
            seq = str(mapping.get(action_key, "") or "").strip()
            if not seq:
                seq = str(self._shortcut_actions[action_key][0] or "").strip()
            rows.append(f"{action_key}={seq}")
        save_ui_string_list(self._shortcut_settings_key(), rows)

    def _setup_shortcuts_from_settings(self) -> None:
        if not hasattr(self, "_shortcut_actions"):
            return

        if hasattr(self, "_shortcuts_runtime"):
            for shortcut in list(getattr(self, "_shortcuts_runtime", []) or []):
                try:
                    shortcut.setParent(None)
                    shortcut.deleteLater()
                except Exception:
                    pass

        shortcut_map = self._load_shortcut_map()
        self._shortcuts_runtime = []

        for action_key, (default_seq, handler) in self._shortcut_actions.items():
            seq_text = str(shortcut_map.get(action_key, default_seq) or "").strip()
            if not seq_text:
                continue
            shortcut = QShortcut(QKeySequence(seq_text), self)
            shortcut.activated.connect(handler)
            self._shortcuts_runtime.append(shortcut)
            setattr(self, f"_shortcut_{action_key}", shortcut)

    def _open_shortcuts_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Konfiguracja skrotow - Komplet")
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        lay.addLayout(form)

        labels = {
            "save": "Zapisz",
            "overwrite": "Nadpisz",
            "load": "Wczytaj",
            "new": "Nowy",
            "focus_search": "Fokus szukaj",
            "duplicate": "Duplikuj",
            "toggle_snap": "Przelacz snap",
            "toggle_left": "Lewy panel",
        }

        current_map = self._load_shortcut_map()
        edits: dict[str, QLineEdit] = {}

        for action_key, (default_seq, _handler) in self._shortcut_actions.items():
            edit = QLineEdit(str(current_map.get(action_key, default_seq) or default_seq))
            edit.setPlaceholderText(default_seq)
            edits[action_key] = edit
            form.addRow(labels.get(action_key, action_key), edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_reset = btns.addButton("Domyslne", QDialogButtonBox.ButtonRole.ResetRole)
        btn_reset.clicked.connect(
            lambda: [
                edits[k].setText(str(self._shortcut_actions[k][0] or ""))
                for k in self._shortcut_actions.keys()
            ]
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_map: dict[str, str] = {}
        for action_key, edit in edits.items():
            value = str(edit.text() or "").strip()
            if not value:
                value = str(self._shortcut_actions[action_key][0] or "")
            new_map[action_key] = value

        self._save_shortcut_map(new_map)
        self._setup_shortcuts_from_settings()

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
            quick_idx = self.cb_quick_material_preset.findData(profile_key)
            self.cb_quick_material_preset.setCurrentIndex(quick_idx if quick_idx >= 0 else 0)
            hardware_overrides = dict(getattr(self._assembly, "hardware_vendor_overrides", {}) or {})
            hardware_vendor = str(hardware_overrides.get("hinge", "") or "").strip().lower()
            hardware_idx = self.cb_hardware_vendor_preset.findData(hardware_vendor)
            self.cb_hardware_vendor_preset.setCurrentIndex(hardware_idx if hardware_idx >= 0 else 0)
            decor_labels = dict(getattr(self._assembly, "decor_labels", {}) or {})
            self.ed_decor_carcass.setText(str(decor_labels.get("carcass", "") or ""))
            self.ed_decor_front.setText(str(decor_labels.get("front", "") or ""))
            decor_key = str(getattr(self._assembly, "decor_preset_key", "") or "").strip()
            if not decor_key:
                decor_key = self._matching_decor_preset_key(decor_labels)
            decor_idx = self.cb_quick_decor_preset.findData(decor_key)
            self.cb_quick_decor_preset.setCurrentIndex(decor_idx if decor_idx >= 0 else 0)
            company_key = str(getattr(self._assembly, "company_collection_key", "") or "").strip()
            if not company_key:
                company_key = self._matching_company_collection_key(profile_key, hardware_vendor, decor_key)
            company_idx = self.cb_company_collection.findData(company_key)
            self.cb_company_collection.setCurrentIndex(company_idx if company_idx >= 0 else 0)

            material_overrides = dict(getattr(self._assembly, "material_overrides", {}) or {})

            def set_material_combo(cb: QComboBox, group_key: str) -> None:
                value = str(material_overrides.get(group_key, "") or "").strip()
                idx_local = cb.findData(value)
                cb.setCurrentIndex(idx_local if idx_local >= 0 else 0)

            set_material_combo(self.cb_material_carcass, "carcass")
            set_material_combo(self.cb_material_front, "front")
            set_material_combo(self.cb_material_back, "back")
            self._refresh_quick_material_preset_hint()
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
        selected_hardware_vendor = str(self.cb_hardware_vendor_preset.currentData() or "").strip().lower()
        self._assembly.hardware_vendor_overrides = {}
        if selected_hardware_vendor:
            self._assembly.hardware_vendor_overrides = {
                "hinge": selected_hardware_vendor,
                "drawer_system": selected_hardware_vendor,
            }
        decor_labels = {
            "carcass": str(self.ed_decor_carcass.text().strip()),
            "front": str(self.ed_decor_front.text().strip()),
        }
        self._assembly.decor_labels = {key: value for key, value in decor_labels.items() if value}
        selected_decor_preset = str(self.cb_quick_decor_preset.currentData() or "").strip()
        if not selected_decor_preset or selected_decor_preset == "custom":
            selected_decor_preset = self._matching_decor_preset_key(self._assembly.decor_labels)
        self._assembly.decor_preset_key = selected_decor_preset
        selected_collection = str(self.cb_company_collection.currentData() or "").strip()
        if not selected_collection or not self._company_collection_matches(
            selected_collection,
            self._assembly.material_profile_key,
            selected_hardware_vendor,
            self._assembly.decor_preset_key,
        ):
            selected_collection = self._matching_company_collection_key(
                self._assembly.material_profile_key,
                selected_hardware_vendor,
                self._assembly.decor_preset_key,
            )
        self._assembly.company_collection_key = selected_collection

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

    def _show_storage_operation_error(self, action_label: str, exc: Exception) -> None:
        action = str(action_label or "wykonac operacje na komplecie").strip()
        message = f"Nie udalo sie {action}.\n\nSzczegoly: {exc}"
        self._set_store_status(message, ok=False)
        try:
            QMessageBox.critical(self, "Blad zapisu/odczytu", message)
        except Exception:
            pass

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
            "order_code": order_name,
            "order_name": order_name,
            "worker_name": worker_name,
            "order_status": order_status,
            "site_address": site_address,
        }

    def _on_save_new(self) -> None:
        try:
            name = self._ensure_name_for_save()
            assembly = self._assembly_snapshot_for_store()
            assembly.name = name
            result = self._assembly_store.save_new(assembly)
            self._set_store_status(result.message_pl, ok=result.ok)
        except Exception as exc:
            self._show_storage_operation_error("zapisac nowy komplet", exc)

    def _on_back_to_order(self) -> None:
        self.sig_open_order_requested.emit(self.current_order_context())

    def _on_overwrite(self) -> None:
        try:
            name = self._ensure_name_for_save()
            assembly = self._assembly_snapshot_for_store()
            assembly.name = name
            result = self._assembly_store.overwrite(assembly)
            self._set_store_status(result.message_pl, ok=result.ok)
        except Exception as exc:
            self._show_storage_operation_error("nadpisac komplet", exc)

    def _on_load(self) -> None:
        try:
            dlg = LoadAssemblyDialog(self, self._assembly_store)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return

            assembly = dlg.selected_assembly()
            if assembly is None:
                self._set_store_status("Nie udalo sie wczytac kompletu.", ok=False)
                return

            self._apply_loaded_assembly(assembly)
            self._set_store_status(f'Wczytano komplet: "{getattr(self._assembly, "name", "") or ""}".', ok=True)
        except Exception as exc:
            self._show_storage_operation_error("wczytac komplet", exc)

    def _apply_loaded_assembly(self, assembly: FurnitureAssemblyDef) -> None:
        self._assembly = FurnitureAssemblyDef.from_dict(assembly.to_dict())
        self._assembly.gap_mm = 0.0
        self._reload_saved_walls()
        self._reload_worker_choices(current_worker=str(getattr(self._assembly, "worker_name", "") or ""))
        self._push_assembly_to_ui()
        self._rebuild_assembly()

    def load_assembly_from_store_name(self, name: str) -> bool:
        try:
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
        except Exception as exc:
            self._set_store_status(f"Nie udalo sie wczytac kompletu: {exc}", ok=False)
            return False

    def start_new_assembly(self) -> None:
        self._assembly = FurnitureAssemblyDef(assembly_id=new_assembly_id())
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
        quote_item_name = str(payload.get("quote_item_name", "") or "").strip()
        quote_item_kind = str(payload.get("quote_item_kind", "") or "").strip()
        order_def = self._order_store.get(order_name) if order_name else None
        client_name = str(payload.get("client_name", "") or getattr(order_def, "client_name", "") or "").strip()
        worker_name = str(payload.get("worker_name", "") or getattr(order_def, "worker_name", "") or "").strip()
        self._assembly = FurnitureAssemblyDef(
            name=quote_item_name or "Komplet 1",
            wall_name=str(payload.get("wall_name", "") or "").strip(),
            client_name=client_name,
            order_name=order_name,
            worker_name=worker_name,
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

        if quote_item_name:
            kind_suffix = f" ({quote_item_kind})" if quote_item_kind else ""
            self._set_store_status(f'Gotowy nowy komplet dla pozycji "{quote_item_name}"{kind_suffix}.', ok=True)
        elif self._assembly.wall_name:
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

    def _current_material_defaults(self) -> dict[str, str]:
        overrides = dict(getattr(self._assembly, "material_overrides", {}) or {})
        return {
            "carcass": str(overrides.get("carcass", "") or "PB18").strip() or "PB18",
            "front": str(overrides.get("front", "") or "MDF19").strip() or "MDF19",
            "back": str(overrides.get("back", "") or "HDF2.5").strip() or "HDF2.5",
        }

    def _build_quick_preset_module(self, preset_key: str) -> ModuleDef | None:
        key = str(preset_key or "").strip().lower()
        if key not in {"front_only", "shelf_only", "wall_panel"}:
            return None

        assembly_height = max(100.0, float(getattr(self._assembly, "height_mm", 2500.0) or 2500.0))
        assembly_depth = max(100.0, float(getattr(self._assembly, "depth_mm", 560.0) or 560.0))
        materials = self._current_material_defaults()

        if key == "front_only":
            module = ModuleDef(
                module_id=new_module_id(),
                name="Front",
                width_mm=600.0,
                depth_mm=19.0,
                height_mm=min(assembly_height, 720.0),
                shelf_count=0,
                divider_count=0,
                visible_parts={"front"},
                materials=materials,
                module_family="kitchen_upper",
                cabinet_kind="upper",
            )
        elif key == "shelf_only":
            module = ModuleDef(
                module_id=new_module_id(),
                name="Polka",
                width_mm=600.0,
                depth_mm=assembly_depth,
                height_mm=18.0,
                shelf_count=1,
                divider_count=0,
                visible_parts={"shelf"},
                materials=materials,
                module_family="kitchen_lower",
                cabinet_kind="lower",
            )
        else:
            module = ModuleDef(
                module_id=new_module_id(),
                name="Panel scienny",
                width_mm=600.0,
                depth_mm=18.0,
                height_mm=assembly_height,
                shelf_count=0,
                divider_count=0,
                visible_parts={"back"},
                materials=materials,
                module_family="kitchen_lower",
                cabinet_kind="lower",
            )

        module.parts = build_module_parts(module, self._catalog)
        return module

    def _add_quick_preset_module(
        self,
        preset_key: str,
        insert_index: int | None = None,
        initial_offset_mm: float | None = None,
    ) -> bool:
        module = self._build_quick_preset_module(preset_key)
        if module is None:
            self._set_store_status("Nieznany preset szybkiego elementu.", ok=False)
            return False

        source_name = f"[preset] {module.name}"
        item = AssemblyModuleItemDef(
            source_name=source_name,
            instance_name=self._next_instance_name(module.name),
            offset_ref_mode="wall_left",
            offset_mm=0.0,
            wall_depth_offset_mm=0.0,
            module=module,
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
        max_left = max(0.0, wall_width - float(getattr(module, "width_mm", 0.0) or 0.0))
        initial_offset_mm = max(0.0, min(float(initial_offset_mm or 0.0), max_left))
        item.offset_mm = float(initial_offset_mm or 0.0)
        items.insert(target_index, item)
        self._rebuild_assembly(select_index=target_index)
        self._set_store_status(f'Dodano preset "{module.name}" do kompletu.', ok=True)
        return True

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
        if hasattr(cloned, "module_id"):
            cloned.module_id = new_module_id()
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
        # jesli brak explicit offset i nie ma poprzedniego, szukaj ostatniego modulu
        # tego samego cabinet_kind zeby nie nakladac modulow inna strefą
        if initial_offset_mm == 0.0 and target_index == len(items):
            new_kind = str(getattr(cloned, "cabinet_kind", "lower") or "lower").strip()
            rightmost = 0.0
            for resolved in self._resolved_items:
                kind = str(getattr(resolved.module, "cabinet_kind", "lower") or "lower").strip()
                if kind == new_kind:
                    rightmost = max(rightmost, float(resolved.x_mm) + float(resolved.width_mm))
            if rightmost > 0.0:
                initial_offset_mm = rightmost
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

    def _on_preview_module_selection_requested(self, index: int, preserve_selection: bool) -> None:
        if not (0 <= int(index) < self.tbl_items.rowCount()):
            return
        selection_model = self.tbl_items.selectionModel()
        if selection_model is None:
            return
        row_index = int(index)
        model_index = self.tbl_items.model().index(row_index, 0)
        if preserve_selection:
            selection_model.select(
                model_index,
                QItemSelectionModel.SelectionFlag.Toggle | QItemSelectionModel.SelectionFlag.Rows,
            )
        else:
            self.tbl_items.selectRow(row_index)
        self._refresh_preview_only()

    def _on_preview_module_selection_group_requested(self, indexes, preserve_selection: bool) -> None:
        selection_model = self.tbl_items.selectionModel()
        if selection_model is None:
            return

        valid_indexes = sorted(
            {
                int(index)
                for index in (indexes or [])
                if 0 <= int(index) < self.tbl_items.rowCount()
            }
        )
        current_indexes = set(self._selected_indexes())

        if preserve_selection:
            target_indexes = set(current_indexes)
            for index in valid_indexes:
                if index in target_indexes:
                    target_indexes.remove(index)
                else:
                    target_indexes.add(index)
        else:
            target_indexes = set(valid_indexes)

        selection_model.clearSelection()
        for row_index in sorted(target_indexes):
            model_index = self.tbl_items.model().index(int(row_index), 0)
            selection_model.select(
                model_index,
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
            )
        self._refresh_preview_only()

    def _on_preview_apply_height_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_height = float(getattr(self._assembly.items[source_index].module, "height_mm", 0.0) or 0.0)
        for index in targets:
            self._assembly.items[index].module.height_mm = source_height
        self._set_store_status(f"Przepisano wysokosc modulu do {len(targets)} zaznaczonych elementow.", ok=True)
        self._rebuild_assembly(select_indexes=targets)

    def _on_preview_apply_width_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_width = float(getattr(self._assembly.items[source_index].module, "width_mm", 0.0) or 0.0)
        for index in targets:
            self._assembly.items[index].module.width_mm = source_width
        self._set_store_status(f"Przepisano szerokosc modulu do {len(targets)} zaznaczonych elementow.", ok=True)
        self._rebuild_assembly(select_indexes=targets)

    def _on_preview_apply_depth_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_depth = float(getattr(self._assembly.items[source_index].module, "depth_mm", 0.0) or 0.0)
        for index in targets:
            self._assembly.items[index].module.depth_mm = source_depth
        self._set_store_status(f"Glebokosc modulu przepisano do {len(targets)} zaznaczonych elementow.", ok=True)
        self._rebuild_assembly(select_indexes=targets)

    def _on_preview_apply_front_material_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_materials = dict(getattr(self._assembly.items[source_index].module, "materials", {}) or {})
        source_front = str(source_materials.get("front", "") or "").strip()
        if not source_front:
            self._set_store_status("Wybrany modul nie ma ustawionego materialu frontu.", ok=False)
            return
        for index in targets:
            material_map = dict(getattr(self._assembly.items[index].module, "materials", {}) or {})
            material_map["front"] = source_front
            self._assembly.items[index].module.materials = material_map
        self._set_store_status(f'Przepisano material frontu "{source_front}" do {len(targets)} zaznaczonych elementow.', ok=True)
        self._rebuild_assembly(select_indexes=targets)

    def _on_preview_apply_carcass_material_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_materials = dict(getattr(self._assembly.items[source_index].module, "materials", {}) or {})
        source_carcass = str(source_materials.get("carcass", "") or "").strip()
        if not source_carcass:
            self._set_store_status("Wybrany modul nie ma ustawionego materialu korpusu.", ok=False)
            return
        for index in targets:
            material_map = dict(getattr(self._assembly.items[index].module, "materials", {}) or {})
            material_map["carcass"] = source_carcass
            self._assembly.items[index].module.materials = material_map
        self._set_store_status(f'Przepisano material korpusu "{source_carcass}" do {len(targets)} zaznaczonych elementow.', ok=True)
        self._rebuild_assembly(select_indexes=targets)

    def _on_preview_apply_back_material_to_selected(self, source_index: int) -> None:
        source_index = int(source_index)
        if source_index < 0 or source_index >= len(self._assembly.items):
            return
        targets = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not targets:
            targets = [source_index]
        source_materials = dict(getattr(self._assembly.items[source_index].module, "materials", {}) or {})
        source_back = str(source_materials.get("back", "") or "").strip()
        if not source_back:
            self._set_store_status("Wybrany modul nie ma ustawionego materialu plecow.", ok=False)
            return
        for index in targets:
            material_map = dict(getattr(self._assembly.items[index].module, "materials", {}) or {})
            material_map["back"] = source_back
            self._assembly.items[index].module.materials = material_map
        self._set_store_status(f'Przepisano material plecow "{source_back}" do {len(targets)} zaznaczonych elementow.', ok=True)
        self._rebuild_assembly(select_indexes=targets)

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
        snapped_offset = self._snap_mm(float(offset_mm or 0.0))
        self._assembly.items[index].offset_mm = max(min_offset, min(float(snapped_offset), max_offset))
        self._rebuild_assembly(select_index=index)

    def _on_preview_module_position_changed(self, index: int, offset_mm: float, y_mm: float) -> None:
        index = int(index)
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview._min_offset_for_module_index(index)
        max_offset = self.preview._max_offset_for_module_index(index)
        max_y = self.preview._max_y_for_index(index)
        snapped_offset = self._snap_mm(float(offset_mm or 0.0))
        snapped_y = self._snap_mm(float(y_mm or 0.0))
        self._assembly.items[index].offset_mm = max(min_offset, min(float(snapped_offset), max_offset))
        self._assembly.items[index].position_y_mm = max(0.0, min(float(snapped_y), max_y))
        self._rebuild_assembly(select_index=index)

    def _on_preview_top_position_changed(self, index: int, offset_mm: float, wall_offset_mm: float) -> None:
        index = int(index)
        if index < 0 or index >= len(self._assembly.items):
            return
        min_offset = self.preview_top._min_offset_for_module_index(index)
        max_offset = self.preview_top._max_offset_for_module_index(index)
        max_wall_offset = self.preview_top._max_wall_depth_offset_for_index(index)
        snapped_offset = self._snap_mm(float(offset_mm or 0.0))
        snapped_wall_offset = self._snap_mm(float(wall_offset_mm or 0.0))
        self._assembly.items[index].offset_mm = max(min_offset, min(float(snapped_offset), max_offset))
        self._assembly.items[index].wall_depth_offset_mm = max(0.0, min(float(snapped_wall_offset), max_wall_offset))
        self._rebuild_assembly(select_index=index)

    def _selected_index(self) -> int:
        rows = self._selected_indexes()
        if not rows:
            return -1
        return int(rows[0])

    def _selected_indexes(self) -> list[int]:
        rows = self.tbl_items.selectionModel().selectedRows() if self.tbl_items.selectionModel() is not None else []
        return sorted({int(row.row()) for row in rows})

    def _on_items_selection_changed(self) -> None:
        self._refresh_preview_only()
        self._sync_selected_offset_editor()
        self._sync_bulk_module_editor()

    def _sync_selected_offset_editor(self) -> None:
        selected_indexes = self._selected_indexes()
        single_selected = len(selected_indexes) == 1
        index = int(selected_indexes[0]) if single_selected else -1
        enabled = single_selected and 0 <= index < len(self._assembly.items)
        self.lab_selected_module_meta.setEnabled(enabled)
        self.cb_selected_x_ref.setEnabled(enabled)
        self.lab_offset_ref.setEnabled(enabled)
        self.cb_selected_y_ref.setEnabled(enabled and not self._is_top_view_active())
        self.sp_selected_offset.setEnabled(enabled)
        self.sp_selected_y.setEnabled(enabled)
        self.sp_selected_width.setEnabled(enabled)
        self.sp_selected_height.setEnabled(enabled)
        self.sp_selected_depth.setEnabled(enabled)
        self.cb_selected_material_carcass.setEnabled(enabled)
        self.cb_selected_material_front.setEnabled(enabled)
        self.cb_selected_material_back.setEnabled(enabled)

        self._is_syncing_offset_ui = True
        try:
            if not enabled:
                if len(selected_indexes) > 1:
                    self.lab_selected_module_meta.setText(
                        f"Zaznaczono {len(selected_indexes)} modulow. Uzyj bloku 'Zaznaczone moduly', aby zmienic je grupowo."
                    )
                else:
                    self.lab_selected_module_meta.setText("Wybierz modul z listy albo kliknij go w podgladzie.")
                self.cb_selected_x_ref.setCurrentIndex(0)
                self.lab_offset_ref.setText("-")
                self.cb_selected_y_ref.setCurrentIndex(0)
                self.sp_selected_offset.setRange(0.0, 0.0)
                self.sp_selected_offset.setValue(0.0)
                self.sp_selected_y.setRange(0.0, 0.0)
                self.sp_selected_y.setValue(0.0)
                self.sp_selected_width.setRange(0.0, 0.0)
                self.sp_selected_width.setValue(0.0)
                self.sp_selected_height.setRange(0.0, 0.0)
                self.sp_selected_height.setValue(0.0)
                self.sp_selected_depth.setRange(0.0, 0.0)
                self.sp_selected_depth.setValue(0.0)
                self._refresh_selected_offset_label()
                self._refresh_selected_y_label()
                return

            current_item = self._assembly.items[index]
            effective_mode = self._effective_horizontal_reference_mode_for_index(index)
            current_item.offset_ref_mode = effective_mode
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

            module_def = current_item.module
            self.sp_selected_width.setRange(100.0, 3000.0)
            self.sp_selected_width.setValue(float(getattr(module_def, "width_mm", 0.0) or 0.0))
            self.sp_selected_height.setRange(100.0, 5000.0)
            self.sp_selected_height.setValue(float(getattr(module_def, "height_mm", 0.0) or 0.0))
            self.sp_selected_depth.setRange(50.0, 2000.0)
            self.sp_selected_depth.setValue(float(getattr(module_def, "depth_mm", 0.0) or 0.0))

            material_map = dict(getattr(module_def, "materials", {}) or {})

            def set_selected_material(cb: QComboBox, group_key: str) -> None:
                value = str(material_map.get(group_key, "") or "").strip()
                idx_local = cb.findData(value)
                cb.setCurrentIndex(idx_local if idx_local >= 0 else 0)

            set_selected_material(self.cb_selected_material_carcass, "carcass")
            set_selected_material(self.cb_selected_material_front, "front")
            set_selected_material(self.cb_selected_material_back, "back")

            min_offset = self.preview._min_offset_for_module_index(index)
            max_offset = self.preview._max_offset_for_module_index(index)
            offset_mm = float(getattr(current_item, "offset_mm", 0.0) or 0.0)
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

    def _sync_bulk_module_editor(self) -> None:
        if not hasattr(self, "btn_apply_bulk_modules"):
            return
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        enabled = bool(selected_indexes)
        self.lab_bulk_modules_meta.setEnabled(enabled)
        self.sp_bulk_height.setEnabled(enabled)
        self.cb_bulk_material_carcass.setEnabled(enabled)
        self.cb_bulk_material_front.setEnabled(enabled)
        self.cb_bulk_material_back.setEnabled(enabled)
        self.btn_apply_bulk_modules.setEnabled(enabled)
        self.block_bulk_modules.set_expanded(enabled and len(selected_indexes) > 1)

        if not enabled:
            self.lab_bulk_modules_meta.setText("Zaznacz kilka modulow z listy, aby zmienic je grupowo.")
            self.sp_bulk_height.blockSignals(True)
            self.sp_bulk_height.setValue(0.0)
            self.sp_bulk_height.blockSignals(False)
            for cb in (
                self.cb_bulk_material_carcass,
                self.cb_bulk_material_front,
                self.cb_bulk_material_back,
            ):
                cb.blockSignals(True)
                cb.setCurrentIndex(0)
                cb.blockSignals(False)
            return

        if len(selected_indexes) == 1:
            self.lab_bulk_modules_meta.setText("Zaznacz wiecej modulow, aby zastosowac te same zmiany grupowo.")
        else:
            self.lab_bulk_modules_meta.setText(
                f"Zaznaczono {len(selected_indexes)} modulow. Ustaw tylko te pola, ktore chcesz nadpisac dla calej grupy."
            )

    def _apply_bulk_changes_to_selected(self) -> None:
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not selected_indexes:
            return

        apply_height = float(self.sp_bulk_height.value()) > 0.0
        carcass_key = str(self.cb_bulk_material_carcass.currentData() or "").strip()
        front_key = str(self.cb_bulk_material_front.currentData() or "").strip()
        back_key = str(self.cb_bulk_material_back.currentData() or "").strip()

        for index in selected_indexes:
            module = self._assembly.items[index].module
            if apply_height:
                module.height_mm = float(self.sp_bulk_height.value())
            material_map = dict(getattr(module, "materials", {}) or {})
            if carcass_key:
                material_map["carcass"] = carcass_key
            if front_key:
                material_map["front"] = front_key
            if back_key:
                material_map["back"] = back_key
            module.materials = material_map

        self._rebuild_assembly(select_indexes=selected_indexes)

    def _on_bulk_materials_changed_auto(self, _index: int) -> None:
        if self._is_syncing_bulk_ui:
            return
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if len(selected_indexes) < 2:
            return

        carcass_key = str(self.cb_bulk_material_carcass.currentData() or "").strip()
        front_key = str(self.cb_bulk_material_front.currentData() or "").strip()
        back_key = str(self.cb_bulk_material_back.currentData() or "").strip()
        if not (carcass_key or front_key or back_key):
            return

        for index in selected_indexes:
            module = self._assembly.items[index].module
            material_map = dict(getattr(module, "materials", {}) or {})
            if carcass_key:
                material_map["carcass"] = carcass_key
            if front_key:
                material_map["front"] = front_key
            if back_key:
                material_map["back"] = back_key
            module.materials = material_map

        self._set_store_status(
            f"Zmieniono materialy dla {len(selected_indexes)} zaznaczonych modulow.",
            ok=True,
        )
        self._rebuild_assembly(select_indexes=selected_indexes)

    def _on_bulk_height_changed_auto(self, value: float) -> None:
        if self._is_syncing_bulk_ui:
            return
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        height_value = float(value or 0.0)
        if len(selected_indexes) < 2 or height_value <= 0.0:
            return

        for index in selected_indexes:
            self._assembly.items[index].module.height_mm = height_value

        self._set_store_status(
            f"Zmieniono wysokosc dla {len(selected_indexes)} zaznaczonych modulow.",
            ok=True,
        )
        self._rebuild_assembly(select_indexes=selected_indexes)

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
        snapped_value = self._snap_mm(float(value or 0.0))
        self._assembly.items[index].offset_mm = max(min_offset, min(float(snapped_value), max_offset))
        self._rebuild_assembly(select_index=index)

    def _on_selected_y_changed(self, value: float) -> None:
        if self._is_syncing_offset_ui:
            return
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        if self._is_top_view_active():
            max_wall_offset = self.preview_top._max_wall_depth_offset_for_index(index)
            snapped_value = self._snap_mm(float(value or 0.0))
            self._assembly.items[index].wall_depth_offset_mm = max(0.0, min(float(snapped_value), max_wall_offset))
        else:
            converted = self._y_from_vertical_offset_ui_value(index, float(value or 0.0))
            self._assembly.items[index].position_y_mm = self._snap_mm(float(converted))
        self._rebuild_assembly(select_index=index)

    def _on_selected_dimensions_changed(self, _value: float) -> None:
        if self._is_syncing_offset_ui:
            return
        index = self._selected_index()
        if index < 0 or index >= len(self._assembly.items):
            return
        old_resolved = list(self._resolved_items or [])
        module = self._assembly.items[index].module
        old_width = (
            float(getattr(old_resolved[index], "width_mm", 0.0) or 0.0)
            if index < len(old_resolved)
            else float(getattr(module, "width_mm", 0.0) or 0.0)
        )
        new_width = float(self.sp_selected_width.value())
        delta_width = float(new_width - old_width)
        module.width_mm = new_width
        module.height_mm = float(self.sp_selected_height.value())
        module.depth_mm = float(self.sp_selected_depth.value())
        self._shift_touching_wall_left_modules_after_width_change(index, old_resolved, delta_width)
        self._rebuild_assembly(select_index=index)

    def _shift_touching_wall_left_modules_after_width_change(
        self,
        index: int,
        old_resolved: list[ResolvedAssemblyItem],
        delta_width_mm: float,
    ) -> None:
        if abs(float(delta_width_mm or 0.0)) < 0.01:
            return
        if index < 0 or index + 1 >= len(self._assembly.items):
            return
        if len(old_resolved) < len(self._assembly.items):
            return

        tolerance_mm = 0.2
        for next_index in range(index + 1, len(self._assembly.items)):
            item = self._assembly.items[next_index]
            if (
                normalize_assembly_offset_ref_mode(getattr(item, "offset_ref_mode", "wall_left"))
                != "wall_left"
            ):
                break

            previous_old = old_resolved[next_index - 1]
            current_old = old_resolved[next_index]
            expected_left = float(previous_old.x_mm) + float(previous_old.width_mm)
            current_left = float(current_old.x_mm)
            if abs(current_left - expected_left) > tolerance_mm:
                break

            item.offset_mm = float(getattr(item, "offset_mm", 0.0) or 0.0) + float(delta_width_mm)

    def _on_selected_module_materials_changed(self, _index: int) -> None:
        if self._is_syncing_offset_ui:
            return
        selected_index = self._selected_index()
        if selected_index < 0 or selected_index >= len(self._assembly.items):
            return
        module = self._assembly.items[selected_index].module
        material_map = dict(getattr(module, "materials", {}) or {})
        material_map["carcass"] = str(self.cb_selected_material_carcass.currentData() or material_map.get("carcass", "") or "")
        material_map["front"] = str(self.cb_selected_material_front.currentData() or material_map.get("front", "") or "")
        material_map["back"] = str(self.cb_selected_material_back.currentData() or material_map.get("back", "") or "")
        module.materials = material_map
        self._rebuild_assembly(select_index=selected_index)

    def _on_remove_selected_item(self) -> None:
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if not selected_indexes:
            return
        for index in sorted(selected_indexes, reverse=True):
            self._assembly.items.pop(index)
        next_index = min(selected_indexes[0], len(self._assembly.items) - 1)
        self._rebuild_assembly(select_index=next_index)

    def _on_duplicate_selected_item(self) -> None:
        self._on_duplicate_selected_item_direction("right")

    def _normalized_duplicate_direction(self, direction: str) -> str:
        direction_key = str(direction or "right").strip().lower()
        if direction_key not in {"right", "left", "down", "up"}:
            return "right"
        return direction_key

    def _selected_indexes_for_duplicate(self) -> list[int]:
        selected_indexes = self._selected_indexes()
        return [index for index in sorted({int(i) for i in selected_indexes}) if 0 <= index < len(self._assembly.items)]

    def _build_duplicate_layout(self, direction: str) -> tuple[list[dict[str, object]], str]:
        direction_key = self._normalized_duplicate_direction(direction)
        valid_indexes = self._selected_indexes_for_duplicate()
        if not valid_indexes:
            return [], direction_key

        gap_mm = max(0.0, float(getattr(self._assembly, "gap_mm", 0.0) or 0.0))
        resolved_lookup = {index: self._resolved_items[index] for index in valid_indexes if 0 <= index < len(self._resolved_items)}

        min_x = None
        max_right = None
        min_y = None
        max_bottom = None
        for index in valid_indexes:
            resolved = resolved_lookup.get(index)
            source_item = self._assembly.items[index]
            x_mm = float(getattr(resolved, "x_mm", getattr(source_item, "offset_mm", 0.0)) or 0.0)
            y_mm = float(getattr(resolved, "y_mm", getattr(source_item, "position_y_mm", 0.0) or 0.0) or 0.0)
            width_mm = float(getattr(resolved, "width_mm", getattr(source_item.module, "width_mm", 0.0)) or 0.0)
            height_mm = float(getattr(resolved, "height_mm", getattr(source_item.module, "height_mm", 0.0)) or 0.0)
            min_x = x_mm if min_x is None else min(min_x, x_mm)
            max_right = (x_mm + width_mm) if max_right is None else max(max_right, x_mm + width_mm)
            min_y = y_mm if min_y is None else min(min_y, y_mm)
            max_bottom = (y_mm + height_mm) if max_bottom is None else max(max_bottom, y_mm + height_mm)

        block_width = max(0.0, float((max_right or 0.0) - (min_x or 0.0)))
        block_height = max(0.0, float((max_bottom or 0.0) - (min_y or 0.0)))
        dx = 0.0
        dy = 0.0
        if direction_key == "right":
            dx = block_width + gap_mm
        elif direction_key == "left":
            dx = -(block_width + gap_mm)
        elif direction_key == "down":
            dy = block_height + gap_mm
        elif direction_key == "up":
            dy = -(block_height + gap_mm)

        wall_width = max(0.0, float(getattr(self._assembly, "width_mm", 0.0) or 0.0))
        wall_height = max(0.0, float(getattr(self._assembly, "height_mm", 0.0) or 0.0))

        layout: list[dict[str, object]] = []
        for index in valid_indexes:
            source_item = self._assembly.items[index]
            source_module = source_item.module
            source_resolved = resolved_lookup.get(index)
            source_x = float(getattr(source_resolved, "x_mm", getattr(source_item, "offset_mm", 0.0)) or 0.0)
            source_y = float(getattr(source_resolved, "y_mm", getattr(source_item, "position_y_mm", 0.0) or 0.0) or 0.0)
            width_mm = float(getattr(source_resolved, "width_mm", getattr(source_module, "width_mm", 0.0)) or 0.0)
            height_mm = float(getattr(source_resolved, "height_mm", getattr(source_module, "height_mm", 0.0)) or 0.0)

            duplicate_x = source_x + dx
            duplicate_y = source_y + dy
            max_left = max(0.0, wall_width - width_mm)
            max_top = max(0.0, wall_height - height_mm)
            duplicate_x = max(0.0, min(float(duplicate_x), max_left))
            duplicate_y = max(0.0, min(float(duplicate_y), max_top))

            layout.append(
                {
                    "index": index,
                    "source_item": source_item,
                    "source_name": str(getattr(source_item, "source_name", "") or getattr(source_module, "name", "") or "Modul"),
                    "duplicate_x": duplicate_x,
                    "duplicate_y": duplicate_y,
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                }
            )
        return layout, direction_key

    def _show_duplicate_direction_preview(self, direction: str) -> None:
        layout, direction_key = self._build_duplicate_layout(direction)
        if not layout:
            return

        min_x = min(float(item["duplicate_x"]) for item in layout)
        max_right = max(float(item["duplicate_x"]) + float(item["width_mm"]) for item in layout)
        min_y = min(float(item["duplicate_y"]) for item in layout)
        max_bottom = max(float(item["duplicate_y"]) + float(item["height_mm"]) for item in layout)

        direction_labels = {
            "right": "Podglad: w prawo",
            "left": "Podglad: w lewo",
            "down": "Podglad: w dol",
            "up": "Podglad: w gore",
        }
        label = direction_labels.get(direction_key, "Podglad: w prawo")

        if self._is_top_view_active():
            top_h = float(self.preview_top._top_view_height())
            top_y = float(self.preview_top._top_view_base_y())
            top_rect = QRectF(float(min_x), top_y, float(max_right - min_x), top_h)
            self.preview_top._update_drag_preview(float(min_x), ghost_rect=top_rect, ghost_label=label)
            self.preview._update_drag_preview(None)
        else:
            front_rect = QRectF(float(min_x), float(min_y), float(max_right - min_x), float(max_bottom - min_y))
            self.preview._update_drag_preview(float(min_x), ghost_rect=front_rect, ghost_label=label)
            self.preview_top._update_drag_preview(None)

    def _on_duplicate_selected_item_repeat(self, multiplier: int) -> None:
        copies = max(0, int(multiplier) - 1)
        if copies <= 0:
            return
        for _ in range(copies):
            self._on_duplicate_selected_item_direction("right")

    def _on_align_selected_requested(self, anchor: str) -> None:
        anchor_key = str(anchor or "").strip().lower()
        if anchor_key in {"left", "right"}:
            self._on_align_selected_horizontal(anchor_key)
            return
        self._on_align_selected_vertical(anchor_key or "top")

    def _on_align_selected_horizontal(self, anchor: str) -> None:
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if len(selected_indexes) < 2:
            return

        resolved_items = {
            index: self._resolved_items[index]
            for index in selected_indexes
            if 0 <= index < len(self._resolved_items)
        }
        if len(resolved_items) < 2:
            return

        anchor_key = str(anchor or "left").strip().lower()
        if anchor_key == "right":
            target_right = max(
                float(getattr(resolved_items[index], "x_mm", 0.0) or 0.0)
                + float(getattr(resolved_items[index], "width_mm", 0.0) or 0.0)
                for index in selected_indexes
                if index in resolved_items
            )
            for index in selected_indexes:
                resolved = resolved_items.get(index)
                if resolved is None:
                    continue
                width_mm = float(getattr(resolved, "width_mm", 0.0) or 0.0)
                target_x = target_right - width_mm
                min_offset = self.preview._min_offset_for_module_index(index)
                max_offset = self.preview._max_offset_for_module_index(index)
                base_x = self.preview._base_x_for_module_index(index)
                target_offset = self._snap_mm(target_x - base_x)
                self._assembly.items[index].offset_ref_mode = "wall_left"
                self._assembly.items[index].offset_mm = max(min_offset, min(float(target_offset), max_offset))
            self._set_store_status(f"Wyrownano {len(selected_indexes)} modulow do prawej.", ok=True)
        else:
            target_left = min(
                float(getattr(resolved_items[index], "x_mm", 0.0) or 0.0)
                for index in selected_indexes
                if index in resolved_items
            )
            for index in selected_indexes:
                min_offset = self.preview._min_offset_for_module_index(index)
                max_offset = self.preview._max_offset_for_module_index(index)
                base_x = self.preview._base_x_for_module_index(index)
                target_offset = self._snap_mm(target_left - base_x)
                self._assembly.items[index].offset_ref_mode = "wall_left"
                self._assembly.items[index].offset_mm = max(min_offset, min(float(target_offset), max_offset))
            self._set_store_status(f"Wyrownano {len(selected_indexes)} modulow do lewej.", ok=True)

        self._rebuild_assembly(select_indexes=selected_indexes)

    def _on_align_selected_vertical(self, anchor: str) -> None:
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if len(selected_indexes) < 2:
            return

        resolved_items = {
            index: self._resolved_items[index]
            for index in selected_indexes
            if 0 <= index < len(self._resolved_items)
        }
        if len(resolved_items) < 2:
            return

        anchor_key = str(anchor or "top").strip().lower()
        if anchor_key == "bottom":
            target_bottom = max(
                float(getattr(resolved_items[index], "y_mm", 0.0) or 0.0)
                + float(getattr(resolved_items[index], "height_mm", 0.0) or 0.0)
                for index in selected_indexes
                if index in resolved_items
            )
            for index in selected_indexes:
                resolved = resolved_items.get(index)
                if resolved is None:
                    continue
                module_height = float(getattr(resolved, "height_mm", 0.0) or 0.0)
                target_y = self._snap_mm(max(0.0, target_bottom - module_height))
                max_y = self.preview._max_y_for_index(index)
                self._assembly.items[index].position_y_mm = max(0.0, min(float(target_y), float(max_y)))
            self._set_store_status(f"Wyrownano {len(selected_indexes)} modulow do dolu.", ok=True)
        else:
            target_top = min(
                float(getattr(resolved_items[index], "y_mm", 0.0) or 0.0)
                for index in selected_indexes
                if index in resolved_items
            )
            for index in selected_indexes:
                max_y = self.preview._max_y_for_index(index)
                snapped_y = self._snap_mm(target_top)
                self._assembly.items[index].position_y_mm = max(0.0, min(float(snapped_y), float(max_y)))
            self._set_store_status(f"Wyrownano {len(selected_indexes)} modulow do gory.", ok=True)

        self._rebuild_assembly(select_indexes=selected_indexes)

    def _on_distribute_selected_horizontally(self) -> None:
        selected_indexes = [index for index in self._selected_indexes() if 0 <= index < len(self._assembly.items)]
        if len(selected_indexes) < 3:
            return

        sortable: list[tuple[int, float]] = []
        for index in selected_indexes:
            x_mm = float(
                getattr(self._resolved_items[index], "x_mm", self._assembly.items[index].offset_mm)
                if 0 <= index < len(self._resolved_items)
                else self._assembly.items[index].offset_mm
            )
            sortable.append((index, x_mm))
        sortable.sort(key=lambda pair: pair[1])

        left_x = float(sortable[0][1])
        right_x = float(sortable[-1][1])
        if len(sortable) <= 1 or right_x <= left_x:
            return
        step = (right_x - left_x) / float(len(sortable) - 1)

        for pos, (index, _x) in enumerate(sortable):
            target_x = self._snap_mm(left_x + step * float(pos))
            self._assembly.items[index].offset_ref_mode = "wall_left"
            min_offset = self.preview._min_offset_for_module_index(index)
            max_offset = self.preview._max_offset_for_module_index(index)
            base_x = self.preview._base_x_for_module_index(index)
            target_offset = max(min_offset, min(float(target_x - base_x), max_offset))
            self._assembly.items[index].offset_mm = target_offset

        self._set_store_status(f"Rownomiernie rozstawiono {len(sortable)} modulow.", ok=True)
        self._rebuild_assembly(select_indexes=[index for index, _x in sortable])

    def _on_duplicate_selected_item_direction(self, direction: str) -> None:
        layout, direction_key = self._build_duplicate_layout(direction)
        if not layout:
            return

        insert_at = int(layout[-1]["index"]) + 1
        inserted_indexes: list[int] = []
        source_items: list[AssemblyModuleItemDef] = []
        for entry in layout:
            source_item = entry["source_item"]
            assert isinstance(source_item, AssemblyModuleItemDef)
            source_items.append(source_item)
            source_module = source_item.module
            cloned_module = ModuleDef.from_dict(source_module.to_dict()) if hasattr(source_module, "to_dict") else ModuleDef()
            if hasattr(cloned_module, "module_id"):
                cloned_module.module_id = new_module_id()
            if not getattr(cloned_module, "parts", None):
                cloned_module.parts = build_module_parts(cloned_module, self._catalog)
            source_name = str(entry["source_name"])
            duplicate_offset = float(entry["duplicate_x"])
            duplicate_y = float(entry["duplicate_y"])

            duplicate_item = AssemblyModuleItemDef(
                source_name=source_name,
                instance_name=self._next_instance_name(source_name),
                offset_ref_mode="wall_left",
                offset_mm=duplicate_offset,
                position_y_mm=duplicate_y,
                wall_depth_offset_mm=float(getattr(source_item, "wall_depth_offset_mm", 0.0) or 0.0),
                module=cloned_module,
            )
            self._assembly.items.insert(insert_at, duplicate_item)
            inserted_indexes.append(insert_at)
            insert_at += 1

        direction_labels = {
            "right": "w prawo",
            "left": "w lewo",
            "down": "w dol",
            "up": "w gore",
        }
        direction_label = direction_labels.get(direction_key, "w prawo")
        if len(source_items) == 1:
            self._set_store_status(f'Duplikowano modul "{source_items[0].display_name()}" ({direction_label}).', ok=True)
        else:
            self._set_store_status(f"Duplikowano {len(source_items)} zaznaczone moduly ({direction_label}).", ok=True)
        self._rebuild_assembly(select_indexes=inserted_indexes)

    def _move_selected_item(self, direction: int) -> None:
        selected_indexes = self._selected_indexes()
        if len(selected_indexes) != 1:
            return
        index = int(selected_indexes[0])
        if index < 0 or index >= len(self._assembly.items):
            return
        new_index = index + int(direction)
        if new_index < 0 or new_index >= len(self._assembly.items):
            return
        items = self._assembly.items
        items[index], items[new_index] = items[new_index], items[index]
        self._rebuild_assembly(select_index=new_index)

    def _rebuild_assembly(self, select_index: int | None = None, select_indexes: list[int] | None = None) -> None:
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
        if select_indexes is None:
            if select_index is not None:
                select_indexes = [int(select_index)]
            else:
                select_indexes = self._selected_indexes()
        self._refresh_items_table(select_index=select_index, selected_indexes=select_indexes)
        self._refresh_project_references()
        self._refresh_summary()
        self._refresh_preview_only()

    def _refresh_items_table(self, select_index: int | None = None, selected_indexes: list[int] | None = None) -> None:
        self.tbl_items.blockSignals(True)
        try:
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

            if selected_indexes is None:
                if select_index is None:
                    selected_indexes = self._selected_indexes()
                else:
                    selected_indexes = [int(select_index)]

            valid_indexes = [index for index in selected_indexes if 0 <= int(index) < self.tbl_items.rowCount()]
            selection_model = self.tbl_items.selectionModel()
            if selection_model is not None:
                selection_model.clearSelection()
                for index in valid_indexes:
                    model_index = self.tbl_items.model().index(int(index), 0)
                    selection_model.select(
                        model_index,
                        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                    )
            if not valid_indexes and self.tbl_items.rowCount() > 0:
                self.tbl_items.selectRow(0)
        finally:
            self.tbl_items.blockSignals(False)

        selected_count = len(self._selected_indexes())
        has_selection = self.tbl_items.rowCount() > 0 and selected_count > 0
        self.btn_remove.setEnabled(has_selection)
        self.btn_move_up.setEnabled(selected_count == 1)
        self.btn_move_down.setEnabled(selected_count == 1)
        self.btn_duplicate.setEnabled(has_selection)
        self.btn_align_left.setEnabled(selected_count >= 2)
        self.btn_align_right.setEnabled(selected_count >= 2)
        self.btn_align_top.setEnabled(selected_count >= 2)
        self.btn_align_bottom.setEnabled(selected_count >= 2)
        self.btn_distribute.setEnabled(selected_count >= 3)
        self._sync_selected_offset_editor()
        self._sync_bulk_module_editor()

    def _refresh_preview_only(self) -> None:
        vertical_mode = self._selected_vertical_reference_mode()
        self.preview.set_vertical_reference_mode(vertical_mode)
        self.preview_top.set_vertical_reference_mode(vertical_mode)
        self.preview.render_assembly(
            self._assembly,
            self._resolved_items,
            selected_index=self._selected_index(),
            selected_indexes=self._selected_indexes(),
        )
        self.preview_top.render_assembly(
            self._assembly,
            self._resolved_items,
            selected_index=self._selected_index(),
            selected_indexes=self._selected_indexes(),
        )
        self._refresh_preview_info_bar()
        self._update_project_reference_preview()

    def _selected_order_details(self) -> tuple[str, str]:
        order_name = str(getattr(self._assembly, "order_name", "") or "").strip()
        if not order_name:
            return str(self._order_status_context or "").strip(), str(self._site_address_context or "").strip()
        order_def = self._order_store.get(order_name)
        if order_def is None:
            return str(self._order_status_context or "").strip(), str(self._site_address_context or "").strip()
        status = str(self._order_status_context or getattr(order_def, "status", "") or "").strip()
        site_address = str(self._site_address_context or getattr(order_def, "site_address", "") or "").strip()
        return status, site_address

    def _refresh_trade_calc(self) -> None:
        """Szybka kalkulacja handlowa w panelu podsumowania kompletu."""
        if not hasattr(self, "sp_trade_labor"):
            return
        material_total = sum(
            item.cost_breakdown.grand_total_pln
            for item in self._resolved_items
        ) if self._resolved_items else 0.0
        labor = float(self.sp_trade_labor.value())
        transport = float(self.sp_trade_transport.value())
        montage = float(self.sp_trade_montage.value())
        margin = float(self.sp_trade_margin.value())
        base = material_total + labor + transport + montage
        netto = base * (1.0 + margin / 100.0)
        brutto = netto * 1.23
        profit = netto - base
        self.lab_trade_netto.setText(f"{netto:,.2f} zl")
        self.lab_trade_brutto.setText(f"{brutto:,.2f} zl")
        self.lab_trade_profit.setText(f"{profit:,.2f} zl")
        color = "#15803d" if profit >= 0 else "#b91c1c"
        self.lab_trade_profit.setStyleSheet(f"font-weight:600; color:{color};")

    def _on_open_in_wycena(self) -> None:
        """Emituje sygnał żeby MainWindow otworzył ten komplet w karcie Wycena."""
        name = str(getattr(self._assembly, "name", "") or "").strip()
        if not name:
            return
        self.sig_open_wycena_requested.emit(name)

    def _on_send_to_shopping_list(self) -> None:
        """Agreguje materialy ze wszystkich modulow kompletu i wrzuca do listy zakupow."""
        if not self._resolved_items:
            self._set_store_status("Brak modulow w komplecie.", ok=False)
            return

        assembly_name = str(getattr(self._assembly, "name", "") or "Komplet")
        order_id = str(getattr(self._assembly, "order_id", "") or "")

        mat_agg: dict[str, list] = {}  # key -> [area_m2, label]
        edge_agg: dict[str, float] = {}  # key -> length_m
        hw_agg: dict[str, list] = {}  # key -> [count, label]

        for item in self._resolved_items:
            bd = item.cost_breakdown
            for line in bd.material_lines:
                if line.key not in mat_agg:
                    mat_agg[line.key] = [0.0, line.label]
                mat_agg[line.key][0] += float(line.area_m2 or 0.0)
            for line in bd.edgeband_lines:
                edge_agg[line.key] = edge_agg.get(line.key, 0.0) + float(line.length_m or 0.0)
            for line in bd.hardware_lines:
                if line.key not in hw_agg:
                    hw_agg[line.key] = [0, line.label]
                hw_agg[line.key][0] += int(line.count or 0)

        try:
            store = ShoppingListStoreJson()
        except Exception as exc:
            self._set_store_status(f"Blad otwarcia listy zakupow: {exc}", ok=False)
            return

        added = 0
        for key, (area, label) in mat_agg.items():
            if area <= 0.0:
                continue
            try:
                store.add_shopping_item(
                    material_id=key,
                    material_name=str(label or key),
                    quantity=round(area, 4),
                    unit="m2",
                    project_name=assembly_name,
                    order_id=order_id,
                )
                added += 1
            except Exception:
                pass

        for key, length_m in edge_agg.items():
            if length_m <= 0.0:
                continue
            try:
                store.add_shopping_item(
                    material_id=f"edge_{key}",
                    material_name=f"Okleina {key}",
                    quantity=round(length_m, 2),
                    unit="mb",
                    project_name=assembly_name,
                    order_id=order_id,
                )
                added += 1
            except Exception:
                pass

        for key, (count, label) in hw_agg.items():
            if count <= 0:
                continue
            try:
                store.add_shopping_item(
                    material_id=f"hw_{key}",
                    material_name=str(label or key),
                    quantity=float(count),
                    unit="szt",
                    project_name=assembly_name,
                    order_id=order_id,
                )
                added += 1
            except Exception:
                pass

        self._set_store_status(
            f'Dodano {added} pozycji z "{assembly_name}" do listy zakupow.', ok=True
        )

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

        self.lab_summary_material_total.setText(f"{material_total:.2f} zl")
        self.lab_summary_edgeband_total.setText(f"{edgeband_total:.2f} zl")
        self.lab_summary_hardware_total.setText(f"{hardware_total:.2f} zl")
        self.lab_summary_grand_total.setText(f"{grand_total:.2f} zl")

        # pasek wypelnienia
        if hasattr(self, "fill_bar"):
            fill_pct = int(round(used_width / wall_width * 100.0)) if wall_width > 0 else 0
            fill_pct = max(0, min(100, fill_pct))
            self.fill_bar.setValue(fill_pct)
            self.fill_bar.setFormat(f"{fill_pct}%")
            self.lab_fill_info.setText(f"{used_width:.0f} / {wall_width:.0f} mm")

        # aktualizuj kalkulacje handlowa
        self._refresh_trade_calc()

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

        hardware_overrides = dict(getattr(self._assembly, "hardware_vendor_overrides", {}) or {})
        hardware_vendor = str(hardware_overrides.get("hinge", "") or "").strip()
        if hardware_vendor:
            lines.append(f"Wariant okuc: {HARDWARE_VENDOR_LABELS.get(hardware_vendor, hardware_vendor.title())}")

        company_collection_key = str(getattr(self._assembly, "company_collection_key", "") or "").strip()
        if company_collection_key:
            lines.append(f"Kolekcja firmowa: {COMPANY_COLLECTION_LABELS.get(company_collection_key, company_collection_key)}")

        decor_labels = dict(getattr(self._assembly, "decor_labels", {}) or {})
        decor_chunks = []
        for group_key, label in (("carcass", "Korpus"), ("front", "Front")):
            selected = str(decor_labels.get(group_key, "") or "").strip()
            if selected:
                decor_chunks.append(f"{label}: {selected}")
        if decor_chunks:
            lines.append(f"Dekor zestawu: {', '.join(decor_chunks)}")

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

