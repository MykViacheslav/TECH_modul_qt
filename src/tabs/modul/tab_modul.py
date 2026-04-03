from __future__ import annotations
import json
from dataclasses import replace
from typing import Dict, Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer, QEvent
from PyQt6.QtGui import QBrush, QPen, QPainter, QColor, QPolygonF, QKeySequence, QShortcut
from PyQt6.QtWidgets import *
from src.ui.collapsible_block import CollapsibleBlock
from src.domain.module_base_group import BASE_GROUP_LABELS_PL, BASE_GROUP_ORDER, module_base_group_label_pl
from src.domain.module_models import ModuleDef, PartDef, module_type_to_cabinet_kind, new_module_id
from src.domain.module_resolution_service import build_resolved_module_domain_state
from src.storage.module_store_json import ModuleStoreJson
from src.storage.resolved_preview_store_json import save_resolved_preview_payload
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.receptura_store_json import RecepturaStoreJson
from src.core.costing.module_costs import calculate_module_cost_breakdown
from src.core.module_parts_service import build_module_parts
from src.services.receptura_bridge_service import build_catalog_material_from_receptura
from src.app.app_settings import (
    load_drawing_settings,
    save_drawing_settings,
    load_modul_splitter_sizes,
    save_modul_splitter_sizes,
    load_ui_string_list,
    save_ui_string_list,
    DrawingSettings,
)
from src.storage.session_store_json import load_last_session, save_last_session, clear_last_session
from src.tabs.modul.dialog_load_module import LoadModuleDialog, ModuleMiniPreview
from src.storage.default_module_store_json import load_default_module, save_default_module, clear_default_module
import os
from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock as ExtractedDrawingSettingsBlock
from src.ui.ui_polish import mark_ui_card, set_ui_variant
from src.tabs.modul.material_grouping import (
    collapse_profile_map_to_groups,
    expand_group_edgebands_to_module_map,
    get_material_edge_group_for_part_key,
    get_material_group_for_part_key,
    normalize_part_key_for_model,
    resolve_group_edgeband_defaults,
)
from src.tabs.modul.carcass_joints_block import CarcassJointsBlock
from src.tabs.modul.dimensions_block import DimensionsBlock
from src.tabs.modul.dividers_block import DividersBlock
from src.tabs.modul.edge_banding_block import EDGE_SIDES_PL, EdgeBandingBlock
from src.tabs.modul.front_hardware_block import FrontHardwareBlock
from src.tabs.modul.materials_block import MaterialsBlock
from src.tabs.receptura.receptura_picker import pick_receptura_rows
from src.tabs.modul.module_defaults import (
    _is_startup_module_state_valid,
    build_default_module,
    build_factory_default_module,
    normalize_rail_offsets_mm,
)
from src.tabs.modul.project_tree_block import ProjectTreeBlock
from src.tabs.modul.parts_table_block import PartsTableBlock
from src.tabs.modul.reference_point_block import ReferencePointBlock
from src.tabs.modul.session_view_block import SessionAndViewBlock
from src.tabs.modul.shelves_block import ShelvesBlock
from src.tabs.modul.visible_parts_block import VisiblePartsBlock
from src.tabs.modul.bom_block import BomBlock
from src.tabs.modul.views_canvas import ViewsCanvas, ZoomGraphicsView
# ==========================================================
# KOMPATYBILNOSC WSTECZNA
# ----------------------------------------------------------
# Stara sciezka importu:
#     from src.tabs.modul.tab_modul import DrawingSettingsBlock
# nadal ma dzialac.
#
# Faktyczna implementacja zostala przeniesiona do:
#     src.tabs.rysunek.drawing_settings_block
# ==========================================================
DrawingSettingsBlock = ExtractedDrawingSettingsBlock
# ==========================================================
# region ZONE_FRAMES (3 strefy czerwonym prostokatem + opcjonalny scroll)
# ==========================================================
class ZoneFrame(QFrame):
    def __init__(self, zone_key: str, title_pl: str, parent: QWidget | None = None, scrollable: bool = False) -> None:
        super().__init__(parent)

        self.zone_key = zone_key
        self.setObjectName(f"zone_{zone_key}")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        lab = QLabel(title_pl)
        lab.setObjectName("zoneTitle")
        lay.addWidget(lab)

        self.body = QWidget(self)
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(8)

        if scrollable:
            sc = QScrollArea(self)
            sc.setWidgetResizable(True)
            sc.setFrameShape(QFrame.Shape.NoFrame)
            sc.setWidget(self.body)
            lay.addWidget(sc, 1)
        else:
            lay.addWidget(self.body, 1)

        self.setStyleSheet("""
            QFrame#zone_left, QFrame#zone_center, QFrame#zone_right {
                border: 1px solid #d8e1ee;
                border-radius: 14px;
                background: #f7f9fc;
            }
            QLabel#zoneTitle {
                font-size: 11px;
                letter-spacing: 0.08em;
                font-weight: 700;
                color: #64748b;
                padding: 1px 4px 3px 4px;
            }
        """)
# endregion


# ==========================================================
# region UI: SpinBox bez przypadkowego scrolla
# ==========================================================
class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Nie zmieniaj wartosci ko'kiem myszy, jesli pole nie ma fokusu."""
    def wheelEvent(self, e):
        if not self.hasFocus():
            e.ignore()
            return
        super().wheelEvent(e)
# endregion
# ==========================================================
# region BLOCK: Materials (z bazy catalog.json)
# ==========================================================
# endregion


# ==========================================================
# region BLOCK: Ustawienia rysunku (GUI -> data/settings.json)
# WYDZIELONE DO: src.tabs.rysunek.drawing_settings_block
# ==========================================================
# Uwaga:
# Lokalna klasa DrawingSettingsBlock zostala usunieta z tego pliku.
# Jedyna obowiazujaca implementacja jest teraz:
#     src.tabs.rysunek.drawing_settings_block.DrawingSettingsBlock
#
# Powod:
# - unikamy duplikacji klas,
# - unikamy konfliktu nazw,
# - przygotowujemy bezpieczne przeniesienie tego bloku
#   poza zakladke "Modul", bez zmiany obecnej logiki dzialania.
# endregion
# ==========================================================
# region CENTER: Zoomable view (WYDZIELONE DO views_canvas.py)
# ==========================================================
# ZoomGraphicsView jest teraz w src.tabs.modul.views_canvas
# endregion


# ==========================================================
# region CENTER: ViewsCanvas (WYDZIELONE DO views_canvas.py)
# ==========================================================
# ViewsCanvas jest teraz w src.tabs.modul.views_canvas
# endregion


