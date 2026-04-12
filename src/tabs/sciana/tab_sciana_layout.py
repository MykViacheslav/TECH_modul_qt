from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, QPointF, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen, QTransform, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
)

from src.app.app_settings import load_ui_string_list, save_ui_string_list, load_ui_theme_settings
from src.domain.wall_models import (
    WallLayoutDef,
    WallMeasurementDef,
    WallObstacleDef,
    WallPhotoDef,
    new_wall_id,
)
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.tabs.sciana.dialog_photo_measure import PhotoMeasureDialog
from src.tabs.sciana.dialog_load_wall import LoadWallDialog
from src.ui.collapsible_block import CollapsibleBlock
from src.ui.ui_polish import mark_ui_card, set_ui_variant
from src.ui.theme_utils import get_muted_color


LAYOUT_TYPE_ITEMS: tuple[tuple[str, str], ...] = (
    ("line", "Prosta"),
    ("l", "L"),
    ("c", "C"),
)

OBSTACLE_KIND_ITEMS: tuple[tuple[str, str], ...] = (
    ("projection", "Wystep"),
    ("recess", "Wneka"),
    ("window", "Okno"),
    ("door", "Drzwi"),
    ("pipe", "Rura"),
    ("socket", "Gniazdko"),
    ("plumbing", "Wod-kan"),
    ("radiator", "Grzejnik"),
    ("sill", "Parapet"),
)

WALL_SIDE_ITEMS: tuple[tuple[str, str], ...] = (
    ("A", "Sciana A"),
    ("B", "Sciana B"),
    ("C", "Sciana C"),
)

OPENING_DIRECTION_ITEMS: tuple[tuple[str, str], ...] = (
    ("fixed", "Stale"),
    ("left", "Lewe"),
    ("right", "Prawe"),
    ("double", "Dwuskrzydlowe"),
)

TECHNICAL_OBSTACLE_KINDS = frozenset(("socket", "plumbing", "radiator", "sill"))
SCIANA_MM_MAX = 20000.0
SCIANA_DEPTH_MM_MAX = 10000.0
SCIANA_HEIGHT_MM_MAX = 10000.0

_IMAGE_ATTACHMENT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
MEASUREMENT_KIND_ITEMS: tuple[tuple[str, str], ...] = (
    ("distance", "Odleglosc"),
    ("width", "Szerokosc"),
    ("height", "Wysokosc"),
    ("depth", "Glebokosc"),
)


def _wall_side_label(side: str) -> str:
    side_key = str(side or "A").strip().upper()
    for key, label in WALL_SIDE_ITEMS:
        if key == side_key:
            return label
    return f"Sciana {side_key}"


def _opening_direction_label(direction: str) -> str:
    direction_key = str(direction or "fixed").strip().lower()
    for key, label in OPENING_DIRECTION_ITEMS:
        if key == direction_key:
            return label
    return str(direction or "Stale")


def _obstacle_kind_label(kind: str) -> str:
    kind_key = str(kind or "").strip().lower()
    for key, label in OBSTACLE_KIND_ITEMS:
        if key == kind_key:
            return label
    return str(kind or "")


def _is_technical_obstacle_kind(kind: str) -> bool:
    return str(kind or "").strip().lower() in TECHNICAL_OBSTACLE_KINDS


def _obstacle_dims_text(obstacle: WallObstacleDef) -> str:
    kind_key = str(getattr(obstacle, "kind", "projection") or "projection").strip().lower()
    x_mm = float(getattr(obstacle, "x_mm", 0.0) or 0.0)
    bottom_mm = float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0)
    width_mm = float(getattr(obstacle, "width_mm", 0.0) or 0.0)
    height_mm = float(getattr(obstacle, "height_mm", 0.0) or 0.0)
    depth_mm = float(getattr(obstacle, "depth_mm", 0.0) or 0.0)
    opening_label = _opening_direction_label(getattr(obstacle, "opening_direction", "fixed"))

    if kind_key == "window":
        return (
            f"x={x_mm:.0f}, parapet={bottom_mm:.0f}, "
            f"w={width_mm:.0f}, otwor={height_mm:.0f}, {opening_label}"
        )
    if kind_key == "door":
        return (
            f"x={x_mm:.0f}, prog={bottom_mm:.0f}, "
            f"w={width_mm:.0f}, otwor={height_mm:.0f}, {opening_label}"
        )
    if kind_key == "socket":
        return (
            f"x={x_mm:.0f}, montaz={bottom_mm:.0f}, "
            f"pole={width_mm:.0f}x{height_mm:.0f}, puszka={depth_mm:.0f}"
        )
    if kind_key == "plumbing":
        return (
            f"x={x_mm:.0f}, przylacza={bottom_mm:.0f}, "
            f"strefa={width_mm:.0f}x{height_mm:.0f}, g={depth_mm:.0f}"
        )
    if kind_key == "radiator":
        return (
            f"x={x_mm:.0f}, dol={bottom_mm:.0f}, "
            f"{width_mm:.0f}x{height_mm:.0f}, odstawanie={depth_mm:.0f}"
        )
    if kind_key == "sill":
        return (
            f"x={x_mm:.0f}, poziom={bottom_mm:.0f}, "
            f"dl={width_mm:.0f}, pas={height_mm:.0f}, wys={depth_mm:.0f}"
        )
    return (
        f"x={x_mm:.0f}, y={bottom_mm:.0f}, "
        f"w={width_mm:.0f}, h={height_mm:.0f}, d={depth_mm:.0f}"
    )


def _obstacle_summary_line(obstacle: WallObstacleDef) -> str | None:
    name = str(getattr(obstacle, "name", "") or _obstacle_kind_label(getattr(obstacle, "kind", "")))
    kind_key = str(getattr(obstacle, "kind", "projection") or "projection").strip().lower()
    bottom_mm = float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0)
    width_mm = float(getattr(obstacle, "width_mm", 0.0) or 0.0)
    height_mm = float(getattr(obstacle, "height_mm", 0.0) or 0.0)
    depth_mm = float(getattr(obstacle, "depth_mm", 0.0) or 0.0)
    opening_label = _opening_direction_label(getattr(obstacle, "opening_direction", "fixed"))

    if kind_key == "window":
        return f"- {name}: parapet {bottom_mm:.0f} mm, otwor {height_mm:.0f} mm, {opening_label}"
    if kind_key == "door":
        return f"- {name}: prog {bottom_mm:.0f} mm, otwor {height_mm:.0f} mm, {opening_label}"
    if kind_key == "socket":
        return f"- {name}: montaz {bottom_mm:.0f} mm, pole {width_mm:.0f} x {height_mm:.0f} mm"
    if kind_key == "plumbing":
        return (
            f"- {name}: przylacza {bottom_mm:.0f} mm, "
            f"strefa {width_mm:.0f} x {height_mm:.0f} mm, glebokosc {depth_mm:.0f} mm"
        )
    if kind_key == "radiator":
        return (
            f"- {name}: dol {bottom_mm:.0f} mm, "
            f"{width_mm:.0f} x {height_mm:.0f} mm, odstawanie {depth_mm:.0f} mm"
        )
    if kind_key == "sill":
        return (
            f"- {name}: poziom {bottom_mm:.0f} mm, "
            f"dlugosc {width_mm:.0f} mm, pas {height_mm:.0f} mm, wysuniecie {depth_mm:.0f} mm"
        )
    return None


def _obstacle_preview_label(obstacle: WallObstacleDef) -> str:
    return _obstacle_kind_label(getattr(obstacle, "kind", ""))


def _measurement_kind_label(kind: str) -> str:
    key = str(kind or "distance").strip().lower()
    for item_key, item_label in MEASUREMENT_KIND_ITEMS:
        if item_key == key:
            return item_label
    return str(kind or "Odleglosc")


