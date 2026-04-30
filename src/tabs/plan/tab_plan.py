from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.assembly_resolution_service import resolve_assembly_items, ResolvedAssemblyItem
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.module_store_json import ModuleStoreJson
from src.storage.wall_store_json import WallStoreJson


@dataclass(frozen=True)
class _ModeSpec:
    key: str
    label: str


OBSTACLE_TYPE_PRESETS: dict[str, tuple[float, float, float]] = {
    "window": (1200.0, 1000.0, 0.0),
    "door": (900.0, 2100.0, 0.0),
    "column": (300.0, 2400.0, 0.0),
    "recess": (600.0, 2200.0, 0.0),
    "pipe": (200.0, 2400.0, 150.0),
    "utility": (150.0, 300.0, 300.0),
}

HIGH_MODULE_WARNING_KEYS = {
    "out_of_wall_left",
    "out_of_wall_right",
    "module_overlap",
    "obstacle_intersection_window",
    "obstacle_intersection_door",
}

HIGH_OBSTACLE_WARNING_KEYS = {
    "obstacle_out_of_wall",
    "obstacle_invalid_size",
    "overlapping_obstacles",
}


class _SceneModuleItem(QGraphicsRectItem):
    def __init__(
        self,
        resolved: ResolvedAssemblyItem,
        scene_index: int,
        has_warning: bool,
        warning_severity: str,
        click_cb,
    ) -> None:
        super().__init__(
            float(resolved.x_mm),
            float(resolved.y_mm),
            max(20.0, float(resolved.width_mm)),
            max(20.0, float(resolved.height_mm)),
        )
        self.resolved = resolved
        self.scene_index = int(scene_index)
        self._has_warning = bool(has_warning)
        self._warning_severity = str(warning_severity or "none").strip().lower()
        self._click_cb = click_cb
        self._selected = False
        self.setPen(QPen(QColor("#1f2937"), 1.4))
        self.setBrush(QBrush(QColor("#dbeafe")))
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._apply_style()

    def set_selected_visual(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setPen(QPen(QColor("#1d4ed8"), 2.2))
            self.setBrush(QBrush(QColor("#bfdbfe")))
            return
        if self._has_warning:
            if self._warning_severity == "high":
                self.setPen(QPen(QColor("#b91c1c"), 2.2))
                self.setBrush(QBrush(QColor("#fee2e2")))
            else:
                self.setPen(QPen(QColor("#ea580c"), 2.0))
                self.setBrush(QBrush(QColor("#ffedd5")))
            return
        if bool(self.resolved.has_collision):
            self.setPen(QPen(QColor("#b91c1c"), 1.8))
            self.setBrush(QBrush(QColor("#fee2e2")))
            return
        self.setPen(QPen(QColor("#1f2937"), 1.4))
        self.setBrush(QBrush(QColor("#dbeafe")))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._click_cb(self.scene_index)
        super().mousePressEvent(event)


class _SceneObstacleItem(QGraphicsRectItem):
    def __init__(self, obstacle_id: str, has_warning: bool, warning_severity: str, click_cb) -> None:
        super().__init__(0.0, 0.0, 10.0, 10.0)
        self.obstacle_id = str(obstacle_id)
        self._click_cb = click_cb
        self._selected = False
        self._has_warning = bool(has_warning)
        self._warning_severity = str(warning_severity or "none").strip().lower()
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._apply_style()

    def set_selected_visual(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setPen(QPen(QColor("#7c2d12"), 2.4))
            self.setBrush(QBrush(QColor(254, 215, 170, 220)))
            return
        if self._has_warning:
            if self._warning_severity == "high":
                self.setPen(QPen(QColor("#dc2626"), 2.0, Qt.PenStyle.DashLine))
                self.setBrush(QBrush(QColor(254, 202, 202, 180)))
            else:
                self.setPen(QPen(QColor("#ea580c"), 2.0, Qt.PenStyle.DashLine))
                self.setBrush(QBrush(QColor(254, 215, 170, 180)))
            return
        self.setPen(QPen(QColor("#ea580c"), 1.6, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor(254, 215, 170, 120)))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._click_cb(self.obstacle_id)
        super().mousePressEvent(event)


class TabPlan(QWidget):
    sig_active_module_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._assembly_store = AssemblyStoreJson()
        self._wall_store = WallStoreJson()
        self._module_store = ModuleStoreJson()
        self._catalog_store = CatalogStoreJson()

        self._modes = [
            _ModeSpec("projekt", "Projekt"),
            _ModeSpec("sciana", "Sciana"),
            _ModeSpec("modul", "Modul"),
            _ModeSpec("komplet", "Komplet"),
        ]
        self._mode_key = "projekt"
        self._resolved_items: list[ResolvedAssemblyItem] = []
        self._module_scene_payload: list[dict[str, Any]] = []
        self._obstacle_scene_payload: list[dict[str, Any]] = []
        self._selected_item: ResolvedAssemblyItem | None = None
        self._selected_scene_index: int = -1
        self._scene_items: list[_SceneModuleItem] = []
        self._obstacle_items: list[_SceneObstacleItem] = []
        self._selected_obstacle_id: str = ""
        self._obstacle_focus_cursor: dict[str, int] = {}
        self._module_obstacle_focus_cursor: dict[int, int] = {}
        self._tree_items_by_scene_index: dict[int, QTreeWidgetItem] = {}
        self._layout_summary: dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_mode_bar())
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        self._left_panel = self._build_left_panel()
        splitter.addWidget(self._left_panel)
        self._center_panel = self._build_center_panel()
        splitter.addWidget(self._center_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 980])

        self._reload_context()

    def _build_mode_bar(self) -> QWidget:
        card = QFrame(self)
        card.setStyleSheet("QFrame { border: 1px solid #dbe4f0; border-radius: 10px; background: #f8fafc; }")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        title = QLabel("Workspace")
        title.setStyleSheet("font-size: 14px; font-weight: 800; color: #0f172a;")
        lay.addWidget(title)
        lay.addSpacing(8)

        self._mode_buttons: dict[str, QPushButton] = {}
        for spec in self._modes:
            btn = QPushButton(spec.label, card)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, key=spec.key: self._set_mode(key))
            lay.addWidget(btn)
            self._mode_buttons[spec.key] = btn

        lay.addStretch(1)
        refresh_btn = QPushButton("Odswiez", card)
        refresh_btn.clicked.connect(self._reload_context)
        lay.addWidget(refresh_btn)
        self._apply_mode_button_styles()
        return card

    def _build_left_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setStyleSheet("QFrame { border: 1px solid #dbe4f0; border-radius: 10px; background: #ffffff; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        context_title = QLabel("Kontekst")
        context_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #0f172a;")
        lay.addWidget(context_title)

        self.cb_wall = QComboBox(panel)
        self.cb_wall.currentIndexChanged.connect(self._on_wall_changed)
        lay.addWidget(self._labeled_row("Sciana", self.cb_wall))

        self.cb_assembly = QComboBox(panel)
        self.cb_assembly.currentIndexChanged.connect(self._on_assembly_changed)
        lay.addWidget(self._labeled_row("Komplet", self.cb_assembly))
        self.lbl_workspace_state = QLabel("-", panel)
        self.lbl_workspace_state.setWordWrap(True)
        self.lbl_workspace_state.setStyleSheet("font-size: 11px; color: #64748b;")
        lay.addWidget(self.lbl_workspace_state)

        self._context_stack = QStackedWidget(panel)
        lay.addWidget(self._context_stack, 1)

        self._ctx_projekt = self._build_context_projekt()
        self._ctx_sciana = self._build_context_sciana()
        self._ctx_modul = self._build_context_modul()
        self._ctx_komplet = self._build_context_komplet()

        self._context_stack.addWidget(self._ctx_projekt)
        self._context_stack.addWidget(self._ctx_sciana)
        self._context_stack.addWidget(self._ctx_modul)
        self._context_stack.addWidget(self._ctx_komplet)
        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setStyleSheet("QFrame { border: 1px solid #dbe4f0; border-radius: 10px; background: #ffffff; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        title = QLabel("Scena workspace")
        title.setStyleSheet("font-size: 13px; font-weight: 800; color: #0f172a;")
        lay.addWidget(title)

        self._scene = QGraphicsScene(self)
        self._scene_view = QGraphicsView(self._scene, panel)
        self._scene_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._scene_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._scene_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._scene_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._scene_view.setStyleSheet("QGraphicsView { border: none; background: #f8fafc; }")
        lay.addWidget(self._scene_view, 1)

        self._scene_hint = QLabel("-", panel)
        self._scene_hint.setWordWrap(True)
        self._scene_hint.setStyleSheet("color: #475569; font-size: 11px;")
        lay.addWidget(self._scene_hint)
        return panel

    def _build_context_projekt(self) -> QWidget:
        box = QWidget(self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.lbl_project_summary = QLabel("-", box)
        self.lbl_project_summary.setWordWrap(True)
        lay.addWidget(self.lbl_project_summary)
        lay.addStretch(1)
        return box

    def _build_context_sciana(self) -> QWidget:
        box = QWidget(self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.lbl_wall_summary = QLabel("-", box)
        self.lbl_wall_summary.setWordWrap(True)
        lay.addWidget(self.lbl_wall_summary)

        self.lst_obstacles = QListWidget(box)
        self.lst_obstacles.itemSelectionChanged.connect(self._on_obstacle_list_selection_changed)
        lay.addWidget(self.lst_obstacles, 1)

        self.cb_obstacle_filter = QComboBox(box)
        self.cb_obstacle_filter.addItem("Wszystkie przeszkody", "all")
        self.cb_obstacle_filter.addItem("Tylko konfliktowe", "conflict")
        self.cb_obstacle_filter.addItem("Tylko krytyczne (H)", "high")
        self.cb_obstacle_filter.currentIndexChanged.connect(lambda _=0: self._refresh_obstacle_context_ui())
        lay.addWidget(self.cb_obstacle_filter)

        self.lbl_obstacle_context = QLabel("Przeszkoda: [brak]", box)
        self.lbl_obstacle_context.setWordWrap(True)
        self.lbl_obstacle_context.setStyleSheet("font-size: 11px; color: #334155;")
        lay.addWidget(self.lbl_obstacle_context)

        row1 = QWidget(box)
        row1_l = QHBoxLayout(row1)
        row1_l.setContentsMargins(0, 0, 0, 0)
        row1_l.setSpacing(6)
        self.cb_obstacle_type = QComboBox(row1)
        for value, label in (
            ("window", "window"),
            ("door", "door"),
            ("column", "column"),
            ("recess", "recess"),
            ("pipe", "pipe"),
            ("utility", "utility"),
        ):
            self.cb_obstacle_type.addItem(label, value)
        self.cb_obstacle_type.currentIndexChanged.connect(self._on_obstacle_type_changed)
        self.ed_obstacle_label = QLineEdit(row1)
        self.ed_obstacle_label.setPlaceholderText("etykieta")
        row1_l.addWidget(self.cb_obstacle_type)
        row1_l.addWidget(self.ed_obstacle_label)
        lay.addWidget(row1)

        row2 = QWidget(box)
        row2_l = QHBoxLayout(row2)
        row2_l.setContentsMargins(0, 0, 0, 0)
        row2_l.setSpacing(6)
        self.sp_obstacle_x = QDoubleSpinBox(row2)
        self.sp_obstacle_x.setRange(-10000.0, 100000.0)
        self.sp_obstacle_x.setDecimals(1)
        self.sp_obstacle_x.setPrefix("X ")
        self.sp_obstacle_x.setSuffix(" mm")
        self.sp_obstacle_y = QDoubleSpinBox(row2)
        self.sp_obstacle_y.setRange(-10000.0, 100000.0)
        self.sp_obstacle_y.setDecimals(1)
        self.sp_obstacle_y.setPrefix("Y ")
        self.sp_obstacle_y.setSuffix(" mm")
        row2_l.addWidget(self.sp_obstacle_x)
        row2_l.addWidget(self.sp_obstacle_y)
        lay.addWidget(row2)

        row3 = QWidget(box)
        row3_l = QHBoxLayout(row3)
        row3_l.setContentsMargins(0, 0, 0, 0)
        row3_l.setSpacing(6)
        self.sp_obstacle_w = QDoubleSpinBox(row3)
        self.sp_obstacle_w.setRange(1.0, 100000.0)
        self.sp_obstacle_w.setDecimals(1)
        self.sp_obstacle_w.setPrefix("W ")
        self.sp_obstacle_w.setSuffix(" mm")
        self.sp_obstacle_h = QDoubleSpinBox(row3)
        self.sp_obstacle_h.setRange(1.0, 100000.0)
        self.sp_obstacle_h.setDecimals(1)
        self.sp_obstacle_h.setPrefix("H ")
        self.sp_obstacle_h.setSuffix(" mm")
        row3_l.addWidget(self.sp_obstacle_w)
        row3_l.addWidget(self.sp_obstacle_h)
        self.sp_obstacle_zone = QDoubleSpinBox(row3)
        self.sp_obstacle_zone.setRange(0.0, 5000.0)
        self.sp_obstacle_zone.setDecimals(1)
        self.sp_obstacle_zone.setPrefix("Z ")
        self.sp_obstacle_zone.setSuffix(" mm")
        self.sp_obstacle_zone.setToolTip("Strefa ostrzegawcza przeszkody (szczegolnie utility/pipe)")
        row3_l.addWidget(self.sp_obstacle_zone)
        lay.addWidget(row3)

        row4 = QWidget(box)
        row4_l = QHBoxLayout(row4)
        row4_l.setContentsMargins(0, 0, 0, 0)
        row4_l.setSpacing(6)
        self.btn_obstacle_new = QPushButton("Nowa", row4)
        self.btn_obstacle_new.clicked.connect(self._on_obstacle_new)
        self.btn_obstacle_add = QPushButton("Dodaj", row4)
        self.btn_obstacle_add.clicked.connect(self._on_obstacle_add)
        self.btn_obstacle_update = QPushButton("Aktualizuj", row4)
        self.btn_obstacle_update.clicked.connect(self._on_obstacle_update)
        self.btn_obstacle_delete = QPushButton("Usun", row4)
        self.btn_obstacle_delete.clicked.connect(self._on_obstacle_delete)
        row4_l.addWidget(self.btn_obstacle_new)
        row4_l.addWidget(self.btn_obstacle_add)
        row4_l.addWidget(self.btn_obstacle_update)
        row4_l.addWidget(self.btn_obstacle_delete)
        lay.addWidget(row4)

        self.btn_obstacle_clamp = QPushButton("Napraw pozycje w scianie", box)
        self.btn_obstacle_clamp.clicked.connect(self._on_obstacle_clamp_to_wall)
        lay.addWidget(self.btn_obstacle_clamp)

        self.btn_obstacle_focus_module = QPushButton("Pokaz kolidujacy modul", box)
        self.btn_obstacle_focus_module.clicked.connect(self._focus_first_module_conflict_from_obstacle)
        lay.addWidget(self.btn_obstacle_focus_module)

        lay.addStretch(1)
        return box

    def _build_context_modul(self) -> QWidget:
        box = QWidget(self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.lbl_module_summary = QLabel("Brak aktywnego modulu.", box)
        self.lbl_module_summary.setWordWrap(True)
        lay.addWidget(self.lbl_module_summary)

        actions_row1 = QWidget(box)
        actions_row1_lay = QHBoxLayout(actions_row1)
        actions_row1_lay.setContentsMargins(0, 0, 0, 0)
        actions_row1_lay.setSpacing(6)
        self.btn_move_left = QPushButton("Przesun w kolejnosci <-", actions_row1)
        self.btn_move_left.clicked.connect(lambda: self._move_selected_in_order(-1))
        self.btn_move_right = QPushButton("Przesun w kolejnosci ->", actions_row1)
        self.btn_move_right.clicked.connect(lambda: self._move_selected_in_order(1))
        actions_row1_lay.addWidget(self.btn_move_left)
        actions_row1_lay.addWidget(self.btn_move_right)
        lay.addWidget(actions_row1)

        actions_row2 = QWidget(box)
        actions_row2_lay = QHBoxLayout(actions_row2)
        actions_row2_lay.setContentsMargins(0, 0, 0, 0)
        actions_row2_lay.setSpacing(6)
        self.btn_align_start = QPushButton("Wyrownaj do startu", actions_row2)
        self.btn_align_start.clicked.connect(self._align_selected_to_start)
        self.btn_align_end = QPushButton("Wyrownaj do konca", actions_row2)
        self.btn_align_end.clicked.connect(self._align_selected_to_end)
        actions_row2_lay.addWidget(self.btn_align_start)
        actions_row2_lay.addWidget(self.btn_align_end)
        lay.addWidget(actions_row2)

        manual_row = QWidget(box)
        manual_row_lay = QHBoxLayout(manual_row)
        manual_row_lay.setContentsMargins(0, 0, 0, 0)
        manual_row_lay.setSpacing(6)
        self.sp_pos_x = QDoubleSpinBox(manual_row)
        self.sp_pos_x.setRange(-10000.0, 100000.0)
        self.sp_pos_x.setDecimals(1)
        self.sp_pos_x.setSingleStep(10.0)
        self.sp_pos_x.setPrefix("X ")
        self.sp_pos_x.setSuffix(" mm")
        self.sp_spacing_after = QDoubleSpinBox(manual_row)
        self.sp_spacing_after.setRange(0.0, 10000.0)
        self.sp_spacing_after.setDecimals(1)
        self.sp_spacing_after.setSingleStep(5.0)
        self.sp_spacing_after.setPrefix("S ")
        self.sp_spacing_after.setSuffix(" mm")
        self.btn_apply_manual = QPushButton("Zastosuj pozycje", manual_row)
        self.btn_apply_manual.clicked.connect(self._apply_selected_manual_position_and_spacing)
        manual_row_lay.addWidget(self.sp_pos_x)
        manual_row_lay.addWidget(self.sp_spacing_after)
        manual_row_lay.addWidget(self.btn_apply_manual)
        lay.addWidget(manual_row)

        self.btn_normalize_layout = QPushButton("Uloz sekwencyjnie", box)
        self.btn_normalize_layout.clicked.connect(self._normalize_layout_positions)
        lay.addWidget(self.btn_normalize_layout)

        self.btn_open_modul_tab = QPushButton("Otworz aktywny modul", box)
        self.btn_open_modul_tab.clicked.connect(self._open_active_module_in_modul_tab)
        lay.addWidget(self.btn_open_modul_tab)

        self.btn_focus_obstacle_conflict = QPushButton("Pokaz kolidujaca przeszkode", box)
        self.btn_focus_obstacle_conflict.clicked.connect(self._focus_first_obstacle_conflict)
        lay.addWidget(self.btn_focus_obstacle_conflict)
        lay.addStretch(1)
        return box

    def _build_context_komplet(self) -> QWidget:
        box = QWidget(self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        info = QLabel("Minimalna struktura: Sciana -> Komplet -> Moduly", box)
        info.setWordWrap(True)
        lay.addWidget(info)
        self.lbl_komplet_summary = QLabel("-", box)
        self.lbl_komplet_summary.setWordWrap(True)
        self.lbl_komplet_summary.setStyleSheet("font-size: 11px; color: #334155;")
        lay.addWidget(self.lbl_komplet_summary)

        self.tree_komplet = QTreeWidget(box)
        self.tree_komplet.setHeaderLabels(["Struktura"])
        self.tree_komplet.header().setStretchLastSection(True)
        self.tree_komplet.itemClicked.connect(self._on_komplet_tree_item_clicked)
        lay.addWidget(self.tree_komplet, 1)
        return box

    def _labeled_row(self, title: str, widget: QWidget) -> QWidget:
        row = QWidget(self)
        lay = QVBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lab = QLabel(title, row)
        lab.setStyleSheet("font-size: 11px; color: #334155; font-weight: 600;")
        lay.addWidget(lab)
        lay.addWidget(widget)
        return row

    def _set_mode(self, mode_key: str) -> None:
        if mode_key not in {spec.key for spec in self._modes}:
            return
        self._mode_key = mode_key
        self._apply_mode_button_styles()
        self._sync_context_stack()
        self._refresh_left_context()

    def _apply_mode_button_styles(self) -> None:
        for key, btn in self._mode_buttons.items():
            if key == self._mode_key:
                btn.setStyleSheet(
                    "QPushButton { background: #1d4ed8; color: #ffffff; border: none; border-radius: 8px; padding: 6px 12px; font-weight: 800; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #eef2ff; color: #1e3a8a; border: 1px solid #dbeafe; border-radius: 8px; padding: 6px 12px; font-weight: 700; }"
                )

    def _sync_context_stack(self) -> None:
        index_map = {"projekt": 0, "sciana": 1, "modul": 2, "komplet": 3}
        self._context_stack.setCurrentIndex(index_map.get(self._mode_key, 0))

    def _reload_context(self) -> None:
        self._fill_wall_combo()
        self._fill_assembly_combo()
        self._load_resolved_items()
        self._sync_selected_item_from_scene_index()
        self._sync_module_payload_selection()
        self._recompute_layout_warnings_and_summary()
        self._sync_obstacle_payload_selection()
        self._refresh_left_context()
        self._rebuild_structure_tree()
        self._render_scene()

    def _fill_wall_combo(self) -> None:
        walls = self._wall_store.list_layouts()
        current = self.cb_wall.currentData()
        self.cb_wall.blockSignals(True)
        self.cb_wall.clear()
        self.cb_wall.addItem("[dowolna]", "")
        for wall in walls:
            wall_name = str(getattr(wall, "name", "") or "")
            self.cb_wall.addItem(wall_name, wall_name)
        idx = max(0, self.cb_wall.findData(current))
        self.cb_wall.setCurrentIndex(idx)
        self.cb_wall.blockSignals(False)

    def _fill_assembly_combo(self) -> None:
        assemblies = self._assembly_store.list_assemblies()
        wall_name_filter = str(self.cb_wall.currentData() or "")
        current = self.cb_assembly.currentData()
        real_items_count = 0
        self.cb_assembly.blockSignals(True)
        self.cb_assembly.clear()
        for assembly in assemblies:
            wall_name = str(getattr(assembly, "wall_name", "") or "")
            if wall_name_filter and wall_name != wall_name_filter:
                continue
            name = str(getattr(assembly, "name", "") or "")
            aid = str(getattr(assembly, "assembly_id", "") or "")
            label = f"{name} ({aid})" if aid else name
            self.cb_assembly.addItem(label, aid or name)
            real_items_count += 1
        if self.cb_assembly.count() == 0:
            self.cb_assembly.addItem("[brak kompletow]", "")
        self.cb_assembly.setEnabled(real_items_count > 0)
        idx = max(0, self.cb_assembly.findData(current))
        self.cb_assembly.setCurrentIndex(idx)
        self.cb_assembly.blockSignals(False)

    def _current_assembly(self):
        assembly_key = str(self.cb_assembly.currentData() or "")
        if not assembly_key:
            return None
        assembly = self._assembly_store.get(assembly_key)
        if assembly is not None:
            return assembly
        for candidate in self._assembly_store.list_assemblies():
            if str(getattr(candidate, "name", "") or "") == assembly_key:
                return candidate
        return None

    def _load_resolved_items(self) -> None:
        self._resolved_items = []
        self._module_scene_payload = []
        self._selected_item = None
        self._selected_scene_index = -1
        assembly = self._current_assembly()
        if assembly is None:
            return
        wall_name = str(getattr(assembly, "wall_name", "") or "")
        linked_wall = self._wall_store.get(wall_name) if wall_name else None
        try:
            self._resolved_items = resolve_assembly_items(
                assembly=assembly,
                catalog=self._catalog_store,
                linked_wall=linked_wall,
            )
        except Exception:
            self._resolved_items = []
            return

        if self._resolved_items:
            self._selected_item = self._resolved_items[0]
            self._selected_scene_index = 0
        self._module_scene_payload = self._build_module_scene_payload(assembly, self._resolved_items)
        self._recompute_layout_warnings_and_summary()

    def _build_module_scene_payload(
        self,
        assembly: Any,
        resolved_items: list[ResolvedAssemblyItem],
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        assembly_id = str(getattr(assembly, "assembly_id", "") or "")
        assembly_name = str(getattr(assembly, "name", "") or "")
        wall_name = str(getattr(assembly, "wall_name", "") or "")
        for index, resolved in enumerate(resolved_items):
            module = resolved.module
            module_id = str(getattr(module, "module_id", "") or "")
            module_name = str(getattr(module, "name", "") or resolved.display_name or "Modul")
            payload.append(
                {
                    "scene_index": int(index),
                    "module_id": module_id,
                    "wall_name": wall_name,
                    "komplet_id": assembly_id,
                    "komplet_name": assembly_name,
                    "pos_x": float(resolved.x_mm),
                    "pos_y": float(resolved.y_mm),
                    "width": float(resolved.width_mm),
                    "height": float(resolved.height_mm),
                    "depth": float(resolved.depth_mm),
                    "occupied_width_mm": float(resolved.width_mm),
                    "display_label": module_name,
                    "sequence_index": int(index),
                    "spacing_after_mm": 0.0,
                    "warning_flags": [],
                    "is_selected": bool(self._selected_item is resolved),
                }
            )
        return payload

    def _build_obstacle_scene_payload(self, wall: Any) -> list[dict[str, Any]]:
        if wall is None:
            return []
        wall_name = str(getattr(wall, "name", "") or "")
        wall_width = max(1.0, float(getattr(wall, "wall_a_width_mm", 3000.0) or 3000.0))
        wall_height = max(1.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
        payload: list[dict[str, Any]] = []
        for index, obstacle in enumerate(list(getattr(wall, "obstacles", []) or [])):
            width = max(1.0, float(getattr(obstacle, "width_mm", 0.0) or 0.0))
            height = max(1.0, float(getattr(obstacle, "height_mm", 0.0) or 0.0))
            pos_x = float(getattr(obstacle, "x_mm", 0.0) or 0.0)
            bottom_offset = float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0)
            pos_y = float(max(0.0, wall_height - bottom_offset - height))
            obstacle_type = str(getattr(obstacle, "kind", "") or "obstacle").strip().lower()
            label = str(getattr(obstacle, "name", "") or obstacle_type or f"obstacle_{index+1}")
            obstacle_id = f"{wall_name}:{index}"
            warning_zone = max(0.0, float(getattr(obstacle, "depth_mm", 0.0) or 0.0))
            warning_flags: list[str] = []
            if width <= 1.0 or height <= 1.0:
                warning_flags.append("obstacle_invalid_size")
            if pos_x < 0.0 or (pos_x + width) > wall_width or pos_y < 0.0 or (pos_y + height) > wall_height:
                warning_flags.append("obstacle_out_of_wall")
            payload.append(
                {
                    "obstacle_id": obstacle_id,
                    "obstacle_index": int(index),
                    "wall_name": wall_name,
                    "obstacle_type": obstacle_type,
                    "pos_x_mm": float(pos_x),
                    "pos_y_mm": float(pos_y),
                    "width_mm": float(width),
                    "height_mm": float(height),
                    "warning_zone_mm": float(warning_zone),
                    "label": label,
                    "warning_flags": warning_flags,
                    "intersecting_module_ids": [],
                    "intersecting_module_count": 0,
                    "is_selected": bool(obstacle_id == self._selected_obstacle_id),
                }
            )
        return payload

    @staticmethod
    def _rects_intersect(ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float) -> bool:
        if aw <= 0.0 or ah <= 0.0 or bw <= 0.0 or bh <= 0.0:
            return False
        return (ax < bx + bw) and (ax + aw > bx) and (ay < by + bh) and (ay + ah > by)

    def _sorted_payload_rows(self) -> list[dict[str, Any]]:
        return sorted(
            self._module_scene_payload,
            key=lambda row: (
                int(row.get("sequence_index", 0)),
                float(row.get("pos_x", 0.0)),
                int(row.get("scene_index", 0)),
            ),
        )

    def _selected_payload_row(self) -> dict[str, Any] | None:
        if self._selected_scene_index < 0:
            return None
        for row in self._module_scene_payload:
            if int(row.get("scene_index", -1)) == self._selected_scene_index:
                return row
        return None

    def _display_module_ref(self, module_ref: str) -> str:
        ref = str(module_ref or "")
        if not ref:
            return "-"
        for row in self._module_scene_payload:
            row_module_id = str(row.get("module_id", "") or "")
            row_label = str(row.get("display_label", "") or "")
            if ref == row_module_id:
                return f"{row_label} ({ref})" if row_label and row_label != ref else ref
            if ref == row_label:
                return row_label
        return ref

    def _module_warning_severity(self, row: dict[str, Any]) -> str:
        warning_flags = {str(flag or "") for flag in list(row.get("warning_flags", []))}
        if warning_flags & HIGH_MODULE_WARNING_KEYS:
            return "high"
        for item in list(row.get("obstacle_warnings", [])):
            if str(item.get("severity", "") or "").strip().lower() == "high":
                return "high"
        if warning_flags:
            return "medium"
        return "none"

    def _obstacle_warning_severity(self, row: dict[str, Any]) -> str:
        warning_flags = {str(flag or "") for flag in list(row.get("warning_flags", []))}
        if warning_flags & HIGH_OBSTACLE_WARNING_KEYS:
            return "high"
        if warning_flags or int(row.get("intersecting_module_count", 0)) > 0:
            return "medium"
        return "none"

    def _obstacle_passes_active_filter(self, row: dict[str, Any]) -> bool:
        mode = str(self.cb_obstacle_filter.currentData() or "all")
        severity = self._obstacle_warning_severity(row)
        if mode == "high":
            return severity == "high"
        if mode == "conflict":
            return severity != "none"
        return True

    def _obstacle_sort_key(self, row: dict[str, Any]) -> tuple[int, str, str]:
        severity = self._obstacle_warning_severity(row)
        rank_map = {"high": 0, "medium": 1, "none": 2}
        rank = int(rank_map.get(severity, 3))
        label = str(row.get("label", "") or "").strip().lower()
        obstacle_type = str(row.get("obstacle_type", "") or "").strip().lower()
        return (rank, label, obstacle_type)

    def _wall_dimensions_for_layout(self) -> tuple[float, float]:
        wall = self._current_wall()
        if wall is not None:
            return (
                max(800.0, float(getattr(wall, "wall_a_width_mm", 3000.0) or 3000.0)),
                max(600.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0)),
            )
        assembly = self._current_assembly()
        if assembly is not None:
            return (
                max(800.0, float(getattr(assembly, "width_mm", 3000.0) or 3000.0)),
                max(600.0, float(getattr(assembly, "height_mm", 2500.0) or 2500.0)),
            )
        return (3000.0, 2500.0)

    def _recompute_layout_warnings_and_summary(self) -> None:
        wall_width, wall_height = self._wall_dimensions_for_layout()
        wall = self._current_wall()
        assembly = self._current_assembly()
        wall_name = str(getattr(wall, "name", "") or getattr(assembly, "wall_name", "") or "[bez sciany]")
        obstacles = list(getattr(wall, "obstacles", []) or []) if wall is not None else []
        self._obstacle_scene_payload = self._build_obstacle_scene_payload(wall)

        for row in self._module_scene_payload:
            row["warning_flags"] = []
            row["obstacle_warnings"] = []

        sorted_rows = self._sorted_payload_rows()
        for row in sorted_rows:
            left = float(row.get("pos_x", 0.0))
            width = max(1.0, float(row.get("width", 0.0)))
            right = left + width
            if left < 0.0:
                row["warning_flags"].append("out_of_wall_left")
            if right > wall_width:
                row["warning_flags"].append("out_of_wall_right")
            if wall is None and str(getattr(assembly, "wall_name", "") or "").strip():
                row["warning_flags"].append("missing_wall_reference")

        sequence_values = [int(row.get("sequence_index", 0)) for row in sorted_rows]
        expected = list(range(len(sorted_rows)))
        invalid_order = sequence_values != expected
        if invalid_order:
            for row in sorted_rows:
                if "invalid_layout_order" not in row["warning_flags"]:
                    row["warning_flags"].append("invalid_layout_order")

        for i, row in enumerate(sorted_rows):
            left = float(row.get("pos_x", 0.0))
            width = max(1.0, float(row.get("width", 0.0)))
            right = left + width
            for other in sorted_rows[:i]:
                o_left = float(other.get("pos_x", 0.0))
                o_width = max(1.0, float(other.get("width", 0.0)))
                o_right = o_left + o_width
                if (left < o_right) and (right > o_left):
                    if "module_overlap" not in row["warning_flags"]:
                        row["warning_flags"].append("module_overlap")
                    if "module_overlap" not in other["warning_flags"]:
                        other["warning_flags"].append("module_overlap")

        for i, obstacle_row in enumerate(self._obstacle_scene_payload):
            ax = float(obstacle_row.get("pos_x_mm", 0.0))
            ay = float(obstacle_row.get("pos_y_mm", 0.0))
            aw = max(1.0, float(obstacle_row.get("width_mm", 0.0)))
            ah = max(1.0, float(obstacle_row.get("height_mm", 0.0)))
            for other in self._obstacle_scene_payload[:i]:
                bx = float(other.get("pos_x_mm", 0.0))
                by = float(other.get("pos_y_mm", 0.0))
                bw = max(1.0, float(other.get("width_mm", 0.0)))
                bh = max(1.0, float(other.get("height_mm", 0.0)))
                if self._rects_intersect(ax, ay, aw, ah, bx, by, bw, bh):
                    if "overlapping_obstacles" not in list(obstacle_row.get("warning_flags", [])):
                        obstacle_row["warning_flags"] = [*list(obstacle_row.get("warning_flags", [])), "overlapping_obstacles"]
                    if "overlapping_obstacles" not in list(other.get("warning_flags", [])):
                        other["warning_flags"] = [*list(other.get("warning_flags", [])), "overlapping_obstacles"]

        for row in sorted_rows:
            scene_index = int(row.get("scene_index", -1))
            if scene_index < 0 or scene_index >= len(self._resolved_items):
                continue
            resolved = self._resolved_items[scene_index]
            mod_x = float(row.get("pos_x", 0.0))
            mod_y = float(resolved.y_mm)
            mod_w = max(1.0, float(row.get("width", 0.0)))
            mod_h = max(1.0, float(row.get("height", 0.0)))
            for obstacle_index, obstacle in enumerate(obstacles):
                obs_w = max(1.0, float(getattr(obstacle, "width_mm", 0.0) or 0.0))
                obs_h = max(1.0, float(getattr(obstacle, "height_mm", 0.0) or 0.0))
                obs_x = max(0.0, float(getattr(obstacle, "x_mm", 0.0) or 0.0))
                obs_bottom = max(0.0, float(getattr(obstacle, "bottom_offset_mm", 0.0) or 0.0))
                obs_y = max(0.0, wall_height - obs_bottom - obs_h)
                kind = str(getattr(obstacle, "kind", "") or "obstacle").strip().lower()
                warning_zone = max(0.0, float(getattr(obstacle, "depth_mm", 0.0) or 0.0))
                zone_expand = warning_zone if kind in {"utility", "socket", "pipe", "shaft"} else 0.0
                check_x = obs_x - zone_expand
                check_y = obs_y - zone_expand
                check_w = obs_w + (2.0 * zone_expand)
                check_h = obs_h + (2.0 * zone_expand)
                if self._rects_intersect(mod_x, mod_y, mod_w, mod_h, check_x, check_y, check_w, check_h):
                    kind_map = {
                        "window": "obstacle_intersection_window",
                        "door": "obstacle_intersection_door",
                        "column": "obstacle_intersection_column",
                        "recess": "obstacle_intersection_recess",
                        "pipe": "obstacle_intersection_pipe",
                        "shaft": "obstacle_intersection_pipe",
                        "utility": "obstacle_intersection_utility",
                        "socket": "obstacle_intersection_utility",
                    }
                    warning_key = kind_map.get(kind, "obstacle_intersection")
                    if warning_key not in row["warning_flags"]:
                        row["warning_flags"].append(warning_key)
                    obstacle_payload = (
                        self._obstacle_scene_payload[obstacle_index]
                        if 0 <= obstacle_index < len(self._obstacle_scene_payload)
                        else {}
                    )
                    obstacle_id = str(obstacle_payload.get("obstacle_id", "") or "")
                    existing_ids = {
                        str(item.get("obstacle_id", "") or "")
                        for item in list(row.get("obstacle_warnings", []))
                    }
                    if obstacle_id not in existing_ids:
                        row["obstacle_warnings"].append(
                            {
                                "warning_type": warning_key,
                                "obstacle_id": obstacle_id,
                                "obstacle_type": str(obstacle_payload.get("obstacle_type", "") or kind or "obstacle"),
                                "module_id": str(row.get("module_id", "") or ""),
                                "severity": "high" if warning_key in {"obstacle_intersection_window", "obstacle_intersection_door"} else "medium",
                                "short_message": (
                                    f"Modul koliduje z przeszkoda "
                                    f"{str(obstacle_payload.get('label', '') or str(getattr(obstacle, 'name', '') or kind or 'obstacle'))}"
                                ),
                            }
                        )
                    module_id = str(row.get("module_id", "") or row.get("display_label", "") or "")
                    if module_id:
                        ids = list(obstacle_payload.get("intersecting_module_ids", []) or [])
                        if module_id not in ids:
                            ids.append(module_id)
                        obstacle_payload["intersecting_module_ids"] = ids
                        obstacle_payload["intersecting_module_count"] = len(ids)

        intervals: list[tuple[float, float]] = []
        for row in sorted_rows:
            left = max(0.0, float(row.get("pos_x", 0.0)))
            right = min(wall_width, float(row.get("pos_x", 0.0)) + max(0.0, float(row.get("width", 0.0))))
            if right > left:
                intervals.append((left, right))
        intervals.sort(key=lambda p: p[0])
        merged: list[tuple[float, float]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append((start, end))
            else:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        occupied = sum(end - start for start, end in merged)
        free = max(0.0, wall_width - occupied)

        overlap_count = sum(1 for row in sorted_rows if "module_overlap" in row.get("warning_flags", []))
        out_of_bounds_count = sum(
            1
            for row in sorted_rows
            if ("out_of_wall_left" in row.get("warning_flags", []) or "out_of_wall_right" in row.get("warning_flags", []))
        )
        obstacle_count = sum(
            1
            for row in sorted_rows
            if any(str(flag).startswith("obstacle_intersection") for flag in list(row.get("warning_flags", [])))
        )
        obstacle_conflict_pairs_count = 0
        obstacle_conflicts_by_type: dict[str, int] = {}
        for row in sorted_rows:
            warnings = list(row.get("obstacle_warnings", []))
            obstacle_conflict_pairs_count += len(warnings)
            for item in warnings:
                key = str(item.get("obstacle_type", "") or "obstacle")
                obstacle_conflicts_by_type[key] = int(obstacle_conflicts_by_type.get(key, 0)) + 1
        module_high_warning_count = sum(1 for row in sorted_rows if self._module_warning_severity(row) == "high")
        module_medium_warning_count = sum(1 for row in sorted_rows if self._module_warning_severity(row) == "medium")
        missing_wall_count = sum(1 for row in sorted_rows if "missing_wall_reference" in row.get("warning_flags", []))
        total_warning_count = sum(len(list(row.get("warning_flags", []))) for row in sorted_rows)
        obstacles_by_type: dict[str, int] = {}
        blocking_obstacle_count = 0
        obstacle_high_warning_count = 0
        obstacle_medium_warning_count = 0
        obstacle_out_of_wall_count = 0
        obstacle_invalid_size_count = 0
        for obstacle_row in self._obstacle_scene_payload:
            key = str(obstacle_row.get("obstacle_type", "") or "obstacle")
            obstacles_by_type[key] = int(obstacles_by_type.get(key, 0)) + 1
            warning_flags = set(str(flag or "") for flag in list(obstacle_row.get("warning_flags", [])))
            if "obstacle_out_of_wall" in warning_flags:
                obstacle_out_of_wall_count += 1
            if "obstacle_invalid_size" in warning_flags:
                obstacle_invalid_size_count += 1
            severity = self._obstacle_warning_severity(obstacle_row)
            if severity == "high":
                obstacle_high_warning_count += 1
            elif severity == "medium":
                obstacle_medium_warning_count += 1
            if severity != "none":
                blocking_obstacle_count += 1
        overlapping_obstacle_count = sum(
            1 for row in self._obstacle_scene_payload if "overlapping_obstacles" in list(row.get("warning_flags", []))
        )

        self._layout_summary = {
            "wall_name": wall_name,
            "wall_width_mm": float(wall_width),
            "occupied_width_mm": float(occupied),
            "free_width_mm": float(free),
            "module_count": len(sorted_rows),
            "overlap_count": int(overlap_count),
            "out_of_bounds_count": int(out_of_bounds_count),
            "obstacle_intersection_count": int(obstacle_count),
            "missing_wall_reference_count": int(missing_wall_count),
            "warning_count": int(total_warning_count),
            "invalid_layout_order_count": int(sum(1 for row in sorted_rows if "invalid_layout_order" in row.get("warning_flags", []))),
            "module_high_warning_count": int(module_high_warning_count),
            "module_medium_warning_count": int(module_medium_warning_count),
            "obstacle_count": int(len(self._obstacle_scene_payload)),
            "obstacles_by_type": obstacles_by_type,
            "blocking_obstacle_count": int(blocking_obstacle_count),
            "obstacle_high_warning_count": int(obstacle_high_warning_count),
            "obstacle_medium_warning_count": int(obstacle_medium_warning_count),
            "obstacle_out_of_wall_count": int(obstacle_out_of_wall_count),
            "obstacle_invalid_size_count": int(obstacle_invalid_size_count),
            "intersecting_module_count": int(obstacle_count),
            "obstacle_conflict_pairs_count": int(obstacle_conflict_pairs_count),
            "obstacle_conflicts_by_type": obstacle_conflicts_by_type,
            "overlapping_obstacle_count": int(overlapping_obstacle_count),
        }

    def _current_wall(self):
        assembly = self._current_assembly()
        if assembly is not None:
            wall_name = str(getattr(assembly, "wall_name", "") or "")
            if wall_name:
                wall = self._wall_store.get(wall_name)
                if wall is not None:
                    return wall
        wall_name_filter = str(self.cb_wall.currentData() or "")
        if wall_name_filter:
            return self._wall_store.get(wall_name_filter)
        return None

    def _draw_wall_context(self, wall_width: float, wall_height: float, wall_label: str) -> None:
        wall_rect = QGraphicsRectItem(0.0, 0.0, wall_width, wall_height)
        wall_rect.setPen(QPen(QColor("#334155"), 1.6))
        wall_rect.setBrush(QBrush(QColor("#f8fafc")))
        self._scene.addItem(wall_rect)

        floor_line = self._scene.addLine(
            0.0,
            wall_height,
            wall_width,
            wall_height,
            QPen(QColor("#94a3b8"), 1.2, Qt.PenStyle.DashLine),
        )
        floor_line.setZValue(5.0)

        title = QGraphicsSimpleTextItem(f"Sciana: {wall_label}")
        title.setBrush(QBrush(QColor("#334155")))
        title.setPos(8.0, 8.0)
        self._scene.addItem(title)

        width_label = QGraphicsSimpleTextItem(f"{wall_width:.0f} mm")
        width_label.setBrush(QBrush(QColor("#64748b")))
        width_label.setPos(max(8.0, (wall_width * 0.5) - 40.0), 8.0)
        self._scene.addItem(width_label)

        height_label = QGraphicsSimpleTextItem(f"H {wall_height:.0f} mm")
        height_label.setBrush(QBrush(QColor("#64748b")))
        height_label.setPos(8.0, max(20.0, wall_height - 22.0))
        self._scene.addItem(height_label)

    def _draw_obstacles(self) -> int:
        self._obstacle_items = []
        count = 0
        for row in self._obstacle_scene_payload:
            obstacle_id = str(row.get("obstacle_id", "") or "")
            x = float(row.get("pos_x_mm", 0.0))
            y = float(row.get("pos_y_mm", 0.0))
            width = max(1.0, float(row.get("width_mm", 0.0)))
            height = max(1.0, float(row.get("height_mm", 0.0)))
            has_warning = bool(list(row.get("warning_flags", [])))
            severity = self._obstacle_warning_severity(row)
            has_warning = has_warning or int(row.get("intersecting_module_count", 0)) > 0
            item = _SceneObstacleItem(obstacle_id, has_warning, severity, self._on_scene_obstacle_clicked)
            item.setRect(x, y, width, height)
            item.set_selected_visual(obstacle_id == self._selected_obstacle_id)
            self._scene.addItem(item)
            self._obstacle_items.append(item)

            label_text = str(row.get("label", "") or str(row.get("obstacle_type", "") or "obstacle"))
            intersects = int(row.get("intersecting_module_count", 0))
            severity_tag = "H" if severity == "high" else ("M" if severity == "medium" else "")
            if severity_tag:
                label_text = f"[{severity_tag}] {label_text}"
            if intersects > 0:
                label_text = f"{label_text} [{intersects}]"
            label = QGraphicsSimpleTextItem(label_text)
            label.setBrush(QBrush(QColor("#9a3412")))
            label.setPos(x + 4.0, y + 4.0)
            self._scene.addItem(label)
            count += 1
        return count

    def _render_scene(self) -> None:
        self._scene.clear()
        self._scene_items = []

        assembly = self._current_assembly()
        wall = self._current_wall()
        if assembly is None and wall is None:
            self._scene.addText("Brak danych kompletu. Wybierz komplet po lewej.")
            self._scene_hint.setText("Workspace Phase 1: brak aktywnego kompletu.")
            return

        if wall is not None:
            wall_width = max(800.0, float(getattr(wall, "wall_a_width_mm", 3000.0) or 3000.0))
            wall_height = max(600.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
            wall_label = str(getattr(wall, "name", "") or "[bez sciany]")
        else:
            wall_width = max(800.0, float(getattr(assembly, "width_mm", 3000.0) or 3000.0))
            wall_height = max(600.0, float(getattr(assembly, "height_mm", 2500.0) or 2500.0))
            wall_label = str(getattr(assembly, "wall_name", "") or "[bez sciany]")
        self._draw_wall_context(wall_width, wall_height, wall_label)
        obstacle_count = self._draw_obstacles()

        payload_by_scene_index = {
            int(row.get("scene_index", -1)): row
            for row in self._module_scene_payload
        }
        for index, resolved in enumerate(self._resolved_items):
            row = payload_by_scene_index.get(index) or {}
            pos_x = float(row.get("pos_x", resolved.x_mm))
            width = max(20.0, float(row.get("width", resolved.width_mm)))
            height = max(20.0, float(row.get("height", resolved.height_mm)))
            has_warning = bool(list(row.get("warning_flags", [])))
            severity = self._module_warning_severity(row)
            item = _SceneModuleItem(resolved, index, has_warning, severity, self._on_scene_module_clicked)
            item.setRect(pos_x, float(resolved.y_mm), width, height)
            self._scene.addItem(item)
            self._scene_items.append(item)

            sequence_index = int(row.get("sequence_index", index))
            text = QGraphicsSimpleTextItem(f"{sequence_index + 1}. {resolved.display_name}")
            text.setBrush(QBrush(QColor("#0f172a")))
            text.setPos(pos_x + 6.0, float(resolved.y_mm) + 6.0)
            self._scene.addItem(text)

        if self._selected_item is not None:
            for item in self._scene_items:
                item.set_selected_visual(item.resolved is self._selected_item)
            self._sync_tree_selection_from_selected_item()
        elif not self._resolved_items:
            empty = QGraphicsSimpleTextItem("Brak modulow w aktywnym komplecie.")
            empty.setBrush(QBrush(QColor("#64748b")))
            empty.setPos(10.0, 36.0)
            self._scene.addItem(empty)

        self._scene.setSceneRect(-20.0, -20.0, wall_width + 40.0, wall_height + 40.0)
        self._scene_view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        if assembly is None:
            self._scene_hint.setText(
                f"Sciana bez kompletu. Przeszkody: {obstacle_count}. "
                "Dodaj komplet, aby zobaczyc moduly w kontekscie sciany."
            )
        else:
            self._scene_hint.setText(
                f"Klik na obiekt sceny wybiera aktywny modul domenowy. "
                f"Przeszkody na scianie: {obstacle_count}. "
                "Edycja dalej odbywa sie przez zakladke Modul (istniejaca logika)."
            )

    def _on_scene_module_clicked(self, resolved: ResolvedAssemblyItem) -> None:
        scene_index = -1
        if isinstance(resolved, int):
            scene_index = int(resolved)
        else:
            for idx, item in enumerate(self._resolved_items):
                if item is resolved:
                    scene_index = idx
                    break
        if scene_index < 0 or scene_index >= len(self._resolved_items):
            return
        self._selected_obstacle_id = ""
        self._selected_scene_index = scene_index
        if self._selected_scene_index not in self._module_obstacle_focus_cursor:
            self._module_obstacle_focus_cursor[self._selected_scene_index] = 0
        self._sync_selected_item_from_scene_index()
        for item in self._scene_items:
            item.set_selected_visual(item.scene_index == self._selected_scene_index)
        for item in self._obstacle_items:
            item.set_selected_visual(False)
        self._sync_module_payload_selection()
        self._sync_obstacle_payload_selection()
        self._sync_tree_selection_from_selected_item()
        active_name = str(getattr(self._selected_item.module, "name", "") or self._selected_item.display_name or "")
        self.sig_active_module_changed.emit(active_name)
        self._refresh_left_context()

    def _on_scene_obstacle_clicked(self, obstacle_id: str) -> None:
        obstacle_id = str(obstacle_id or "")
        if not obstacle_id:
            return
        self._selected_obstacle_id = obstacle_id
        if obstacle_id not in self._obstacle_focus_cursor:
            self._obstacle_focus_cursor[obstacle_id] = 0
        self._selected_scene_index = -1
        self._selected_item = None
        for item in self._scene_items:
            item.set_selected_visual(False)
        for item in self._obstacle_items:
            item.set_selected_visual(item.obstacle_id == obstacle_id)
        self._sync_module_payload_selection()
        self._sync_obstacle_payload_selection()
        self._refresh_left_context()

    def _refresh_left_context(self) -> None:
        self._sync_context_stack()
        self._refresh_workspace_state()
        self._refresh_project_context()
        self._refresh_wall_context()
        self._refresh_module_context()
        self._refresh_komplet_context()

    def _refresh_workspace_state(self) -> None:
        assembly = self._current_assembly()
        if assembly is None:
            self.lbl_workspace_state.setText("Brak aktywnego kompletu. Dodaj lub wybierz komplet.")
            return
        if not self._resolved_items:
            self.lbl_workspace_state.setText("Aktywny komplet nie ma jeszcze modulow.")
            return
        self.lbl_workspace_state.setText(
            f"Aktywny komplet: {str(getattr(assembly, 'name', '') or '-')}, "
            f"moduly: {len(self._resolved_items)}"
        )

    def _refresh_project_context(self) -> None:
        walls_count = len(self._wall_store.list_layouts())
        assemblies = self._assembly_store.list_assemblies()
        modules_count = len(self._resolved_items)
        self.lbl_project_summary.setText(
            f"Tryb Projekt\n"
            f"Sciany: {walls_count}\n"
            f"Komplety: {len(assemblies)}\n"
            f"Moduly na aktywnej scenie: {modules_count}"
        )

    def _refresh_wall_context(self) -> None:
        wall = self._current_wall()
        assembly = self._current_assembly()
        if wall is None:
            if assembly is None:
                self.lbl_wall_summary.setText("Brak aktywnej sciany/kompletu.")
                self._refresh_obstacle_context_ui()
                return
            wall_name = str(getattr(assembly, "wall_name", "") or "[bez sciany]")
            wall_width = float(getattr(assembly, "width_mm", 0.0) or 0.0)
            wall_height = float(getattr(assembly, "height_mm", 0.0) or 0.0)
            self.lbl_wall_summary.setText(
                f"Tryb Sciana\n"
                f"Sciana: {wall_name}\n"
                f"Szerokosc: {wall_width:.0f} mm\n"
                f"Wysokosc: {wall_height:.0f} mm\n"
                f"Przeszkody: {int(self._layout_summary.get('obstacle_count', 0))}\n"
                f"Aktywny komplet: {str(getattr(assembly, 'name', '') or '[brak]')}\n"
                f"Zajete: {float(self._layout_summary.get('occupied_width_mm', 0.0)):.0f} mm\n"
                f"Wolne: {float(self._layout_summary.get('free_width_mm', 0.0)):.0f} mm\n"
                f"Kolizje modul-przeszkoda: {int(self._layout_summary.get('intersecting_module_count', 0))}\n"
                f"Out-of-wall: {int(self._layout_summary.get('obstacle_out_of_wall_count', 0))}\n"
                f"Invalid-size: {int(self._layout_summary.get('obstacle_invalid_size_count', 0))}\n"
                f"Nakladajace sie przeszkody: {int(self._layout_summary.get('overlapping_obstacle_count', 0))}\n"
                f"Sciana nie istnieje w bazie. Pokazano fallback z kompletu."
            )
            self._refresh_obstacle_context_ui()
            return
        wall_name = str(getattr(wall, "name", "") or "[bez sciany]")
        wall_width = float(getattr(wall, "wall_a_width_mm", 0.0) or 0.0)
        wall_height = float(getattr(wall, "room_height_mm", 0.0) or 0.0)
        obstacle_count = len(list(getattr(wall, "obstacles", []) or []))
        obstacle_types = dict(self._layout_summary.get("obstacles_by_type", {}) or {})
        types_line = ", ".join(f"{k}:{v}" for k, v in sorted(obstacle_types.items())) if obstacle_types else "[brak]"
        conflict_types = dict(self._layout_summary.get("obstacle_conflicts_by_type", {}) or {})
        conflict_types_line = ", ".join(f"{k}:{v}" for k, v in sorted(conflict_types.items())) if conflict_types else "[brak]"
        self.lbl_wall_summary.setText(
            f"Tryb Sciana\n"
            f"Sciana: {wall_name}\n"
            f"Szerokosc: {wall_width:.0f} mm\n"
            f"Wysokosc: {wall_height:.0f} mm\n"
            f"Przeszkody: {obstacle_count}\n"
            f"Typy przeszkod: {types_line}\n"
            f"Aktywny komplet: {str(getattr(assembly, 'name', '') or '[brak]')}\n"
            f"Zajete: {float(self._layout_summary.get('occupied_width_mm', 0.0)):.0f} mm\n"
            f"Wolne: {float(self._layout_summary.get('free_width_mm', 0.0)):.0f} mm\n"
            f"Kolizje modul-przeszkoda: {int(self._layout_summary.get('intersecting_module_count', 0))}\n"
            f"Pary kolizji modul-przeszkoda: {int(self._layout_summary.get('obstacle_conflict_pairs_count', 0))}\n"
            f"Konflikty wg typu: {conflict_types_line}\n"
            f"Przeszkody H/M: {int(self._layout_summary.get('obstacle_high_warning_count', 0))} / "
            f"{int(self._layout_summary.get('obstacle_medium_warning_count', 0))}\n"
            f"Out-of-wall: {int(self._layout_summary.get('obstacle_out_of_wall_count', 0))}\n"
            f"Invalid-size: {int(self._layout_summary.get('obstacle_invalid_size_count', 0))}\n"
            f"Nakladajace sie przeszkody: {int(self._layout_summary.get('overlapping_obstacle_count', 0))}\n"
            f"To jest wspolny context pod dalszy rozwoj Sciany."
        )
        self._refresh_obstacle_context_ui()

    def _refresh_module_context(self) -> None:
        if self._selected_item is None:
            self.lbl_module_summary.setText("Brak aktywnego modulu. Kliknij modul na scenie.")
            self.btn_open_modul_tab.setEnabled(False)
            self.btn_focus_obstacle_conflict.setEnabled(False)
            self.btn_move_left.setEnabled(False)
            self.btn_move_right.setEnabled(False)
            self.btn_align_start.setEnabled(False)
            self.btn_align_end.setEnabled(False)
            self.sp_pos_x.setEnabled(False)
            self.sp_spacing_after.setEnabled(False)
            self.btn_apply_manual.setEnabled(False)
            self.btn_normalize_layout.setEnabled(False)
            return
        module = self._selected_item.module
        assembly = self._current_assembly()
        wall = self._current_wall()
        row = self._selected_payload_row() or {}
        warning_flags = list(row.get("warning_flags", []))
        obstacle_warnings = list(row.get("obstacle_warnings", []))
        warning_severity = self._module_warning_severity(row)
        obstacle_short = "; ".join(
            str(item.get("short_message", "") or "").strip()
            for item in obstacle_warnings[:3]
            if str(item.get("short_message", "") or "").strip()
        )
        obstacle_types_counts: dict[str, int] = {}
        for item in obstacle_warnings:
            key = str(item.get("obstacle_type", "") or "obstacle")
            obstacle_types_counts[key] = int(obstacle_types_counts.get(key, 0)) + 1
        obstacle_types_line = ", ".join(f"{k}:{v}" for k, v in sorted(obstacle_types_counts.items())) if obstacle_types_counts else "[brak]"
        sequence_index = int(row.get("sequence_index", 0))
        pos_x = float(row.get("pos_x", getattr(self._selected_item, "x_mm", 0.0)))
        width = float(row.get("width", getattr(module, "width_mm", 0.0)))
        self.lbl_module_summary.setText(
            f"Tryb Modul\n"
            f"Nazwa: {str(getattr(module, 'name', '') or self._selected_item.display_name)}\n"
            f"Sciana: {str(getattr(wall, 'name', '') or '[bez sciany]')}\n"
            f"Komplet: {str(getattr(assembly, 'name', '') or '[bez kompletu]')}\n"
            f"Kolejnosc: {sequence_index + 1}\n"
            f"Pozycja X: {pos_x:.0f} mm\n"
            f"Szerokosc zajeta: {width:.0f} mm\n"
            f"W x H x D: {float(getattr(module, 'width_mm', 0.0) or 0.0):.0f} x "
            f"{float(getattr(module, 'height_mm', 0.0) or 0.0):.0f} x "
            f"{float(getattr(module, 'depth_mm', 0.0) or 0.0):.0f} mm\n"
            f"X/Y na scenie: {float(pos_x):.0f} / {float(self._selected_item.y_mm):.0f} mm\n"
            f"Severity: {warning_severity}\n"
            f"Warningi: {', '.join(warning_flags) if warning_flags else '[brak]'}\n"
            f"Kolizje z przeszkodami: {len(obstacle_warnings)}\n"
            f"Konflikty typy: {obstacle_types_line}\n"
            f"Detale kolizji: {obstacle_short if obstacle_short else '[brak]'}"
        )
        self.btn_open_modul_tab.setEnabled(True)
        self.btn_focus_obstacle_conflict.setEnabled(len(obstacle_warnings) > 0)
        self.btn_move_left.setEnabled(True)
        self.btn_move_right.setEnabled(True)
        self.btn_align_start.setEnabled(True)
        self.btn_align_end.setEnabled(True)
        self.sp_pos_x.blockSignals(True)
        self.sp_spacing_after.blockSignals(True)
        self.sp_pos_x.setValue(float(row.get("pos_x", 0.0)))
        self.sp_spacing_after.setValue(float(row.get("spacing_after_mm", 0.0)))
        self.sp_pos_x.blockSignals(False)
        self.sp_spacing_after.blockSignals(False)
        self.sp_pos_x.setEnabled(True)
        self.sp_spacing_after.setEnabled(True)
        self.btn_apply_manual.setEnabled(True)
        self.btn_normalize_layout.setEnabled(True)

    def _refresh_komplet_context(self) -> None:
        self._tree_items_by_scene_index = {}
        assembly = self._current_assembly()
        if assembly is None:
            self.tree_komplet.clear()
            self.lbl_komplet_summary.setText("Brak aktywnego kompletu.")
            return
        self.tree_komplet.clear()
        wall_name = str(getattr(assembly, "wall_name", "") or "[bez sciany]")
        assembly_name = str(getattr(assembly, "name", "") or "Komplet")
        wall_item = QTreeWidgetItem([wall_name])
        self.tree_komplet.addTopLevelItem(wall_item)
        komplet_item = QTreeWidgetItem([assembly_name])
        wall_item.addChild(komplet_item)
        for row in self._sorted_payload_rows():
            scene_index = int(row.get("scene_index", -1))
            if scene_index < 0 or scene_index >= len(self._resolved_items):
                continue
            resolved = self._resolved_items[scene_index]
            sequence_index = int(row.get("sequence_index", 0))
            module_name = str(getattr(resolved.module, "name", "") or resolved.display_name or "Modul")
            child = QTreeWidgetItem([f"{sequence_index + 1}. {module_name}"])
            child.setData(0, int(Qt.ItemDataRole.UserRole), module_name)
            child.setData(0, int(Qt.ItemDataRole.UserRole) + 1, int(scene_index))
            komplet_item.addChild(child)
            self._tree_items_by_scene_index[int(scene_index)] = child
        if not self._resolved_items:
            komplet_item.addChild(QTreeWidgetItem(["[brak modulow]"]))
        wall_item.setExpanded(True)
        komplet_item.setExpanded(True)
        active_module = (
            str(getattr(self._selected_item.module, "name", "") or self._selected_item.display_name or "")
            if self._selected_item is not None
            else "[brak]"
        )
        self.lbl_komplet_summary.setText(
            f"Tryb Komplet\n"
            f"Komplet: {assembly_name}\n"
            f"Sciana: {wall_name}\n"
            f"Liczba modulow: {len(self._resolved_items)}\n"
            f"Aktywny modul: {active_module}\n"
            f"Zajete: {float(self._layout_summary.get('occupied_width_mm', 0.0)):.0f} mm\n"
            f"Wolne: {float(self._layout_summary.get('free_width_mm', 0.0)):.0f} mm\n"
            f"Warningi: {int(self._layout_summary.get('warning_count', 0))}\n"
            f"Moduly H/M: {int(self._layout_summary.get('module_high_warning_count', 0))} / "
            f"{int(self._layout_summary.get('module_medium_warning_count', 0))}\n"
            f"Kolizje modul-przeszkoda: {int(self._layout_summary.get('intersecting_module_count', 0))}\n"
            f"Pary kolizji modul-przeszkoda: {int(self._layout_summary.get('obstacle_conflict_pairs_count', 0))}\n"
            f"Przeszkody H/M: {int(self._layout_summary.get('obstacle_high_warning_count', 0))} / "
            f"{int(self._layout_summary.get('obstacle_medium_warning_count', 0))}\n"
            f"Out-of-wall: {int(self._layout_summary.get('obstacle_out_of_wall_count', 0))}\n"
            f"Invalid-size: {int(self._layout_summary.get('obstacle_invalid_size_count', 0))}\n"
            f"Konflikty typy: {', '.join(f'{k}:{v}' for k, v in sorted(dict(self._layout_summary.get('obstacle_conflicts_by_type', {}) or {}).items())) or '[brak]'}"
        )
        self._sync_tree_selection_from_selected_item()

    def _rebuild_structure_tree(self) -> None:
        self._refresh_komplet_context()

    def _open_active_module_in_modul_tab(self) -> None:
        if self._selected_item is None:
            return
        main_tabs = self._find_parent_tab_widget()
        if main_tabs is None:
            return

        target_idx = -1
        target_widget: Any = None
        for idx in range(main_tabs.count()):
            w = main_tabs.widget(idx)
            if w is None:
                continue
            if str(type(w).__name__) == "TabModul":
                target_idx = idx
                target_widget = w
                break
        if target_idx < 0:
            return

        main_tabs.setCurrentIndex(target_idx)
        selected = self._selected_item
        candidate_names = [
            str(getattr(selected.item, "source_name", "") or "").strip(),
            str(getattr(selected.module, "name", "") or "").strip(),
        ]
        if target_widget is not None and hasattr(target_widget, "load_module_from_store_name"):
            for name in candidate_names:
                if not name:
                    continue
                if self._module_store.get(name) is None:
                    continue
                try:
                    if bool(target_widget.load_module_from_store_name(name)):
                        break
                except Exception:
                    continue

    def _focus_first_obstacle_conflict(self) -> None:
        row = self._selected_payload_row()
        if row is None:
            return
        warnings = list(row.get("obstacle_warnings", []))
        if not warnings:
            return
        obstacle_ids: list[str] = []
        for warning in warnings:
            obstacle_id = str(warning.get("obstacle_id", "") or "").strip()
            if obstacle_id and obstacle_id not in obstacle_ids:
                obstacle_ids.append(obstacle_id)
        if not obstacle_ids:
            return
        scene_index = int(row.get("scene_index", -1))
        cursor = int(self._module_obstacle_focus_cursor.get(scene_index, 0))
        obstacle_id = obstacle_ids[cursor % len(obstacle_ids)]
        self._module_obstacle_focus_cursor[scene_index] = (cursor + 1) % max(1, len(obstacle_ids))
        if not obstacle_id:
            return
        self._selected_obstacle_id = obstacle_id
        self._selected_scene_index = -1
        self._selected_item = None
        self._sync_module_payload_selection()
        self._sync_obstacle_payload_selection()
        for obs_item in self._obstacle_items:
            obs_item.set_selected_visual(obs_item.obstacle_id == obstacle_id)
        for mod_item in self._scene_items:
            mod_item.set_selected_visual(False)
        self._set_mode("sciana")
        self._refresh_left_context()

    def _find_parent_tab_widget(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def _on_komplet_tree_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        raw_index = item.data(0, int(Qt.ItemDataRole.UserRole) + 1)
        try:
            scene_index = int(raw_index)
        except Exception:
            return
        if scene_index < 0 or scene_index >= len(self._resolved_items):
            return
        self._on_scene_module_clicked(self._resolved_items[scene_index])

    def _sync_tree_selection_from_selected_item(self) -> None:
        if self._selected_item is None:
            return
        selected_index = -1
        for index, resolved in enumerate(self._resolved_items):
            if resolved is self._selected_item:
                selected_index = index
                break
        if selected_index < 0:
            return
        tree_item = self._tree_items_by_scene_index.get(selected_index)
        if tree_item is None:
            return
        self.tree_komplet.blockSignals(True)
        self.tree_komplet.setCurrentItem(tree_item)
        self.tree_komplet.scrollToItem(tree_item)
        self.tree_komplet.blockSignals(False)

    def _sync_selected_item_from_scene_index(self) -> None:
        if self._selected_scene_index < 0 or self._selected_scene_index >= len(self._resolved_items):
            self._selected_item = None
            return
        self._selected_item = self._resolved_items[self._selected_scene_index]

    def _sync_module_payload_selection(self) -> None:
        selected_index = int(self._selected_scene_index)
        for row in self._module_scene_payload:
            try:
                row_index = int(row.get("scene_index", -1))
            except Exception:
                row_index = -1
            row["is_selected"] = bool(row_index == selected_index)

    def _sync_obstacle_payload_selection(self) -> None:
        selected_id = str(self._selected_obstacle_id or "")
        known = {str(row.get("obstacle_id", "") or "") for row in self._obstacle_scene_payload}
        if selected_id and selected_id not in known:
            self._selected_obstacle_id = ""
            selected_id = ""
        for row in self._obstacle_scene_payload:
            row["is_selected"] = bool(str(row.get("obstacle_id", "") or "") == selected_id)

    def _selected_obstacle_row(self) -> dict[str, Any] | None:
        selected_id = str(self._selected_obstacle_id or "")
        if not selected_id:
            return None
        for row in self._obstacle_scene_payload:
            if str(row.get("obstacle_id", "") or "") == selected_id:
                return row
        return None

    def _refresh_obstacle_context_ui(self) -> None:
        selected = self._selected_obstacle_row()
        if selected is not None and not self._obstacle_passes_active_filter(selected):
            self._selected_obstacle_id = ""
            self._sync_obstacle_payload_selection()

        self.lst_obstacles.blockSignals(True)
        self.lst_obstacles.clear()
        ordered_rows = sorted(self._obstacle_scene_payload, key=self._obstacle_sort_key)
        for row in ordered_rows:
            if not self._obstacle_passes_active_filter(row):
                continue
            severity = self._obstacle_warning_severity(row)
            severity_tag = "H" if severity == "high" else ("M" if severity == "medium" else "-")
            text = (
                f"[{severity_tag}] {str(row.get('obstacle_type', '') or 'obstacle')} | "
                f"{str(row.get('label', '') or '-')} | "
                f"kolizje:{int(row.get('intersecting_module_count', 0))}"
            )
            item = QListWidgetItem(text)
            item.setData(int(Qt.ItemDataRole.UserRole), str(row.get("obstacle_id", "") or ""))
            self.lst_obstacles.addItem(item)
            if bool(row.get("is_selected")):
                self.lst_obstacles.setCurrentItem(item)
        self.lst_obstacles.blockSignals(False)

        selected = self._selected_obstacle_row()
        if selected is None:
            self.lbl_obstacle_context.setText(
                "Przeszkoda: [brak]\n"
                f"Liczba przeszkod: {len(self._obstacle_scene_payload)}"
            )
            self._set_obstacle_form_from_row(None)
            self.btn_obstacle_update.setEnabled(False)
            self.btn_obstacle_delete.setEnabled(False)
            self.btn_obstacle_clamp.setEnabled(False)
            self.btn_obstacle_focus_module.setEnabled(False)
            return
        self._set_obstacle_form_from_row(selected)
        module_refs = list(selected.get("intersecting_module_ids", []))
        module_labels = [self._display_module_ref(str(ref or "")) for ref in module_refs]
        severity = self._obstacle_warning_severity(selected)
        self.lbl_obstacle_context.setText(
            f"Przeszkoda: {str(selected.get('label', '') or '-')}\n"
            f"Typ: {str(selected.get('obstacle_type', '') or '-')}\n"
            f"X/Y: {float(selected.get('pos_x_mm', 0.0)):.0f} / {float(selected.get('pos_y_mm', 0.0)):.0f} mm\n"
            f"W/H: {float(selected.get('width_mm', 0.0)):.0f} / {float(selected.get('height_mm', 0.0)):.0f} mm\n"
            f"Strefa Z: {float(selected.get('warning_zone_mm', 0.0)):.0f} mm\n"
            f"Severity: {severity}\n"
            f"Moduly w kolizji: {int(selected.get('intersecting_module_count', 0))}\n"
            f"Moduly: {', '.join(module_labels) if module_labels else '[brak]'}\n"
            f"Warningi: {', '.join(list(selected.get('warning_flags', []))) if list(selected.get('warning_flags', [])) else '[brak]'}"
        )
        self.btn_obstacle_update.setEnabled(True)
        self.btn_obstacle_delete.setEnabled(True)
        self.btn_obstacle_clamp.setEnabled("obstacle_out_of_wall" in list(selected.get("warning_flags", [])))
        self.btn_obstacle_focus_module.setEnabled(int(selected.get("intersecting_module_count", 0)) > 0)

    def _set_obstacle_form_from_row(self, row: dict[str, Any] | None) -> None:
        if row is None:
            self.cb_obstacle_type.setCurrentIndex(0)
            self.ed_obstacle_label.setText("")
            self.sp_obstacle_x.setValue(0.0)
            self.sp_obstacle_y.setValue(0.0)
            self._apply_obstacle_type_preset(str(self.cb_obstacle_type.currentData() or "window"))
            return
        type_idx = self.cb_obstacle_type.findData(str(row.get("obstacle_type", "") or "window"))
        self.cb_obstacle_type.setCurrentIndex(max(0, type_idx))
        self.ed_obstacle_label.setText(str(row.get("label", "") or ""))
        self.sp_obstacle_x.setValue(float(row.get("pos_x_mm", 0.0)))
        self.sp_obstacle_y.setValue(float(row.get("pos_y_mm", 0.0)))
        self.sp_obstacle_w.setValue(max(1.0, float(row.get("width_mm", 1.0))))
        self.sp_obstacle_h.setValue(max(1.0, float(row.get("height_mm", 1.0))))
        self.sp_obstacle_zone.setValue(max(0.0, float(row.get("warning_zone_mm", 0.0))))

    def _obstacle_from_form(self, wall_height: float) -> dict[str, Any]:
        kind = str(self.cb_obstacle_type.currentData() or self.cb_obstacle_type.currentText() or "window").strip().lower()
        label = str(self.ed_obstacle_label.text() or kind or "obstacle").strip()
        pos_x = float(self.sp_obstacle_x.value())
        pos_y = float(self.sp_obstacle_y.value())
        width = max(1.0, float(self.sp_obstacle_w.value()))
        height = max(1.0, float(self.sp_obstacle_h.value()))
        warning_zone = max(0.0, float(self.sp_obstacle_zone.value()))
        bottom_offset = max(0.0, float(wall_height - pos_y - height))
        return {
            "kind": kind,
            "name": label,
            "x_mm": pos_x,
            "bottom_offset_mm": bottom_offset,
            "width_mm": width,
            "height_mm": height,
            "depth_mm": warning_zone,
        }

    def _on_obstacle_list_selection_changed(self) -> None:
        item = self.lst_obstacles.currentItem()
        if item is None:
            return
        obstacle_id = str(item.data(int(Qt.ItemDataRole.UserRole)) or "")
        if not obstacle_id:
            return
        self._selected_obstacle_id = obstacle_id
        if obstacle_id not in self._obstacle_focus_cursor:
            self._obstacle_focus_cursor[obstacle_id] = 0
        self._selected_scene_index = -1
        self._selected_item = None
        self._sync_module_payload_selection()
        self._sync_obstacle_payload_selection()
        for obs_item in self._obstacle_items:
            obs_item.set_selected_visual(obs_item.obstacle_id == obstacle_id)
        for mod_item in self._scene_items:
            mod_item.set_selected_visual(False)
        self._set_obstacle_form_from_row(self._selected_obstacle_row())
        self._refresh_left_context()

    def _on_obstacle_new(self) -> None:
        self._selected_obstacle_id = ""
        self._sync_obstacle_payload_selection()
        self._set_obstacle_form_from_row(None)
        self._refresh_obstacle_context_ui()

    def _on_obstacle_type_changed(self, _index: int) -> None:
        selected = self._selected_obstacle_row()
        if selected is not None:
            return
        obstacle_type = str(self.cb_obstacle_type.currentData() or "window")
        self._apply_obstacle_type_preset(obstacle_type)

    def _apply_obstacle_type_preset(self, obstacle_type: str) -> None:
        key = str(obstacle_type or "").strip().lower()
        default_w, default_h, default_zone = OBSTACLE_TYPE_PRESETS.get(key, (600.0, 1000.0, 0.0))
        self.sp_obstacle_w.setValue(float(default_w))
        self.sp_obstacle_h.setValue(float(default_h))
        self.sp_obstacle_zone.setValue(float(default_zone))

    def _on_obstacle_add(self) -> None:
        wall = self._current_wall()
        if wall is None:
            return
        wall_height = max(1.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
        obstacle_data = self._obstacle_from_form(wall_height)
        try:
            from src.domain.wall_models import WallObstacleDef
            current = list(getattr(wall, "obstacles", []) or [])
            current.append(WallObstacleDef.from_dict(obstacle_data))
            wall.obstacles = current
            self._wall_store.overwrite(wall)
            self._selected_obstacle_id = f"{str(getattr(wall, 'name', '') or '')}:{len(current)-1}"
            self._obstacle_focus_cursor[self._selected_obstacle_id] = 0
            self._reload_context()
        except Exception:
            return

    def _on_obstacle_update(self) -> None:
        selected = self._selected_obstacle_row()
        wall = self._current_wall()
        if selected is None or wall is None:
            return
        idx = int(selected.get("obstacle_index", -1))
        if idx < 0:
            return
        wall_height = max(1.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
        obstacle_data = self._obstacle_from_form(wall_height)
        try:
            from src.domain.wall_models import WallObstacleDef
            current = list(getattr(wall, "obstacles", []) or [])
            if idx >= len(current):
                return
            current[idx] = WallObstacleDef.from_dict(obstacle_data)
            wall.obstacles = current
            self._wall_store.overwrite(wall)
            self._selected_obstacle_id = f"{str(getattr(wall, 'name', '') or '')}:{idx}"
            self._obstacle_focus_cursor[self._selected_obstacle_id] = 0
            self._reload_context()
        except Exception:
            return

    def _on_obstacle_delete(self) -> None:
        selected = self._selected_obstacle_row()
        wall = self._current_wall()
        if selected is None or wall is None:
            return
        idx = int(selected.get("obstacle_index", -1))
        if idx < 0:
            return
        try:
            current = list(getattr(wall, "obstacles", []) or [])
            if idx >= len(current):
                return
            current.pop(idx)
            wall.obstacles = current
            self._wall_store.overwrite(wall)
            removed_id = str(self._selected_obstacle_id or "")
            if removed_id:
                self._obstacle_focus_cursor.pop(removed_id, None)
            self._selected_obstacle_id = ""
            self._reload_context()
        except Exception:
            return

    def _on_obstacle_clamp_to_wall(self) -> None:
        selected = self._selected_obstacle_row()
        wall = self._current_wall()
        if selected is None or wall is None:
            return
        idx = int(selected.get("obstacle_index", -1))
        if idx < 0:
            return
        wall_width = max(1.0, float(getattr(wall, "wall_a_width_mm", 3000.0) or 3000.0))
        wall_height = max(1.0, float(getattr(wall, "room_height_mm", 2500.0) or 2500.0))
        width = max(1.0, float(selected.get("width_mm", 1.0)))
        height = max(1.0, float(selected.get("height_mm", 1.0)))
        x = float(selected.get("pos_x_mm", 0.0))
        y = float(selected.get("pos_y_mm", 0.0))
        x = max(0.0, min(x, max(0.0, wall_width - width)))
        y = max(0.0, min(y, max(0.0, wall_height - height)))
        bottom_offset = max(0.0, wall_height - y - height)
        try:
            from src.domain.wall_models import WallObstacleDef
            current = list(getattr(wall, "obstacles", []) or [])
            if idx >= len(current):
                return
            updated = {
                "kind": str(selected.get("obstacle_type", "") or "obstacle"),
                "name": str(selected.get("label", "") or "obstacle"),
                "x_mm": float(x),
                "bottom_offset_mm": float(bottom_offset),
                "width_mm": float(width),
                "height_mm": float(height),
                "depth_mm": float(selected.get("warning_zone_mm", 0.0) or 0.0),
            }
            current[idx] = WallObstacleDef.from_dict(updated)
            wall.obstacles = current
            self._wall_store.overwrite(wall)
            self._selected_obstacle_id = f"{str(getattr(wall, 'name', '') or '')}:{idx}"
            self._obstacle_focus_cursor[self._selected_obstacle_id] = 0
            self._reload_context()
        except Exception:
            return

    def _focus_first_module_conflict_from_obstacle(self) -> None:
        obstacle = self._selected_obstacle_row()
        if obstacle is None:
            return
        obstacle_id = str(obstacle.get("obstacle_id", "") or "").strip()
        if not obstacle_id:
            return
        target_scene_indexes: list[int] = []
        for row in self._module_scene_payload:
            obstacle_warnings = list(row.get("obstacle_warnings", []))
            for warning in obstacle_warnings:
                if str(warning.get("obstacle_id", "") or "").strip() == obstacle_id:
                    target_scene_indexes.append(int(row.get("scene_index", -1)))
                    break
        target_scene_indexes = [idx for idx in target_scene_indexes if 0 <= idx < len(self._resolved_items)]
        if not target_scene_indexes:
            return
        cursor = int(self._obstacle_focus_cursor.get(obstacle_id, 0))
        target_scene_index = target_scene_indexes[cursor % len(target_scene_indexes)]
        self._obstacle_focus_cursor[obstacle_id] = (cursor + 1) % max(1, len(target_scene_indexes))
        if target_scene_index < 0 or target_scene_index >= len(self._resolved_items):
            return
        self._on_scene_module_clicked(self._resolved_items[target_scene_index])
        self._set_mode("modul")

    def _normalize_sequence_indexes(self) -> None:
        rows = self._sorted_payload_rows()
        for idx, row in enumerate(rows):
            row["sequence_index"] = int(idx)

    def _apply_layout_state_change(self) -> None:
        self._sync_selected_item_from_scene_index()
        self._sync_module_payload_selection()
        self._recompute_layout_warnings_and_summary()
        self._sync_obstacle_payload_selection()
        self._refresh_left_context()
        self._rebuild_structure_tree()
        self._render_scene()

    def _move_selected_in_order(self, delta: int) -> None:
        if delta == 0:
            return
        row = self._selected_payload_row()
        if row is None:
            return
        rows = self._sorted_payload_rows()
        current_pos = -1
        for idx, candidate in enumerate(rows):
            if candidate is row:
                current_pos = idx
                break
        if current_pos < 0:
            return
        target_pos = current_pos + int(delta)
        if target_pos < 0 or target_pos >= len(rows):
            return
        current_seq = int(rows[current_pos].get("sequence_index", current_pos))
        target_seq = int(rows[target_pos].get("sequence_index", target_pos))
        rows[current_pos]["sequence_index"] = target_seq
        rows[target_pos]["sequence_index"] = current_seq
        self._normalize_sequence_indexes()
        self._apply_layout_state_change()

    def _align_selected_to_start(self) -> None:
        row = self._selected_payload_row()
        if row is None:
            return
        row["pos_x"] = 0.0
        self._apply_layout_state_change()

    def _align_selected_to_end(self) -> None:
        row = self._selected_payload_row()
        if row is None:
            return
        wall_width, _ = self._wall_dimensions_for_layout()
        width = max(1.0, float(row.get("width", 0.0)))
        row["pos_x"] = float(wall_width - width)
        self._apply_layout_state_change()

    def _apply_selected_manual_position_and_spacing(self) -> None:
        row = self._selected_payload_row()
        if row is None:
            return
        row["pos_x"] = float(self.sp_pos_x.value())
        row["spacing_after_mm"] = max(0.0, float(self.sp_spacing_after.value()))
        self._apply_layout_state_change()

    def _normalize_layout_positions(self) -> None:
        rows = self._sorted_payload_rows()
        x_cursor = 0.0
        for idx, row in enumerate(rows):
            row["sequence_index"] = int(idx)
            row["pos_x"] = float(x_cursor)
            x_cursor += max(1.0, float(row.get("width", 0.0))) + max(0.0, float(row.get("spacing_after_mm", 0.0)))
        self._apply_layout_state_change()

    def _on_wall_changed(self, _index: int) -> None:
        self._fill_assembly_combo()
        self._load_resolved_items()
        self._sync_selected_item_from_scene_index()
        self._sync_module_payload_selection()
        self._recompute_layout_warnings_and_summary()
        self._sync_obstacle_payload_selection()
        self._refresh_left_context()
        self._rebuild_structure_tree()
        self._render_scene()

    def _on_assembly_changed(self, _index: int) -> None:
        self._load_resolved_items()
        self._sync_selected_item_from_scene_index()
        self._sync_module_payload_selection()
        self._recompute_layout_warnings_and_summary()
        self._sync_obstacle_payload_selection()
        self._refresh_left_context()
        self._rebuild_structure_tree()
        self._render_scene()