# ==========================================================
# region TAB: TabModul (CALY UKLAD - bez dubli)
# ==========================================================
class TabModul(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._store = ModuleStoreJson()
        self._catalog = CatalogStoreJson()
        self._receptura_store = RecepturaStoreJson()

        # --- SESSION tylko tutaj (TabModul) ---
        self._session_ready = False
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.timeout.connect(self._session_save_now)

        testing = str(os.environ.get("TECH_MODUL_TESTING", "")).strip() == "1"
        sess = None if testing else load_last_session()
        if sess:
            loaded_draft, ui = sess
            # jesli sesja pusta lub zepsuta, ignoruj
            if _is_startup_module_state_valid(loaded_draft):
                self._draft = loaded_draft
                self._selected_part_key = str(ui.get("selected_part_key") or "side_left")
            else:
                if not testing:
                    try:
                        clear_last_session()
                    except Exception:
                        pass
                self._draft = build_default_module()
                self._selected_part_key = "side_left"
        else:
            self._draft = build_default_module()
            self._selected_part_key = "side_left"
        # --- SAFETY: nie startuj z pustym lub smieciowym stanem ---
        if not _is_startup_module_state_valid(self._draft):
            self._draft = build_factory_default_module()
            self._selected_part_key = "side_left"
        # TECH: jawny stan resolved-domain (na razie bez wplywu na GUI)
        self._resolved_domain_state = build_resolved_module_domain_state(self._draft)

        # TECH:
        # pierwszy render w __init__ potrafi policzyc fit zanim widget
        # dostanie finalny rozmiar na ekranie.
        # Dlatego robimy jeszcze jeden, opoSniony fit po showEvent.
        self._startup_canvas_fit_done = False
        self._zone_splitter_restore_done = False
        self._zone_splitter_saved_sizes = self._load_zone_splitter_sizes()
        self._zone_splitter_save_timer = QTimer(self)
        self._zone_splitter_save_timer.setSingleShot(True)
        self._zone_splitter_save_timer.timeout.connect(self._save_zone_splitter_sizes)

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        split = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(split, 1)

        self.zone_left = ZoneFrame("left", "PARAMETRY", self, scrollable=True)
        self.zone_center = ZoneFrame("center", "MODUL KONSTRUKTORSKI", self, scrollable=False)
        self.zone_right = ZoneFrame("right", "BOM I KOSZTY", self, scrollable=True)

        self.zone_left.setMinimumWidth(320)
        self.zone_right.setMinimumWidth(320)

        split.addWidget(self.zone_left)
        split.addWidget(self.zone_center)
        split.addWidget(self.zone_right)

        self._zone_splitter = split
        self._zone_splitter.setChildrenCollapsible(False)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        self._apply_zone_splitter_sizes(self._zone_splitter_saved_sizes)
        self._zone_splitter.splitterMoved.connect(self._on_zone_splitter_moved)

        # ---------- LEFT BLOCKS ----------
        self.blk_dims = CollapsibleBlock("Wymiary modulu")
        self.blk_dims.setObjectName("blk_dims")
        self.dim = DimensionsBlock()
        self.blk_dims.content_layout().addWidget(self.dim)
        self.zone_left.body_lay.addWidget(self.blk_dims)

        self.blk_mat = CollapsibleBlock("Materialy")
        self.blk_mat.setObjectName("blk_mat")
        self.mat = MaterialsBlock(self._catalog)
        self.blk_mat.content_layout().addWidget(self.mat)
        self.zone_left.body_lay.addWidget(self.blk_mat)

        self.blk_fhw = CollapsibleBlock("Front i wyposazenie")
        self.blk_fhw.setObjectName("blk_fhw")
        self.fhw = FrontHardwareBlock(self._catalog)
        self.blk_fhw.content_layout().addWidget(self.fhw)
        self.zone_left.body_lay.addWidget(self.blk_fhw)

        self.blk_joint = CollapsibleBlock("Elementy korpusu")
        self.blk_joint.setObjectName("blk_joint")
        self.joint = CarcassJointsBlock()
        self.blk_joint.content_layout().addWidget(self.joint)
        self.zone_left.body_lay.addWidget(self.blk_joint)

        self.blk_shelves = CollapsibleBlock("Polki")
        self.blk_shelves.setObjectName("blk_shelves")
        self.shelves = ShelvesBlock()
        self.blk_shelves.content_layout().addWidget(self.shelves)
        self.zone_left.body_lay.addWidget(self.blk_shelves)

        self.blk_div = CollapsibleBlock("Przegrody")
        self.blk_div.setObjectName("blk_div")
        self.dividers = DividersBlock()
        self.blk_div.content_layout().addWidget(self.dividers)
        self.zone_left.body_lay.addWidget(self.blk_div)

        self.blk_ref = CollapsibleBlock("Punkt odniesienia")
        self.blk_ref.setObjectName("blk_ref")
        self.ref = ReferencePointBlock()
        self.blk_ref.content_layout().addWidget(self.ref)
        self.zone_left.body_lay.addWidget(self.blk_ref)

        self.blk_tree = CollapsibleBlock("Lista formatek")
        self.blk_tree.setObjectName("blk_tree")
        self.blk_tree.setMaximumHeight(360)
        self.tree = PartsTableBlock()
        self.blk_tree.content_layout().addWidget(self.tree)
        self.zone_left.body_lay.addWidget(self.blk_tree)

        self.blk_vis = CollapsibleBlock("Widoczne elementy")
        self.blk_vis.setObjectName("blk_vis")
        self.blk_vis.setMaximumHeight(280)
        self.vis = VisiblePartsBlock()
        self.blk_vis.content_layout().addWidget(self.vis)
        self.zone_left.body_lay.addWidget(self.blk_vis)

        self.blk_sess = CollapsibleBlock("Sesja i widok")
        self.blk_sess.setObjectName("blk_sess")
        self.blk_sess.setMaximumHeight(260)
        self.sessview = SessionAndViewBlock()
        self.blk_sess.content_layout().addWidget(self.sessview)
        self.zone_left.body_lay.addWidget(self.blk_sess)

        # TECH:
        # blok ustawien rysunku ma dalej istniec w TabModul dla synchronizacji,
        # ale nie moze byc widoczny ani dodany do lewego layoutu "Modul".
        self.draw_settings = ExtractedDrawingSettingsBlock(self)
        self.draw_settings.hide()

        # porzadek startowy lewej kolumny
        self._apply_left_blocks_startup_visibility()

        self.zone_left.body_lay.addStretch(1)

        # ---------- CENTER ----------
        self.quick_bar = QFrame(self.zone_center)
        self.quick_bar.setObjectName("modul_quick_bar")
        mark_ui_card(self.quick_bar, elevated=False)
        self.quick_bar.setStyleSheet("""
            QFrame#modul_quick_bar {
                background: #edf3fb;
                border: 1px solid #d5e1f1;
                border-radius: 14px;
            }
        """)
        quick_lay = QHBoxLayout(self.quick_bar)
        quick_lay.setContentsMargins(12, 10, 12, 10)
        quick_lay.setSpacing(10)

        self.btn_q_new = QPushButton("Nowy")
        self.btn_q_new.clicked.connect(self.start_new_module)
        set_ui_variant(self.btn_q_new, "primary")
        self.btn_q_new.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_new)

        self.btn_q_clear = QPushButton("Wyczysc")
        self.btn_q_clear.clicked.connect(self._on_clear_current_module)
        set_ui_variant(self.btn_q_clear, "primary")
        self.btn_q_clear.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_clear)

        self.btn_q_save = QPushButton("Zapisz")
        self.btn_q_save.clicked.connect(self._shortcut_save_module)
        set_ui_variant(self.btn_q_save, "primary")
        self.btn_q_save.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_save)

        self.btn_q_overwrite = QPushButton("Nadpisz")
        self.btn_q_overwrite.clicked.connect(self._on_overwrite)
        set_ui_variant(self.btn_q_overwrite, "ghost")
        self.btn_q_overwrite.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_overwrite)

        self.btn_q_load = QPushButton("Wczytaj")
        self.btn_q_load.clicked.connect(self._on_load_from_base_preview)
        set_ui_variant(self.btn_q_load, "primary")
        self.btn_q_load.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_load)

        self.btn_q_delete = QPushButton("Usun")
        self.btn_q_delete.clicked.connect(self._on_dim_delete_clicked)
        set_ui_variant(self.btn_q_delete, "ghost")
        self.btn_q_delete.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_delete)

        self.btn_q_focus_name = QPushButton("Nazwa")
        self.btn_q_focus_name.clicked.connect(self._shortcut_focus_module_name)
        set_ui_variant(self.btn_q_focus_name, "ghost")
        self.btn_q_focus_name.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_focus_name)

        self.btn_q_doors = QPushButton("Drzwi")
        self.btn_q_doors.clicked.connect(lambda: self._set_facade_mode_quick("doors"))
        set_ui_variant(self.btn_q_doors, "ghost")
        self.btn_q_doors.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_doors)

        self.btn_q_drawers = QPushButton("Szuflady")
        self.btn_q_drawers.clicked.connect(lambda: self._set_facade_mode_quick("drawers"))
        set_ui_variant(self.btn_q_drawers, "ghost")
        self.btn_q_drawers.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_drawers)

        self.btn_q_shortcuts = QPushButton("Skroty")
        self.btn_q_shortcuts.clicked.connect(self._open_shortcuts_dialog)
        set_ui_variant(self.btn_q_shortcuts, "ghost")
        self.btn_q_shortcuts.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_shortcuts)

        self.btn_q_receptura = QPushButton("Receptura")
        self.btn_q_receptura.clicked.connect(self._on_import_materials_from_receptura)
        set_ui_variant(self.btn_q_receptura, "success")
        self.btn_q_receptura.setMinimumHeight(36)
        quick_lay.addWidget(self.btn_q_receptura)

        quick_lay.addStretch(1)
        self.zone_center.body_lay.addWidget(self.quick_bar, 0)

        self.canvas = ViewsCanvas()
        self.canvas.set_preview_mode(True)
        self.zone_center.body_lay.addWidget(self.canvas, 1)

        # ---------- RIGHT ----------
        blk_preview = CollapsibleBlock("Podglad modulu")
        self.preview_mini = ModuleMiniPreview(self.zone_right)
        self.preview_mini.setMinimumHeight(240)
        self.preview_info = QLabel("-", self.zone_right)
        self.preview_info.setWordWrap(True)
        self.preview_info.setStyleSheet("font-weight:600; color:#213042;")
        blk_preview.content_layout().addWidget(self.preview_mini)
        blk_preview.content_layout().addWidget(self.preview_info)
        self.zone_right.body_lay.addWidget(blk_preview, 0)

        blk_edge = CollapsibleBlock("Oklejanie formatki")
        self.edge = EdgeBandingBlock(self._catalog)
        blk_edge.content_layout().addWidget(self.edge)
        self.zone_right.body_lay.addWidget(blk_edge, 1)

        blk_bom = CollapsibleBlock("BOM i koszty")
        self.bom = BomBlock(self._catalog)
        blk_bom.content_layout().addWidget(self.bom)
        self.zone_right.body_lay.addWidget(blk_bom, 1)

        self.zone_right.body_lay.addStretch(1)

        # hooki (jesli masz)
        if hasattr(self, "_hook_signals"):
            self._hook_signals()

        # buduj czesci + UI
        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        elif hasattr(self, "_rebuild_parts"):
            self._rebuild_parts()

        if hasattr(self, "_push_draft_to_ui"):
            self._push_draft_to_ui()

        # TECH:
        # po starcie zsynchronizuj ukryty blok ustawien rysunku
        # z aktualnym storage
        self.reload_drawing_settings_from_storage()

        # wybor elementu
        if getattr(self._draft, "parts", None):
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        if hasattr(self, "_render_right"):
            self._render_right()

        self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)
        self._session_ready = True
        self._session_save_request()
        self.sessview.sig_clear_last.connect(self._on_clear_last_state)
        self.sessview.sig_hide_front_changed.connect(self._on_hide_front_toggle)
        self._shortcut_actions = {
            "save": ("Ctrl+S", self._shortcut_save_module),
            "overwrite": ("Ctrl+Shift+S", self._on_overwrite),
            "load": ("Ctrl+L", self._on_load_from_base_preview),
            "new": ("Ctrl+N", self.start_new_module),
            "focus_name": ("Ctrl+F", self._shortcut_focus_module_name),
            "toggle_front": ("Ctrl+H", self._toggle_front_preview_visibility),
        }
        self._setup_shortcuts_from_settings()

    def _shortcut_save_module(self) -> None:
        name = str(self.dim.ed_name.text() or "").strip() if hasattr(self, "dim") else ""
        if name and self._store_has(name):
            self._on_overwrite()
        else:
            self._on_save_new()

    def _shortcut_focus_module_name(self) -> None:
        if hasattr(self, "dim") and hasattr(self.dim, "ed_name"):
            self.dim.ed_name.setFocus()
            self.dim.ed_name.selectAll()

    def _shortcut_settings_key(self) -> str:
        return "modul_shortcuts_v2"

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

    def _set_facade_mode_quick(self, mode: str) -> None:
        mode_key = str(mode or "").strip().lower()
        if not hasattr(self, "fhw") or not hasattr(self.fhw, "cb_facade_mode"):
            return
        idx = self.fhw.cb_facade_mode.findData(mode_key)
        if idx < 0:
            return
        self.fhw.cb_facade_mode.setCurrentIndex(idx)

    def _toggle_front_preview_visibility(self) -> None:
        if hasattr(self, "fhw") and hasattr(self.fhw, "chk_temp_hide_front"):
            now = bool(self.fhw.chk_temp_hide_front.isChecked())
            self.fhw.chk_temp_hide_front.setChecked(not now)

    def _open_shortcuts_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Konfiguracja skrotow - Modul")
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        lay.addLayout(form)

        labels = {
            "save": "Zapisz",
            "overwrite": "Nadpisz",
            "load": "Wczytaj",
            "new": "Nowy",
            "focus_name": "Fokus nazwy",
            "toggle_front": "Pokaz/ukryj front",
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

    def _on_import_materials_from_receptura(self) -> None:
        source_rows = self._receptura_store.list_for_module()
        if not source_rows:
            QMessageBox.information(self, "Receptura", "Brak pozycji oznaczonych 'Do modulu'.")
            return

        picked_rows = pick_receptura_rows(
            self,
            source_rows,
            title="Wybierz pozycje z Receptury do Modulu",
            subtitle="Wybrane pozycje zostana dodane/uzupelnione w katalogu materialow Modulu.",
            allow_multi=True,
        )
        if not picked_rows:
            return

        exported = self._catalog.export_catalog()
        materials = [dict(item) for item in (exported.get("materials") or []) if isinstance(item, dict)]
        idx_by_key = {str(item.get("key", "") or "").strip(): idx for idx, item in enumerate(materials)}

        added = 0
        updated = 0
        for row in picked_rows:
            material_row = build_catalog_material_from_receptura(row)
            key = str(material_row.get("key", "") or "").strip()
            if not key:
                continue
            existing_idx = idx_by_key.get(key, -1)
            if existing_idx >= 0:
                if dict(materials[existing_idx]) != dict(material_row):
                    materials[existing_idx] = dict(material_row)
                    updated += 1
            else:
                idx_by_key[key] = len(materials)
                materials.append(dict(material_row))
                added += 1

        if added <= 0 and updated <= 0:
            QMessageBox.information(self, "Receptura", "Brak zmian do importu.")
            return

        try:
            self._catalog.replace_catalog(materials=materials)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Receptura",
                f"Nie udalo sie zaimportowac materialow do katalogu Modulu.\n\nSzczegoly: {exc}",
            )
            return

        self._on_catalog_changed()
        QMessageBox.information(
            self,
            "Receptura",
            (
                f"Import zakonczony.\n"
                f"Dodano materialow: {added}\n"
                f"Zaktualizowano materialow: {updated}\n\n"
                f"Nowe pozycje znajdziesz w bloku 'Materialy modulu' i w BOM."
            ),
        )

    def _get_collapsible_block_body(self, block: QWidget | None) -> QWidget | None:
        """
        Zwraca widget-body z CollapsibleBlock.
        Nie dotykamy nag'owka - chowamy/pokazujemy tylko zawartosc.
        """
        if block is None:
            return None

        try:
            lay = block.content_layout()
        except Exception:
            return None

        if lay is None:
            return None

        try:
            body = lay.parentWidget()
        except Exception:
            body = None

        return body

    def _set_collapsible_block_body_visible(self, block: QWidget | None, visible: bool) -> None:
        body = self._get_collapsible_block_body(block)
        if body is not None:
            body.setVisible(bool(visible))

    def _apply_left_blocks_startup_visibility(self) -> None:
        """
        Ustawia spokojniejszy widok startowy zakladki "Modul".

        Zostaja otwarte:
        - Wymiary
        - Materialy
        - Fronty i okucia
        - Laczenia korpusu

        Startowo zwiniete:
        - Po'ki
        - Piony
        - Punkt odniesienia
        - Drzewo projektu
        - Widoczne elementy
        - Sesja i widok
        """
        self._set_collapsible_block_body_visible(getattr(self, "blk_dims", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_mat", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_fhw", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_joint", None), True)

        self._set_collapsible_block_body_visible(getattr(self, "blk_shelves", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_div", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_ref", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_tree", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_vis", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_sess", None), False)

    def _apply_edgeband_to_selected(self) -> None:
        keys = self.tree.selected_part_keys()
        if not keys:
            keys = [self._selected_part_key]

        eb = dict(self.edge.get_edge_banding())
        applied = 0
        for k in keys:
            p = self._draft.parts.get(k)
            if p is None:
                continue
            p.edge_banding = dict(eb)  # dokladnie to samo na wszystkich
            applied += 1

        # odswiez prawy panel dla aktywnego elementu
        self._render_right()
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)
        self.edge.set_selected_count(applied if applied > 0 else 1)

    def _apply_edgeband_to_all_shelves(self) -> None:
        eb = dict(self.edge.get_edge_banding())
        shelf_keys = [k for k in (self._draft.parts or {}).keys() if k.startswith("shelf_")]

        applied = 0
        for k in shelf_keys:
            p = self._draft.parts.get(k)
            if p is None:
                continue
            p.edge_banding = dict(eb)
            applied += 1

        self._render_right()
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)
        self.edge.set_selected_count(applied if applied > 0 else 1)

    def _choose_startup_selected_part_key(self) -> str:
        """
        Wybiera sensowny element startowy do zaznaczenia po uruchomieniu zakladki.

        Priorytet:
        1) front__front
        2) side_left
        3) pierwszy dostepny part
        """
        parts = dict(getattr(self._draft, "parts", {}) or {})
        if not parts:
            return ""

        if "front__front" in parts:
            return "front__front"

        if "side_left" in parts:
            return "side_left"

        return next(iter(parts.keys()))


    def showEvent(self, event) -> None:
        super().showEvent(event)

        if not getattr(self, "_zone_splitter_restore_done", False):
            self._zone_splitter_restore_done = True
            QTimer.singleShot(0, self._apply_zone_splitter_sizes)

        # po pierwszym pokazaniu widgetu zrob jeszcze jeden fit,
        # juz na realnym rozmiarze srodkowej strefy / canvasa
        if not getattr(self, "_startup_canvas_fit_done", False):
            QTimer.singleShot(0, self._run_startup_canvas_fit)

    def closeEvent(self, event) -> None:
        try:
            if hasattr(self, "_zone_splitter_save_timer") and self._zone_splitter_save_timer.isActive():
                self._zone_splitter_save_timer.stop()
            self._save_zone_splitter_sizes()
        except Exception:
            pass
        super().closeEvent(event)

    def _default_zone_splitter_sizes(self) -> list[int]:
        return [360, 900, 360]

    def _normalize_zone_splitter_sizes(self, sizes) -> list[int]:
        fallback = list(getattr(self, "_zone_splitter_saved_sizes", self._default_zone_splitter_sizes()) or self._default_zone_splitter_sizes())
        if not isinstance(sizes, (list, tuple)) or len(sizes) != 3:
            return fallback

        out: list[int] = []
        for value in sizes:
            try:
                parsed = int(value)
            except Exception:
                return fallback
            if parsed <= 0:
                return fallback
            out.append(parsed)
        return out

    def _load_zone_splitter_sizes(self) -> list[int]:
        return self._normalize_zone_splitter_sizes(load_modul_splitter_sizes(self._default_zone_splitter_sizes()))

    def _apply_zone_splitter_sizes(self, sizes=None) -> None:
        if not hasattr(self, "_zone_splitter"):
            return
        normalized = self._normalize_zone_splitter_sizes(
            sizes if sizes is not None else self._load_zone_splitter_sizes()
        )
        self._zone_splitter_saved_sizes = list(normalized)
        self._zone_splitter.setSizes(normalized)

    def _save_zone_splitter_sizes(self, sizes=None) -> None:
        if sizes is None:
            if not hasattr(self, "_zone_splitter"):
                return
            sizes = self._zone_splitter.sizes()
        normalized = self._normalize_zone_splitter_sizes(sizes)
        self._zone_splitter_saved_sizes = list(normalized)
        save_modul_splitter_sizes(normalized)

    def _on_zone_splitter_moved(self, _pos: int, _index: int) -> None:
        if hasattr(self, "_zone_splitter_save_timer"):
            self._zone_splitter_save_timer.start(180)

    def _run_startup_canvas_fit(self) -> None:
        """
        Dodatkowy fit startowy po faktycznym pokazaniu widgetu.

        Cel:
        - poprawic pierwszy widok po uruchomieniu,
        - ustawic sensowny element startowy,
        - bez zmiany logiki modulu,
        - bez zmiany zwyklego dzialania renderera.
        """
        if getattr(self, "_startup_canvas_fit_done", False):
            return

        self._startup_canvas_fit_done = True

        key = self._choose_startup_selected_part_key()
        if key:
            self._selected_part_key = key
            if hasattr(self, "tree") and hasattr(self.tree, "select_part"):
                self.tree.select_part(key)

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=True,
                selected_part_key=getattr(self, "_selected_part_key", "")
            )
    # ---------------------------
    # region HOOKS
    # ---------------------------
    def _hook_signals(self) -> None:
        self.tree.sig_selected_part.connect(self._on_selected_part)
        self.tree.sig_visibility_changed.connect(self._on_parts_table_visibility_changed)
        self.tree.sig_grain_changed.connect(self._on_parts_table_grain_changed)
        self.canvas.sig_clicked_part.connect(self._on_canvas_part_clicked)

        if hasattr(self.canvas, "sig_front_zone_handle_clicked"):
            self.canvas.sig_front_zone_handle_clicked.connect(self._on_front_zone_handle_clicked)

        if hasattr(self.canvas, "sig_front_zone_handle_dragged"):
            self.canvas.sig_front_zone_handle_dragged.connect(self._on_front_zone_handle_dragged)

        if hasattr(self.canvas, "sig_rail_offset_handle_clicked"):
            self.canvas.sig_rail_offset_handle_clicked.connect(self._on_rail_offset_handle_clicked)

        if hasattr(self.canvas, "sig_rail_offset_handle_dragged"):
            self.canvas.sig_rail_offset_handle_dragged.connect(self._on_rail_offset_handle_dragged)

        # CRUD bazy modulow
        # sig_new / sig_clear nie istnieja w DimensionsBlock - pomijamy
        self.dim.sig_save.connect(self._on_dim_save_clicked)
        self.dim.sig_overwrite.connect(self._on_dim_overwrite_clicked)
        self.dim.sig_load.connect(self._on_load_from_base_preview)
        self.dim.sig_delete.connect(self._on_dim_delete_clicked)

        # zmiany wymiarow -> render
        self.dim.ed_name.textChanged.connect(self._on_any_change)
        self.dim.ed_name.textChanged.connect(self._refresh_crud_action_state)
        self.dim.cb_base_group.currentIndexChanged.connect(self._on_any_change)
        self.dim.sp_w.valueChanged.connect(self._on_any_change)
        self.dim.sp_d.valueChanged.connect(self._on_any_change)
        self.dim.sp_h.valueChanged.connect(self._on_any_change)
        if hasattr(self.dim, "sp_top_rail_offset"):
            self.dim.sp_top_rail_offset.valueChanged.connect(self._on_any_change)
        if hasattr(self.dim, "sp_bottom_rail_offset"):
            self.dim.sp_bottom_rail_offset.valueChanged.connect(self._on_any_change)

        self.vis.sig_changed.connect(self._on_any_change)
        self.joint.sig_changed.connect(self._on_any_change)
        self.ref.sig_changed.connect(self._on_any_change)
        self.shelves.sig_changed.connect(self._on_any_change)
        self.dividers.sig_changed.connect(self._on_any_change)
        self.mat.sig_changed.connect(self._on_any_change)
        if hasattr(self.mat, "sig_profile_selected"):
            self.mat.sig_profile_selected.connect(self._on_material_profile_selected)
        if hasattr(self.mat, "sig_catalog_changed"):
            self.mat.sig_catalog_changed.connect(self._on_catalog_changed)

        # okleina ma osobny handler (nie przebudowuje czesci)
        self.edge.sig_changed.connect(self._on_edge_changed)
        if hasattr(self.bom, "sig_material_changed"):
            self.bom.sig_material_changed.connect(self._on_part_material_changed)
        if hasattr(self.bom, "sig_material_reset_requested"):
            self.bom.sig_material_reset_requested.connect(self._on_part_material_reset_requested)

        self.draw_settings.sig_changed.connect(self._on_drawing_settings_changed)
        self.fhw.sig_changed.connect(self._on_any_change)

        if hasattr(self.fhw, "chk_temp_hide_front") and hasattr(self.canvas, "set_preview_hide_front"):
            self.canvas.set_preview_hide_front(bool(self.fhw.chk_temp_hide_front.isChecked()))
            self.fhw.chk_temp_hide_front.toggled.connect(self.canvas.set_preview_hide_front)

        self.sessview.sig_clear_last.connect(self._on_clear_last_state)
        self.sessview.sig_hide_front_changed.connect(self._on_hide_front_toggle)
        self.sessview.sig_set_current_as_default.connect(self._on_set_current_as_default)

    # ---------------------------
    # region UI <-> DRAFT
    # ---------------------------
    def _push_draft_to_ui(self) -> None:
        self._is_pushing_ui = True
        try:
            self.dim.sp_w.blockSignals(True)
            self.dim.sp_d.blockSignals(True)
            self.dim.sp_h.blockSignals(True)
            if hasattr(self.dim, "sp_top_rail_offset"):
                self.dim.sp_top_rail_offset.blockSignals(True)
            if hasattr(self.dim, "sp_bottom_rail_offset"):
                self.dim.sp_bottom_rail_offset.blockSignals(True)

            self.dim.ed_name.setText(getattr(self._draft, "name", "") or "")
            current_group = str(getattr(self._draft, "base_group", "kitchen") or "kitchen")
            known_groups = list(BASE_GROUP_ORDER)
            if hasattr(self, "_store") and hasattr(self._store, "list_base_groups"):
                try:
                    known_groups = list(self._store.list_base_groups() or known_groups)
                except Exception:
                    known_groups = list(BASE_GROUP_ORDER)
            if current_group and current_group not in known_groups:
                known_groups.append(current_group)

            self.dim.cb_base_group.blockSignals(True)
            self.dim.cb_base_group.clear()
            for key in known_groups:
                self.dim.cb_base_group.addItem(module_base_group_label_pl(key), key)

            idx = self.dim.cb_base_group.findData(current_group)
            if idx < 0:
                idx = self.dim.cb_base_group.findData("other")
            if idx >= 0:
                self.dim.cb_base_group.setCurrentIndex(idx)
            self.dim.sp_w.setValue(float(self._draft.width_mm))
            self.dim.sp_d.setValue(float(self._draft.depth_mm))
            self.dim.sp_h.setValue(float(self._draft.height_mm))

            if hasattr(self.dim, "sp_top_rail_offset"):
                self.dim.sp_top_rail_offset.setValue(
                    float(getattr(self._draft, "top_rail_offset_mm", 0.0) or 0.0)
                )
            if hasattr(self.dim, "sp_bottom_rail_offset"):
                self.dim.sp_bottom_rail_offset.setValue(
                    float(getattr(self._draft, "bottom_rail_offset_mm", 0.0) or 0.0)
                )

            self.vis.set_checked(set(getattr(self._draft, "visible_parts", set()) or set()))
            self.joint.set_value(getattr(self._draft, "carcass_joint_type", "type1"))
            if hasattr(self.mat, "set_profile_key"):
                self.mat.set_profile_key(str(getattr(self._draft, "material_profile_key", "STD_WHITE") or "STD_WHITE"))
            self.mat.set_materials(dict(getattr(self._draft, "materials", {}) or {}))
            if hasattr(self.mat, "set_edgebands"):
                self.mat.set_edgebands(dict(getattr(self._draft, "edgebands", {}) or {}))

            if hasattr(self.fhw, "cb_front_layout"):
                idx = self.fhw.cb_front_layout.findData(
                    str(getattr(self._draft, "front_layout", "overlay") or "overlay")
                )
                if idx >= 0:
                    self.fhw.cb_front_layout.setCurrentIndex(idx)

            if hasattr(self.fhw, "cb_front_height_mode"):
                idx = self.fhw.cb_front_height_mode.findData(
                    str(getattr(self._draft, "front_height_mode", "full") or "full")
                )
                if idx >= 0:
                    self.fhw.cb_front_height_mode.setCurrentIndex(idx)

            if hasattr(self.fhw, "cb_front_top_ref_mode"):
                idx = self.fhw.cb_front_top_ref_mode.findData(
                    str(getattr(self._draft, "front_top_ref_mode", "rail_end") or "rail_end")
                )
                if idx >= 0:
                    self.fhw.cb_front_top_ref_mode.setCurrentIndex(idx)

            if hasattr(self.fhw, "cb_front_bottom_ref_mode"):
                idx = self.fhw.cb_front_bottom_ref_mode.findData(
                    str(getattr(self._draft, "front_bottom_ref_mode", "rail_end") or "rail_end")
                )
                if idx >= 0:
                    self.fhw.cb_front_bottom_ref_mode.setCurrentIndex(idx)

            if hasattr(self.fhw, "sp_front_offset_top"):
                self.fhw.sp_front_offset_top.setValue(
                    float(getattr(self._draft, "front_offset_top_mm", 0.0) or 0.0)
                )

            if hasattr(self.fhw, "sp_front_offset_bottom"):
                self.fhw.sp_front_offset_bottom.setValue(
                    float(getattr(self._draft, "front_offset_bottom_mm", 0.0) or 0.0)
                )

            if hasattr(self.fhw, "sp_gap_left"):
                self.fhw.sp_gap_left.setValue(
                    float(getattr(self._draft, "front_gap_left_mm", 0.0) or 0.0)
                )
            if hasattr(self.fhw, "sp_gap_right"):
                self.fhw.sp_gap_right.setValue(
                    float(getattr(self._draft, "front_gap_right_mm", 0.0) or 0.0)
                )
            if hasattr(self.fhw, "sp_gap_top"):
                self.fhw.sp_gap_top.setValue(
                    float(getattr(self._draft, "front_gap_top_mm", 0.0) or 0.0)
                )
            if hasattr(self.fhw, "sp_gap_bottom"):
                self.fhw.sp_gap_bottom.setValue(
                    float(getattr(self._draft, "front_gap_bottom_mm", 0.0) or 0.0)
                )
            if hasattr(self.fhw, "sp_gap_between_vertical"):
                self.fhw.sp_gap_between_vertical.setValue(
                    float(getattr(self._draft, "front_gap_between_vertical_mm", 0.0) or 0.0)
                )

            if hasattr(self.fhw, "cb_facade_mode"):
                idx = self.fhw.cb_facade_mode.findData(
                    str(getattr(self._draft, "facade_mode", "doors") or "doors")
                )
                if idx >= 0:
                    self.fhw.cb_facade_mode.setCurrentIndex(idx)

            if hasattr(self.fhw, "sp_drawer_count"):
                self.fhw.sp_drawer_count.setValue(int(getattr(self._draft, "drawer_count", 3) or 3))

            if hasattr(self.fhw, "cb_drawer_layout_mode"):
                idx = self.fhw.cb_drawer_layout_mode.findData(
                    str(getattr(self._draft, "drawer_layout_mode", "equal") or "equal")
                )
                if idx >= 0:
                    self.fhw.cb_drawer_layout_mode.setCurrentIndex(idx)

            if hasattr(self.fhw, "sp_drawer_small_front_h"):
                self.fhw.sp_drawer_small_front_h.setValue(
                    float(getattr(self._draft, "drawer_small_front_height_mm", 140.0) or 140.0)
                )

            self.shelves.set_value(int(getattr(self._draft, "shelf_count", 0) or 0))
            self.shelves.set_enabled(True)

            self.dividers.set_values(
                int(getattr(self._draft, "divider_count", 0) or 0),
                str(getattr(self._draft, "shelf_mount", "right") or "right")
            )
            self.dividers.set_enabled(True)
            self.dividers.set_mount_enabled(int(getattr(self._draft, "divider_count", 0) or 0) > 0)

            if hasattr(self, "_sync_existence_dependent_visibility_ui"):
                self._sync_existence_dependent_visibility_ui()

            if hasattr(self, "ref"):
                self.ref.set_values(
                    str(getattr(self._draft, "cabinet_kind", "lower") or "lower"),
                    str(getattr(self._draft, "ref_point", "LBB") or "LBB"),
                    module_type=str(getattr(self._draft, "module_type", "legacy") or "legacy"),
                )

        finally:
            self.dim.sp_w.blockSignals(False)
            self.dim.sp_d.blockSignals(False)
            self.dim.sp_h.blockSignals(False)
            self.dim.cb_base_group.blockSignals(False)
            if hasattr(self.dim, "sp_top_rail_offset"):
                self.dim.sp_top_rail_offset.blockSignals(False)
            if hasattr(self.dim, "sp_bottom_rail_offset"):
                self.dim.sp_bottom_rail_offset.blockSignals(False)

            self._is_pushing_ui = False

        self._refresh_crud_action_state()

    def _sync_existence_dependent_visibility_ui(self) -> None:
        if not hasattr(self, "vis"):
            return

        try:
            shelf_count_ui = int(self.shelves.get_value())
        except Exception:
            shelf_count_ui = int(getattr(self._draft, "shelf_count", 0) or 0)

        try:
            div_count_ui = int(self.dividers.get_count())
        except Exception:
            div_count_ui = int(getattr(self._draft, "divider_count", 0) or 0)

        shelf_exists = shelf_count_ui > 0
        divider_exists = div_count_ui > 0

        prev_shelf_enabled = self.vis.is_part_enabled("shelf")
        prev_div_enabled = self.vis.is_part_enabled("divider")

        if shelf_exists:
            self.vis.set_part_enabled("shelf", True)
            if (not prev_shelf_enabled) and (not self.vis.is_part_checked("shelf")):
                self.vis.set_part_checked("shelf", True)
        else:
            self.vis.set_part_checked("shelf", False)
            self.vis.set_part_enabled("shelf", False)

        if divider_exists:
            self.vis.set_part_enabled("divider", True)
            if (not prev_div_enabled) and (not self.vis.is_part_checked("divider")):
                self.vis.set_part_checked("divider", True)
        else:
            self.vis.set_part_checked("divider", False)
            self.vis.set_part_enabled("divider", False)

        if hasattr(self, "dividers") and hasattr(self.dividers, "set_mount_enabled"):
            self.dividers.set_mount_enabled(divider_exists)

    def _refresh_crud_action_state(self, *_args) -> None:
        if not hasattr(self, "dim"):
            return

        name = str(self.dim.ed_name.text() or "").strip()
        has_name = bool(name)
        exists_in_store = False

        if has_name:
            try:
                exists_in_store = bool(self._store_has(name))
            except Exception:
                exists_in_store = False

        overwrite_enabled = has_name and exists_in_store
        delete_enabled = has_name and exists_in_store

        if hasattr(self.dim, "btn_over"):
            self.dim.btn_over.setEnabled(overwrite_enabled)
        if hasattr(self.dim, "btn_del"):
            self.dim.btn_del.setEnabled(delete_enabled)

        if hasattr(self, "btn_q_overwrite"):
            self.btn_q_overwrite.setEnabled(overwrite_enabled)
        if hasattr(self, "btn_q_delete"):
            self.btn_q_delete.setEnabled(delete_enabled)

    def _pull_ui_to_draft(self) -> None:
        vis = set(self.vis.get_visible_parts() or set())

        try:
            shelf_count = max(0, int(self.shelves.get_value()))
        except Exception:
            shelf_count = 0

        try:
            div_count = max(0, int(self.dividers.get_count()))
        except Exception:
            div_count = 0

        # istnienie elementu steruje tym, czy checkbox w ogole ma sens
        if shelf_count <= 0:
            vis.discard("shelf")

        if div_count <= 0:
            vis.discard("divider")

        mats = self.mat.get_materials()
        group_edge_defaults = self.mat.get_edgebands() if hasattr(self.mat, "get_edgebands") else {}
        merged_module_edgebands = expand_group_edgebands_to_module_map(
            group_edge_defaults,
            dict(getattr(self._draft, "edgebands", {}) or {}),
        )

        try:
            carcass_key = str(mats.get("carcass", "PB18") or "PB18")
        except Exception:
            carcass_key = "PB18"

        try:
            t_carcass = float(self._catalog.material_thickness(carcass_key, 18.0) or 18.0)
        except Exception:
            t_carcass = 18.0

        try:
            top_rail_offset_raw = float(self.dim.sp_top_rail_offset.value())
        except Exception:
            top_rail_offset_raw = 0.0

        try:
            bottom_rail_offset_raw = float(self.dim.sp_bottom_rail_offset.value())
        except Exception:
            bottom_rail_offset_raw = 0.0

        top_rail_offset_mm, bottom_rail_offset_mm = normalize_rail_offsets_mm(
            height_mm=float(self.dim.sp_h.value()),
            rail_thickness_mm=t_carcass,
            top_offset_mm=top_rail_offset_raw,
            bottom_offset_mm=bottom_rail_offset_raw,
        )


        # ----------------------------------------------------------
        # POLA DATACLASSA ModuleDef -> tylko one moga isc do replace()
        # ----------------------------------------------------------
        selected_module_type = self.ref.get_module_type() if hasattr(self, "ref") else getattr(self._draft, "module_type", "legacy")
        selected_cabinet_kind = self.ref.get_kind() if hasattr(self, "ref") else getattr(self._draft, "cabinet_kind", "lower")
        if selected_module_type != "legacy":
            selected_cabinet_kind = module_type_to_cabinet_kind(
                selected_module_type,
                fallback_kind=selected_cabinet_kind,
            )

        self._draft = replace(
            self._draft,
            name=self.dim.ed_name.text().strip(),
            base_group=str(self.dim.cb_base_group.currentData() or "other"),
            width_mm=float(self.dim.sp_w.value()),
            depth_mm=float(self.dim.sp_d.value()),
            height_mm=float(self.dim.sp_h.value()),
            top_rail_offset_mm=top_rail_offset_mm,
            bottom_rail_offset_mm=bottom_rail_offset_mm,
            visible_parts=vis,

            shelf_count=shelf_count,
            divider_count=div_count,
            shelf_mount=self.dividers.get_mount(),
            module_type=selected_module_type,

            carcass_joint_type=self.joint.get_value(),
            material_profile_key=str(self.mat.get_profile_key() if hasattr(self.mat, "get_profile_key") else getattr(self._draft, "material_profile_key", "STD_WHITE") or "STD_WHITE"),
            materials=mats,
            edgebands=merged_module_edgebands,

            cabinet_kind=selected_cabinet_kind,
            ref_point=self.ref.get_ref() if hasattr(self, "ref") else getattr(self._draft, "ref_point", "LBB"),

            front_layout=str(self.fhw.cb_front_layout.currentData() or "overlay"),
            front_height_mode=str(self.fhw.cb_front_height_mode.currentData() or "full"),
            front_offset_top_mm=float(self.fhw.sp_front_offset_top.value()),
            front_offset_bottom_mm=float(self.fhw.sp_front_offset_bottom.value()),
            facade_mode=str(self.fhw.cb_facade_mode.currentData() or "doors"),
            drawer_count=int(self.fhw.sp_drawer_count.value()),
            drawer_layout_mode=str(self.fhw.cb_drawer_layout_mode.currentData() or "equal"),
            drawer_small_front_height_mm=float(self.fhw.sp_drawer_small_front_h.value()),
            hinge_vendor=str(self.fhw.cb_hinge_vendor.currentData() or "generic"),
            drawer_vendor=str(self.fhw.cb_drawer_vendor.currentData() or "generic"),
            drawer_tip_on=bool(self.fhw.chk_tipon.isChecked()),
            drawer_rear_clearance_mm=float(self.fhw.sp_rear.value()),
            drawer_tip_on_clearance_mm=float(self.fhw.sp_tip.value()),
        )

        # ----------------------------------------------------------
        # POLA DYNAMICZNE -> NIE sa w __init__ ModuleDef
        # zapisujemy je jawnie po replace()
        # ----------------------------------------------------------
        top_ref_mode = "rail_end"
        bottom_ref_mode = "rail_end"

        if hasattr(self.fhw, "cb_front_top_ref_mode"):
            try:
                top_ref_mode = str(self.fhw.cb_front_top_ref_mode.currentData() or "rail_end")
            except Exception:
                top_ref_mode = "rail_end"

        if hasattr(self.fhw, "cb_front_bottom_ref_mode"):
            try:
                bottom_ref_mode = str(self.fhw.cb_front_bottom_ref_mode.currentData() or "rail_end")
            except Exception:
                bottom_ref_mode = "rail_end"

        gap_left = 0.0
        gap_right = 0.0
        gap_top = 0.0
        gap_bottom = 0.0
        gap_between_vertical = 0.0

        if hasattr(self.fhw, "sp_gap_left"):
            try:
                gap_left = float(self.fhw.sp_gap_left.value())
            except Exception:
                gap_left = 0.0

        if hasattr(self.fhw, "sp_gap_right"):
            try:
                gap_right = float(self.fhw.sp_gap_right.value())
            except Exception:
                gap_right = 0.0

        if hasattr(self.fhw, "sp_gap_top"):
            try:
                gap_top = float(self.fhw.sp_gap_top.value())
            except Exception:
                gap_top = 0.0

        if hasattr(self.fhw, "sp_gap_bottom"):
            try:
                gap_bottom = float(self.fhw.sp_gap_bottom.value())
            except Exception:
                gap_bottom = 0.0

        if hasattr(self.fhw, "sp_gap_between_vertical"):
            try:
                gap_between_vertical = float(self.fhw.sp_gap_between_vertical.value())
            except Exception:
                gap_between_vertical = 0.0

        setattr(self._draft, "front_top_ref_mode", top_ref_mode)
        setattr(self._draft, "front_bottom_ref_mode", bottom_ref_mode)

        setattr(self._draft, "front_gap_left_mm", gap_left)
        setattr(self._draft, "front_gap_right_mm", gap_right)
        setattr(self._draft, "front_gap_top_mm", gap_top)
        setattr(self._draft, "front_gap_bottom_mm", gap_bottom)
        setattr(self._draft, "front_gap_between_vertical_mm", gap_between_vertical)

        self._resolved_domain_state = build_resolved_module_domain_state(self._draft)

    def _on_clear_last_state(self) -> None:
        clear_last_session()

        self._draft = build_default_module()
        self._selected_part_key = "side_left"
        self._resolved_domain_state = build_resolved_module_domain_state(self._draft)

        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        else:
            self._rebuild_parts()

        self._push_draft_to_ui()

        if self._draft.parts:
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        self._render_right()
        self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)

        self._session_save_request()

    def _on_clear_default_start(self) -> None:
        clear_default_module()

        self._draft = build_default_module()
        self._selected_part_key = "side_left"
        self._resolved_domain_state = build_resolved_module_domain_state(self._draft)

        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        else:
            self._rebuild_parts()

        self._push_draft_to_ui()

        if getattr(self._draft, "parts", None):
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        self._render_right()
        self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)

        self._session_save_now()

    def _on_set_current_as_default(self) -> None:
        if hasattr(self, "_pull_ui_to_draft"):
            self._pull_ui_to_draft()

        import os
        testing = os.environ.get("TECH_MODUL_TESTING", "").strip() == "1"

        try:
            save_default_module(self._draft)
        except ValueError as e:
            if testing:
                # w testach: nie pokazuj okienek, tylko rzuc b'ad
                raise
            QMessageBox.warning(
                self,
                "Nie zapisano startowego",
                f"{e}\n\nUstaw poprawne wymiary i zaznacz elementy, potem sprobuj ponownie."
            )
            return

        if testing:
            return

        QMessageBox.information(
            self,
            "Startowe ustawione",
            "Zapisano biezacy modul jako startowy.\n"
            "Zobaczysz go po restarcie, gdy nie ma sesji lub po 'Wyczysc ostatni stan'."
        )


    def _on_hide_front_toggle(self, hide: bool) -> None:
        s = load_drawing_settings()
        # hide=True => show_front_part=False
        new_s = DrawingSettings(
            rect_line_color=s.rect_line_color,
            rect_line_width_px=s.rect_line_width_px,
            dim_line_color=s.dim_line_color,
            dim_line_width_px=s.dim_line_width_px,
            dim_end_style=s.dim_end_style,
            grid_enabled=s.grid_enabled,
            grid_step_mm=s.grid_step_mm,
            grid_color=s.grid_color,
            grid_width_px=s.grid_width_px,
            show_front_part=(not hide),
            front_mode=s.front_mode,
            edgeband_color=getattr(s, "edgeband_color", "#cc0000"),
            edgeband_width_px=getattr(s, "edgeband_width_px", 4),
        )
        save_drawing_settings(new_s)
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)


    # endregion

    # ---------------------------
    # region PARTS (BOM / wymiary / oklejanie)
    # ---------------------------
    def rebuild_parts(self) -> None:
        """
        Buduje self._draft.parts na podstawie:
        - visible_parts
        - shelf_count / divider_count
        - shelf_mount (lewy/prawy segment)
        - grubosci materia'ow
        """
        self._draft.parts = build_module_parts(self._draft, self._catalog)
        self.tree.rebuild_from_module(self._draft)

    # endregion

    # ==========================================================
    # region APPLY: wczytanie modulu -> UI (pewnie)
    # ==========================================================
    def _restore_front_zone_fields_from_store_payload(self, m: ModuleDef) -> ModuleDef:
        if m is None:
            return m

        name = str(getattr(m, "name", "") or "").strip()
        if not name:
            return m

        raw_all = None
        try:
            if hasattr(self, "_store") and hasattr(self._store, "_read_all"):
                raw_all = self._store._read_all()
        except Exception:
            raw_all = None

        if not isinstance(raw_all, dict):
            return m

        raw = raw_all.get(name)
        if not isinstance(raw, dict):
            return m

        front_keys = (
            "front_layout",
            "front_height_mode",
            "front_top_ref_mode",
            "front_bottom_ref_mode",
            "front_offset_top_mm",
            "front_offset_bottom_mm",
            "front_gap_left_mm",
            "front_gap_right_mm",
            "front_gap_top_mm",
            "front_gap_bottom_mm",
            "front_gap_between_vertical_mm",
            "top_rail_offset_mm",
            "bottom_rail_offset_mm",

        )

        source = raw
        if "module" in raw and isinstance(raw["module"], dict):
            source = raw["module"]

        for key in front_keys:
            if key not in source:
                continue
            try:
                setattr(m, key, source[key])
            except Exception:
                pass

        return m

    def _apply_loaded_module(self, m: ModuleDef) -> None:
        m = self._restore_front_zone_fields_from_store_payload(m)

        self._draft = m
        self._resolved_domain_state = build_resolved_module_domain_state(self._draft)

        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        else:
            self._rebuild_parts()

        self._push_draft_to_ui()

        if getattr(self._draft, "parts", None):
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        self._render_right()
        self.canvas.render_module(
            self._draft,
            fit=True,
            selected_part_key=self._selected_part_key,
        )

        if os.environ.get("TECH_MODUL_WRITE_RESOLVED_DEBUG_ON_LOAD", "").strip() == "1":
            try:
                self.save_resolved_preview_payload_debug_file()
            except Exception:
                pass

        self._session_save_now()

    def get_resolved_domain_state_dict(self) -> dict:
        """
        Zwraca techniczny snapshot resolved-domain-state.

        Na tym etapie:
        - bez wplywu na GUI,
        - bez wplywu na renderer,
        - tylko do bezpiecznego odczytu / diagnostyki / przyszlego preview.
        """
        state = getattr(self, "_resolved_domain_state", None)

        if state is None:
            state = build_resolved_module_domain_state(self._draft)
            self._resolved_domain_state = state

        if hasattr(state, "to_dict"):
            return state.to_dict()

        return {}

    def get_domain_debug_snapshot_dict(self) -> dict:
        """
        Zwraca techniczny snapshot:
        - draft
        - resolved

        Bez wplywu na GUI i renderer.
        Ma sluzyc tylko do bezpiecznej diagnostyki i przyszlych integracji.
        """
        draft = getattr(self, "_draft", None)
        resolved = self.get_resolved_domain_state_dict()

        if hasattr(draft, "to_dict"):
            draft_dict = draft.to_dict()
        else:
            draft_dict = {}

        return {
            "draft": draft_dict,
            "resolved": resolved,
        }

    def get_resolved_preview_payload_dict(self) -> dict:
        """
        Zwraca waski, stabilny payload preview oparty o resolved-domain-state.

        Na tym etapie:
        - bez wplywu na GUI,
        - bez wplywu na renderer,
        - tylko techniczny krok pod przyszly preview / debug / eksport.
        """
        resolved = self.get_resolved_domain_state_dict()

        return {
            "module_name": resolved.get("module_name", ""),
            "module_family_key": resolved.get("module_family_key", ""),
            "material_profile_key": resolved.get("material_profile_key", ""),
            "cabinet_kind": resolved.get("cabinet_kind", ""),
            "ref_point": resolved.get("ref_point", ""),
            "effective_dims": {
                "width_mm": float(resolved.get("width_mm", 0.0) or 0.0),
                "depth_mm": float(resolved.get("depth_mm", 0.0) or 0.0),
                "height_mm": float(resolved.get("height_mm", 0.0) or 0.0),
            },
            "materials": dict(resolved.get("materials", {}) or {}),
            "edgebands": dict(resolved.get("edgebands", {}) or {}),
        }
    def get_resolved_preview_payload_json(self) -> str:
        """
        Zwraca resolved preview payload w postaci stabilnego JSON tekstowego.

        Na tym etapie:
        - bez wplywu na GUI,
        - bez wplywu na renderer,
        - tylko techniczny krok pod przyszly preview / eksport / debug.
        """
        payload = self.get_resolved_preview_payload_dict()

        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def reload_drawing_settings_from_storage(self) -> None:
        """
        Przeladowuje ustawienia rysunku z storage do zakladki "Modul".

        Na tym etapie:
        - nie zmienia danych modulu,
        - odswieza ukryty blok draw_settings,
        - synchronizuje checkbox "Ukryj front na rysunku",
        - synchronizuje ukryte pola zgodnosci w DimensionsBlock,
        - odswieza canvas bez resetu fit/zoom.
        """
        s = load_drawing_settings()

        if hasattr(s, "to_dict"):
            try:
                data = s.to_dict()
            except Exception:
                data = dict(getattr(s, "__dict__", {}) or {})
        else:
            data = dict(getattr(s, "__dict__", {}) or {})

        if hasattr(self, "draw_settings") and hasattr(self.draw_settings, "set_from_settings"):
            self.draw_settings.set_from_settings(data)

        if hasattr(self, "sessview") and hasattr(self.sessview, "chk_hide_front"):
            hide_front = not bool(data.get("show_front_part", True))
            self.sessview.chk_hide_front.blockSignals(True)
            self.sessview.chk_hide_front.setChecked(hide_front)
            self.sessview.chk_hide_front.blockSignals(False)

        # TECH:
        # ukryte pola w DimensionsBlock zostaja tylko jako zgodnosc wsteczna.
        # Zrod'em prawdy sa teraz storage + zak'adka "Rysunek".
        if hasattr(self, "dim") and hasattr(self.dim, "sp_hinge_edge_offset"):
            self.dim.sp_hinge_edge_offset.blockSignals(True)
            self.dim.sp_hinge_edge_offset.setValue(
                float(data.get("hinge_edge_offset_mm", data.get("hinge_edge_offset", 12.0)) or 12.0)
            )
            self.dim.sp_hinge_edge_offset.blockSignals(False)

        if hasattr(self, "dim") and hasattr(self.dim, "sp_auto_double_front_width"):
            self.dim.sp_auto_double_front_width.blockSignals(True)
            self.dim.sp_auto_double_front_width.setValue(
                float(data.get("auto_double_front_width_mm", data.get("auto_double_front_width", 600.0)) or 600.0)
            )
            self.dim.sp_auto_double_front_width.blockSignals(False)

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=getattr(self, "_selected_part_key", "")
            )

    def get_effective_hinge_edge_offset_mm(self) -> float:
        """
        Zwraca efektywny offset zawiasu od brzegu.

        Zrod'o prawdy:
        1) self.draw_settings
        2) storage (load_drawing_settings)
        3) twardy fallback

        Ukryte pola w DimensionsBlock nie sa juz Srod'em prawdy.
        """
        if hasattr(self, "draw_settings") and hasattr(self.draw_settings, "to_settings"):
            try:
                data = self.draw_settings.to_settings() or {}
                return float(data.get("hinge_edge_offset_mm", data.get("hinge_edge_offset", 12.0)) or 12.0)
            except Exception:
                pass

        s = load_drawing_settings()
        if hasattr(s, "to_dict"):
            try:
                data = s.to_dict() or {}
                return float(data.get("hinge_edge_offset_mm", data.get("hinge_edge_offset", 12.0)) or 12.0)
            except Exception:
                pass

        data = dict(getattr(s, "__dict__", {}) or {})
        return float(data.get("hinge_edge_offset_mm", data.get("hinge_edge_offset", 12.0)) or 12.0)

    def get_effective_auto_double_front_width_mm(self) -> float:
        """
        Zwraca efektywny prog szerokosci dla automatycznych 2 drzwi.

        Zrod'o prawdy:
        1) self.draw_settings
        2) storage (load_drawing_settings)
        3) twardy fallback

        Ukryte pola w DimensionsBlock nie sa juz Srod'em prawdy.
        """
        if hasattr(self, "draw_settings") and hasattr(self.draw_settings, "to_settings"):
            try:
                data = self.draw_settings.to_settings() or {}
                return float(data.get("auto_double_front_width_mm", data.get("auto_double_front_width", 600.0)) or 600.0)
            except Exception:
                pass

        s = load_drawing_settings()
        if hasattr(s, "to_dict"):
            try:
                data = s.to_dict() or {}
                return float(data.get("auto_double_front_width_mm", data.get("auto_double_front_width", 600.0)) or 600.0)
            except Exception:
                pass

        data = dict(getattr(s, "__dict__", {}) or {})
        return float(data.get("auto_double_front_width_mm", data.get("auto_double_front_width", 600.0)) or 600.0)


    def save_resolved_preview_payload_debug_file(self) -> str:
        """
        Zapisuje aktualny resolved preview payload do technicznego pliku debugowego.

        Na tym etapie:
        - bez wplywu na GUI,
        - bez wplywu na renderer,
        - tylko techniczny krok pod debug / preview / eksport.
        """
        payload = self.get_resolved_preview_payload_dict()
        return save_resolved_preview_payload(payload)

    # ---------------------------
    # region RENDER
    # ---------------------------
    def _render_right(self) -> None:
        key = self._selected_part_key
        part = self._draft.parts.get(key)

        if part is None and self._draft.parts:
            key = next(iter(self._draft.parts.keys()))
            self._selected_part_key = key
            part = self._draft.parts.get(key)

        if part is not None:
            fallback_edge_key = self.edge.get_default_edgeband_key() if hasattr(self.edge, "get_default_edgeband_key") else "Brak"
            group_defaults = resolve_group_edgeband_defaults(
                dict(getattr(self._draft, "edgebands", {}) or {}),
                fallback_key=fallback_edge_key,
            )
            group_key = get_material_edge_group_for_part_key(part.key)
            if hasattr(self.edge, "set_default_edgeband_key"):
                self.edge.set_default_edgeband_key(group_defaults.get(group_key, fallback_edge_key))

            self.edge.set_current_part(part.key, part.name_pl)
            self.edge.load_edge_banding(part.edge_banding or {})
            self.bom.set_part(part, default_material_key=self._default_material_key_for_part(part.key))
        else:
            self.edge.set_current_part("", "(brak)")
            if hasattr(self.bom, "clear_part"):
                self.bom.clear_part()

        # NAJWAZNIEJSZE: zawsze licz z CALEGO modulu
        self.bom.set_module(self._draft)

        # licznik zaznaczen (jesli masz multi)
        if hasattr(self.tree, "selected_part_keys"):
            self.edge.set_selected_count(len(self.tree.selected_part_keys()) or 1)
        else:
            self.edge.set_selected_count(1)

        self._refresh_module_mini_preview()

    def _refresh_module_mini_preview(self) -> None:
        if not hasattr(self, "preview_mini"):
            return

        try:
            self.preview_mini.set_module(self._draft)
        except Exception:
            return

        if not hasattr(self, "preview_info"):
            return

        name = str(getattr(self._draft, "name", "") or "").strip() or "Nowy modul"
        try:
            width_mm = float(getattr(self._draft, "width_mm", 0.0) or 0.0)
            height_mm = float(getattr(self._draft, "height_mm", 0.0) or 0.0)
            depth_mm = float(getattr(self._draft, "depth_mm", 0.0) or 0.0)
        except Exception:
            width_mm = 0.0
            height_mm = 0.0
            depth_mm = 0.0

        dims_line = f"{int(round(width_mm))} x {int(round(height_mm))} x {int(round(depth_mm))} mm"
        self.preview_info.setText(f"{name}\n{dims_line}")
    # endregion

    # ---------------------------
    # region EVENTS
    # ---------------------------
    def _on_any_change(self) -> None:
        if getattr(self, "_is_pushing_ui", False):
            return

        if hasattr(self, "_sync_existence_dependent_visibility_ui"):
            self._sync_existence_dependent_visibility_ui()

        current_vis = set(self.vis.get_visible_parts() or set())
        prev_vis_now = set(getattr(self, "_last_vis_now", current_vis) or set())
        vis_now = set(current_vis)

        # aktualne wartosci z UI
        try:
            shelf_ui = int(self.shelves.get_value())
        except Exception:
            shelf_ui = 0

        try:
            div_ui = int(self.dividers.get_count())
        except Exception:
            div_ui = 0

        # 1) jesli user ODZNACZYL checkbox recznie -> wyzeruj licznik
        if ("divider" in prev_vis_now) and ("divider" not in current_vis):
            self._is_pushing_ui = True
            try:
                self.dividers.set_values(0, self.dividers.get_mount())
            finally:
                self._is_pushing_ui = False
            div_ui = 0
            vis_now.discard("divider")

        if ("shelf" in prev_vis_now) and ("shelf" not in current_vis):
            self._is_pushing_ui = True
            try:
                self.shelves.set_value(0)
            finally:
                self._is_pushing_ui = False
            shelf_ui = 0
            vis_now.discard("shelf")

        # 2) AUTO-SYNC: licznik > 0 => checkbox ma sie dopasowac
        if div_ui > 0:
            vis_now.add("divider")
        else:
            vis_now.discard("divider")

        if shelf_ui > 0:
            vis_now.add("shelf")
        else:
            vis_now.discard("shelf")

        # 3) docisnij poprawiony stan checkboxow do UI
        if vis_now != current_vis:
            self._is_pushing_ui = True
            try:
                self.vis.set_checked(vis_now)
            finally:
                self._is_pushing_ui = False

        # 4) aktywnosc blokow
        if hasattr(self.dividers, "set_enabled"):
            self.dividers.set_enabled(True)

        if hasattr(self.dividers, "set_mount_enabled"):
            self.dividers.set_mount_enabled(div_ui > 0)

        # Blok po'ek musi pozostac aktywny takze przy 0 po'ek,
        # zeby uzytkownik mog' dodac pierwsza po'ke z powrotem.
        if hasattr(self.shelves, "set_enabled"):
            self.shelves.set_enabled(True)

        # 5) NORMALIZACJA STREFY FRONTU wzgledem aktualnej wysokosci modulu
        module_h_mm = 0.0
        try:
            module_h_mm = float(self.dim.sp_h.value())
        except Exception:
            module_h_mm = float(getattr(self._draft, "height_mm", 0.0) or 0.0)

        top_rail_mm = 18.0
        try:
            parts = getattr(self._draft, "parts", None) or {}
            p_top = parts.get("top")
            if p_top and getattr(p_top, "dims_mm", None) and "t" in p_top.dims_mm:
                top_rail_mm = float(p_top.dims_mm["t"])
        except Exception:
            top_rail_mm = 18.0

        if hasattr(self, "fhw") and hasattr(self.fhw, "normalize_front_zone"):
            self.fhw.normalize_front_zone(
                module_height_mm=module_h_mm,
                top_rail_thickness_mm=top_rail_mm,
            )

        # 6) UI -> draft
        self._pull_ui_to_draft()

        # 7) przebudowa parts
        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        elif hasattr(self, "_rebuild_parts"):
            self._rebuild_parts()

        # 8) odswiezenie prawej strony i canvasa
        if hasattr(self, "_render_right"):
            self._render_right()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=True,
                selected_part_key=getattr(self, "_selected_part_key", "")
            )

        # TECH: kontrolowany zapis resolved preview debug file po zmianie UI
        # dzia'a tylko wtedy, gdy jawnie w'aczysz:
        # TECH_MODUL_WRITE_RESOLVED_DEBUG_ON_CHANGE=1
        if os.environ.get("TECH_MODUL_WRITE_RESOLVED_DEBUG_ON_CHANGE", "").strip() == "1":
            try:
                self.save_resolved_preview_payload_debug_file()
            except Exception:
                pass

        # 9) zapamietaj stan
        self._last_vis_now = set(vis_now)
        self._last_div_ui = div_ui
        self._last_shelf_ui = shelf_ui
    # ==========================================================
    # region PARTS SYNC: po'ki/piony musza przebudowac parts
    # ==========================================================
    def _ensure_parts_consistent(self) -> bool:
        """
        Jesli zmieni'a sie liczba po'ek/pionow lub ich widocznosc,
        musimy przebudowac parts, bo inaczej rysunek sie nie zmieni.
        """
        vp = set(getattr(self._draft, "visible_parts", set()) or set())

        shelf_n = int(getattr(self._draft, "shelf_count", 0) or 0) if "shelf" in vp else 0
        div_n = int(getattr(self._draft, "divider_count", 0) or 0) if "divider" in vp else 0
        shelf_mount = str(getattr(self._draft, "shelf_mount", "right") or "right").strip().lower()
        expected_shelf_parts = shelf_n * 2 if (shelf_mount == "both" and div_n > 0) else shelf_n

        parts = getattr(self._draft, "parts", None) or {}
        self._draft.parts = parts

        exist_shelves = [k for k in parts.keys() if str(k).startswith("shelf_")]
        exist_divs = [k for k in parts.keys() if str(k).startswith("divider_")]

        need = (len(exist_shelves) != expected_shelf_parts) or (len(exist_divs) != div_n)

        if not need:
            return False

        if hasattr(self, "rebuild_parts"):
            self.rebuild_parts()
        else:
            self._rebuild_parts()



        return True

    # endregion


    # ==========================================================
    # region EDGE: oklejanie (nie przebudowuje czesci!)
    # ==========================================================
    def _normalize_part_key_for_selection(self, part_key: str) -> str:
        return normalize_part_key_for_model(part_key)

    def _default_material_key_for_part(self, part_key: str) -> str:
        group_key = get_material_group_for_part_key(part_key)
        materials = dict(getattr(self._draft, "materials", {}) or {})

        if group_key == "front":
            return str(materials.get("front", "MDF19") or "MDF19")
        if group_key == "back":
            return str(materials.get("back", "HDF2.5") or "HDF2.5")
        return str(materials.get("carcass", "PB18") or "PB18")

    def _apply_material_to_part(self, part: PartDef, material_key: str, override_key: str = "") -> None:
        selected_key = str(material_key or "").strip()
        part.material_key = selected_key
        part.material_override_key = str(override_key or "").strip()

        try:
            current_t = float((part.dims_mm or {}).get("t", 0.0) or 0.0)
        except Exception:
            current_t = 0.0

        try:
            new_t = float(self._catalog.material_thickness(selected_key, current_t) or current_t)
        except Exception:
            new_t = current_t

        if isinstance(part.dims_mm, dict):
            part.dims_mm["t"] = new_t

    def _edge_get_current_dict(self) -> dict:
        # preferuj publiczna metode
        if hasattr(self.edge, "get_edge_banding"):
            try:
                d = self.edge.get_edge_banding()
                return dict(d or {})
            except Exception:
                pass

        # fallback na typowe pola
        for attr in ("edge_banding", "_edge_banding", "current_edge_banding"):
            if hasattr(self.edge, attr):
                try:
                    d = getattr(self.edge, attr)
                    return dict(d or {})
                except Exception:
                    pass

        return {}

    def _on_edge_changed(self) -> None:
        # zapisz okleine do zaznaczonych elementow (albo jednego)
        if not getattr(self, "_draft", None) or not getattr(self._draft, "parts", None):
            return

        eb = self._edge_get_current_dict()

        if hasattr(self.tree, "selected_part_keys"):
            keys = list(self.tree.selected_part_keys() or [])
        else:
            keys = [getattr(self, "_selected_part_key", "")]

        if not keys:
            keys = [getattr(self, "_selected_part_key", "")]

        for k in keys:
            if not k:
                continue
            # normalizacja (gdyby kiedys polecialo "front__top")
            base_k = k.split("__", 1)[0] if "__" in k else (k.split("@", 1)[0] if "@" in k else k)
            part = self._draft.parts.get(base_k)
            if part is not None:
                part.edge_banding = dict(eb)

        # odswiez prawa strone + rysunek (bez rebuild_parts)
        self._render_right()
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)

        self._session_save_request()

    def _on_part_material_changed(self, material_key: str) -> None:
        if not getattr(self, "_draft", None) or not getattr(self._draft, "parts", None):
            return

        base_key = self._normalize_part_key_for_selection(getattr(self, "_selected_part_key", ""))
        if not base_key:
            return

        part = self._draft.parts.get(base_key)
        if part is None:
            return

        selected_key = str(material_key or "").strip()
        if not selected_key:
            return

        default_key = self._default_material_key_for_part(base_key)
        override_key = "" if selected_key == default_key else selected_key
        self._apply_material_to_part(part, selected_key, override_key=override_key)

        self._render_right()
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)
        self._session_save_request()

    def _on_part_material_reset_requested(self) -> None:
        if not getattr(self, "_draft", None) or not getattr(self._draft, "parts", None):
            return

        base_key = self._normalize_part_key_for_selection(getattr(self, "_selected_part_key", ""))
        if not base_key:
            return

        part = self._draft.parts.get(base_key)
        if part is None:
            return

        default_key = self._default_material_key_for_part(base_key)
        self._apply_material_to_part(part, default_key, override_key="")

        self._render_right()
        self.canvas.render_module(self._draft, fit=False, selected_part_key=self._selected_part_key)
        self._session_save_request()

    def _on_material_profile_selected(self, profile_key: str) -> None:
        if getattr(self, "_is_pushing_ui", False):
            return

        profile = self._catalog.get_material_profile(str(profile_key or "STD_WHITE"))
        grouped_materials = collapse_profile_map_to_groups(
            dict(profile.material_map or {}),
            fallback_map=self.mat.get_materials() if hasattr(self.mat, "get_materials") else {},
        )
        grouped_edgebands = collapse_profile_map_to_groups(
            dict(profile.edgeband_map or {}),
            fallback_map=self.mat.get_edgebands() if hasattr(self.mat, "get_edgebands") else {},
        )
        hardware_vendors = dict(profile.hardware_vendor_map or {})

        self._is_pushing_ui = True
        try:
            if hasattr(self.mat, "set_materials"):
                self.mat.set_materials(grouped_materials)
            if hasattr(self.mat, "set_edgebands"):
                self.mat.set_edgebands(grouped_edgebands)

            hinge_vendor = str(hardware_vendors.get("hinge", "") or "").strip().lower()
            if hinge_vendor and hasattr(self.fhw, "cb_hinge_vendor"):
                idx = self.fhw.cb_hinge_vendor.findData(hinge_vendor)
                if idx >= 0:
                    self.fhw.cb_hinge_vendor.setCurrentIndex(idx)

            drawer_vendor = str(hardware_vendors.get("drawer_system", "") or "").strip().lower()
            if drawer_vendor and hasattr(self.fhw, "cb_drawer_vendor"):
                idx = self.fhw.cb_drawer_vendor.findData(drawer_vendor)
                if idx >= 0:
                    self.fhw.cb_drawer_vendor.setCurrentIndex(idx)
        finally:
            self._is_pushing_ui = False

        self._on_any_change()

    def _on_catalog_changed(self) -> None:
        if hasattr(self, "mat") and hasattr(self.mat, "reload_catalog"):
            self.mat.reload_catalog()
        if hasattr(self, "edge") and hasattr(self.edge, "reload_catalog"):
            self.edge.reload_catalog()
        if hasattr(self, "bom") and hasattr(self.bom, "reload_catalog"):
            self.bom.reload_catalog()
        if hasattr(self, "fhw") and hasattr(self.fhw, "reload_catalog"):
            self.fhw.reload_catalog()

        self._on_any_change()

    # endregion

    def _sync_front_zone_selection_context(self, selected_key: str = "") -> None:
        key = str(selected_key or getattr(self, "_selected_part_key", "") or "").strip()

        if not hasattr(self, "fhw"):
            return

        if key == "front":
            if hasattr(self, "canvas") and hasattr(self.canvas, "clear_active_rail_offset_handle"):
                self.canvas.clear_active_rail_offset_handle()
            mode = str(self.fhw.cb_front_height_mode.currentData() or "full").strip().lower()

            if mode == "full":
                self.fhw.set_zone_context(
                    "Wybrano front. Aktywna jest pelna wysokosc frontu modulu."
                )
            elif mode == "to_top_rail":
                self.fhw.set_zone_context(
                    "Wybrano front. Tryb do wienca gornego - mozesz regulowac dolna granice strefy."
                )
            else:
                self.fhw.set_zone_context(
                    "Wybrano front. Tryb offsetow - mozesz regulowac gorna i dolna granice strefy."
                )
        else:
            self.fhw.clear_zone_context()
            if hasattr(self, "canvas") and hasattr(self.canvas, "clear_active_preview_handle"):
                self.canvas.clear_active_preview_handle()
            elif hasattr(self, "canvas") and hasattr(self.canvas, "clear_active_front_zone_handle"):
                self.canvas.clear_active_front_zone_handle()

    def _on_selected_part(self, part_key: str) -> None:
        self._selected_part_key = part_key
        self._sync_front_zone_selection_context(part_key)

        if hasattr(self, "_render_right"):
            self._render_right()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=self._selected_part_key,
            )

        if hasattr(self, "edge") and hasattr(self.edge, "set_selected_count"):
            try:
                self.edge.set_selected_count(len(self.tree.selected_part_keys()))
            except Exception:
                self.edge.set_selected_count(1)

        if hasattr(self, "_session_save_request"):
            self._session_save_request()

    def _on_parts_table_visibility_changed(self, part_key: str, visible: bool) -> None:
        """Obsluга klikniecia ikony oka w tabeli formatek — toggluje widocznosc elementu."""
        if not getattr(self, "_draft", None):
            return
        from dataclasses import replace as _dc_replace
        vp = set(getattr(self._draft, "visible_parts", set()) or set())
        if visible:
            vp.add(part_key)
        else:
            vp.discard(part_key)
        try:
            self._draft = _dc_replace(self._draft, visible_parts=vp)
        except Exception:
            return
        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(self._draft, fit=False,
                                      selected_part_key=getattr(self, "_selected_part_key", ""))
        if hasattr(self, "_session_save_request"):
            self._session_save_request()

    def _on_parts_table_grain_changed(self, part_key: str, grain_direction: str) -> None:
        """Obsluга klikniecia komorki uslojenia w tabeli — zmienia grain_direction w PartDef."""
        if not getattr(self, "_draft", None):
            return
        from dataclasses import replace as _dc_replace
        parts = dict(self._draft.parts or {})
        part = parts.get(part_key)
        if part is None:
            return
        parts[part_key] = _dc_replace(part, grain_direction=grain_direction)
        try:
            self._draft = _dc_replace(self._draft, parts=parts)
        except Exception:
            return
        if hasattr(self, "_session_save_request"):
            self._session_save_request()

    def _on_canvas_part_clicked(self, part_key: str) -> None:
        if "__" in part_key:
            base_key = part_key.split("__", 1)[0]
        elif "@" in part_key:
            base_key = part_key.split("@", 1)[0]
        else:
            base_key = part_key

        self._selected_part_key = base_key

        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ShiftModifier:
            if hasattr(self.tree, "toggle_part"):
                self.tree.toggle_part(base_key)
            else:
                self.tree.select_part(base_key)
        else:
            self.tree.select_part(base_key)

        if base_key != "front":
            if hasattr(self.canvas, "clear_active_preview_handle"):
                self.canvas.clear_active_preview_handle()
            elif hasattr(self.canvas, "clear_active_front_zone_handle"):
                self.canvas.clear_active_front_zone_handle()

        self._sync_front_zone_selection_context(base_key)

        if hasattr(self, "_render_right"):
            self._render_right()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=self._selected_part_key,
            )

        if hasattr(self, "edge") and hasattr(self.edge, "set_selected_count"):
            try:
                self.edge.set_selected_count(len(self.tree.selected_part_keys()))
            except Exception:
                self.edge.set_selected_count(1)

    def _on_front_zone_handle_clicked(self, handle_key: str) -> None:
        role = "dolny"
        if str(handle_key).endswith("__top"):
            role = "gorny"

        self._selected_part_key = "front"

        try:
            self.tree.select_part("front")
        except Exception:
            pass

        if hasattr(self, "canvas") and hasattr(self.canvas, "set_active_front_zone_handle"):
            self.canvas.set_active_front_zone_handle(handle_key)

        if hasattr(self.fhw, "set_hint"):
            self.fhw.set_hint(
                f"Wybrano {role} uchwyt strefy frontu. "
                f"Mozesz przeciagac go myszka w pionie."
            )

        if hasattr(self.fhw, "set_zone_context"):
            mode = str(self.fhw.cb_front_height_mode.currentData() or "full").strip().lower()
            if mode == "to_top_rail":
                self.fhw.set_zone_context(
                    f"Aktywna edycja: {role} uchwyt strefy frontu. "
                    f"W tym trybie regulujesz dolna granice strefy."
                )
            else:
                self.fhw.set_zone_context(
                    f"Aktywna edycja: {role} uchwyt strefy frontu. "
                    f"Zmiana od razu aktualizuje offsety w panelu."
                )

        if hasattr(self, "_render_right"):
            self._render_right()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=self._selected_part_key,
            )

        if hasattr(self, "edge") and hasattr(self.edge, "set_selected_count"):
            try:
                self.edge.set_selected_count(len(self.tree.selected_part_keys()))
            except Exception:
                self.edge.set_selected_count(1)

    def _on_rail_offset_handle_clicked(self, handle_key: str) -> None:
        base_key = "bottom"
        role = "dolny"
        if str(handle_key).endswith("__top"):
            base_key = "top"
            role = "gorny"

        self._selected_part_key = base_key

        try:
            self.tree.select_part(base_key)
        except Exception:
            pass

        if hasattr(self, "canvas") and hasattr(self.canvas, "set_active_rail_offset_handle"):
            self.canvas.set_active_rail_offset_handle(handle_key)

        if hasattr(self.fhw, "set_hint"):
            self.fhw.set_hint(
                f"Wybrano {role} uchwyt wienca. Zlap niebieski pasek i przeciagaj go myszka w pionie "
                f"albo wpisz offset w polach po lewej."
            )

        if hasattr(self, "_render_right"):
            self._render_right()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=self._selected_part_key,
            )

        if hasattr(self, "edge") and hasattr(self.edge, "set_selected_count"):
            try:
                self.edge.set_selected_count(len(self.tree.selected_part_keys()))
            except Exception:
                self.edge.set_selected_count(1)

    def _on_front_zone_handle_dragged(self, handle_key: str, scene_y: float) -> None:
        mode = str(self.fhw.cb_front_height_mode.currentData() or "full").strip().lower()
        if mode not in ("offsets", "to_top_rail"):
            return

        H = float(self.dim.sp_h.value())
        min_face_h = 2.0

        t_carcass = 18.0
        try:
            p_sl = (self._draft.parts or {}).get("side_left")
            if p_sl and getattr(p_sl, "dims_mm", None) and "t" in p_sl.dims_mm:
                t_carcass = float(p_sl.dims_mm["t"])
        except Exception:
            t_carcass = 18.0

        current_top = float(self.fhw.sp_front_offset_top.value())
        current_bottom = float(self.fhw.sp_front_offset_bottom.value())

        if mode == "to_top_rail":
            top_off = max(0.0, float(t_carcass))
        else:
            top_off = max(0.0, current_top)

        y = max(0.0, min(float(scene_y), H))
        changed = False

        if str(handle_key).endswith("__top") and mode == "offsets":
            max_top = max(0.0, H - current_bottom - min_face_h)
            new_top = max(0.0, min(y, max_top))

            if abs(new_top - current_top) >= 0.1:
                self.fhw.sp_front_offset_top.setValue(new_top)
                changed = True

        elif str(handle_key).endswith("__bottom"):
            max_bottom = max(0.0, H - top_off - min_face_h)
            new_bottom = max(0.0, min(H - y, max_bottom))

            if abs(new_bottom - current_bottom) >= 0.1:
                self.fhw.sp_front_offset_bottom.setValue(new_bottom)
                changed = True

        if changed:
            self._selected_part_key = "front"

            if hasattr(self, "canvas") and hasattr(self.canvas, "set_active_front_zone_handle"):
                self.canvas.set_active_front_zone_handle(handle_key)

            self._sync_front_zone_selection_context("front")

            if hasattr(self.fhw, "set_hint"):
                if mode == "to_top_rail":
                    self.fhw.set_hint(
                        f"Strefa frontu: do wienca gornego, dol {self.fhw.sp_front_offset_bottom.value():.1f} mm."
                    )
                else:
                    self.fhw.set_hint(
                        f"Strefa frontu: gora {self.fhw.sp_front_offset_top.value():.1f} mm, "
                        f"dol {self.fhw.sp_front_offset_bottom.value():.1f} mm."
                    )

            if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
                self.canvas.render_module(
                    self._draft,
                    fit=False,
                    selected_part_key=self._selected_part_key,
                )

    def _on_rail_offset_handle_dragged(self, handle_key: str, scene_y: float) -> None:
        H = float(self.dim.sp_h.value())

        t_carcass = 18.0
        try:
            p_sl = (self._draft.parts or {}).get("side_left")
            if p_sl and getattr(p_sl, "dims_mm", None) and "t" in p_sl.dims_mm:
                t_carcass = float(p_sl.dims_mm["t"])
        except Exception:
            t_carcass = 18.0

        current_top = float(self.dim.sp_top_rail_offset.value())
        current_bottom = float(self.dim.sp_bottom_rail_offset.value())

        y = max(0.0, min(float(scene_y), H))
        changed = False
        base_key = "bottom"

        if str(handle_key).endswith("__top"):
            base_key = "top"
            max_top = max(0.0, H - 2.0 * t_carcass - current_bottom)
            new_top = max(0.0, min(y, max_top))

            if abs(new_top - current_top) >= 0.1:
                self.dim.sp_top_rail_offset.setValue(new_top)
                changed = True

        elif str(handle_key).endswith("__bottom"):
            max_bottom = max(0.0, H - 2.0 * t_carcass - current_top)
            new_bottom = max(0.0, min(H - t_carcass - y, max_bottom))

            if abs(new_bottom - current_bottom) >= 0.1:
                self.dim.sp_bottom_rail_offset.setValue(new_bottom)
                changed = True

        if changed:
            self._selected_part_key = base_key

            try:
                self.tree.select_part(base_key)
            except Exception:
                pass

            if hasattr(self, "canvas") and hasattr(self.canvas, "set_active_rail_offset_handle"):
                self.canvas.set_active_rail_offset_handle(handle_key)

            if hasattr(self.fhw, "set_hint"):
                self.fhw.set_hint(
                    f"Wieniec gorny: {self.dim.sp_top_rail_offset.value():.1f} mm, "
                    f"wieniec dolny: {self.dim.sp_bottom_rail_offset.value():.1f} mm."
                )

            if hasattr(self, "_render_right"):
                self._render_right()

            if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
                self.canvas.render_module(
                    self._draft,
                    fit=False,
                    selected_part_key=self._selected_part_key,
                )
    def _on_drawing_settings_changed(self) -> None:
        self._sync_front_zone_selection_context()

        if hasattr(self, "canvas") and hasattr(self.canvas, "render_module"):
            self.canvas.render_module(
                self._draft,
                fit=False,
                selected_part_key=self._selected_part_key,
            )

    def _show_storage_operation_error(self, action_label: str, exc: Exception) -> None:
        action = str(action_label or "wykonac operacje na module").strip()
        message = (
            f"Nie udalo sie {action}.\n\n"
            f"Szczegoly: {exc}"
        )
        try:
            QMessageBox.critical(self, "Blad zapisu/odczytu", message)
        except Exception:
            pass

    def _on_save_new(self) -> None:
        try:
            self._pull_ui_to_draft()
            if not self._draft.name:
                QMessageBox.warning(self, "Brak nazwy", "Podaj nazwe modulu przed zapisem.")
                return

            res = self._store.save_new(self._draft)
        except Exception as exc:
            self._show_storage_operation_error("zapisac nowy modul", exc)
            return

        ok = bool(getattr(res, "ok", True))
        message = str(getattr(res, "message_pl", "") or "Zapis zakonczony.")
        if ok:
            QMessageBox.information(self, "Zapis", message)
        else:
            QMessageBox.warning(self, "Zapis", message)
        self._refresh_crud_action_state()

    def _on_overwrite(self) -> None:
        try:
            self._pull_ui_to_draft()
            if not self._draft.name:
                QMessageBox.warning(self, "Brak nazwy", "Podaj nazwe modulu przed nadpisaniem.")
                return

            res = self._store.overwrite(self._draft)
        except Exception as exc:
            self._show_storage_operation_error("nadpisac modul", exc)
            return

        ok = bool(getattr(res, "ok", True))
        message = str(getattr(res, "message_pl", "") or "Nadpisywanie zakonczone.")
        if ok:
            QMessageBox.information(self, "Nadpisz", message)
        else:
            QMessageBox.warning(self, "Nadpisz", message)
        self._refresh_crud_action_state()

    def _on_load(self) -> None:
        name = self.dim.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Brak nazwy", "Wpisz nazwe modulu do wczytania.")
            return

        try:
            m = self._store.get(name)
        except Exception as exc:
            self._show_storage_operation_error(f'wczytac modul "{name}"', exc)
            return
        if m is None:
            QMessageBox.warning(self, "Brak w bazie", f'Nie znaleziono modulu "{name}".')
            return

        ans = QMessageBox.question(self, "Wczytac...", f'Wczytac modul "{name}"...')
        if ans != QMessageBox.StandardButton.Yes:
            return

        try:
            self._apply_loaded_module(m)
        except Exception as exc:
            self._show_storage_operation_error(f'zastosowac wczytany modul "{name}"', exc)

    def _session_save_request(self) -> None:
        if not getattr(self, "_session_ready", False):
            return
        # nie zapisuj pustego stanu
        if not getattr(self._draft, "visible_parts", None):
            return
        self._session_timer.start(250)

    def _session_save_now(self) -> None:
        if not getattr(self, "_session_ready", False):
            return
        if not getattr(self._draft, "visible_parts", None):
            return
        try:
            ui = {"selected_part_key": self._selected_part_key}
            save_last_session(self._draft, ui)
        except Exception:
            pass

    def _apply_module(self, m: ModuleDef) -> None:
        # pelne, poprawne zastosowanie modulu (tu byl problem "otwiera nieprawidlowa")
        self._draft = m
        if not getattr(self._draft, "parts", None):
            # czesci beda zbudowane z widocznych/materiali
            if hasattr(self, "rebuild_parts"):
                self.rebuild_parts()
            else:
                self._rebuild_parts()
        else:
            # i tak przebuduj, zeby by'o spojnie z aktualna logika
            if hasattr(self, "rebuild_parts"):
                self.rebuild_parts()
            else:
                self._rebuild_parts()

        self._push_draft_to_ui()

        if self._draft.parts:
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        self._render_right()
        self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)

        # wazne dla "restart nie dzia'a" - zapisz sesje od razu
        if hasattr(self, "_session_save_now"):
            self._session_save_now()

    def _on_load_from_base_preview(self) -> None:
        try:
            dlg = LoadModuleDialog(self, self._store)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return

            res = dlg.result_value()
            if res is None:
                return

            if not self._is_testing():
                answer = QMessageBox.question(
                    self,
                    "Wczytaj modul",
                    f'Wczytac modul "{res.name}"?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

            self._apply_loaded_module(res.module)
            self._refresh_crud_action_state()
        except Exception as exc:
            self._show_storage_operation_error("wczytac modul z podgladu bazy", exc)

    def load_module_from_store_name(self, name: str) -> bool:
        try:
            module_name = str(name or "").strip()
            if not module_name:
                return False

            module = self._store.get(module_name) if hasattr(self._store, "get") else None
            if module is None:
                return False

            self._apply_loaded_module(module)
            return True
        except Exception:
            return False

    def _on_clear_current_module(self) -> None:
        if not self._is_testing():
            answer = QMessageBox.question(
                self,
                "Wyczysc modul",
                "Wyczysc aktualny modul i porzucic niezapisane zmiany?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._apply_loaded_module(build_default_module())
        self._refresh_crud_action_state()

    def start_new_module(self) -> None:
        self._apply_loaded_module(build_default_module())
        self._refresh_crud_action_state()

    # ==========================================================
    # region BASE CRUD: Zapisz / Nadpisz / Usun (odporne na rozne sygnatury store)
    # ==========================================================
    def _is_testing(self) -> bool:
        return str(os.environ.get("TECH_MODUL_TESTING", "")).strip() == "1"

    def _store_list_names(self) -> list[str]:
        for fn in ("list_names", "list_module_names", "names", "list"):
            if hasattr(self._store, fn):
                try:
                    out = getattr(self._store, fn)()
                    return list(out) if out is not None else []
                except Exception:
                    pass
        return []

    def _store_has(self, name: str) -> bool:
        names = self._store_list_names()
        if names is not None:
            return name in names

        # fallback: probuj load/get, ale ostroznie
        for fn in ("load", "load_module", "get", "read"):
            if hasattr(self._store, fn):
                try:
                    out = getattr(self._store, fn)(name)
                    if out is None:
                        return False

                    if hasattr(out, "name"):
                        return str(getattr(out, "name", "") or "") == name

                    if isinstance(out, dict):
                        if "name" in out:
                            return str(out.get("name") or "") == name
                        if "module" in out and isinstance(out["module"], dict):
                            return str(out["module"].get("name") or "") == name

                    # nie zgadujemy "True" tylko dlatego, ze cos wroci'o
                    return False
                except Exception:
                    return False
        return False

    def _store_call(self, fn_name: str, variants: list[tuple]) -> bool:
        """
        Wywo'uje store.fn_name na kolejnych wariantach argumentow.
        Zwraca True gdy sie uda, False gdy brak metody.
        """
        if not hasattr(self._store, fn_name):
            return False

        fn = getattr(self._store, fn_name)
        last_error: Exception | None = None

        for args in variants:
            try:
                fn(*args)
                return True
            except (TypeError, AttributeError) as e:
                last_error = e
                continue

        if last_error is not None:
            raise last_error
        return False

    def _build_store_payload(self, name: str, m: ModuleDef) -> dict:
        """
        Buduje payload do zapisu i jawnie dopina front zone,
        referencje frontu i luzy frontowe.
        """
        try:
            payload = m.to_dict()
        except Exception:
            payload = dict(getattr(m, "__dict__", {}) or {})

        payload = dict(payload or {})
        payload["name"] = payload.get("name") or name

        payload["front_layout"] = str(
            getattr(m, "front_layout", None)
            or self.fhw.cb_front_layout.currentData()
            or "overlay"
        )

        payload["front_height_mode"] = str(
            getattr(m, "front_height_mode", None)
            or self.fhw.cb_front_height_mode.currentData()
            or "full"
        )

        payload["front_top_ref_mode"] = str(
            getattr(m, "front_top_ref_mode", None)
            or self.fhw.cb_top_ref_mode.currentData()
            or "rail_end"
        )
        payload["front_bottom_ref_mode"] = str(
            getattr(m, "front_bottom_ref_mode", None)
            or self.fhw.cb_bottom_ref_mode.currentData()
            or "rail_end"
        )

        try:
            payload["front_offset_top_mm"] = float(
                getattr(m, "front_offset_top_mm", self.fhw.sp_front_offset_top.value())
            )
        except Exception:
            payload["front_offset_top_mm"] = float(self.fhw.sp_front_offset_top.value())

        try:
            payload["front_offset_bottom_mm"] = float(
                getattr(m, "front_offset_bottom_mm", self.fhw.sp_front_offset_bottom.value())
            )
        except Exception:
            payload["front_offset_bottom_mm"] = float(self.fhw.sp_front_offset_bottom.value())

        def _num_attr(attr_name: str, widget_value: float) -> float:
            try:
                return float(getattr(m, attr_name, widget_value))
            except Exception:
                return float(widget_value)

        try:
            payload["top_rail_offset_mm"] = float(
                getattr(m, "top_rail_offset_mm", self.dim.sp_top_rail_offset.value())
            )
        except Exception:
            payload["top_rail_offset_mm"] = float(self.dim.sp_top_rail_offset.value())

        try:
            payload["bottom_rail_offset_mm"] = float(
                getattr(m, "bottom_rail_offset_mm", self.dim.sp_bottom_rail_offset.value())
            )
        except Exception:
            payload["bottom_rail_offset_mm"] = float(self.dim.sp_bottom_rail_offset.value())


        payload["front_gap_left_mm"] = _num_attr("front_gap_left_mm", self.fhw.sp_gap_left.value())
        payload["front_gap_right_mm"] = _num_attr("front_gap_right_mm", self.fhw.sp_gap_right.value())
        payload["front_gap_top_mm"] = _num_attr("front_gap_top_mm", self.fhw.sp_gap_top.value())
        payload["front_gap_bottom_mm"] = _num_attr("front_gap_bottom_mm", self.fhw.sp_gap_bottom.value())
        payload["front_gap_between_vertical_mm"] = _num_attr(
            "front_gap_between_vertical_mm",
            self.fhw.sp_gap_between_vertical.value(),
        )

        return payload

    def _store_force_front_zone_fields_in_json(self, name: str, payload: dict) -> None:
        """
        Awaryjny dopis front zone, referencji frontu i luzow
        bezposrednio do surowego JSON-a store.
        """
        try:
            if not hasattr(self._store, "_read_all") or not hasattr(self._store, "_write_all"):
                return

            raw_all = self._store._read_all()
            if not isinstance(raw_all, dict):
                return

            entry = raw_all.get(name)
            if entry is None:
                return

            front_keys = (
                "front_layout",
                "front_height_mode",
                "front_top_ref_mode",
                "front_bottom_ref_mode",
                "front_offset_top_mm",
                "front_offset_bottom_mm",
                "front_gap_left_mm",
                "front_gap_right_mm",
                "front_gap_top_mm",
                "front_gap_bottom_mm",
                "front_gap_between_vertical_mm",
                "top_rail_offset_mm",
                "bottom_rail_offset_mm",
                "top_rail_offset_mm",
                "bottom_rail_offset_mm",

            )

            if isinstance(entry, dict):
                if "module" in entry and isinstance(entry["module"], dict):
                    mod = dict(entry["module"])
                    for k in front_keys:
                        if k in payload:
                            mod[k] = payload[k]
                    entry = dict(entry)
                    entry["module"] = mod
                    raw_all[name] = entry
                else:
                    entry = dict(entry)
                    for k in front_keys:
                        if k in payload:
                            entry[k] = payload[k]
                    raw_all[name] = entry

                self._store._write_all(raw_all)
        except Exception:
            pass

    def _patch_module_for_store(self, name: str, m: ModuleDef, payload: dict):
        try:
            m.name = name
        except Exception:
            pass

        for k in (
                "front_layout",
                "front_height_mode",
                "front_top_ref_mode",
                "front_bottom_ref_mode",
                "front_offset_top_mm",
                "front_offset_bottom_mm",
                "front_gap_left_mm",
                "front_gap_right_mm",
                "front_gap_top_mm",
                "front_gap_bottom_mm",
                "front_gap_between_vertical_mm",
        ):
            try:
                setattr(m, k, payload[k])
            except Exception:
                pass

        original_to_dict = getattr(m, "to_dict", None)
        patched = False

        try:
            setattr(m, "to_dict", lambda: dict(payload))
            patched = True
        except Exception:
            patched = False

        return original_to_dict, patched

    def _restore_module_after_store(self, m: ModuleDef, original_to_dict, patched: bool) -> None:
        if not patched:
            return

        try:
            setattr(m, "to_dict", original_to_dict)
        except Exception:
            pass

    def _store_save_new(self, name: str, m: ModuleDef) -> None:
        payload = self._build_store_payload(name, m)
        original_to_dict, patched = self._patch_module_for_store(name, m, payload)

        existed_before = self._store_has(name)

        try:
            if self._store_call("save_new", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                return

            if self._store_call("save", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                if existed_before:
                    raise ValueError("Taka nazwa juz istnieje. Uzyj 'Nadpisz'.")
                return

            if self._store_call("upsert", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                if existed_before:
                    raise ValueError("Taka nazwa juz istnieje. Uzyj 'Nadpisz'.")
                return

            raise RuntimeError("ModuleStoreJson: brak metody save_new/save/upsert.")
        finally:
            self._restore_module_after_store(m, original_to_dict, patched)

    def _store_overwrite(self, name: str, m: ModuleDef) -> None:
        payload = self._build_store_payload(name, m)
        original_to_dict, patched = self._patch_module_for_store(name, m, payload)

        try:
            if self._store_call("overwrite", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                return

            if self._store_call("save", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                return

            if self._store_call("upsert", [
                (m,),
                (name, m),
                (payload,),
                (name, payload),
                ({name: payload},),
                ({"name": name, "module": payload},),
            ]):
                self._store_force_front_zone_fields_in_json(name, payload)
                return

            raise RuntimeError("ModuleStoreJson: brak metody overwrite/save/upsert.")
        finally:
            self._restore_module_after_store(m, original_to_dict, patched)
    def _store_delete(self, name: str) -> None:
        if self._store_call("delete", [(name,), ({"name": name},)]):
            return
        if self._store_call("remove", [(name,), ({"name": name},)]):
            return
        raise RuntimeError("ModuleStoreJson: brak metody delete/remove.")

    def _on_dim_save_clicked(self) -> None:
        self._on_any_change()

        name = (self.dim.ed_name.text() or "").strip()
        if not name:
            name = f"MOD_{int(self._draft.width_mm)}x{int(self._draft.depth_mm)}x{int(self._draft.height_mm)}"
            self.dim.ed_name.setText(name)

        try:
            self._store_save_new(name, self._draft)
            self._session_save_now()
            if not self._is_testing():
                QMessageBox.information(self, "Zapisano", f"Zapisano modul: {name}")
            self._refresh_crud_action_state()
        except Exception as e:
            if self._is_testing():
                raise
            QMessageBox.warning(self, "B'ad zapisu", str(e))

    def _on_dim_overwrite_clicked(self) -> None:
        self._on_any_change()

        name = (self.dim.ed_name.text() or "").strip()
        if not name:
            if self._is_testing():
                raise ValueError("Brak nazwy modulu.")
            QMessageBox.information(self, "Nadpisz", "Wpisz nazwe modulu.")
            return

        try:
            self._store_overwrite(name, self._draft)
            self._session_save_now()
            if not self._is_testing():
                QMessageBox.information(self, "Nadpisano", f"Nadpisano modul: {name}")
            self._refresh_crud_action_state()
        except Exception as e:
            if self._is_testing():
                raise
            QMessageBox.warning(self, "B'ad nadpisu", str(e))

    def _on_dim_delete_clicked(self) -> None:
        name = (self.dim.ed_name.text() or "").strip()
        if not name:
            if self._is_testing():
                raise ValueError("Brak nazwy modulu.")
            QMessageBox.information(self, "Usun", "Wpisz nazwe modulu.")
            return

        if not self._is_testing():
            if QMessageBox.question(self, "Usun modul",
                                    f"Usunac modul z bazy...\n\n{name}") != QMessageBox.StandardButton.Yes:
                return

        try:
            self._store_delete(name)
            if not self._is_testing():
                QMessageBox.information(self, "Usunieto", f"Usunieto: {name}")
            self._refresh_crud_action_state()
        except Exception as e:
            if self._is_testing():
                raise
            QMessageBox.warning(self, "B'ad usuwania", str(e))
    # endregion
# endregion