class WallPreviewView(QGraphicsView):
    sig_obstacle_selected = pyqtSignal(int)
    sig_obstacle_dragged = pyqtSignal(int, float, float)
    sig_obstacle_dimension_changed = pyqtSignal(int, float, float)
    sig_view_resized = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, view_mode: str = "both") -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(self.renderHints())
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport().installEventFilter(self)
        self._view_mode = str(view_mode or "both").strip().lower()

        self._wall = WallLayoutDef(wall_id=new_wall_id())
        self._selected_obstacle_index = -1
        self._front_view_rect = QRectF()
        self._top_view_bounds = QRectF()
        self._top_wall_rects: dict[str, QRectF] = {}
        self._drag_payload: dict | None = None
        self._front_dimension_editors: dict[str, QDoubleSpinBox] = {}
        self._is_syncing_front_dimension_editors = False

    def set_selected_obstacle_index(self, index: int) -> None:
        self._selected_obstacle_index = int(index)

    def front_dimension_editor(self, key: str) -> QDoubleSpinBox | None:
        return self._front_dimension_editors.get(str(key or "").strip().lower())

    def _fit_scene_to_view(self) -> None:
        scene_rect = self.scene.sceneRect()
        if scene_rect.isNull() or scene_rect.isEmpty():
            return
        self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def max_fit_scale(self) -> float:
        scene_rect = self.scene.sceneRect()
        viewport_rect = self.viewport().rect()
        if scene_rect.isNull() or scene_rect.isEmpty():
            return 0.0
        if viewport_rect.width() <= 0 or viewport_rect.height() <= 0:
            return 0.0

        width_scale = float(viewport_rect.width()) / max(1.0, float(scene_rect.width()))
        height_scale = float(viewport_rect.height()) / max(1.0, float(scene_rect.height()))
        return max(0.0, min(width_scale, height_scale))

    def apply_uniform_scale(self, scale: float) -> None:
        target = max(0.0001, float(scale))
        transform = QTransform()
        transform.scale(target, target)
        self.setTransform(transform)
        scene_rect = self.scene.sceneRect()
        if not scene_rect.isNull() and not scene_rect.isEmpty():
            self.centerOn(scene_rect.center())

    def _tight_scene_rect(self, fallback: QRectF, x_margin: float = 24.0, y_margin: float = 24.0) -> QRectF:
        bounds = self.scene.itemsBoundingRect()
        if bounds.isNull() or bounds.isEmpty():
            bounds = QRectF(fallback)
        return bounds.adjusted(-x_margin, -y_margin, x_margin, y_margin)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_scene_to_view()
        self.sig_view_resized.emit()

    def _wall_width_for_side(self, wall: WallLayoutDef, side: str) -> float:
        side_key = str(side or "A").strip().upper()
        if side_key == "B":
            return float(getattr(wall, "wall_b_width_mm", 2600.0) or 2600.0)
        if side_key == "C":
            return float(getattr(wall, "wall_c_width_mm", 2600.0) or 2600.0)
        return float(getattr(wall, "wall_a_width_mm", 4000.0) or 4000.0)

    def _obstacle_fill(self, kind: str) -> QColor:
        kind_key = str(kind or "projection").strip().lower()
        if kind_key == "window":
            return QColor("#eaf7ff")
        if kind_key == "door":
            return QColor("#fff2df")
        if kind_key == "pipe":
            return QColor("#ededed")
        if kind_key == "recess":
            return QColor("#f5f5f5")
        if kind_key == "socket":
            return QColor("#fff8de")
        if kind_key == "plumbing":
            return QColor("#e8fbf7")
        if kind_key == "radiator":
            return QColor("#ffe9e5")
        if kind_key == "sill":
            return QColor("#eef3f7")
        return QColor("#ebf4ff")

    @staticmethod
    def _tag_for_obstacle(index: int, view_kind: str) -> str:
        return f"wall_obstacle::{int(index)}::{str(view_kind or '').strip().lower()}"

    @staticmethod
    def _parse_obstacle_tag(raw: str) -> tuple[int, str] | None:
        parts = str(raw or "").strip().split("::")
        if len(parts) != 3 or parts[0] != "wall_obstacle":
            return None
        try:
            return int(parts[1]), str(parts[2])
        except Exception:
            return None

    def _add_text(self, text: str, pos: QPointF, color_hex: str = "#333333", scale: float = 1.0) -> None:
        item = QGraphicsSimpleTextItem(text)
        item.setBrush(QBrush(QColor(color_hex)))
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        item.setScale(float(scale))
        item.setZValue(40.0)
        item.setPos(pos)
        self.scene.addItem(item)

    def _add_rect(
        self,
        rect: QRectF,
        pen: QPen,
        brush: QBrush,
        z: float = 0.0,
        data_key: str = "",
    ) -> None:
        item = QGraphicsRectItem(rect)
        item.setPen(pen)
        item.setBrush(brush)
        item.setZValue(z)
        if data_key:
            item.setData(0, data_key)
            item.setCursor(Qt.CursorShape.OpenHandCursor)
        self.scene.addItem(item)

    def scene_rect_for_obstacle(self, obstacle_index: int, view_kind: str) -> QRectF | None:
        wanted_key = self._tag_for_obstacle(obstacle_index, view_kind)
        for item in self.scene.items():
            try:
                if str(item.data(0) or "") == wanted_key and hasattr(item, "rect"):
                    return item.rect()
            except Exception:
                continue
        return None

    def _build_top_obstacle_rect(self, obstacle: WallObstacleDef) -> QRectF | None:
        side = str(getattr(obstacle, "wall_side", "A") or "A").strip().upper()
        x_mm = float(getattr(obstacle, "x_mm", 0.0) or 0.0)
        width_mm = float(getattr(obstacle, "width_mm", 600.0) or 600.0)
        depth_mm = max(80.0, float(getattr(obstacle, "depth_mm", 120.0) or 120.0))

        if side == "A" and "A" in self._top_wall_rects:
            base = self._top_wall_rects["A"]
            return QRectF(base.left() + x_mm, base.top(), width_mm, depth_mm)
        if side == "B" and "B" in self._top_wall_rects:
            base = self._top_wall_rects["B"]
            return QRectF(base.left(), base.top() + x_mm, depth_mm, width_mm)
        if side == "C" and "C" in self._top_wall_rects:
            base = self._top_wall_rects["C"]
            return QRectF(base.right() - depth_mm, base.top() + x_mm, depth_mm, width_mm)
        return None

    @staticmethod
    def _add_arrow_marker(
        scene: QGraphicsScene,
        point: QPointF,
        orientation: str,
        pen: QPen,
    ) -> None:
        size = 10.0
        x = float(point.x())
        y = float(point.y())
        if orientation == "left":
            scene.addLine(x, y, x + size, y - size * 0.45, pen)
            scene.addLine(x, y, x + size, y + size * 0.45, pen)
            return
        if orientation == "right":
            scene.addLine(x, y, x - size, y - size * 0.45, pen)
            scene.addLine(x, y, x - size, y + size * 0.45, pen)
            return
        if orientation == "up":
            scene.addLine(x, y, x - size * 0.45, y + size, pen)
            scene.addLine(x, y, x + size * 0.45, y + size, pen)
            return
        if orientation == "down":
            scene.addLine(x, y, x - size * 0.45, y - size, pen)
            scene.addLine(x, y, x + size * 0.45, y - size, pen)

    def _build_dimension_spinbox(self, value_mm: float, max_value_mm: float) -> QDoubleSpinBox:
        editor = QDoubleSpinBox()
        editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        editor.setDecimals(1)
        editor.setKeyboardTracking(False)
        editor.setSingleStep(10.0)
        editor.setSuffix(" mm")
        editor.setRange(0.0, max(0.0, float(max_value_mm)))
        editor.setValue(float(value_mm))
        editor.setFixedWidth(124)
        editor.setMinimumHeight(30)
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

    def _add_front_dimension_overlays(
        self,
        obstacle_index: int,
        obstacle: WallObstacleDef,
        front_rect: QRectF,
        show_editors: bool,
    ) -> None:
        line_pen = QPen(QColor("#2b6cb0"))
        line_pen.setWidth(2)
        guide_pen = QPen(QColor("#8db7e8"))
        guide_pen.setWidth(1)
        guide_pen.setStyle(Qt.PenStyle.DashLine)

        box_left = float(self._front_view_rect.left())
        box_bottom = float(self._front_view_rect.bottom())
        obstacle_left = float(front_rect.left())
        obstacle_bottom = float(front_rect.bottom())
        box_mid_y = float(front_rect.center().y())
        box_mid_x = float(front_rect.center().x())

        line_y = box_mid_y
        line_x = box_mid_x

        self.scene.addLine(box_left, line_y, obstacle_left, line_y, line_pen)
        self.scene.addLine(box_left, line_y - 18.0, box_left, line_y + 18.0, guide_pen)
        self.scene.addLine(obstacle_left, line_y - 18.0, obstacle_left, line_y + 18.0, guide_pen)
        self._add_arrow_marker(self.scene, QPointF(box_left, line_y), "left", line_pen)
        self._add_arrow_marker(self.scene, QPointF(obstacle_left, line_y), "right", line_pen)

        self.scene.addLine(line_x, obstacle_bottom, line_x, box_bottom, line_pen)
        self.scene.addLine(line_x - 18.0, obstacle_bottom, line_x + 18.0, obstacle_bottom, guide_pen)
        self.scene.addLine(line_x - 18.0, box_bottom, line_x + 18.0, box_bottom, guide_pen)
        self._add_arrow_marker(self.scene, QPointF(line_x, obstacle_bottom), "up", line_pen)
        self._add_arrow_marker(self.scene, QPointF(line_x, box_bottom), "down", line_pen)

        if not show_editors:
            return

        max_x = max(0.0, self._wall_width_for_side(self._wall, obstacle.wall_side) - float(obstacle.width_mm))
        max_bottom = max(0.0, float(self._wall.room_height_mm) - float(obstacle.height_mm))

        editor_x = self._build_dimension_spinbox(float(obstacle.x_mm), max_x)
        editor_bottom = self._build_dimension_spinbox(float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0), max_bottom)

        proxy_x = self.scene.addWidget(editor_x)
        proxy_bottom = self.scene.addWidget(editor_bottom)

        proxy_x.setZValue(20.0)
        proxy_bottom.setZValue(20.0)
        proxy_x.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        proxy_bottom.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        proxy_x.setPos(
            (box_left + obstacle_left) * 0.5 - float(editor_x.width()) * 0.5,
            line_y - 44.0,
        )
        proxy_bottom.setPos(
            line_x + 14.0,
            (obstacle_bottom + box_bottom) * 0.5 - float(editor_bottom.height()) * 0.5,
        )

        self._front_dimension_editors["x"] = editor_x
        self._front_dimension_editors["bottom"] = editor_bottom

        def _emit_dimension_change() -> None:
            if self._is_syncing_front_dimension_editors:
                return
            self.sig_obstacle_dimension_changed.emit(
                int(obstacle_index),
                float(editor_x.value()),
                float(editor_bottom.value()),
            )

        editor_x.editingFinished.connect(_emit_dimension_change)
        editor_bottom.editingFinished.connect(_emit_dimension_change)

    def _add_front_layout_guides(self) -> None:
        room_height = max(1.0, float(getattr(self._wall, "room_height_mm", 2600.0) or 2600.0))
        front_width = max(1.0, float(self._front_view_rect.width()))
        base_plinth = max(0.0, min(float(getattr(self._wall, "base_plinth_mm", 0.0) or 0.0), room_height))
        upper_clearance = max(0.0, min(float(getattr(self._wall, "upper_clearance_mm", 0.0) or 0.0), room_height))
        top_offset = max(0.0, min(float(getattr(self._wall, "top_offset_mm", 0.0) or 0.0), room_height))
        bottom_offset = max(0.0, min(float(getattr(self._wall, "bottom_offset_mm", 0.0) or 0.0), room_height))
        base_left = max(0.0, min(float(getattr(self._wall, "base_offset_left_mm", 0.0) or 0.0), front_width))
        max_right = max(0.0, front_width - base_left)
        base_right = max(0.0, min(float(getattr(self._wall, "base_offset_right_mm", 0.0) or 0.0), max_right))
        upper_left = max(0.0, min(float(getattr(self._wall, "upper_offset_left_mm", 0.0) or 0.0), front_width))
        max_upper_right = max(0.0, front_width - upper_left)
        upper_right = max(0.0, min(float(getattr(self._wall, "upper_offset_right_mm", 0.0) or 0.0), max_upper_right))

        guide_pen = QPen(QColor("#9b8b00"))
        guide_pen.setWidth(2)
        guide_pen.setStyle(Qt.PenStyle.DashLine)
        label_color = "#7a5e00"

        if base_plinth > 0.0:
            y = float(self._front_view_rect.bottom() - base_plinth)
            self.scene.addLine(self._front_view_rect.left(), y, self._front_view_rect.right(), y, guide_pen)
            self._add_text(
                f"Dolny cokol {base_plinth:.0f} mm",
                QPointF(self._front_view_rect.left() + 10.0, y - 22.0),
                label_color,
            )

        if upper_clearance > 0.0:
            y = float(self._front_view_rect.top() + upper_clearance)
            self.scene.addLine(self._front_view_rect.left(), y, self._front_view_rect.right(), y, guide_pen)
            self._add_text(
                f"Gorny odstep {upper_clearance:.0f} mm",
                QPointF(self._front_view_rect.left() + 10.0, y + 6.0),
                label_color,
            )

        if top_offset > 0.0:
            y = float(self._front_view_rect.top() + top_offset)
            self.scene.addLine(self._front_view_rect.left(), y, self._front_view_rect.right(), y, guide_pen)
            self._add_text(
                f"Gorny offset {top_offset:.0f} mm",
                QPointF(self._front_view_rect.right() - 180.0, y + 6.0),
                label_color,
            )

        if bottom_offset > 0.0:
            y = float(self._front_view_rect.bottom() - bottom_offset)
            self.scene.addLine(self._front_view_rect.left(), y, self._front_view_rect.right(), y, guide_pen)
            self._add_text(
                f"Dolny offset {bottom_offset:.0f} mm",
                QPointF(self._front_view_rect.right() - 180.0, y - 22.0),
                label_color,
            )

        if base_left > 0.0:
            x = float(self._front_view_rect.left() + base_left)
            self.scene.addLine(x, self._front_view_rect.top(), x, self._front_view_rect.bottom(), guide_pen)
            self._add_text(
                f"L {base_left:.0f}",
                QPointF(x + 6.0, self._front_view_rect.bottom() - 30.0),
                label_color,
            )

        if base_right > 0.0:
            x = float(self._front_view_rect.right() - base_right)
            self.scene.addLine(x, self._front_view_rect.top(), x, self._front_view_rect.bottom(), guide_pen)
            self._add_text(
                f"P {base_right:.0f}",
                QPointF(x + 6.0, self._front_view_rect.bottom() - 30.0),
                label_color,
            )

        if upper_left > 0.0:
            x = float(self._front_view_rect.left() + upper_left)
            self.scene.addLine(x, self._front_view_rect.top(), x, self._front_view_rect.bottom(), guide_pen)
            self._add_text(
                f"GL {upper_left:.0f}",
                QPointF(x + 6.0, self._front_view_rect.top() + 12.0),
                label_color,
            )

        if upper_right > 0.0:
            x = float(self._front_view_rect.right() - upper_right)
            self.scene.addLine(x, self._front_view_rect.top(), x, self._front_view_rect.bottom(), guide_pen)
            self._add_text(
                f"GP {upper_right:.0f}",
                QPointF(x + 6.0, self._front_view_rect.top() + 30.0),
                label_color,
            )

    def render_wall(self, wall: WallLayoutDef, fit: bool = True) -> None:
        self._wall = WallLayoutDef.from_dict(wall.to_dict()) if hasattr(wall, "to_dict") else wall
        self.scene.clear()
        self._top_wall_rects = {}
        self._front_dimension_editors = {}

        layout_type = str(getattr(self._wall, "layout_type", "line") or "line")
        front_side = str(getattr(self._wall, "front_view_wall_side", "A") or "A").strip().upper()
        room_height = max(1800.0, float(getattr(self._wall, "room_height_mm", 2600.0) or 2600.0))
        wall_a = max(500.0, float(getattr(self._wall, "wall_a_width_mm", 4000.0) or 4000.0))
        wall_b = max(500.0, float(getattr(self._wall, "wall_b_width_mm", 2600.0) or 2600.0))
        wall_c = max(500.0, float(getattr(self._wall, "wall_c_width_mm", 2600.0) or 2600.0))
        wall_thickness = max(10.0, min(16.0, float(getattr(self._wall, "base_depth_mm", 600.0) or 600.0) * 0.025))

        if layout_type == "line" and front_side != "A":
            front_side = "A"
        if layout_type == "l" and front_side == "C":
            front_side = "A"

        front_w = self._wall_width_for_side(self._wall, front_side)
        self._front_view_rect = QRectF(0.0, 0.0, front_w, room_height)
        top_origin = QPointF(0.0, 0.0)
        top_extent_w = max(
            wall_a,
            float(getattr(self._wall, "island_offset_x_mm", 0.0) or 0.0)
            + float(getattr(self._wall, "island_width_mm", 0.0) or 0.0),
            wall_thickness,
        )
        top_extent_h = max(
            wall_thickness,
            wall_b if layout_type in ("l", "c") else wall_thickness,
            wall_c if layout_type == "c" else wall_thickness,
            float(getattr(self._wall, "island_offset_y_mm", 0.0) or 0.0)
            + float(getattr(self._wall, "island_depth_mm", 0.0) or 0.0),
        )
        self._top_view_bounds = QRectF(top_origin.x(), top_origin.y(), top_extent_w, top_extent_h)

        wall_pen = QPen(QColor("#1f1f1f"))
        wall_pen.setWidth(3)
        wall_brush = QBrush(QColor("#f4f4f4"))
        guide_pen = QPen(QColor("#b8b8b8"))
        guide_pen.setWidth(1)
        selected_pen = QPen(QColor("#d97706"))
        selected_pen.setWidth(2)

        show_front = self._view_mode in ("both", "front")
        show_top = self._view_mode in ("both", "top")

        if show_front:
            self._add_text(front_side, QPointF(self._front_view_rect.left() + 8.0, self._front_view_rect.top() + 8.0))
            self._add_rect(self._front_view_rect, wall_pen, wall_brush)
            self.scene.addLine(
                self._front_view_rect.left(),
                self._front_view_rect.bottom(),
                self._front_view_rect.right(),
                self._front_view_rect.bottom(),
                guide_pen,
            )
            self._add_front_layout_guides()

        rect_a = QRectF(top_origin.x(), top_origin.y(), wall_a, wall_thickness)
        self._top_wall_rects["A"] = rect_a
        if show_top:
            self._add_rect(rect_a, wall_pen, wall_brush)
            self._add_text("A", QPointF(rect_a.left() + 8.0, rect_a.top() + 2.0))

        if layout_type in ("l", "c"):
            rect_b = QRectF(top_origin.x(), top_origin.y(), wall_thickness, wall_b)
            self._top_wall_rects["B"] = rect_b
            if show_top:
                self._add_rect(rect_b, wall_pen, wall_brush)
                self._add_text("B", QPointF(rect_b.left() + 2.0, rect_b.top() + 10.0))

        if layout_type == "c":
            rect_c = QRectF(top_origin.x() + wall_a - wall_thickness, top_origin.y(), wall_thickness, wall_c)
            self._top_wall_rects["C"] = rect_c
            if show_top:
                self._add_rect(rect_c, wall_pen, wall_brush)
                self._add_text("C", QPointF(rect_c.left() + 2.0, rect_c.top() + 10.0))

        if show_top and bool(getattr(self._wall, "has_island", False)):
            island_pen = QPen(QColor("#a85f00"))
            island_pen.setWidth(2)
            island_rect = QRectF(
                top_origin.x() + float(getattr(self._wall, "island_offset_x_mm", 1200.0) or 1200.0),
                top_origin.y() + float(getattr(self._wall, "island_offset_y_mm", 1400.0) or 1400.0),
                float(getattr(self._wall, "island_width_mm", 1800.0) or 1800.0),
                float(getattr(self._wall, "island_depth_mm", 900.0) or 900.0),
            )
            self._add_rect(island_rect, island_pen, QBrush(QColor("#fff1da")), z=1.0)
            self._add_text("Wyspa", QPointF(island_rect.left() + 8.0, island_rect.top() + 8.0), "#7a4600")

        for index, obstacle in enumerate(list(getattr(self._wall, "obstacles", []) or [])):
            side = str(getattr(obstacle, "wall_side", "A") or "A").strip().upper()
            x_mm = max(0.0, float(getattr(obstacle, "x_mm", 0.0) or 0.0))
            width_mm = max(50.0, float(getattr(obstacle, "width_mm", 600.0) or 600.0))
            height_mm = max(50.0, float(getattr(obstacle, "height_mm", 1000.0) or 1000.0))
            bottom_mm = max(0.0, float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0))
            is_selected = index == int(getattr(self, "_selected_obstacle_index", -1))
            pen = selected_pen if is_selected else QPen(QColor("#6b8cb1"))
            if not is_selected:
                pen.setWidth(1)
                pen.setColor(QColor("#9bb2c7"))
            fill = QColor(self._obstacle_fill(getattr(obstacle, "kind", "projection")))
            fill.setAlpha(165 if is_selected else 72)
            brush = QBrush(fill)
            label = _obstacle_preview_label(obstacle)

            if show_front and side == front_side:
                front_rect = QRectF(
                    self._front_view_rect.left() + x_mm,
                    self._front_view_rect.bottom() - bottom_mm - height_mm,
                    width_mm,
                    height_mm,
                )
                self._add_rect(front_rect, pen, brush, z=5.0, data_key=self._tag_for_obstacle(index, "front"))
                kind_key = str(getattr(obstacle, "kind", "projection") or "projection").strip().lower()
                show_main_label = is_selected or (
                    not _is_technical_obstacle_kind(kind_key)
                    and (front_rect.width() >= 260.0 or front_rect.height() >= 180.0)
                )
                show_detail_symbol = is_selected or (
                    not _is_technical_obstacle_kind(kind_key)
                    and (front_rect.width() >= 220.0 or front_rect.height() >= 180.0)
                )
                if show_main_label:
                    self._add_text(label, QPointF(front_rect.left() + 6.0, front_rect.top() + 6.0), "#385575", scale=1.0)

                if kind_key == "window":
                    pass
                elif kind_key == "door" and show_detail_symbol:
                    swing_pen = QPen(QColor("#a85f00"))
                    swing_pen.setWidth(1)
                    if str(getattr(obstacle, "opening_direction", "fixed")).strip().lower() == "left":
                        self.scene.addLine(
                            front_rect.left() + 10.0,
                            front_rect.bottom() - 10.0,
                            front_rect.right() - 10.0,
                            front_rect.top() + 10.0,
                            swing_pen,
                        )
                    elif str(getattr(obstacle, "opening_direction", "fixed")).strip().lower() == "right":
                        self.scene.addLine(
                            front_rect.right() - 10.0,
                            front_rect.bottom() - 10.0,
                            front_rect.left() + 10.0,
                            front_rect.top() + 10.0,
                            swing_pen,
                        )
                    elif str(getattr(obstacle, "opening_direction", "fixed")).strip().lower() == "double":
                        mid_x = front_rect.center().x()
                        self.scene.addLine(
                            mid_x,
                            front_rect.bottom() - 10.0,
                            front_rect.left() + 10.0,
                            front_rect.top() + 10.0,
                            swing_pen,
                        )
                        self.scene.addLine(
                            mid_x,
                            front_rect.bottom() - 10.0,
                            front_rect.right() - 10.0,
                            front_rect.top() + 10.0,
                            swing_pen,
                        )
                elif kind_key == "socket" and is_selected:
                    symbol_pen = QPen(QColor("#9a6b00"))
                    symbol_pen.setWidth(1)
                    cx = front_rect.center().x()
                    cy = front_rect.center().y()
                    self.scene.addEllipse(cx - 16.0, cy - 8.0, 10.0, 10.0, symbol_pen, QBrush(QColor("#fffdf4")))
                    self.scene.addEllipse(cx + 6.0, cy - 8.0, 10.0, 10.0, symbol_pen, QBrush(QColor("#fffdf4")))
                    self.scene.addLine(cx - 20.0, cy - 20.0, cx + 20.0, cy - 20.0, symbol_pen)
                elif kind_key == "plumbing" and is_selected:
                    pipe_pen = QPen(QColor("#0f766e"))
                    pipe_pen.setWidth(2)
                    cx = front_rect.center().x()
                    self.scene.addLine(cx - 14.0, front_rect.top() + 18.0, cx - 14.0, front_rect.bottom() - 16.0, pipe_pen)
                    self.scene.addLine(cx + 14.0, front_rect.top() + 18.0, cx + 14.0, front_rect.bottom() - 16.0, pipe_pen)
                    self.scene.addLine(cx - 24.0, front_rect.bottom() - 18.0, cx - 4.0, front_rect.bottom() - 4.0, pipe_pen)
                    self.scene.addLine(cx + 24.0, front_rect.bottom() - 18.0, cx + 4.0, front_rect.bottom() - 4.0, pipe_pen)
                elif kind_key == "radiator" and show_detail_symbol:
                    rib_pen = QPen(QColor("#c2410c"))
                    rib_pen.setWidth(1)
                    left = front_rect.left() + 14.0
                    right = front_rect.right() - 14.0
                    top = front_rect.top() + 14.0
                    bottom = front_rect.bottom() - 12.0
                    self.scene.addLine(left, top, right, top, rib_pen)
                    for step in range(4):
                        rib_x = left + step * max(12.0, (right - left) / 3.5)
                        self.scene.addLine(rib_x, top, rib_x, bottom, rib_pen)
                elif kind_key == "sill" and is_selected:
                    sill_pen = QPen(QColor("#475569"))
                    sill_pen.setWidth(2)
                    y_line = front_rect.center().y()
                    self.scene.addLine(front_rect.left() + 10.0, y_line, front_rect.right() - 10.0, y_line, sill_pen)
                if is_selected:
                    show_editors = (
                        self._drag_payload is not None
                        and int(self._drag_payload.get("index", -1)) == index
                        and str(self._drag_payload.get("view", "")).strip().lower() == "front"
                    )
                    self._add_front_dimension_overlays(index, obstacle, front_rect, show_editors=show_editors)

            top_rect = self._build_top_obstacle_rect(obstacle)
            if show_top and top_rect is not None:
                self._add_rect(top_rect, pen, brush, z=5.0, data_key=self._tag_for_obstacle(index, "top"))
                if is_selected or (
                    not _is_technical_obstacle_kind(getattr(obstacle, "kind", ""))
                    and (top_rect.width() >= 260.0 or top_rect.height() >= 180.0)
                ):
                    self._add_text(label, QPointF(top_rect.left() + 4.0, top_rect.top() + 4.0), "#385575", scale=0.9)

        if self._view_mode == "front":
            scene_bounds = self._tight_scene_rect(
                self._front_view_rect.adjusted(-40.0, -30.0, 40.0, 40.0),
                x_margin=16.0,
                y_margin=16.0,
            )
        elif self._view_mode == "top":
            scene_bounds = self._tight_scene_rect(
                self._top_view_bounds.adjusted(-40.0, -30.0, 40.0, 30.0),
                x_margin=14.0,
                y_margin=14.0,
            )
        else:
            scene_bounds = self._tight_scene_rect(
                self.scene.itemsBoundingRect().adjusted(-60.0, -40.0, 60.0, 50.0),
                x_margin=18.0,
                y_margin=18.0,
            )
        self.scene.setSceneRect(scene_bounds)
        if fit:
            self._fit_scene_to_view()

    def _obstacle_tag_from_view_pos(self, pos) -> tuple[int, str] | None:
        for item in self.items(pos):
            try:
                parsed = self._parse_obstacle_tag(str(item.data(0) or ""))
            except Exception:
                parsed = None
            if parsed is not None:
                return parsed
        return None

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            et = event.type()
            if et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                parsed = self._obstacle_tag_from_view_pos(event.pos())
                if parsed is not None:
                    index, view_kind = parsed
                    obstacle = self._wall.obstacles[index]
                    scene_pos = self.mapToScene(event.pos())
                    self.sig_obstacle_selected.emit(index)
                    rect = self.scene_rect_for_obstacle(index, view_kind)
                    if rect is not None:
                        if view_kind == "front":
                            self._drag_payload = {
                                "index": index,
                                "view": "front",
                                "left_offset": float(scene_pos.x() - rect.left()),
                                "bottom_delta": float(rect.bottom() - scene_pos.y()),
                            }
                        else:
                            side = str(getattr(obstacle, "wall_side", "A") or "A").strip().upper()
                            axis_offset = float(scene_pos.x() - rect.left()) if side == "A" else float(scene_pos.y() - rect.top())
                            self._drag_payload = {
                                "index": index,
                                "view": "top",
                                "side": side,
                                "axis_offset": axis_offset,
                            }
                    event.accept()
                    return True
            elif et == QEvent.Type.MouseMove and self._drag_payload and event.buttons() & Qt.MouseButton.LeftButton:
                payload = dict(self._drag_payload)
                idx = int(payload.get("index", -1))
                if 0 <= idx < len(self._wall.obstacles):
                    obstacle = self._wall.obstacles[idx]
                    scene_pos = self.mapToScene(event.pos())
                    current_bottom = float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0)
                    if str(payload.get("view", "")) == "front":
                        x_mm = float(scene_pos.x() - float(payload.get("left_offset", 0.0)) - self._front_view_rect.left())
                        rect_bottom = float(scene_pos.y() + float(payload.get("bottom_delta", 0.0)))
                        bottom_mm = float(self._front_view_rect.bottom() - rect_bottom)
                        self.sig_obstacle_dragged.emit(idx, x_mm, bottom_mm)
                    else:
                        side = str(payload.get("side", "A") or "A")
                        axis_offset = float(payload.get("axis_offset", 0.0))
                        if side == "A":
                            x_mm = float(scene_pos.x() - axis_offset - self._top_wall_rects["A"].left())
                        else:
                            base_rect = self._top_wall_rects.get(side)
                            x_mm = float(scene_pos.y() - axis_offset - (base_rect.top() if base_rect is not None else 0.0))
                        self.sig_obstacle_dragged.emit(idx, x_mm, current_bottom)
                event.accept()
                return True
            elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self._drag_payload:
                self._drag_payload = None
                self.render_wall(self._wall, fit=False)
                event.accept()
                return True
        return super().eventFilter(obj, event)


class TabScianaLayout(QWidget):
    sig_open_komplet_requested = pyqtSignal(dict)
    sig_open_order_requested = pyqtSignal(dict)

    def __init__(
        self,
        parent: QWidget | None = None,
        store: WallStoreJson | None = None,
        client_store: ClientStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("sciana_layout_root")
        self._wall = WallLayoutDef(wall_id=new_wall_id())
        self._store = store if store is not None else WallStoreJson()
        self._client_store = client_store if client_store is not None else ClientStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._is_pushing_ui = False
        self._is_syncing_obstacle_editor = False
        self._is_syncing_preview_scales = False
        self._selected_obstacle_index = -1
        self._loaded_wall_name = ""
        self._startup_visibility_applied_once = False
        self._order_id_context = ""
        self._left_zone_visible = True
        self._left_zone_last_width = 390
        self._right_zone_visible = True
        self._right_zone_last_width = 380
        theme = load_ui_theme_settings()
        self._is_tech = str(theme.motif).strip().lower() == "tech" and str(theme.mode).strip().lower() == "night"
        self._muted = "#9bb0cd" if self._is_tech else "#555"

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.left_zone_toggle = QPushButton("Pokaz lewy panel", self)
        self.left_zone_toggle.setStyleSheet(
            f"QPushButton {{ border:none; background:transparent; color:{self._muted};"
            " font-weight:600; padding:4px; text-align:left; }}"
        )
        self.left_zone_toggle.clicked.connect(self._toggle_left_zone)
        # Hide root vertical toggle to reclaim horizontal workspace.
        self.left_zone_toggle.hide()

        self.right_zone_toggle = QPushButton("Panel informacyjny >", self)
        self.right_zone_toggle.setStyleSheet(
            f"QPushButton {{ border:none; background:transparent; color:{self._muted};"
            " font-weight:600; padding:4px; text-align:left; }}"
        )
        self.right_zone_toggle.clicked.connect(self._toggle_right_zone)
        # Hide root vertical toggle to reclaim horizontal workspace.
        self.right_zone_toggle.hide()

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.main_splitter.setObjectName("sciana_main_splitter")
        self.main_splitter.setHandleWidth(10)
        root.addWidget(self.main_splitter, 1)

        self.left_zone = self._build_left_zone()
        self.center_zone = self._build_center_zone()
        self.right_zone = self._build_right_zone()
        self.left_zone.setMinimumWidth(320)
        self.right_zone.setMinimumWidth(320)

        self.main_splitter.addWidget(self.left_zone)
        self.main_splitter.addWidget(self.center_zone)
        self.main_splitter.addWidget(self.right_zone)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([360, 980, 360])
        self.left_zone.show()
        self._apply_desktop_visual_styles()

        self._apply_block_startup_visibility()
        self._reload_client_choices()
        self._reload_order_choices()
        self._reload_worker_choices()
        self._push_wall_to_ui()
        self._refresh_all()

        self._shortcut_actions = {
            "save": ("Ctrl+S", self._shortcut_save_wall),
            "overwrite": ("Ctrl+Shift+S", self._on_overwrite),
            "load": ("Ctrl+L", self._on_load),
            "new": ("Ctrl+N", self.start_new_wall),
            "next": ("Ctrl+Return", self._on_go_to_komplet),
            "focus_name": ("Ctrl+F", self._shortcut_focus_wall_name),
        }
        self._setup_shortcuts_from_settings()
        self._refresh_left_zone_toggle_button()

    def _apply_desktop_visual_styles(self) -> None:
        if self._is_tech:
            self.setStyleSheet(
                """
                QWidget#sciana_layout_root {
                    background: #0b1020;
                }
                QWidget#sciana_zone_left,
                QWidget#sciana_zone_center,
                QWidget#sciana_zone_right {
                    border: 1px solid #243c5f;
                    border-radius: 14px;
                    background: #0f172a;
                }
                QLabel#sciana_zone_title {
                    font-size: 11px;
                    letter-spacing: 0.08em;
                    font-weight: 700;
                    color: #9bb0cd;
                    padding: 2px 4px 4px 4px;
                }
                QFrame#sciana_layout_quick_bar {
                    background: #111b30;
                    border: 1px solid #2a4368;
                    border-radius: 14px;
                }
                QGroupBox#sciana_view_card,
                QGroupBox#sciana_top_card {
                    border: 1px solid #2a4368;
                    border-radius: 12px;
                    margin-top: 10px;
                    background: #111b30;
                    font-weight: 700;
                    color: #dbe9ff;
                }
                QGroupBox#sciana_view_card::title,
                QGroupBox#sciana_top_card::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    top: -1px;
                    padding: 0 4px;
                    color: #9cb7dc;
                    font-size: 12px;
                }
                QTableWidget {
                    border: 1px solid #2a4368;
                    border-radius: 10px;
                    background: #111b30;
                    gridline-color: #243c5f;
                    selection-background-color: #1d4ed8;
                    selection-color: #f2f7ff;
                }
                QHeaderView::section {
                    background: #15253f;
                    color: #dbe9ff;
                    padding: 6px 8px;
                    border: 0;
                    border-right: 1px solid #243c5f;
                    border-bottom: 1px solid #243c5f;
                    font-weight: 700;
                }
                QLabel#sciana_side_note {
                    color: #9bb0cd;
                    line-height: 1.35;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QWidget#sciana_layout_root {
                    background: #f3f6fb;
                }
                QWidget#sciana_zone_left,
                QWidget#sciana_zone_center,
                QWidget#sciana_zone_right {
                    border: 1px solid #d8e1ee;
                    border-radius: 14px;
                    background: #f7f9fc;
                }
                QLabel#sciana_zone_title {
                    font-size: 11px;
                    letter-spacing: 0.08em;
                    font-weight: 700;
                    color: #64748b;
                    padding: 2px 4px 4px 4px;
                }
                QFrame#sciana_layout_quick_bar {
                    background: #edf3fb;
                    border: 1px solid #d5e1f1;
                    border-radius: 14px;
                }
                QGroupBox#sciana_view_card,
                QGroupBox#sciana_top_card {
                    border: 1px solid #d8e1ee;
                    border-radius: 12px;
                    margin-top: 10px;
                    background: #ffffff;
                    font-weight: 700;
                    color: #334155;
                }
                QGroupBox#sciana_view_card::title,
                QGroupBox#sciana_top_card::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    top: -1px;
                    padding: 0 4px;
                    color: #475569;
                    font-size: 12px;
                }
                QTableWidget {
                    border: 1px solid #d8e1ee;
                    border-radius: 10px;
                    background: #ffffff;
                    gridline-color: #e5e7eb;
                    selection-background-color: #dbeafe;
                    selection-color: #0f172a;
                }
                QHeaderView::section {
                    background: #edf2f8;
                    color: #334155;
                    padding: 6px 8px;
                    border: 0;
                    border-right: 1px solid #dbe3ee;
                    border-bottom: 1px solid #dbe3ee;
                    font-weight: 700;
                }
                QLabel#sciana_side_note {
                    color: #334155;
                    line-height: 1.35;
                }
                """
            )
        self._style_collapsible_blocks()

    def _style_collapsible_blocks(self) -> None:
        block_style = (
            """
            QToolButton {
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 700;
                text-align: left;
                border: 1px solid #2a4368;
                border-radius: 11px;
                background: #111b30;
                color: #dbe9ff;
            }
            QToolButton:hover {
                background: #1a2740;
                border-color: #3b82f6;
            }
            QFrame#contentPanel {
                border: 1px solid #243c5f;
                border-top: 0px;
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
                background: #0f172a;
            }
            """
            if self._is_tech
            else
            """
            QToolButton {
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 700;
                text-align: left;
                border: 1px solid #d4deed;
                border-radius: 11px;
                background: #f0f5fd;
                color: #1f2f45;
            }
            QToolButton:hover {
                background: #e8effa;
                border-color: #c4d3e8;
            }
            QFrame#contentPanel {
                border: 1px solid #dbe4f0;
                border-top: 0px;
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
                background: #f9fbff;
            }
            """
        )
        for block in (
            getattr(self, "blk_identity", None),
            getattr(self, "blk_dims", None),
            getattr(self, "blk_store", None),
            getattr(self, "blk_obstacles", None),
            getattr(self, "blk_photos", None),
            getattr(self, "blk_measurements", None),
            getattr(self, "blk_notes", None),
            getattr(self, "blk_summary", None),
            getattr(self, "blk_collisions", None),
            getattr(self, "blk_obstacle_details", None),
            # blk_suggestions and blk_room are None after Step 27 — skipped by `if block is not None`
            getattr(self, "blk_suggestions", None),
        ):
            if block is not None:
                block.setStyleSheet(block_style)

    def _build_left_zone(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("sciana_zone_left")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # internal zone label removed (Step 23)

        # --- blk_identity: core identity + wall type ---
        self.blk_identity = CollapsibleBlock("Sciana: Podstawowe", panel)
        identity_body = QWidget(self.blk_identity)
        identity_form = QFormLayout(identity_body)
        identity_form.setSpacing(6)

        self.ed_name = QLineEdit()
        self.cb_client = QComboBox()
        self.cb_order = QComboBox()
        self.ed_order_id = QLineEdit()
        self.ed_order_id.setReadOnly(True)
        self.ed_order_id.setPlaceholderText("ID zamowienia")
        self.cb_worker = QComboBox()

        self.cb_layout_type = QComboBox()
        for key, label in LAYOUT_TYPE_ITEMS:
            self.cb_layout_type.addItem(label, key)

        self.cb_front_wall = QComboBox()
        for key, label in WALL_SIDE_ITEMS:
            self.cb_front_wall.addItem(label, key)

        self.chk_island = QCheckBox("Dodaj wyspe / polwysep")

        identity_form.addRow("Nazwa", self.ed_name)
        identity_form.addRow("Klient", self.cb_client)
        identity_form.addRow("Zamowienie", self.cb_order)
        identity_form.addRow("ID zamowienia", self.ed_order_id)
        identity_form.addRow("Pracownik", self.cb_worker)
        identity_form.addRow("Typ ukladu", self.cb_layout_type)
        identity_form.addRow("Widok z przodu", self.cb_front_wall)
        identity_form.addRow("", self.chk_island)

        self.blk_identity.content_layout().addWidget(identity_body)
        layout.addWidget(self.blk_identity)

        # --- blk_dims: wall dimensions, clearances, offsets, island ---
        self.blk_dims = CollapsibleBlock("Wymiary i offsets", panel)
        dims_body = QWidget(self.blk_dims)
        dims_form = QFormLayout(dims_body)
        dims_form.setSpacing(6)
        self._layout_form = dims_form  # used by _set_form_row_visible for island/wall_b/wall_c

        self.sp_wall_a = QDoubleSpinBox()
        self.sp_wall_a.setRange(500.0, SCIANA_MM_MAX)
        self.sp_wall_a.setDecimals(1)
        self.sp_wall_a.setSuffix(" mm")

        self.sp_wall_b = QDoubleSpinBox()
        self.sp_wall_b.setRange(500.0, SCIANA_MM_MAX)
        self.sp_wall_b.setDecimals(1)
        self.sp_wall_b.setSuffix(" mm")

        self.sp_wall_c = QDoubleSpinBox()
        self.sp_wall_c.setRange(500.0, SCIANA_MM_MAX)
        self.sp_wall_c.setDecimals(1)
        self.sp_wall_c.setSuffix(" mm")

        self.sp_room_height = QDoubleSpinBox()
        self.sp_room_height.setRange(1800.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_room_height.setDecimals(1)
        self.sp_room_height.setSuffix(" mm")

        self.sp_base_depth = QDoubleSpinBox()
        self.sp_base_depth.setRange(300.0, SCIANA_DEPTH_MM_MAX)
        self.sp_base_depth.setDecimals(1)
        self.sp_base_depth.setSuffix(" mm")

        self.sp_base_plinth = QDoubleSpinBox()
        self.sp_base_plinth.setRange(0.0, SCIANA_DEPTH_MM_MAX)
        self.sp_base_plinth.setDecimals(1)
        self.sp_base_plinth.setSuffix(" mm")

        self.sp_upper_clearance = QDoubleSpinBox()
        self.sp_upper_clearance.setRange(0.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_upper_clearance.setDecimals(1)
        self.sp_upper_clearance.setSuffix(" mm")

        self.sp_top_offset = QDoubleSpinBox()
        self.sp_top_offset.setRange(0.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_top_offset.setDecimals(1)
        self.sp_top_offset.setSuffix(" mm")

        self.sp_bottom_offset = QDoubleSpinBox()
        self.sp_bottom_offset.setRange(0.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_bottom_offset.setDecimals(1)
        self.sp_bottom_offset.setSuffix(" mm")

        self.sp_base_offset_left = QDoubleSpinBox()
        self.sp_base_offset_left.setRange(0.0, SCIANA_MM_MAX)
        self.sp_base_offset_left.setDecimals(1)
        self.sp_base_offset_left.setSuffix(" mm")

        self.sp_base_offset_right = QDoubleSpinBox()
        self.sp_base_offset_right.setRange(0.0, SCIANA_MM_MAX)
        self.sp_base_offset_right.setDecimals(1)
        self.sp_base_offset_right.setSuffix(" mm")

        self.sp_upper_offset_left = QDoubleSpinBox()
        self.sp_upper_offset_left.setRange(0.0, SCIANA_MM_MAX)
        self.sp_upper_offset_left.setDecimals(1)
        self.sp_upper_offset_left.setSuffix(" mm")

        self.sp_upper_offset_right = QDoubleSpinBox()
        self.sp_upper_offset_right.setRange(0.0, SCIANA_MM_MAX)
        self.sp_upper_offset_right.setDecimals(1)
        self.sp_upper_offset_right.setSuffix(" mm")

        self.sp_island_w = QDoubleSpinBox()
        self.sp_island_w.setRange(400.0, SCIANA_MM_MAX)
        self.sp_island_w.setDecimals(1)
        self.sp_island_w.setSuffix(" mm")

        self.sp_island_d = QDoubleSpinBox()
        self.sp_island_d.setRange(300.0, SCIANA_DEPTH_MM_MAX)
        self.sp_island_d.setDecimals(1)
        self.sp_island_d.setSuffix(" mm")

        self.sp_island_x = QDoubleSpinBox()
        self.sp_island_x.setRange(0.0, SCIANA_MM_MAX)
        self.sp_island_x.setDecimals(1)
        self.sp_island_x.setSuffix(" mm")

        self.sp_island_y = QDoubleSpinBox()
        self.sp_island_y.setRange(0.0, SCIANA_MM_MAX)
        self.sp_island_y.setDecimals(1)
        self.sp_island_y.setSuffix(" mm")

        dims_form.addRow("Sciana A", self.sp_wall_a)
        dims_form.addRow("Sciana B", self.sp_wall_b)
        dims_form.addRow("Sciana C", self.sp_wall_c)
        dims_form.addRow("Wysokosc pomieszczenia", self.sp_room_height)
        dims_form.addRow("Glebokosc zabudowy", self.sp_base_depth)
        dims_form.addRow("Dolny cokol", self.sp_base_plinth)
        dims_form.addRow("Gorny odstep", self.sp_upper_clearance)
        dims_form.addRow("Gorny offset", self.sp_top_offset)
        dims_form.addRow("Dolny offset", self.sp_bottom_offset)
        dims_form.addRow("Dolne od lewej", self.sp_base_offset_left)
        dims_form.addRow("Dolne od prawej", self.sp_base_offset_right)
        dims_form.addRow("Gorne od lewej", self.sp_upper_offset_left)
        dims_form.addRow("Gorne od prawej", self.sp_upper_offset_right)
        dims_form.addRow("Szerokosc wyspy", self.sp_island_w)
        dims_form.addRow("Glebokosc wyspy", self.sp_island_d)
        dims_form.addRow("Wyspa X", self.sp_island_x)
        dims_form.addRow("Wyspa Y", self.sp_island_y)

        self.blk_dims.content_layout().addWidget(dims_body)
        layout.addWidget(self.blk_dims)

        self.btn_save = QPushButton("Zapisz")
        self.btn_load = QPushButton("Wczytaj")
        self.btn_overwrite = QPushButton("Nadpisz")
        self.btn_back_to_order = QPushButton("Wroc: Zamowienie")
        self.btn_go_to_komplet = QPushButton("Dalej: Komplet")
        self.btn_go_to_komplet.setMinimumHeight(32)
        set_ui_variant(self.btn_save, "primary")
        set_ui_variant(self.btn_load, "ghost")
        set_ui_variant(self.btn_overwrite, "ghost")
        set_ui_variant(self.btn_back_to_order, "ghost")
        set_ui_variant(self.btn_go_to_komplet, "success")
        for button in (
            self.btn_save,
            self.btn_load,
            self.btn_overwrite,
            self.btn_back_to_order,
            self.btn_go_to_komplet,
        ):
            button.setMinimumHeight(32)

        self.lab_store_status = QLabel("")

        self.lab_store_status.setWordWrap(True)

        self.lab_store_status.setStyleSheet(f"color:{get_muted_color()};")

        self.blk_store = CollapsibleBlock("Zapis i przejscie", panel)
        store_body = QWidget(self.blk_store)
        store_panel_layout = QVBoxLayout(store_body)
        store_panel_layout.setContentsMargins(0, 0, 0, 0)
        store_panel_layout.setSpacing(6)

        store_btns = QHBoxLayout()
        store_btns.setContentsMargins(0, 0, 0, 0)
        store_btns.setSpacing(6)
        store_btns.addWidget(self.btn_save)
        store_btns.addWidget(self.btn_load)
        store_btns.addWidget(self.btn_overwrite)
        store_btns.addStretch(1)
        store_panel_layout.addLayout(store_btns)
        nav_btns = QHBoxLayout()
        nav_btns.setContentsMargins(0, 0, 0, 0)
        nav_btns.setSpacing(6)
        nav_btns.addWidget(self.btn_back_to_order)
        nav_btns.addWidget(self.btn_go_to_komplet)
        store_panel_layout.addLayout(nav_btns)
        store_panel_layout.addWidget(self.lab_store_status)
        self.blk_store.content_layout().addWidget(store_body)
        layout.addWidget(self.blk_store)

        self.blk_obstacles = CollapsibleBlock("Przeszkody", panel)
        obstacles_body = QWidget(self.blk_obstacles)
        obs_layout = QVBoxLayout(obstacles_body)
        obs_form = QFormLayout()
        self._obstacle_form = obs_form

        self.cb_obstacle_kind = QComboBox()
        for key, label in OBSTACLE_KIND_ITEMS:
            self.cb_obstacle_kind.addItem(label, key)

        self.cb_obstacle_side = QComboBox()
        for key, label in WALL_SIDE_ITEMS:
            self.cb_obstacle_side.addItem(label, key)

        self.ed_obstacle_name = QLineEdit()

        self.cb_obstacle_opening = QComboBox()
        for key, label in OPENING_DIRECTION_ITEMS:
            self.cb_obstacle_opening.addItem(label, key)

        self.sp_obstacle_x = QDoubleSpinBox()
        self.sp_obstacle_x.setRange(0.0, SCIANA_MM_MAX)
        self.sp_obstacle_x.setDecimals(1)
        self.sp_obstacle_x.setSuffix(" mm")

        self.sp_obstacle_bottom = QDoubleSpinBox()
        self.sp_obstacle_bottom.setRange(0.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_obstacle_bottom.setDecimals(1)
        self.sp_obstacle_bottom.setSuffix(" mm")

        self.sp_obstacle_w = QDoubleSpinBox()
        self.sp_obstacle_w.setRange(50.0, SCIANA_MM_MAX)
        self.sp_obstacle_w.setDecimals(1)
        self.sp_obstacle_w.setSuffix(" mm")

        self.sp_obstacle_h = QDoubleSpinBox()
        self.sp_obstacle_h.setRange(50.0, SCIANA_HEIGHT_MM_MAX)
        self.sp_obstacle_h.setDecimals(1)
        self.sp_obstacle_h.setSuffix(" mm")

        self.sp_obstacle_d = QDoubleSpinBox()
        self.sp_obstacle_d.setRange(10.0, SCIANA_DEPTH_MM_MAX)
        self.sp_obstacle_d.setDecimals(1)
        self.sp_obstacle_d.setSuffix(" mm")

        obs_form.addRow("Typ", self.cb_obstacle_kind)
        obs_form.addRow("Sciana", self.cb_obstacle_side)
        obs_form.addRow("Nazwa", self.ed_obstacle_name)
        obs_form.addRow("Kierunek otwierania", self.cb_obstacle_opening)
        obs_form.addRow("Offset", self.sp_obstacle_x)
        obs_form.addRow("Od podlogi", self.sp_obstacle_bottom)
        obs_form.addRow("Szerokosc", self.sp_obstacle_w)
        obs_form.addRow("Wysokosc", self.sp_obstacle_h)
        obs_form.addRow("Glebokosc", self.sp_obstacle_d)
        self._ensure_form_label_widget(obs_form, self.sp_obstacle_x, "Offset")
        self._ensure_form_label_widget(obs_form, self.sp_obstacle_bottom, "Od podlogi")
        self._ensure_form_label_widget(obs_form, self.sp_obstacle_w, "Szerokosc")
        self._ensure_form_label_widget(obs_form, self.sp_obstacle_h, "Wysokosc")
        self._ensure_form_label_widget(obs_form, self.sp_obstacle_d, "Glebokosc")
        self._ensure_form_label_widget(obs_form, self.cb_obstacle_opening, "Kierunek otwierania")
        obs_layout.addLayout(obs_form)

        obs_btns = QHBoxLayout()
        self.btn_add_obstacle = QPushButton("Dodaj przeszkode")
        self.btn_apply_obstacle = QPushButton("Zastosuj do zaznaczonej")
        self.btn_remove_obstacle = QPushButton("Usun zaznaczona")
        set_ui_variant(self.btn_add_obstacle, "primary")
        set_ui_variant(self.btn_apply_obstacle, "success")
        set_ui_variant(self.btn_remove_obstacle, "danger")
        for button in (self.btn_add_obstacle, self.btn_apply_obstacle, self.btn_remove_obstacle):
            button.setMinimumHeight(30)
        obs_btns.addWidget(self.btn_add_obstacle)
        obs_btns.addWidget(self.btn_apply_obstacle)
        obs_btns.addWidget(self.btn_remove_obstacle)
        obs_layout.addLayout(obs_btns)

        self.tbl_obstacles = QTableWidget(0, 4, obstacles_body)
        self.tbl_obstacles.setHorizontalHeaderLabels(["Typ", "Sciana", "Nazwa", "Wymiary"])
        self.tbl_obstacles.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_obstacles.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_obstacles.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_obstacles.verticalHeader().setVisible(False)
        self.tbl_obstacles.horizontalHeader().setStretchLastSection(True)
        obs_layout.addWidget(self.tbl_obstacles)
        self.blk_obstacles.content_layout().addWidget(obstacles_body)
        layout.addWidget(self.blk_obstacles)

        self.blk_photos = CollapsibleBlock("Zdjecia miejsca", panel)
        photos_body = QWidget(self.blk_photos)
        photos_layout = QVBoxLayout(photos_body)
        photos_form = QFormLayout()

        self.ed_photo_path = QLineEdit()
        self.ed_photo_caption = QLineEdit()
        photos_form.addRow("Sciezka", self.ed_photo_path)
        photos_form.addRow("Opis", self.ed_photo_caption)
        photos_layout.addLayout(photos_form)

        photo_btns = QHBoxLayout()
        self.btn_add_photo = QPushButton("Dodaj sciezke")
        self.btn_remove_photo = QPushButton("Usun zaznaczone")
        set_ui_variant(self.btn_add_photo, "primary")
        set_ui_variant(self.btn_remove_photo, "danger")
        self.btn_add_photo.setMinimumHeight(30)
        self.btn_remove_photo.setMinimumHeight(30)
        photo_btns.addWidget(self.btn_add_photo)
        photo_btns.addWidget(self.btn_remove_photo)
        photos_layout.addLayout(photo_btns)

        self.tbl_photos = QTableWidget(0, 2, photos_body)
        self.tbl_photos.setHorizontalHeaderLabels(["Sciezka", "Opis"])
        self.tbl_photos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_photos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_photos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_photos.verticalHeader().setVisible(False)
        self.tbl_photos.horizontalHeader().setStretchLastSection(True)
        photos_layout.addWidget(self.tbl_photos)
        self.blk_photos.content_layout().addWidget(photos_body)
        layout.addWidget(self.blk_photos)

        self.blk_measurements = CollapsibleBlock("Pomiary (MVP)", panel)
        measurements_body = QWidget(self.blk_measurements)
        measurements_layout = QVBoxLayout(measurements_body)
        measurements_form = QFormLayout()

        self.ed_quote_reference = QLineEdit()
        self.ed_quote_reference.setPlaceholderText("Powiazanie z wycena, np. WSTEPNA-001 / Szafa 1")
        measurements_form.addRow("Ref. wyceny", self.ed_quote_reference)

        self.ed_measure_name = QLineEdit()
        self.ed_measure_name.setPlaceholderText("np. sciana A netto")
        measurements_form.addRow("Nazwa", self.ed_measure_name)

        self.cb_measure_kind = QComboBox()
        for item_key, item_label in MEASUREMENT_KIND_ITEMS:
            self.cb_measure_kind.addItem(item_label, item_key)
        measurements_form.addRow("Typ", self.cb_measure_kind)

        self.sp_measure_value = QDoubleSpinBox()
        self.sp_measure_value.setRange(0.0, SCIANA_MM_MAX)
        self.sp_measure_value.setDecimals(1)
        self.sp_measure_value.setSuffix(" mm")
        measurements_form.addRow("Wartosc", self.sp_measure_value)

        self.ed_measure_photo_path = QLineEdit()
        self.ed_measure_photo_path.setPlaceholderText("Opcjonalnie: sciezka do zdjecia")
        measurements_form.addRow("Zdjecie", self.ed_measure_photo_path)

        self.ed_measure_note = QLineEdit()
        self.ed_measure_note.setPlaceholderText("Uwagi")
        measurements_form.addRow("Notatka", self.ed_measure_note)

        measurements_layout.addLayout(measurements_form)

        measurement_btns = QHBoxLayout()
        self.btn_add_measurement = QPushButton("Dodaj pomiar")
        self.btn_remove_measurement = QPushButton("Usun zaznaczony")
        self.btn_measure_from_photo = QPushButton("Pomiar ze zdjecia")
        set_ui_variant(self.btn_add_measurement, "primary")
        set_ui_variant(self.btn_remove_measurement, "danger")
        set_ui_variant(self.btn_measure_from_photo, "success")
        for button in (self.btn_add_measurement, self.btn_remove_measurement, self.btn_measure_from_photo):
            button.setMinimumHeight(30)
        measurement_btns.addWidget(self.btn_add_measurement)
        measurement_btns.addWidget(self.btn_remove_measurement)
        measurement_btns.addWidget(self.btn_measure_from_photo)
        measurements_layout.addLayout(measurement_btns)

        self.tbl_measurements = QTableWidget(0, 5, measurements_body)
        self.tbl_measurements.setHorizontalHeaderLabels(["Nazwa", "Typ", "Wartosc", "Zdjecie", "Notatka"])
        self.tbl_measurements.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_measurements.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_measurements.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_measurements.verticalHeader().setVisible(False)
        self.tbl_measurements.horizontalHeader().setStretchLastSection(True)
        measurements_layout.addWidget(self.tbl_measurements)
        self.blk_measurements.content_layout().addWidget(measurements_body)
        layout.addWidget(self.blk_measurements)

        self.ed_notes = QTextEdit()
        self.ed_notes.setPlaceholderText("Uwagi o scianie, oknach, drzwiach, rurach, zdjeciach i montazu...")
        self.blk_notes = CollapsibleBlock("Notatki", panel)
        notes_body = QWidget(self.blk_notes)
        notes_layout = QVBoxLayout(notes_body)
        notes_layout.addWidget(self.ed_notes)
        self.blk_notes.content_layout().addWidget(notes_body)
        layout.addWidget(self.blk_notes)

        layout.addStretch(1)

        self.ed_name.textChanged.connect(self._on_any_change)
        self.cb_client.currentIndexChanged.connect(self._on_client_selection_changed)
        self.cb_order.currentIndexChanged.connect(self._on_order_selection_changed)
        self.cb_worker.currentIndexChanged.connect(self._on_any_change)
        self.cb_layout_type.currentIndexChanged.connect(self._on_any_change)
        self.cb_front_wall.currentIndexChanged.connect(self._on_any_change)
        self.chk_island.toggled.connect(self._on_any_change)
        self.sp_wall_a.valueChanged.connect(self._on_any_change)
        self.sp_wall_b.valueChanged.connect(self._on_any_change)
        self.sp_wall_c.valueChanged.connect(self._on_any_change)
        self.sp_room_height.valueChanged.connect(self._on_any_change)
        self.sp_base_depth.valueChanged.connect(self._on_any_change)
        self.sp_base_plinth.valueChanged.connect(self._on_any_change)
        self.sp_upper_clearance.valueChanged.connect(self._on_any_change)
        self.sp_top_offset.valueChanged.connect(self._on_any_change)
        self.sp_bottom_offset.valueChanged.connect(self._on_any_change)
        self.sp_base_offset_left.valueChanged.connect(self._on_any_change)
        self.sp_base_offset_right.valueChanged.connect(self._on_any_change)
        self.sp_upper_offset_left.valueChanged.connect(self._on_any_change)
        self.sp_upper_offset_right.valueChanged.connect(self._on_any_change)
        self.sp_island_w.valueChanged.connect(self._on_any_change)
        self.sp_island_d.valueChanged.connect(self._on_any_change)
        self.sp_island_x.valueChanged.connect(self._on_any_change)
        self.sp_island_y.valueChanged.connect(self._on_any_change)
        self.ed_quote_reference.textChanged.connect(self._on_any_change)
        self.ed_notes.textChanged.connect(self._on_any_change)

        self.btn_add_obstacle.clicked.connect(self._on_add_obstacle)
        self.btn_apply_obstacle.clicked.connect(self._on_apply_obstacle)
        self.btn_remove_obstacle.clicked.connect(self._on_remove_obstacle)
        self.btn_add_photo.clicked.connect(self._on_add_photo)
        self.btn_remove_photo.clicked.connect(self._on_remove_photo)
        self.btn_add_measurement.clicked.connect(self._on_add_measurement)
        self.btn_remove_measurement.clicked.connect(self._on_remove_measurement)
        self.btn_measure_from_photo.clicked.connect(self._on_measurement_from_photo)
        self.btn_save.clicked.connect(self._on_save_new)
        self.btn_load.clicked.connect(self._on_load)
        self.btn_overwrite.clicked.connect(self._on_overwrite)
        self.btn_back_to_order.clicked.connect(self._on_back_to_order)
        self.btn_go_to_komplet.clicked.connect(self._on_go_to_komplet)
        self.tbl_obstacles.itemSelectionChanged.connect(self._on_obstacle_selection_changed)
        self.cb_obstacle_kind.currentIndexChanged.connect(self._on_selected_obstacle_editor_changed)
        self.cb_obstacle_opening.currentIndexChanged.connect(self._on_selected_obstacle_editor_changed)
        self.cb_obstacle_side.currentIndexChanged.connect(self._on_selected_obstacle_editor_changed)
        self.ed_obstacle_name.textChanged.connect(self._on_selected_obstacle_editor_changed)
        self.sp_obstacle_x.valueChanged.connect(self._on_selected_obstacle_editor_changed)
        self.sp_obstacle_bottom.valueChanged.connect(self._on_selected_obstacle_editor_changed)
        self.sp_obstacle_w.valueChanged.connect(self._on_selected_obstacle_editor_changed)
        self.sp_obstacle_h.valueChanged.connect(self._on_selected_obstacle_editor_changed)
        self.sp_obstacle_d.valueChanged.connect(self._on_selected_obstacle_editor_changed)
        self.tbl_measurements.itemSelectionChanged.connect(self._on_measurement_selection_changed)

        return panel

    def _wrap_row_widget(self, parent: QWidget, layout: QHBoxLayout) -> QWidget:
        holder = QWidget(parent)
        holder.setLayout(layout)
        return holder

    def _build_center_zone(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("sciana_zone_center")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # internal zone label removed (Step 23)

        self.quick_actions_bar = QFrame(panel)
        self.quick_actions_bar.setObjectName("sciana_layout_quick_bar")
        mark_ui_card(self.quick_actions_bar, elevated=False)

        # Two-row layout: file/session row | navigation/tools row
        quick_vbox = QVBoxLayout(self.quick_actions_bar)
        quick_vbox.setContentsMargins(10, 8, 10, 8)
        quick_vbox.setSpacing(6)

        # --- Row 1: file / session actions ---
        quick_row1 = QHBoxLayout()
        quick_row1.setSpacing(8)

        self.btn_q_save = QPushButton("Zapisz")
        self.btn_q_save.clicked.connect(self._shortcut_save_wall)
        set_ui_variant(self.btn_q_save, "primary")

        self.btn_q_overwrite = QPushButton("Nadpisz")
        self.btn_q_overwrite.clicked.connect(self._on_overwrite)
        set_ui_variant(self.btn_q_overwrite, "ghost")

        self.btn_q_load = QPushButton("Wczytaj")
        self.btn_q_load.clicked.connect(self._on_load)
        set_ui_variant(self.btn_q_load, "ghost")

        self.btn_q_new = QPushButton("Nowa sciana")
        self.btn_q_new.clicked.connect(self.start_new_wall)
        set_ui_variant(self.btn_q_new, "ghost")

        for btn, min_w, max_w in (
            (self.btn_q_save, 96, 124),
            (self.btn_q_overwrite, 102, 132),
            (self.btn_q_load, 96, 124),
            (self.btn_q_new, 110, 144),
        ):
            btn.setMinimumWidth(min_w)
            btn.setMaximumWidth(max_w)
            btn.setMinimumHeight(32)
            btn.setMaximumHeight(32)

        quick_row1.addWidget(self.btn_q_save)
        quick_row1.addWidget(self.btn_q_overwrite)
        quick_row1.addWidget(self.btn_q_load)
        quick_row1.addWidget(self.btn_q_new)
        quick_row1.addStretch(1)
        quick_vbox.addLayout(quick_row1)

        # --- Row 2: navigation / tools ---
        quick_row2 = QHBoxLayout()
        quick_row2.setSpacing(8)

        self.btn_q_focus_name = QPushButton("Focusuj nazwe")
        self.btn_q_focus_name.clicked.connect(self._shortcut_focus_wall_name)
        set_ui_variant(self.btn_q_focus_name, "ghost")

        self.btn_q_order = QPushButton("Zamowienie")
        self.btn_q_order.clicked.connect(self._on_back_to_order)
        set_ui_variant(self.btn_q_order, "ghost")

        self.btn_q_next = QPushButton("Dalej →")
        self.btn_q_next.clicked.connect(self._on_go_to_komplet)
        set_ui_variant(self.btn_q_next, "success")

        self.btn_q_shortcuts = QPushButton("Skroty")
        self.btn_q_shortcuts.clicked.connect(self._open_shortcuts_dialog)
        set_ui_variant(self.btn_q_shortcuts, "ghost")

        # keep btn_q_more as an object (referenced elsewhere) but keep it hidden
        self.btn_q_more = QToolButton(self.quick_actions_bar)
        self.btn_q_more.setText("Wiecej")
        self.btn_q_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        set_ui_variant(self.btn_q_more, "ghost")
        self._quick_more_menu = QMenu(self.btn_q_more)
        self._quick_more_menu.addAction("Nadpisz", self._on_overwrite)
        self._quick_more_menu.addAction("Wczytaj", self._on_load)
        self._quick_more_menu.addAction("Nowa sciana", self.start_new_wall)
        self._quick_more_menu.addAction("Nazwa", self._shortcut_focus_wall_name)
        self._quick_more_menu.addAction("Zamowienie", self._on_back_to_order)
        self._quick_more_menu.addAction("Skroty", self._open_shortcuts_dialog)
        self.btn_q_more.setMenu(self._quick_more_menu)
        self.btn_q_more.hide()

        for btn, min_w, max_w in (
            (self.btn_q_focus_name, 116, 150),
            (self.btn_q_order, 110, 144),
            (self.btn_q_next, 90, 116),
            (self.btn_q_shortcuts, 88, 114),
        ):
            btn.setMinimumWidth(min_w)
            btn.setMaximumWidth(max_w)
            btn.setMinimumHeight(32)
            btn.setMaximumHeight(32)

        quick_row2.addWidget(self.btn_q_focus_name)
        quick_row2.addWidget(self.btn_q_order)
        quick_row2.addWidget(self.btn_q_next)
        quick_row2.addWidget(self.btn_q_shortcuts)
        quick_row2.addStretch(1)
        quick_vbox.addLayout(quick_row2)

        layout.addWidget(self.quick_actions_bar, 0)

        grp_front = QGroupBox("Widok z przodu", panel)
        grp_front.setObjectName("sciana_view_card")
        mark_ui_card(grp_front, elevated=False)
        grp_front_layout = QVBoxLayout(grp_front)
        grp_front_layout.setContentsMargins(8, 12, 8, 8)
        self.preview = WallPreviewView(grp_front, view_mode="front")
        self.preview.setMinimumHeight(420)
        self.preview.sig_obstacle_selected.connect(self._on_preview_obstacle_selected)
        self.preview.sig_obstacle_dragged.connect(self._on_preview_obstacle_dragged)
        self.preview.sig_obstacle_dimension_changed.connect(self._on_preview_obstacle_dimension_changed)
        self.preview.sig_view_resized.connect(self._on_preview_resized)
        grp_front_layout.addWidget(self.preview, 1)
        layout.addWidget(grp_front, 3)

        grp_top = QGroupBox("Widok z gory", panel)
        grp_top.setObjectName("sciana_top_card")
        mark_ui_card(grp_top, elevated=False)
        grp_top_layout = QVBoxLayout(grp_top)
        grp_top_layout.setContentsMargins(8, 12, 8, 8)
        self.preview_top = WallPreviewView(grp_top, view_mode="top")
        self.preview_top.setMinimumHeight(220)
        self.preview_top.sig_obstacle_selected.connect(self._on_preview_obstacle_selected)
        self.preview_top.sig_obstacle_dragged.connect(self._on_preview_obstacle_dragged)
        self.preview_top.sig_obstacle_dimension_changed.connect(self._on_preview_obstacle_dimension_changed)
        self.preview_top.sig_view_resized.connect(self._on_preview_resized)
        grp_top_layout.addWidget(self.preview_top, 1)

        grp_front.setMinimumHeight(360)
        grp_top.setMinimumHeight(220)

        self.center_views_splitter = QSplitter(Qt.Orientation.Vertical, panel)
        self.center_views_splitter.setChildrenCollapsible(False)
        self.center_views_splitter.addWidget(grp_front)
        self.center_views_splitter.addWidget(grp_top)
        self.center_views_splitter.setStretchFactor(0, 4)
        self.center_views_splitter.setStretchFactor(1, 2)
        self.center_views_splitter.setSizes([620, 280])

        layout.addWidget(self.center_views_splitter, 1)
        return panel

    def _build_right_zone(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("sciana_zone_right")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # --- blk_summary: wall state + room info combined (open by default) ---
        # blk_room was a separate block before Step 27; merged here to reduce density.
        self.blk_summary = CollapsibleBlock("Podsumowanie sciany", panel)
        summary_body = QWidget(self.blk_summary)
        summary_vbox = QVBoxLayout(summary_body)
        summary_vbox.setContentsMargins(0, 0, 0, 0)
        summary_vbox.setSpacing(6)

        self.lab_summary = QLabel("-")
        self.lab_summary.setObjectName("sciana_side_note")
        self.lab_summary.setWordWrap(True)
        summary_vbox.addWidget(self.lab_summary)

        _room_divider = QFrame(summary_body)
        _room_divider.setFrameShape(QFrame.Shape.HLine)
        _room_divider.setFrameShadow(QFrame.Shadow.Plain)
        _room_divider.setStyleSheet("color: #e0d8cc; margin: 2px 0;")
        summary_vbox.addWidget(_room_divider)

        _room_header = QLabel("Pomieszczenie", summary_body)
        _room_header.setStyleSheet("font-size: 11px; font-weight: 600; color: #6b7280;")
        summary_vbox.addWidget(_room_header)

        self.lab_room_info = QLabel("-")
        self.lab_room_info.setObjectName("sciana_side_note")
        self.lab_room_info.setWordWrap(True)
        summary_vbox.addWidget(self.lab_room_info)

        self.blk_summary.content_layout().addWidget(summary_body)
        layout.addWidget(self.blk_summary)
        self.blk_room = None  # merged into blk_summary

        # --- blk_collisions: warnings (open by default) ---
        self.blk_collisions = CollapsibleBlock("Kolizje i ostrzezenia", panel)
        coll_body = QWidget(self.blk_collisions)
        coll_vbox = QVBoxLayout(coll_body)
        coll_vbox.setContentsMargins(4, 4, 4, 4)
        coll_vbox.setSpacing(3)
        self.lab_collisions = QLabel("-")
        self.lab_collisions.setObjectName("sciana_side_note")
        self.lab_collisions.setWordWrap(True)
        self.lab_collisions.setStyleSheet("font-size:11px;")
        coll_vbox.addWidget(self.lab_collisions)
        self.blk_collisions.content_layout().addWidget(coll_body)
        layout.addWidget(self.blk_collisions)

        # --- blk_obstacle_details: detail view (collapsed by default) ---
        self.blk_obstacle_details = CollapsibleBlock("Detale przeszkod", panel)
        obstacle_details_body = QWidget(self.blk_obstacle_details)
        obstacle_details_layout = QVBoxLayout(obstacle_details_body)
        self.lab_obstacle_details = QLabel("-")
        self.lab_obstacle_details.setObjectName("sciana_side_note")
        self.lab_obstacle_details.setWordWrap(True)
        obstacle_details_layout.addWidget(self.lab_obstacle_details)
        self.blk_obstacle_details.content_layout().addWidget(obstacle_details_body)
        layout.addWidget(self.blk_obstacle_details)

        # --- flat hint note (was blk_suggestions CollapsibleBlock — static text only) ---
        # Demoted to a flat muted note to reduce same-weight block stacking.
        _hint_frame = QFrame(panel)
        _hint_frame.setFrameShape(QFrame.Shape.NoFrame)
        _hint_vbox = QVBoxLayout(_hint_frame)
        _hint_vbox.setContentsMargins(8, 6, 8, 4)
        _hint_vbox.setSpacing(3)
        _hint_header = QLabel("Dalsze parametry", _hint_frame)
        _hint_header.setStyleSheet("font-size: 11px; font-weight: 600; color: #9ca3af;")
        _hint_vbox.addWidget(_hint_header)
        self.lab_suggestions = QLabel(
            "W kolejnych krokach warto dodac:\n"
            "- punkty elektryczne i wod-kan\n"
            "- parapet i wysokosci okien\n"
            "- wentylacje, grzejniki i listwy\n"
            "- montaz AGD stalego\n"
            "- powiazanie ze zdjeciami i pomiarami z miejsca"
        )
        self.lab_suggestions.setObjectName("sciana_side_note")
        self.lab_suggestions.setWordWrap(True)
        self.lab_suggestions.setStyleSheet("font-size: 11px; color: #9ca3af;")
        _hint_vbox.addWidget(self.lab_suggestions)
        layout.addWidget(_hint_frame)
        self.blk_suggestions = None  # no longer a CollapsibleBlock — replaced with flat hint

        layout.addStretch(1)
        return panel

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._startup_visibility_applied_once:
            self._apply_block_startup_visibility()
            self._startup_visibility_applied_once = True
        self._push_wall_to_ui()
        self._refresh_all()
        self._ensure_center_views_splitter_visibility()

    def _selected_client_name(self) -> str:
        return str(self.cb_client.currentData() or "").strip()

    def _ensure_center_views_splitter_visibility(self) -> None:
        if not hasattr(self, "center_views_splitter"):
            return

        available_height = int(self.center_views_splitter.height() or self.center_views_splitter.size().height() or 0)
        if available_height <= 0:
            self.center_views_splitter.setSizes([620, 280])
            return

        top_height = max(220, int(available_height * 0.28))
        front_height = max(360, available_height - top_height)

        if front_height + top_height > available_height:
            overflow = (front_height + top_height) - available_height
            front_height = max(300, front_height - overflow)

        self.center_views_splitter.setSizes([front_height, top_height])

    def _selected_order_name(self) -> str:
        return str(self.cb_order.currentData() or "").strip()

    def _selected_worker_name(self) -> str:
        return str(self.cb_worker.currentData() or "").strip()

    def _wall_width_for_side(self, wall: WallLayoutDef, side: str) -> float:
        side_key = str(side or "A").strip().upper()
        if side_key == "B":
            return float(getattr(wall, "wall_b_width_mm", 2600.0) or 2600.0)
        if side_key == "C":
            return float(getattr(wall, "wall_c_width_mm", 2600.0) or 2600.0)
        return float(getattr(wall, "wall_a_width_mm", 4000.0) or 4000.0)

    def _reload_client_choices(self, current_client: str = "") -> None:
        current_client = str(current_client or "").strip()
        client_names = [str(name or "").strip() for name in self._client_store.list_names() if str(name or "").strip()]

        self.cb_client.blockSignals(True)
        self.cb_client.clear()
        self.cb_client.addItem("[brak]", "")
        for client_name in client_names:
            self.cb_client.addItem(client_name, client_name)
        if current_client and self.cb_client.findData(current_client) < 0:
            self.cb_client.addItem(current_client, current_client)
        idx = self.cb_client.findData(current_client)
        if idx < 0:
            idx = 0
        self.cb_client.setCurrentIndex(idx)
        self.cb_client.blockSignals(False)

    def _reload_order_choices(self, selected_client: str = "", current_order: str = "") -> None:
        selected_client = str(selected_client or "").strip()
        current_order = str(current_order or "").strip()
        orders = self._order_store.list_orders()
        order_codes: list[str] = []

        for order in orders:
            code = str(getattr(order, "code", "") or "").strip()
            if not code:
                continue
            order_client = str(getattr(order, "client_name", "") or "").strip()
            if selected_client and order_client != selected_client:
                continue
            order_codes.append(code)

        self.cb_order.blockSignals(True)
        self.cb_order.clear()
        self.cb_order.addItem("[brak]", "")
        for code in order_codes:
            self.cb_order.addItem(code, code)
        if current_order and self.cb_order.findData(current_order) < 0:
            self.cb_order.addItem(current_order, current_order)
        idx = self.cb_order.findData(current_order)
        if idx < 0:
            idx = 0
        self.cb_order.setCurrentIndex(idx)
        self.cb_order.blockSignals(False)
        self._refresh_order_id_field()

    def _refresh_order_id_field(self) -> None:
        order_name = self._selected_order_name()
        order_id = ""
        if order_name:
            order_def = self._order_store.get(order_name)
            order_id = str(getattr(order_def, "order_id", "") or "").strip() if order_def is not None else ""
        if not order_id:
            order_id = str(self._order_id_context or "").strip()
        self.ed_order_id.setText(order_id)

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

    def _on_client_selection_changed(self) -> None:
        current_order = self._selected_order_name()
        selected_client = self._selected_client_name()
        preserved_order = ""
        worker_name = ""
        if current_order:
            order_def = self._order_store.get(current_order)
            order_client = str(getattr(order_def, "client_name", "") or "").strip() if order_def is not None else ""
            if not selected_client or order_client == selected_client:
                preserved_order = current_order
                worker_name = str(getattr(order_def, "worker_name", "") or "").strip() if order_def is not None else ""
        self._reload_order_choices(selected_client=selected_client, current_order=preserved_order)
        self._reload_worker_choices(current_worker=worker_name)
        self._on_any_change()

    def _on_order_selection_changed(self) -> None:
        current_order = self._selected_order_name()
        worker_name = ""
        if current_order:
            order_def = self._order_store.get(current_order)
            if order_def is not None:
                worker_name = str(getattr(order_def, "worker_name", "") or "").strip()
        self._reload_worker_choices(current_worker=worker_name or self._selected_worker_name())
        self._refresh_order_id_field()
        self._on_any_change()

    def _selected_order_details(self) -> tuple[str, str]:
        order_name = str(getattr(self._wall, "order_name", "") or "").strip()
        if not order_name:
            return "", ""
        order_def = self._order_store.get(order_name)
        if order_def is None:
            return "", ""
        status = str(getattr(order_def, "status", "") or "").strip()
        site_address = str(getattr(order_def, "site_address", "") or "").strip()
        return status, site_address

    def _push_wall_to_ui(self) -> None:
        self._is_pushing_ui = True
        try:
            self.ed_name.setText(str(getattr(self._wall, "name", "Sciana 1") or "Sciana 1"))
            wall_client = str(getattr(self._wall, "client_name", "") or "").strip()
            wall_order = str(getattr(self._wall, "order_name", "") or "").strip()
            wall_worker = str(getattr(self._wall, "worker_name", "") or "").strip()
            self._reload_client_choices(current_client=wall_client)
            self._reload_order_choices(selected_client=wall_client, current_order=wall_order)
            self._reload_worker_choices(current_worker=wall_worker)
            self._refresh_order_id_field()

            idx = self.cb_layout_type.findData(str(getattr(self._wall, "layout_type", "line") or "line"))
            if idx < 0:
                idx = 0
            self.cb_layout_type.setCurrentIndex(idx)

            front_idx = self.cb_front_wall.findData(str(getattr(self._wall, "front_view_wall_side", "A") or "A"))
            if front_idx < 0:
                front_idx = 0
            self.cb_front_wall.setCurrentIndex(front_idx)

            self.chk_island.setChecked(bool(getattr(self._wall, "has_island", False)))
            self.sp_wall_a.setValue(float(getattr(self._wall, "wall_a_width_mm", 4000.0) or 4000.0))
            self.sp_wall_b.setValue(float(getattr(self._wall, "wall_b_width_mm", 2600.0) or 2600.0))
            self.sp_wall_c.setValue(float(getattr(self._wall, "wall_c_width_mm", 2600.0) or 2600.0))
            self.sp_room_height.setValue(float(getattr(self._wall, "room_height_mm", 2600.0) or 2600.0))
            self.sp_base_depth.setValue(float(getattr(self._wall, "base_depth_mm", 600.0) or 600.0))
            self.sp_base_plinth.setValue(float(getattr(self._wall, "base_plinth_mm", 100.0) or 100.0))
            self.sp_upper_clearance.setValue(float(getattr(self._wall, "upper_clearance_mm", 0.0) or 0.0))
            self.sp_top_offset.setValue(float(getattr(self._wall, "top_offset_mm", 0.0) or 0.0))
            self.sp_bottom_offset.setValue(float(getattr(self._wall, "bottom_offset_mm", 0.0) or 0.0))
            self.sp_base_offset_left.setValue(float(getattr(self._wall, "base_offset_left_mm", 0.0) or 0.0))
            self.sp_base_offset_right.setValue(float(getattr(self._wall, "base_offset_right_mm", 0.0) or 0.0))
            self.sp_upper_offset_left.setValue(float(getattr(self._wall, "upper_offset_left_mm", 0.0) or 0.0))
            self.sp_upper_offset_right.setValue(float(getattr(self._wall, "upper_offset_right_mm", 0.0) or 0.0))
            self.sp_island_w.setValue(float(getattr(self._wall, "island_width_mm", 1800.0) or 1800.0))
            self.sp_island_d.setValue(float(getattr(self._wall, "island_depth_mm", 900.0) or 900.0))
            self.sp_island_x.setValue(float(getattr(self._wall, "island_offset_x_mm", 1200.0) or 1200.0))
            self.sp_island_y.setValue(float(getattr(self._wall, "island_offset_y_mm", 1400.0) or 1400.0))
            quote_ref = str(getattr(self._wall, "quote_item_reference", "") or "").strip()
            if not quote_ref and (
                str(getattr(self._wall, "quote_item_name", "") or "").strip()
                or str(getattr(self._wall, "quote_item_kind", "") or "").strip()
            ):
                quote_name = str(getattr(self._wall, "quote_item_name", "") or "").strip()
                quote_kind = str(getattr(self._wall, "quote_item_kind", "") or "").strip()
                quote_ref = f"{quote_name} ({quote_kind})".strip() if quote_kind else quote_name
            self.ed_quote_reference.setText(quote_ref)
            self.ed_notes.setPlainText(str(getattr(self._wall, "notes", "") or ""))
        finally:
            self._is_pushing_ui = False

    def _pull_ui_to_wall(self) -> None:
        self._wall.name = str(self.ed_name.text().strip() or "Sciana 1")
        self._wall.client_name = self._selected_client_name()
        self._wall.order_name = self._selected_order_name()
        self._wall.worker_name = self._selected_worker_name()
        self._wall.layout_type = str(self.cb_layout_type.currentData() or "line")
        self._wall.front_view_wall_side = str(self.cb_front_wall.currentData() or "A")
        self._wall.has_island = bool(self.chk_island.isChecked())
        self._wall.wall_a_width_mm = float(self.sp_wall_a.value())
        self._wall.wall_b_width_mm = float(self.sp_wall_b.value())
        self._wall.wall_c_width_mm = float(self.sp_wall_c.value())
        self._wall.room_height_mm = float(self.sp_room_height.value())
        self._wall.base_depth_mm = float(self.sp_base_depth.value())
        self._wall.base_plinth_mm = float(self.sp_base_plinth.value())
        self._wall.upper_clearance_mm = float(self.sp_upper_clearance.value())
        self._wall.top_offset_mm = float(self.sp_top_offset.value())
        self._wall.bottom_offset_mm = float(self.sp_bottom_offset.value())
        self._wall.base_offset_left_mm = float(self.sp_base_offset_left.value())
        self._wall.base_offset_right_mm = float(self.sp_base_offset_right.value())
        self._wall.upper_offset_left_mm = float(self.sp_upper_offset_left.value())
        self._wall.upper_offset_right_mm = float(self.sp_upper_offset_right.value())
        self._wall.island_width_mm = float(self.sp_island_w.value())
        self._wall.island_depth_mm = float(self.sp_island_d.value())
        self._wall.island_offset_x_mm = float(self.sp_island_x.value())
        self._wall.island_offset_y_mm = float(self.sp_island_y.value())
        self._wall.quote_item_reference = str(self.ed_quote_reference.text().strip())
        self._wall.notes = str(self.ed_notes.toPlainText().strip())

        self._validate_wall_offsets_and_island()

    def _validate_wall_offsets_and_island(self) -> None:
        """Clamp base/upper offsets so they don't exceed wall width, and island to room bounds."""
        adjustments: list[str] = []
        wall_a = float(self._wall.wall_a_width_mm or 0.0)

        # --- base offsets ---
        base_left = float(self._wall.base_offset_left_mm or 0.0)
        base_right = float(self._wall.base_offset_right_mm or 0.0)
        if wall_a > 0 and base_left + base_right >= wall_a:
            ratio = base_left / (base_left + base_right) if (base_left + base_right) > 0 else 0.5
            max_total = wall_a - 1.0
            new_left = round(max_total * ratio, 1)
            new_right = round(max_total - new_left, 1)
            adjustments.append(
                f"Odsuniecie podstawy L+R ({base_left:.0f}+{base_right:.0f}) >= sciana A ({wall_a:.0f}) - przycieto do {new_left:.0f}+{new_right:.0f}"
            )
            self._wall.base_offset_left_mm = new_left
            self._wall.base_offset_right_mm = new_right

        # --- upper offsets ---
        upper_left = float(self._wall.upper_offset_left_mm or 0.0)
        upper_right = float(self._wall.upper_offset_right_mm or 0.0)
        if wall_a > 0 and upper_left + upper_right >= wall_a:
            ratio = upper_left / (upper_left + upper_right) if (upper_left + upper_right) > 0 else 0.5
            max_total = wall_a - 1.0
            new_left = round(max_total * ratio, 1)
            new_right = round(max_total - new_left, 1)
            adjustments.append(
                f"Odsuniecie gornych L+R ({upper_left:.0f}+{upper_right:.0f}) >= sciana A ({wall_a:.0f}) - przycieto do {new_left:.0f}+{new_right:.0f}"
            )
            self._wall.upper_offset_left_mm = new_left
            self._wall.upper_offset_right_mm = new_right

        # --- island bounds ---
        if self._wall.has_island:
            layout_type = str(self._wall.layout_type or "line")
            room_width = wall_a
            room_depth = float(self._wall.wall_b_width_mm or 0.0) if layout_type in ("l", "c") else SCIANA_DEPTH_MM_MAX
            island_x = float(self._wall.island_offset_x_mm or 0.0)
            island_y = float(self._wall.island_offset_y_mm or 0.0)
            island_w = float(self._wall.island_width_mm or 0.0)
            island_d = float(self._wall.island_depth_mm or 0.0)

            if island_w > room_width and room_width > 0:
                adjustments.append(
                    f"Szerokosc wyspy ({island_w:.0f}) > sciana A ({room_width:.0f}) - przycieto"
                )
                self._wall.island_width_mm = room_width
                island_w = room_width

            if room_depth < SCIANA_DEPTH_MM_MAX and island_d > room_depth and room_depth > 0:
                adjustments.append(
                    f"Glebokosc wyspy ({island_d:.0f}) > sciana B ({room_depth:.0f}) - przycieto"
                )
                self._wall.island_depth_mm = room_depth
                island_d = room_depth

            if room_width > 0 and island_x + island_w > room_width:
                new_x = max(0.0, room_width - island_w)
                adjustments.append(
                    f"Wyspa X ({island_x:.0f}) wychodzi poza sciane A - przycieto do {new_x:.0f}"
                )
                self._wall.island_offset_x_mm = new_x

            if room_depth < SCIANA_DEPTH_MM_MAX and room_depth > 0 and island_y + island_d > room_depth:
                new_y = max(0.0, room_depth - island_d)
                adjustments.append(
                    f"Wyspa Y ({island_y:.0f}) wychodzi poza sciane B - przycieto do {new_y:.0f}"
                )
                self._wall.island_offset_y_mm = new_y

        if adjustments:
            # Update spinboxes to reflect clamped values without triggering recursive changes
            self._is_pushing_ui = True
            try:
                self.sp_base_offset_left.setValue(float(self._wall.base_offset_left_mm))
                self.sp_base_offset_right.setValue(float(self._wall.base_offset_right_mm))
                self.sp_upper_offset_left.setValue(float(self._wall.upper_offset_left_mm))
                self.sp_upper_offset_right.setValue(float(self._wall.upper_offset_right_mm))
                if self._wall.has_island:
                    self.sp_island_w.setValue(float(self._wall.island_width_mm))
                    self.sp_island_d.setValue(float(self._wall.island_depth_mm))
                    self.sp_island_x.setValue(float(self._wall.island_offset_x_mm))
                    self.sp_island_y.setValue(float(self._wall.island_offset_y_mm))
            finally:
                self._is_pushing_ui = False

            QMessageBox.warning(
                self,
                "Korekta wartosci",
                "Wartosci zostaly skorygowane:\n\n" + "\n".join(adjustments),
            )

    def _on_any_change(self) -> None:
        if self._is_pushing_ui:
            return
        self._reload_wall_side_combos()
        self._pull_ui_to_wall()
        self._refresh_all()

    def _available_wall_sides(self) -> list[tuple[str, str]]:
        layout_type = str(self.cb_layout_type.currentData() or getattr(self._wall, "layout_type", "line") or "line")
        if layout_type == "c":
            return list(WALL_SIDE_ITEMS)
        if layout_type == "l":
            return [item for item in WALL_SIDE_ITEMS if item[0] in ("A", "B")]
        return [item for item in WALL_SIDE_ITEMS if item[0] == "A"]

    def _reload_wall_side_combos(self) -> None:
        available = self._available_wall_sides()
        front_current = str(self.cb_front_wall.currentData() or getattr(self._wall, "front_view_wall_side", "A") or "A")
        obstacle_current = str(self.cb_obstacle_side.currentData() or "A")

        self.cb_front_wall.blockSignals(True)
        self.cb_front_wall.clear()
        for key, label in available:
            self.cb_front_wall.addItem(label, key)
        idx = self.cb_front_wall.findData(front_current)
        if idx < 0:
            idx = 0
        self.cb_front_wall.setCurrentIndex(idx)
        self.cb_front_wall.blockSignals(False)

        self.cb_obstacle_side.blockSignals(True)
        self.cb_obstacle_side.clear()
        for key, label in available:
            self.cb_obstacle_side.addItem(label, key)
        idx = self.cb_obstacle_side.findData(obstacle_current)
        if idx < 0:
            idx = 0
        self.cb_obstacle_side.setCurrentIndex(idx)
        self.cb_obstacle_side.blockSignals(False)

    def _obstacle_label(self, kind_key: str) -> str:
        for key, label in OBSTACLE_KIND_ITEMS:
            if key == kind_key:
                return label
        return kind_key

    def _set_form_row_visible(self, form: QFormLayout, field: QWidget, visible: bool) -> None:
        label = form.labelForField(field)
        if label is not None:
            label.setVisible(bool(visible))
        field.setVisible(bool(visible))

    def _set_form_row_label(self, form: QFormLayout, field: QWidget, label_text: str) -> None:
        label = form.labelForField(field)
        if label is not None and hasattr(label, "setText"):
            label.setText(str(label_text))

    def _ensure_form_label_widget(self, form: QFormLayout, field: QWidget, label_text: str) -> None:
        label = form.labelForField(field)
        if label is not None and hasattr(label, "text") and hasattr(label, "setText"):
            return
        row, _role = form.getWidgetPosition(field)
        if row < 0:
            return
        replacement = QLabel(str(label_text or ""))
        form.setWidget(row, QFormLayout.ItemRole.LabelRole, replacement)

    def _set_store_status(self, message_pl: str, ok: bool = True) -> None:
        if not hasattr(self, "lab_store_status"):
            return
        self.lab_store_status.setText(str(message_pl or ""))
        self.lab_store_status.setStyleSheet("color:#0f6a2f;" if ok else "color:#a61b1b;")

    def _show_storage_operation_error(self, action_label: str, exc: Exception) -> None:
        action = str(action_label or "wykonac operacje na scianie").strip()
        message = f"Nie udalo sie {action}.\n\nSzczegoly: {exc}"
        self._set_store_status(message, ok=False)
        try:
            QMessageBox.critical(self, "Blad zapisu/odczytu", message)
        except Exception:
            pass

    def _shortcut_save_wall(self) -> None:
        try:
            name = str(self.ed_name.text().strip() or "")
            existing = self._store.get(name) if name else None
            if existing is not None:
                self._on_overwrite()
            else:
                self._on_save_new()
        except Exception as exc:
            self._show_storage_operation_error("sprawdzic sciane przed zapisem", exc)

    def _shortcut_focus_wall_name(self) -> None:
        self.ed_name.setFocus()
        self.ed_name.selectAll()

    def _shortcut_settings_key(self) -> str:
        return "sciana_layout_shortcuts_v2"

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
        dlg.setWindowTitle("Konfiguracja skrotow - Sciana")
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        lay.addLayout(form)

        labels = {
            "save": "Zapisz",
            "overwrite": "Nadpisz",
            "load": "Wczytaj",
            "new": "Nowa",
            "next": "Dalej do kompletu",
            "focus_name": "Fokus nazwy",
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

    def _wall_snapshot_for_store(self) -> WallLayoutDef:
        self._pull_ui_to_wall()
        return WallLayoutDef.from_dict(self._wall.to_dict())

    def _next_store_wall_name(self, base_name: str) -> str:
        candidate = str(base_name or "Sciana 1").strip() or "Sciana 1"
        existing = set(self._store.list_names()) if hasattr(self._store, "list_names") else set()
        if candidate not in existing:
            return candidate

        index = 2
        while True:
            next_name = f"{candidate} #{index}"
            if next_name not in existing:
                return next_name
            index += 1

    def _ensure_name_for_save(self) -> str:
        name = str(self.ed_name.text().strip() or getattr(self._wall, "name", "") or "Sciana 1")
        if self.ed_name.text().strip() == name:
            self._wall.name = name
            return name
        self.ed_name.blockSignals(True)
        try:
            self.ed_name.setText(name)
        finally:
            self.ed_name.blockSignals(False)
        self._wall.name = name
        return name

    def _context_payload_from_wall(self, wall: WallLayoutDef) -> dict:
        front_side = str(getattr(wall, "front_view_wall_side", "A") or "A")
        order_name = str(getattr(wall, "order_name", "") or "").strip()
        order_def = self._order_store.get(order_name) if order_name else None
        linear_kinds = {"distance", "width", "height", "depth"}
        linear_total_mm = sum(
            float(getattr(item, "value_mm", 0.0) or 0.0)
            for item in (list(getattr(wall, "measurements", []) or []))
            if str(getattr(item, "kind", "distance") or "distance").strip().lower() in linear_kinds
        )
        return {
            "wall_name": str(getattr(wall, "name", "") or "").strip(),
            "client_name": str(getattr(wall, "client_name", "") or "").strip(),
            "order_code": order_name,
            "order_name": order_name,
            "order_id": str(getattr(order_def, "order_id", "") or "").strip(),
            "worker_name": str(getattr(wall, "worker_name", "") or "").strip(),
            "order_status": str(getattr(order_def, "status", "") or "").strip(),
            "order_progress_percent": float(getattr(order_def, "progress_percent", 0.0) or 0.0),
            "order_calendar_stage": str(getattr(order_def, "calendar_stage", "") or "").strip(),
            "order_calendar_date": str(getattr(order_def, "calendar_date", "") or "").strip(),
            "date_montaz": str(getattr(order_def, "date_montaz", "") or "").strip(),
            "date_montaz_end": str(getattr(order_def, "date_montaz_end", "") or "").strip(),
            "site_address": str(getattr(order_def, "site_address", "") or "").strip(),
            "quote_item_name": str(getattr(wall, "quote_item_name", "") or "").strip(),
            "quote_item_kind": str(getattr(wall, "quote_item_kind", "") or "").strip(),
            "quote_item_reference": str(getattr(wall, "quote_item_reference", "") or "").strip(),
            "measurements_count": len(list(getattr(wall, "measurements", []) or [])),
            "measurements_linear_total_mm": float(linear_total_mm),
            "width_mm": float(self._wall_width_for_side(wall, front_side)),
            "height_mm": float(getattr(wall, "room_height_mm", 2500.0) or 2500.0),
            "depth_mm": float(getattr(wall, "base_depth_mm", 560.0) or 560.0),
        }

    def _ensure_wall_saved_for_next_step(self) -> tuple[WallLayoutDef | None, bool]:
        name = self._ensure_name_for_save()
        wall = self._wall_snapshot_for_store()
        wall.name = str(name or "Sciana 1").strip() or "Sciana 1"

        existing = self._store.get(wall.name) if hasattr(self._store, "get") else None
        loaded_name = str(self._loaded_wall_name or "").strip()

        if existing is not None and loaded_name != wall.name:
            safe_name = self._next_store_wall_name(wall.name)
            wall.name = safe_name
            self.ed_name.blockSignals(True)
            try:
                self.ed_name.setText(safe_name)
            finally:
                self.ed_name.blockSignals(False)
            self._wall.name = safe_name

        result = self._store.overwrite(wall)
        self._loaded_wall_name = wall.name
        self._set_store_status(result.message_pl, ok=result.ok)
        return (wall if result.ok else None), bool(result.ok)

    def _get_collapsible_block_body(self, block: QWidget | None) -> QWidget | None:
        if block is None:
            return None
        try:
            lay = block.content_layout()
        except Exception:
            return None
        if lay is None:
            return None
        try:
            return lay.parentWidget()
        except Exception:
            return None

    def _set_collapsible_block_body_visible(self, block: QWidget | None, visible: bool) -> None:
        if block is not None and hasattr(block, "set_expanded"):
            try:
                block.set_expanded(bool(visible))
                return
            except Exception:
                pass
        body = self._get_collapsible_block_body(block)
        if body is not None:
            body.setVisible(bool(visible))

    def _apply_block_startup_visibility(self) -> None:
        # left zone
        self._set_collapsible_block_body_visible(getattr(self, "blk_identity", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_dims", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_store", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_obstacles", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_photos", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_measurements", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_notes", None), False)
        # right zone — blk_room and blk_suggestions are None after Step 27 (merged/replaced)
        self._set_collapsible_block_body_visible(getattr(self, "blk_summary", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_collisions", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_obstacle_details", None), False)

    def _refresh_obstacle_field_context(self) -> None:
        kind_key = str(self.cb_obstacle_kind.currentData() or "projection").strip().lower()
        is_window = kind_key == "window"
        is_door = kind_key == "door"
        is_socket = kind_key == "socket"
        is_plumbing = kind_key == "plumbing"
        is_radiator = kind_key == "radiator"
        is_sill = kind_key == "sill"
        has_opening = is_window or is_door

        if is_window:
            bottom_label = "Parapet"
            width_label = "Szerokosc otworu"
            height_label = "Wysokosc otworu"
            depth_label = "Glebokosc"
        elif is_door:
            bottom_label = "Od podlogi"
            width_label = "Szerokosc otworu"
            height_label = "Wysokosc otworu"
            depth_label = "Glebokosc"
        elif is_socket:
            bottom_label = "Wysokosc montazu"
            width_label = "Szerokosc pola"
            height_label = "Wysokosc pola"
            depth_label = "Glebokosc puszki"
        elif is_plumbing:
            bottom_label = "Wysokosc przylaczy"
            width_label = "Szerokosc strefy"
            height_label = "Wysokosc strefy"
            depth_label = "Glebokosc strefy"
        elif is_radiator:
            bottom_label = "Od podlogi"
            width_label = "Szerokosc grzejnika"
            height_label = "Wysokosc grzejnika"
            depth_label = "Odstawanie"
        elif is_sill:
            bottom_label = "Wysokosc parapetu"
            width_label = "Dlugosc parapetu"
            height_label = "Wysokosc pasa"
            depth_label = "Wysuniecie"
        else:
            bottom_label = "Od podlogi"
            width_label = "Szerokosc"
            height_label = "Wysokosc"
            depth_label = "Glebokosc"

        opening_label = "Kierunek skrzydla" if is_window else "Kierunek otwierania"

        self._set_form_row_label(self._obstacle_form, self.sp_obstacle_bottom, bottom_label)
        self._set_form_row_label(self._obstacle_form, self.sp_obstacle_w, width_label)
        self._set_form_row_label(self._obstacle_form, self.sp_obstacle_h, height_label)
        self._set_form_row_label(self._obstacle_form, self.sp_obstacle_d, depth_label)
        self._set_form_row_label(self._obstacle_form, self.cb_obstacle_opening, opening_label)
        self._set_form_row_visible(self._obstacle_form, self.cb_obstacle_opening, has_opening)

    def _selected_obstacle_row(self) -> int:
        rows = self.tbl_obstacles.selectionModel().selectedRows() if self.tbl_obstacles.selectionModel() is not None else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _sync_obstacle_editor_from_index(self, index: int) -> None:
        if index < 0 or index >= len(self._wall.obstacles):
            return
        obstacle = self._wall.obstacles[index]
        self._is_syncing_obstacle_editor = True
        try:
            kind_idx = self.cb_obstacle_kind.findData(obstacle.kind)
            if kind_idx >= 0:
                self.cb_obstacle_kind.setCurrentIndex(kind_idx)
            opening_idx = self.cb_obstacle_opening.findData(getattr(obstacle, "opening_direction", "fixed"))
            if opening_idx >= 0:
                self.cb_obstacle_opening.setCurrentIndex(opening_idx)
            side_idx = self.cb_obstacle_side.findData(obstacle.wall_side)
            if side_idx >= 0:
                self.cb_obstacle_side.setCurrentIndex(side_idx)
            self.ed_obstacle_name.setText(str(obstacle.name or ""))
            self.sp_obstacle_x.setValue(float(obstacle.x_mm))
            self.sp_obstacle_bottom.setValue(float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0))
            self.sp_obstacle_w.setValue(float(obstacle.width_mm))
            self.sp_obstacle_h.setValue(float(obstacle.height_mm))
            self.sp_obstacle_d.setValue(float(obstacle.depth_mm))
        finally:
            self._is_syncing_obstacle_editor = False
        self._refresh_obstacle_field_context()

    def _select_obstacle_row(self, index: int) -> None:
        if 0 <= index < self.tbl_obstacles.rowCount():
            self.tbl_obstacles.selectRow(index)
            self._selected_obstacle_index = index
            self._set_selected_obstacle_index_on_previews(index)

    def _set_selected_obstacle_index_on_previews(self, index: int) -> None:
        for preview in self._all_previews():
            preview.set_selected_obstacle_index(index)

    def _render_previews(self, fit: bool = False) -> None:
        for preview in self._all_previews():
            preview.set_selected_obstacle_index(self._selected_obstacle_index)
            preview.render_wall(self._wall, fit=False)
        self._sync_preview_scales()

    def _all_previews(self) -> list[WallPreviewView]:
        previews: list[WallPreviewView] = []
        if hasattr(self, "preview") and self.preview is not None:
            previews.append(self.preview)
        if hasattr(self, "preview_top") and self.preview_top is not None:
            previews.append(self.preview_top)
        return previews

    def _sync_preview_scales(self) -> None:
        previews = [preview for preview in self._all_previews() if preview.isVisible()]
        if not previews or self._is_syncing_preview_scales:
            return

        self._is_syncing_preview_scales = True
        try:
            fit_scales = [preview.max_fit_scale() for preview in previews]
            fit_scales = [scale for scale in fit_scales if scale > 0.0]
            if not fit_scales:
                return

            target_scale = min(fit_scales)
            for preview in previews:
                preview.apply_uniform_scale(target_scale)
        finally:
            self._is_syncing_preview_scales = False

    def _on_preview_resized(self) -> None:
        self._sync_preview_scales()

    def _clamp_obstacle_to_wall(self, obstacle: WallObstacleDef) -> None:
        wall_width = self._wall_width_for_side(self._wall, obstacle.wall_side)
        max_x = max(0.0, wall_width - float(getattr(obstacle, "width_mm", 0.0) or 0.0))
        room_height = float(getattr(self._wall, "room_height_mm", 2600.0) or 2600.0)
        max_bottom = max(0.0, room_height - float(getattr(obstacle, "height_mm", 0.0) or 0.0))

        obstacle.x_mm = max(0.0, min(float(getattr(obstacle, "x_mm", 0.0) or 0.0), max_x))
        obstacle.bottom_offset_mm = max(
            0.0,
            min(float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0), max_bottom),
        )

    def _clamp_obstacle_to_wall_with_warning(self, obstacle: WallObstacleDef) -> bool:
        """Clamp obstacle to wall boundaries and show a warning if values were adjusted.

        Returns True if any value was clamped.
        """
        wall_width = self._wall_width_for_side(self._wall, obstacle.wall_side)
        room_height = float(getattr(self._wall, "room_height_mm", 2600.0) or 2600.0)

        original_x = float(getattr(obstacle, "x_mm", 0.0) or 0.0)
        original_bottom = float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0)
        original_w = float(getattr(obstacle, "width_mm", 0.0) or 0.0)
        original_h = float(getattr(obstacle, "height_mm", 0.0) or 0.0)

        adjustments: list[str] = []

        if original_w > wall_width:
            obstacle.width_mm = wall_width
            adjustments.append(
                f"Szerokosc ({original_w:.0f}) przekracza szerokosc sciany ({wall_width:.0f}) - przycieto do {wall_width:.0f} mm"
            )

        if original_h > room_height:
            obstacle.height_mm = room_height
            adjustments.append(
                f"Wysokosc ({original_h:.0f}) przekracza wysokosc pomieszczenia ({room_height:.0f}) - przycieto do {room_height:.0f} mm"
            )

        self._clamp_obstacle_to_wall(obstacle)

        if obstacle.x_mm != original_x:
            adjustments.append(
                f"Pozycja X ({original_x:.0f}) przycieta do {obstacle.x_mm:.0f} mm (sciana: {wall_width:.0f} mm)"
            )
        if obstacle.bottom_offset_mm != original_bottom:
            adjustments.append(
                f"Offset dolny ({original_bottom:.0f}) przyciety do {obstacle.bottom_offset_mm:.0f} mm (wysokosc: {room_height:.0f} mm)"
            )

        if adjustments:
            QMessageBox.warning(
                self,
                "Korekta przeszkody",
                "Wartosci przeszkody zostaly skorygowane:\n\n" + "\n".join(adjustments),
            )
            return True
        return False

    def _write_editor_to_obstacle(self, row: int, show_warning: bool = False) -> bool:
        if row < 0 or row >= len(self._wall.obstacles):
            return False

        obstacle = self._wall.obstacles[row]
        obstacle.kind = str(self.cb_obstacle_kind.currentData() or "projection")
        obstacle.wall_side = str(self.cb_obstacle_side.currentData() or "A")
        obstacle.name = str(self.ed_obstacle_name.text().strip() or self.cb_obstacle_kind.currentText())
        obstacle.opening_direction = str(self.cb_obstacle_opening.currentData() or "fixed")
        obstacle.x_mm = float(self.sp_obstacle_x.value())
        obstacle.bottom_offset_mm = float(self.sp_obstacle_bottom.value())
        obstacle.width_mm = float(self.sp_obstacle_w.value())
        obstacle.height_mm = float(self.sp_obstacle_h.value())
        obstacle.depth_mm = float(self.sp_obstacle_d.value())
        if show_warning:
            self._clamp_obstacle_to_wall_with_warning(obstacle)
        else:
            self._clamp_obstacle_to_wall(obstacle)
        return True

    def _on_selected_obstacle_editor_changed(self) -> None:
        self._refresh_obstacle_field_context()
        if self._is_pushing_ui or self._is_syncing_obstacle_editor:
            return

        row = self._selected_obstacle_row()
        if not self._write_editor_to_obstacle(row):
            return

        self._selected_obstacle_index = row
        self._refresh_obstacles_table()
        self._refresh_summary()
        self._select_obstacle_row(row)
        self._render_previews(fit=False)

    def _on_add_obstacle(self) -> None:
        obstacle = WallObstacleDef(
            kind=str(self.cb_obstacle_kind.currentData() or "projection"),
            wall_side=str(self.cb_obstacle_side.currentData() or "A"),
            name=str(self.ed_obstacle_name.text().strip() or self.cb_obstacle_kind.currentText()),
            opening_direction=str(self.cb_obstacle_opening.currentData() or "fixed"),
            x_mm=float(self.sp_obstacle_x.value()),
            bottom_offset_mm=float(self.sp_obstacle_bottom.value()),
            width_mm=float(self.sp_obstacle_w.value()),
            height_mm=float(self.sp_obstacle_h.value()),
            depth_mm=float(self.sp_obstacle_d.value()),
        )
        clamped = self._clamp_obstacle_to_wall_with_warning(obstacle)
        self._wall.obstacles.append(obstacle)
        self.ed_obstacle_name.clear()
        self._selected_obstacle_index = len(self._wall.obstacles) - 1
        self._refresh_all(fit=False)
        self._select_obstacle_row(self._selected_obstacle_index)

    def _on_apply_obstacle(self) -> None:
        row = self._selected_obstacle_row()
        if not self._write_editor_to_obstacle(row, show_warning=True):
            return

        self._selected_obstacle_index = row
        self._refresh_all(fit=False)
        self._select_obstacle_row(row)

    def _on_remove_obstacle(self) -> None:
        row = self._selected_obstacle_row()
        if row < 0 or row >= len(self._wall.obstacles):
            return
        self._wall.obstacles.pop(row)
        self._selected_obstacle_index = min(row, len(self._wall.obstacles) - 1)
        self._refresh_all(fit=False)
        self._select_obstacle_row(self._selected_obstacle_index)

    def _on_add_photo(self) -> None:
        path = str(self.ed_photo_path.text().strip())
        if not path:
            return
        photo = WallPhotoDef(path=path, caption=str(self.ed_photo_caption.text().strip()))
        self._wall.photos.append(photo)
        self.ed_photo_path.clear()
        self.ed_photo_caption.clear()
        self._refresh_all(fit=False)

    def _on_remove_photo(self) -> None:
        rows = self.tbl_photos.selectionModel().selectedRows() if self.tbl_photos.selectionModel() is not None else []
        if not rows:
            return
        row = int(rows[0].row())
        if 0 <= row < len(self._wall.photos):
            self._wall.photos.pop(row)
        self._refresh_all(fit=False)

    def _selected_photo_row(self) -> int:
        rows = self.tbl_photos.selectionModel().selectedRows() if self.tbl_photos.selectionModel() is not None else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _guess_measure_photo_path(self) -> str:
        direct_path = str(self.ed_measure_photo_path.text().strip())
        if direct_path:
            return direct_path
        selected_photo_row = self._selected_photo_row()
        if 0 <= selected_photo_row < len(self._wall.photos):
            candidate = str(getattr(self._wall.photos[selected_photo_row], "path", "") or "").strip()
            if candidate:
                return candidate
        if self._wall.photos:
            candidate = str(getattr(self._wall.photos[0], "path", "") or "").strip()
            if candidate:
                return candidate
        return ""

    def _on_measurement_from_photo(self) -> None:
        photo_path = self._guess_measure_photo_path()
        dlg = PhotoMeasureDialog(
            self,
            photo_path=photo_path,
            quote_reference=str(getattr(self._wall, "quote_item_reference", "") or "").strip(),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dlg.measurement_payload()
        if not isinstance(payload, dict):
            return

        self.ed_measure_name.setText(str(payload.get("name", "") or "Pomiar ze zdjecia"))
        kind_key = str(payload.get("kind", "distance") or "distance").strip().lower()
        kind_index = self.cb_measure_kind.findData(kind_key)
        if kind_index >= 0:
            self.cb_measure_kind.setCurrentIndex(kind_index)
        self.sp_measure_value.setValue(float(payload.get("value_mm", 0.0) or 0.0))
        self.ed_measure_photo_path.setText(str(payload.get("photo_path", "") or "").strip())
        self.ed_measure_note.setText(str(payload.get("note", "") or "").strip())

        quote_ref = str(payload.get("quote_reference", "") or "").strip()
        if quote_ref and not str(self.ed_quote_reference.text().strip()):
            self.ed_quote_reference.setText(quote_ref)

        self._on_add_measurement()

    def _on_obstacle_selection_changed(self) -> None:
        row = self._selected_obstacle_row()
        self._selected_obstacle_index = row
        self._set_selected_obstacle_index_on_previews(row)
        if row >= 0:
            self._sync_obstacle_editor_from_index(row)
        self._render_previews(fit=False)

    def _on_preview_obstacle_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._wall.obstacles):
            return
        obstacle = self._wall.obstacles[index]
        front_idx = self.cb_front_wall.findData(obstacle.wall_side)
        if front_idx >= 0 and self.cb_front_wall.currentIndex() != front_idx:
            self.cb_front_wall.setCurrentIndex(front_idx)
        self._select_obstacle_row(index)
        self._sync_obstacle_editor_from_index(index)
        self._render_previews(fit=False)

    def _on_preview_obstacle_dragged(self, index: int, x_mm: float, bottom_mm: float) -> None:
        if index < 0 or index >= len(self._wall.obstacles):
            return

        obstacle = self._wall.obstacles[index]
        obstacle.x_mm = float(x_mm)
        obstacle.bottom_offset_mm = float(bottom_mm)
        self._clamp_obstacle_to_wall(obstacle)

        self._selected_obstacle_index = index
        self._refresh_obstacles_table()
        self._refresh_summary()
        self._select_obstacle_row(index)
        self._sync_obstacle_editor_from_index(index)
        self._render_previews(fit=False)

    def _on_preview_obstacle_dimension_changed(self, index: int, x_mm: float, bottom_mm: float) -> None:
        if index < 0 or index >= len(self._wall.obstacles):
            return

        obstacle = self._wall.obstacles[index]
        obstacle.x_mm = float(x_mm)
        obstacle.bottom_offset_mm = float(bottom_mm)
        self._clamp_obstacle_to_wall(obstacle)

        self._selected_obstacle_index = index
        self._refresh_obstacles_table()
        self._refresh_summary()
        self._select_obstacle_row(index)
        self._sync_obstacle_editor_from_index(index)
        self._render_previews(fit=False)

    def _refresh_obstacles_table(self) -> None:
        self.tbl_obstacles.setRowCount(len(self._wall.obstacles))
        for row, obstacle in enumerate(self._wall.obstacles):
            dims = _obstacle_dims_text(obstacle)
            values = [
                self._obstacle_label(obstacle.kind),
                obstacle.wall_side,
                obstacle.name,
                dims,
            ]
            for col, value in enumerate(values):
                self.tbl_obstacles.setItem(row, col, QTableWidgetItem(value))

    def _refresh_photos_table(self) -> None:
        self.tbl_photos.setRowCount(len(self._wall.photos))
        for row, photo in enumerate(self._wall.photos):
            self.tbl_photos.setItem(row, 0, QTableWidgetItem(photo.path))
            self.tbl_photos.setItem(row, 1, QTableWidgetItem(photo.caption))

    def _selected_measurement_row(self) -> int:
        rows = (
            self.tbl_measurements.selectionModel().selectedRows()
            if self.tbl_measurements.selectionModel() is not None
            else []
        )
        if not rows:
            return -1
        return int(rows[0].row())

    def _on_measurement_selection_changed(self) -> None:
        self._refresh_ui_state()

    def _on_add_measurement(self) -> None:
        name = str(self.ed_measure_name.text().strip() or self.cb_measure_kind.currentText())
        measurement = WallMeasurementDef(
            name=name,
            kind=str(self.cb_measure_kind.currentData() or "distance"),
            value_mm=float(self.sp_measure_value.value()),
            photo_path=str(self.ed_measure_photo_path.text().strip()),
            note=str(self.ed_measure_note.text().strip()),
        )
        self._wall.measurements.append(measurement)
        self.ed_measure_name.clear()
        self.sp_measure_value.setValue(0.0)
        self.ed_measure_photo_path.clear()
        self.ed_measure_note.clear()
        self._refresh_all(fit=False)
        if self.tbl_measurements.rowCount() > 0:
            self.tbl_measurements.selectRow(self.tbl_measurements.rowCount() - 1)

    def _on_remove_measurement(self) -> None:
        row = self._selected_measurement_row()
        if row < 0 or row >= len(self._wall.measurements):
            return
        self._wall.measurements.pop(row)
        self._refresh_all(fit=False)
        if self.tbl_measurements.rowCount() > 0:
            self.tbl_measurements.selectRow(min(row, self.tbl_measurements.rowCount() - 1))

    def _refresh_measurements_table(self) -> None:
        self.tbl_measurements.setRowCount(len(self._wall.measurements))
        for row, item in enumerate(self._wall.measurements):
            values = [
                str(getattr(item, "name", "") or ""),
                _measurement_kind_label(str(getattr(item, "kind", "distance") or "distance")),
                f"{float(getattr(item, 'value_mm', 0.0) or 0.0):.1f} mm",
                str(getattr(item, "photo_path", "") or ""),
                str(getattr(item, "note", "") or ""),
            ]
            for col, value in enumerate(values):
                self.tbl_measurements.setItem(row, col, QTableWidgetItem(value))

    def _is_visual_attachment_entry(self, entry: dict | None) -> bool:
        if not isinstance(entry, dict):
            return False
        path = str(entry.get("path", "") or "").strip()
        if not path:
            return False
        kind = str(entry.get("kind", "") or "").strip().lower()
        suffix = Path(path).suffix.strip().lower()
        return kind in {"obraz", "referencja"} or suffix in _IMAGE_ATTACHMENT_EXTENSIONS

    def _attachment_target_matches(self, entry: dict | None, target_kind: str, candidate_names: set[str]) -> bool:
        if not isinstance(entry, dict):
            return False
        raw_target_kind = str(entry.get("target_kind", "") or "").strip().lower()
        raw_target_name = str(entry.get("target_name", "") or "").strip().lower()
        if raw_target_kind in {"", "zamowienie"}:
            return True
        if raw_target_kind != str(target_kind or "").strip().lower():
            return False
        if not raw_target_name:
            return True
        return raw_target_name in candidate_names

    def _architect_reference_caption(self, entry: dict | None) -> str:
        if not isinstance(entry, dict):
            return ""
        description = str(entry.get("description", "") or "").strip()
        source_page = str(entry.get("source_page", "") or "").strip()
        parts = [chunk for chunk in (description, source_page) if chunk]
        if parts:
            return " | ".join(parts)
        target_name = str(entry.get("target_name", "") or "").strip()
        target_kind = str(entry.get("target_kind", "") or "").strip()
        if target_kind and target_name:
            return f"{target_kind}: {target_name}"
        if target_kind:
            return target_kind
        return ""

    def _load_architect_reference_photos(
        self,
        order_name: str,
        candidate_names: list[str] | tuple[str, ...] = (),
    ) -> list[WallPhotoDef]:
        order_code = str(order_name or "").strip()
        if not order_code:
            return []
        order_def = self._order_store.get(order_code)
        if order_def is None:
            return []

        normalized_candidates = {
            str(name or "").strip().lower()
            for name in candidate_names
            if str(name or "").strip()
        }

        photos: list[WallPhotoDef] = []
        seen_paths: set[str] = set()
        for attachment in list(getattr(order_def, "attachments", []) or []):
            if not self._is_visual_attachment_entry(attachment):
                continue
            if not self._attachment_target_matches(attachment, "sciana", normalized_candidates):
                continue
            path = str(attachment.get("path", "") or "").strip()
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            photos.append(
                WallPhotoDef(
                    path=path,
                    caption=self._architect_reference_caption(attachment),
                )
            )
        return photos

    # =====================================================================
    # PANEL POMIESZCZENIA + KOLIZJE
    # =====================================================================

    def _compute_room_metrics(self) -> dict:
        w = self._wall
        wall_a = max(1.0, float(w.wall_a_width_mm or 4000))
        wall_b = max(1.0, float(w.wall_b_width_mm or 2600))
        wall_c = max(1.0, float(w.wall_c_width_mm or 2600))
        room_h = max(1.0, float(w.room_height_mm or 2600))
        base_depth = max(1.0, float(w.base_depth_mm or 600))
        plinth = max(0.0, float(w.base_plinth_mm or 0))
        upper_cl = max(0.0, float(w.upper_clearance_mm or 0))
        top_off = max(0.0, float(w.top_offset_mm or 0))
        bot_off = max(0.0, float(w.bottom_offset_mm or 0))
        left_off_base = max(0.0, float(w.base_offset_left_mm or 0))
        right_off_base = max(0.0, float(w.base_offset_right_mm or 0))
        left_off_upper = max(0.0, float(w.upper_offset_left_mm or 0))
        right_off_upper = max(0.0, float(w.upper_offset_right_mm or 0))
        layout = str(w.layout_type or "line")
        base_zone_h = max(0.0, room_h - plinth - upper_cl - top_off - bot_off)
        total_wall_mm = wall_a
        if layout in ("l", "c"):
            total_wall_mm += wall_b
        if layout == "c":
            total_wall_mm += wall_c
        base_avail_w = max(0.0, wall_a - left_off_base - right_off_base)
        upper_avail_w = max(0.0, wall_a - left_off_upper - right_off_upper)
        area_a_m2 = wall_a * room_h / 1_000_000
        obstacles = list(w.obstacles or [])
        obs_count = len(obstacles)
        obs_area_m2 = sum(
            float(getattr(o, "width_mm", 0) or 0) * float(getattr(o, "height_mm", 0) or 0)
            for o in obstacles
        ) / 1_000_000
        fill_pct = (obs_area_m2 / area_a_m2 * 100.0) if area_a_m2 > 0 else 0.0
        return {
            "wall_a": wall_a, "wall_b": wall_b, "wall_c": wall_c,
            "room_h": room_h, "base_depth": base_depth, "plinth": plinth,
            "upper_cl": upper_cl, "top_off": top_off, "bot_off": bot_off,
            "base_zone_h": base_zone_h, "layout": layout,
            "total_wall_mm": total_wall_mm,
            "base_avail_w": base_avail_w, "upper_avail_w": upper_avail_w,
            "area_a_m2": area_a_m2,
            "obs_count": obs_count, "obs_area_m2": obs_area_m2,
            "fill_pct": fill_pct,
        }

    def _refresh_room_panel(self) -> None:
        if not hasattr(self, "lab_room_info"):
            return
        m = self._compute_room_metrics()
        layout_label = {"line": "Prosta", "l": "L", "c": "C"}.get(m["layout"], m["layout"])
        lines = [f"Uklad: {layout_label}", f"Sciana A: {m['wall_a']:.0f} mm"]
        if m["layout"] in ("l", "c"):
            lines.append(f"Sciana B: {m['wall_b']:.0f} mm")
        if m["layout"] == "c":
            lines.append(f"Sciana C: {m['wall_c']:.0f} mm")
        lines += [
            f"Lacznie scian: {m['total_wall_mm']:.0f} mm",
            f"Wysokosc pomieszczenia: {m['room_h']:.0f} mm",
            f"Glebokosc zabudowy: {m['base_depth']:.0f} mm",
            "",
            f"Cokol: {m['plinth']:.0f} mm",
            f"Gorny odstep: {m['upper_cl']:.0f} mm",
            f"Strefa zabudowy (wys.): {m['base_zone_h']:.0f} mm",
            f"Szerokosc dolnej zabudowy: {m['base_avail_w']:.0f} mm",
            f"Szerokosc gornej zabudowy: {m['upper_avail_w']:.0f} mm",
            "",
            f"Powierzchnia sciany A: {m['area_a_m2']:.2f} m2",
            f"Przeszkody ({m['obs_count']}): {m['obs_area_m2']:.2f} m2",
            f"Wypelnienie: {m['fill_pct']:.1f}%",
        ]
        self.lab_room_info.setText("\n".join(lines))

    def _detect_collisions(self) -> list[str]:
        warnings: list[str] = []
        obstacles = list(self._wall.obstacles or [])
        room_h = max(1.0, float(self._wall.room_height_mm or 2600))
        wall_a = max(1.0, float(self._wall.wall_a_width_mm or 4000))
        plinth = max(0.0, float(self._wall.base_plinth_mm or 0))
        # -- 1. Nakładanie przeszkod na tej samej scianie --
        by_side: dict[str, list] = {}
        for obs in obstacles:
            side = str(getattr(obs, "wall_side", "A") or "A").strip().upper()
            by_side.setdefault(side, []).append(obs)
        for side, obs_list in by_side.items():
            for i, a in enumerate(obs_list):
                ax1 = float(getattr(a, "x_mm", 0) or 0)
                ax2 = ax1 + max(0.0, float(getattr(a, "width_mm", 0) or 0))
                ay1 = float(getattr(a, "bottom_offset_mm", 0) or 0)
                ay2 = ay1 + max(0.0, float(getattr(a, "height_mm", 0) or 0))
                for j, b in enumerate(obs_list):
                    if j <= i:
                        continue
                    bx1 = float(getattr(b, "x_mm", 0) or 0)
                    bx2 = bx1 + max(0.0, float(getattr(b, "width_mm", 0) or 0))
                    by1 = float(getattr(b, "bottom_offset_mm", 0) or 0)
                    by2 = by1 + max(0.0, float(getattr(b, "height_mm", 0) or 0))
                    if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                        na = str(getattr(a, "name", "") or f"#{i+1}").strip() or f"#{i+1}"
                        nb = str(getattr(b, "name", "") or f"#{j+1}").strip() or f"#{j+1}"
                        warnings.append(f"[{side}] Nakladanie: {na} <-> {nb}")
        # -- 2. Przeszkody poza granicami sciany --
        for obs in obstacles:
            side = str(getattr(obs, "wall_side", "A") or "A").strip().upper()
            x1 = float(getattr(obs, "x_mm", 0) or 0)
            x2 = x1 + max(0.0, float(getattr(obs, "width_mm", 0) or 0))
            y1 = float(getattr(obs, "bottom_offset_mm", 0) or 0)
            y2 = y1 + max(0.0, float(getattr(obs, "height_mm", 0) or 0))
            name = str(getattr(obs, "name", "") or getattr(obs, "kind", "?")).strip() or "?"
            if side == "A" and x2 > wall_a:
                warnings.append(f"[A] {name}: wystaje poza sciane o {x2 - wall_a:.0f} mm")
            if y2 > room_h:
                warnings.append(f"[{side}] {name}: wykracza poza sufit o {y2 - room_h:.0f} mm")
            if y1 < 0:
                warnings.append(f"[{side}] {name}: y < 0 (ponizej podlogi)")
        # -- 3. Przeszkody techniczne w strefie cokolu --
        technical = {"pipe", "socket", "plumbing"}
        for obs in obstacles:
            kind = str(getattr(obs, "kind", "") or "").strip()
            if kind not in technical:
                continue
            name = str(getattr(obs, "name", "") or kind).strip() or kind
            y1 = float(getattr(obs, "bottom_offset_mm", 0) or 0)
            y2 = y1 + max(0.0, float(getattr(obs, "height_mm", 0) or 0))
            if plinth > 0 and y1 < plinth:
                warnings.append(f"{name}: srodek w strefie cokolu ({plinth:.0f} mm)")
        return warnings

    def _refresh_collisions(self) -> None:
        if not hasattr(self, "lab_collisions"):
            return
        warnings = self._detect_collisions()
        if not warnings:
            self.lab_collisions.setStyleSheet(
                "font-size:11px; color:#15803d; font-weight:600;"
            )
            self.lab_collisions.setText("Brak kolizji")
        else:
            self.lab_collisions.setStyleSheet(
                "font-size:11px; color:#b91c1c; font-weight:600;"
            )
            self.lab_collisions.setText("\n".join(f"[!] {w}" for w in warnings))

    def _refresh_summary(self) -> None:
        layout_label = self.cb_layout_type.currentText()
        island_txt = "tak" if bool(getattr(self._wall, "has_island", False)) else "nie"
        technical_count = sum(1 for obstacle in self._wall.obstacles if _is_technical_obstacle_kind(getattr(obstacle, "kind", "")))
        linear_kinds = {"distance", "width", "height", "depth"}
        measurements = list(getattr(self._wall, "measurements", []) or [])
        measurements_linear_total_mm = sum(
            float(getattr(item, "value_mm", 0.0) or 0.0)
            for item in measurements
            if str(getattr(item, "kind", "distance") or "distance").strip().lower() in linear_kinds
        )
        order_status, site_address = self._selected_order_details()
        lines = [
            f"Nazwa: {self._wall.name}",
            f"Klient: {getattr(self._wall, 'client_name', '') or '-'}",
            f"Zamowienie: {getattr(self._wall, 'order_name', '') or '-'}",
            f"Pracownik: {getattr(self._wall, 'worker_name', '') or '-'}",
            f"Ref. wyceny: {getattr(self._wall, 'quote_item_reference', '') or '-'}",
            f"Typ ukladu: {layout_label}",
            f"Widok z przodu: {_wall_side_label(getattr(self._wall, 'front_view_wall_side', 'A'))}",
            f"Wyspa: {island_txt}",
            f"Sciana A: {self._wall.wall_a_width_mm:.0f} mm",
        ]

        if self._wall.layout_type in ("l", "c"):
            lines.append(f"Sciana B: {self._wall.wall_b_width_mm:.0f} mm")
        if self._wall.layout_type == "c":
            lines.append(f"Sciana C: {self._wall.wall_c_width_mm:.0f} mm")

        lines.extend(
            [
                f"Wysokosc pomieszczenia: {self._wall.room_height_mm:.0f} mm",
                f"Glebokosc zabudowy: {self._wall.base_depth_mm:.0f} mm",
                f"Dolny cokol: {getattr(self._wall, 'base_plinth_mm', 0.0):.0f} mm",
                f"Gorny odstep: {getattr(self._wall, 'upper_clearance_mm', 0.0):.0f} mm",
                f"Gorny offset: {getattr(self._wall, 'top_offset_mm', 0.0):.0f} mm",
                f"Dolny offset: {getattr(self._wall, 'bottom_offset_mm', 0.0):.0f} mm",
                f"Dolne od lewej: {getattr(self._wall, 'base_offset_left_mm', 0.0):.0f} mm",
                f"Dolne od prawej: {getattr(self._wall, 'base_offset_right_mm', 0.0):.0f} mm",
                f"Gorne od lewej: {getattr(self._wall, 'upper_offset_left_mm', 0.0):.0f} mm",
                f"Gorne od prawej: {getattr(self._wall, 'upper_offset_right_mm', 0.0):.0f} mm",
                f"Przeszkody: {len(self._wall.obstacles)}",
                f"Elementy techniczne: {technical_count}",
                f"Zdjecia: {len(self._wall.photos)}",
                f"Pomiary: {len(measurements)}",
                f"Suma pomiarow liniowych: {measurements_linear_total_mm:.0f} mm",
            ]
        )

        if order_status:
            lines.append(f"Status zamowienia: {order_status}")
        if site_address:
            lines.append(f"Adres realizacji: {site_address}")

        if self._wall.notes:
            lines.extend(["", "Notatki:", self._wall.notes])

        self.lab_summary.setText("\n".join(lines))

        detail_lines: list[str] = []
        for obstacle in self._wall.obstacles[:8]:
            detail_line = _obstacle_summary_line(obstacle)
            if detail_line:
                detail_lines.append(detail_line)
        if hasattr(self, "lab_obstacle_details"):
            self.lab_obstacle_details.setText("\n".join(detail_lines) if detail_lines else "-")

        self._refresh_room_panel()
        self._refresh_collisions()
    def _refresh_ui_state(self) -> None:
        layout_type = str(self.cb_layout_type.currentData() or "line")
        has_corner = layout_type in ("l", "c")
        has_c = layout_type == "c"
        has_island = bool(self.chk_island.isChecked())
        has_selected_obstacle = 0 <= self._selected_obstacle_index < len(self._wall.obstacles)
        has_selected_measurement = 0 <= self._selected_measurement_row() < len(self._wall.measurements)

        self._refresh_obstacle_field_context()
        self._set_form_row_visible(self._layout_form, self.sp_wall_b, has_corner)
        self._set_form_row_visible(self._layout_form, self.sp_wall_c, has_c)
        self._set_form_row_visible(self._layout_form, self.sp_island_w, has_island)
        self._set_form_row_visible(self._layout_form, self.sp_island_d, has_island)
        self._set_form_row_visible(self._layout_form, self.sp_island_x, has_island)
        self._set_form_row_visible(self._layout_form, self.sp_island_y, has_island)
        self.btn_apply_obstacle.setEnabled(has_selected_obstacle)
        self.btn_remove_obstacle.setEnabled(has_selected_obstacle)
        self.btn_remove_measurement.setEnabled(has_selected_measurement)

    def _refresh_all(self, fit: bool = True) -> None:
        self._reload_wall_side_combos()
        self._pull_ui_to_wall()
        self._refresh_ui_state()
        self._refresh_obstacles_table()
        self._refresh_photos_table()
        self._refresh_measurements_table()
        self._refresh_summary()
        self._render_previews(fit=fit)

    def _on_save_new(self) -> None:
        try:
            name = self._ensure_name_for_save()
            wall = self._wall_snapshot_for_store()
            wall.name = name
            result = self._store.save_new(wall)
            if result.ok:
                self._loaded_wall_name = wall.name
            self._set_store_status(result.message_pl, ok=result.ok)
        except Exception as exc:
            self._show_storage_operation_error("zapisac nowa sciane", exc)

    def _on_overwrite(self) -> None:
        try:
            name = self._ensure_name_for_save()
            wall = self._wall_snapshot_for_store()
            wall.name = name
            result = self._store.overwrite(wall)
            if result.ok:
                self._loaded_wall_name = wall.name
            self._set_store_status(result.message_pl, ok=result.ok)
        except Exception as exc:
            self._show_storage_operation_error("nadpisac sciane", exc)

    def _on_load(self) -> None:
        try:
            dlg = LoadWallDialog(self, self._store)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return

            wall = dlg.selected_wall()
            if wall is None:
                self._set_store_status("Nie wybrano sciany do wczytania.", ok=False)
                return

            self._wall = WallLayoutDef.from_dict(wall.to_dict())
            self._selected_obstacle_index = -1
            self._set_selected_obstacle_index_on_previews(-1)
            self._push_wall_to_ui()
            self._refresh_all()
            self._loaded_wall_name = str(getattr(self._wall, "name", "") or "").strip()
            self._set_store_status(f'Wczytano sciane: "{self._wall.name}".', ok=True)
        except Exception as exc:
            self._show_storage_operation_error("wczytac sciane", exc)

    def load_wall_from_store_name(self, name: str) -> bool:
        try:
            wall_name = str(name or "").strip()
            if not wall_name:
                return False

            wall = self._store.get(wall_name) if hasattr(self._store, "get") else None
            if wall is None:
                return False

            self._wall = WallLayoutDef.from_dict(wall.to_dict())
            self._selected_obstacle_index = -1
            self._set_selected_obstacle_index_on_previews(-1)
            self._push_wall_to_ui()
            self._refresh_all()
            self._loaded_wall_name = str(getattr(self._wall, "name", "") or "").strip()
            self._set_store_status(f'Wczytano sciane: "{self._wall.name}".', ok=True)
            return True
        except Exception as exc:
            self._set_store_status(f"Nie udalo sie wczytac sciany: {exc}", ok=False)
            return False

    def _build_wall_notes_from_order_context(self, payload: dict[str, object], order_def: object | None) -> str:
        sections: list[str] = []

        quote_item_description = str(payload.get("quote_item_description", "") or "").strip()
        if quote_item_description:
            sections.append(quote_item_description)

        order_notes = str(getattr(order_def, "notes", "") or payload.get("order_notes", "") or "").strip()
        if order_notes:
            sections.append(f"Notatki zamowienia: {order_notes}")

        calendar_note = str(getattr(order_def, "calendar_note", "") or payload.get("order_calendar_note", "") or "").strip()
        if calendar_note:
            sections.append(f"Uwagi kalendarza: {calendar_note}")

        if order_def is None:
            fallback_lines: list[str] = []
            order_status = str(payload.get("order_status", "") or "").strip()
            calendar_stage = str(payload.get("order_calendar_stage", "") or "").strip()
            calendar_date = str(payload.get("order_calendar_date", "") or "").strip()
            site_address = str(payload.get("site_address", "") or "").strip()
            if order_status:
                fallback_lines.append(f"Status zamowienia: {order_status}")
            if calendar_stage or calendar_date:
                label = " / ".join(part for part in (calendar_stage, calendar_date) if part)
                fallback_lines.append(f"Kalendarz: {label}")
            if site_address:
                fallback_lines.append(f"Adres realizacji: {site_address}")
            if fallback_lines:
                sections.append("\n".join(fallback_lines))

        return "\n\n".join(section for section in sections if section)

    def start_new_wall_from_order_context(self, context: dict | None = None) -> None:
        payload = context if isinstance(context, dict) else {}
        quote_item_name = str(payload.get("quote_item_name", "") or "").strip()
        quote_item_kind = str(payload.get("quote_item_kind", "") or "").strip()
        order_name = str(payload.get("order_name", "") or "").strip()
        order_def = self._order_store.get(order_name) if order_name else None
        self._order_id_context = str(
            payload.get("order_id", "") or getattr(order_def, "order_id", "") or ""
        ).strip()
        client_name = str(payload.get("client_name", "") or getattr(order_def, "client_name", "") or "").strip()
        worker_name = str(payload.get("worker_name", "") or getattr(order_def, "worker_name", "") or "").strip()
        self._wall = WallLayoutDef(
            name=quote_item_name or "Sciana 1",
            client_name=client_name,
            order_name=order_name,
            quote_item_name=quote_item_name,
            quote_item_kind=quote_item_kind,
            quote_item_reference=str(payload.get("quote_item_reference", "") or "").strip()
            or (f"{quote_item_name} ({quote_item_kind})" if quote_item_name and quote_item_kind else quote_item_name),
            worker_name=worker_name,
            notes=self._build_wall_notes_from_order_context(payload, order_def),
        )
        self._wall.photos = self._load_architect_reference_photos(
            order_name=order_name,
            candidate_names=(self._wall.name, quote_item_name),
        )
        self._selected_obstacle_index = -1
        self._set_selected_obstacle_index_on_previews(-1)
        self._loaded_wall_name = ""
        self._push_wall_to_ui()
        self._refresh_all()
        if self._wall.photos:
            self.blk_photos.set_expanded(True)
        if quote_item_name:
            kind_suffix = f" ({quote_item_kind})" if quote_item_kind else ""
            ref_suffix = f" Zaladowano {len(self._wall.photos)} referencje." if self._wall.photos else ""
            self._set_store_status(
                f'Gotowa nowa sciana dla pozycji "{quote_item_name}"{kind_suffix}.{ref_suffix}',
                ok=True,
            )
        elif self._wall.client_name or self._wall.order_name or self._wall.worker_name:
            ref_suffix = f" Zaladowano {len(self._wall.photos)} referencje." if self._wall.photos else ""
            self._set_store_status(f"Gotowa nowa sciana z danymi zamowienia.{ref_suffix}", ok=True)
        else:
            self._set_store_status("Gotowa nowa sciana.", ok=True)

    def _refresh_left_zone_toggle_button(self) -> None:
        if not hasattr(self, "left_zone_toggle"):
            return
        if self._left_zone_visible:
            self.left_zone_toggle.setText("Ukryj lewy panel")
        else:
            self.left_zone_toggle.setText("Pokaz lewy panel")

    def _toggle_left_zone(self) -> None:
        if not hasattr(self, "main_splitter"):
            return
        sizes = list(self.main_splitter.sizes())
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
            target_left = max(220, int(self._left_zone_last_width or 390))
            target_left = min(target_left, max(220, total_main - 300))
            restored_center = max(300, total_main - target_left)
            self._left_zone_visible = True
            self.left_zone.show()
            self.main_splitter.setSizes([target_left, restored_center, right])
        self._refresh_left_zone_toggle_button()

    def _toggle_right_zone(self) -> None:
        self._right_zone_visible = not self._right_zone_visible
        splitter = getattr(self, "main_splitter", None)
        if splitter is None:
            return
        if self._right_zone_visible:
            self.right_zone.setVisible(True)
            self.right_zone_toggle.setText("Panel informacyjny >")
            sizes = list(splitter.sizes())
            if len(sizes) >= 3:
                sizes[2] = self._right_zone_last_width
                splitter.setSizes(sizes)
        else:
            sizes = list(splitter.sizes())
            if len(sizes) >= 3:
                self._right_zone_last_width = sizes[2]
                sizes[2] = 0
                splitter.setSizes(sizes)
            self.right_zone.setVisible(False)
            self.right_zone_toggle.setText("< Panel informacyjny")

    def start_new_wall(self) -> None:
        self._wall = WallLayoutDef(wall_id=new_wall_id())
        self._order_id_context = ""
        self._selected_obstacle_index = -1
        self._set_selected_obstacle_index_on_previews(-1)
        self._loaded_wall_name = ""
        self._push_wall_to_ui()
        self._refresh_all()
        self._set_store_status("Gotowa nowa sciana.", ok=True)

    def _on_go_to_komplet(self) -> None:
        wall, ok = self._ensure_wall_saved_for_next_step()
        if not ok or wall is None:
            return
        self.sig_open_komplet_requested.emit(self._context_payload_from_wall(wall))

    def _on_back_to_order(self) -> None:
        self.sig_open_order_requested.emit(self._context_payload_from_wall(self._wall))
