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
from src.core.costing.module_costs import calculate_module_cost_breakdown
from src.core.module_parts_service import build_module_parts
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
from src.tabs.modul.dialog_load_module import LoadModuleDialog
from src.storage.default_module_store_json import load_default_module, save_default_module, clear_default_module
import os
from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock as ExtractedDrawingSettingsBlock
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
from src.tabs.modul.module_defaults import (
    _is_startup_module_state_valid,
    build_default_module,
    build_factory_default_module,
    normalize_rail_offsets_mm,
)
from src.tabs.modul.project_tree_block import ProjectTreeBlock
from src.tabs.modul.reference_point_block import ReferencePointBlock
from src.tabs.modul.session_view_block import SessionAndViewBlock
from src.tabs.modul.shelves_block import ShelvesBlock
from src.tabs.modul.visible_parts_block import VisiblePartsBlock
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
        lab.setStyleSheet("font-weight:700;")
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
                border: 2px solid #cc0000;
                border-radius: 8px;
                background: #ffffff;
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
class BomBlock(QWidget):
    sig_material_changed = pyqtSignal(str)
    sig_material_reset_requested = pyqtSignal()

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog

        self._is_loading_material_editor = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.title = QLabel("BOM (zaznacz element w drzewie)")
        self.title.setStyleSheet("font-weight:700;")
        lay.addWidget(self.title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.v_name = QLabel("-")
        self.v_mat = QLabel("-")
        self.v_dims = QLabel("-")
        self.v_edge = QLabel("-")
        self.v_offsets = QLabel("-")

        self.form.addRow("Nazwa", self.v_name)
        self.form.addRow("Material", self.v_mat)
        self.form.addRow("Wymiary", self.v_dims)
        self.form.addRow("Oklejanie", self.v_edge)
        self.form.addRow("Offsety wiencow", self.v_offsets)

        self.cb_part_material = QComboBox()

        self.btn_reset_part_material = QPushButton("Reset do grupy")
        self.btn_reset_part_material.setEnabled(False)

        material_row = QWidget(self)
        material_row_lay = QHBoxLayout(material_row)
        material_row_lay.setContentsMargins(0, 0, 0, 0)
        material_row_lay.setSpacing(6)
        material_row_lay.addWidget(self.cb_part_material, 1)
        material_row_lay.addWidget(self.btn_reset_part_material, 0)

        self.form.addRow("Material detalu", material_row)

        lay.addLayout(self.form)

        self.sum_title = QLabel("Podsumowanie materialow (szt / m2 / zl)")
        self.sum_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.sum_title)

        self.v_sum = QLabel("-")
        self.v_sum.setWordWrap(True)
        lay.addWidget(self.v_sum)

        self.eb_title = QLabel("Podsumowanie okleiny (mb)")
        self.eb_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.eb_title)

        self.v_eb = QLabel("-")
        self.v_eb.setWordWrap(True)
        lay.addWidget(self.v_eb)

        self.hw_title = QLabel("Podsumowanie okuc (szt / kpl / zl)")
        self.hw_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.hw_title)

        self.v_hw = QLabel("-")
        self.v_hw.setWordWrap(True)
        lay.addWidget(self.v_hw)

        self.total_title = QLabel("Koszt modulu")
        self.total_title.setStyleSheet("font-weight:700; margin-top:6px;")
        lay.addWidget(self.total_title)

        self.v_total = QLabel("-")
        self.v_total.setWordWrap(True)
        lay.addWidget(self.v_total)

        lay.addStretch(1)

        self._reload_catalog_cache()
        self.cb_part_material.currentIndexChanged.connect(self._emit_material_changed)
        self.btn_reset_part_material.clicked.connect(self.sig_material_reset_requested.emit)
        self.clear_part()

    def _reload_catalog_cache(self) -> None:
        materials = self._catalog.list_materials() or []
        self._mat_name = {m.key: m.name_pl for m in materials}
        self._mat_price = {}
        for material in materials:
            try:
                price = float(getattr(material, "price_pln_per_m2", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._mat_price[material.key] = price

        edgebands = self._catalog.list_edgebands() or []
        self._eb_name = {e.key: e.name_pl for e in edgebands}
        self._eb_price = {}
        for edgeband in edgebands:
            try:
                price = float(getattr(edgeband, "price_pln_per_m", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._eb_price[edgeband.key] = price

        hardware = self._catalog.list_hardware() or []
        self._hw_name = {item.key: item.name_pl for item in hardware}
        self._hw_price = {}
        for item in hardware:
            try:
                price = float(getattr(item, "price_pln", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0.0:
                self._hw_price[item.key] = price

        current_key = str(self.cb_part_material.currentData() or "")
        self._is_loading_material_editor = True
        try:
            self.cb_part_material.clear()
            for material in materials:
                self.cb_part_material.addItem(self._material_combo_label(material), material.key)
            idx = self.cb_part_material.findData(current_key)
            if idx < 0 and self.cb_part_material.count() > 0:
                idx = 0
            if idx >= 0:
                self.cb_part_material.setCurrentIndex(idx)
        finally:
            self._is_loading_material_editor = False

    def reload_catalog(self) -> None:
        self._reload_catalog_cache()

    def _material_combo_label(self, material) -> str:
        label = f"{material.key} ({material.thickness_mm:g} mm) - {material.name_pl}"
        manufacturer = str(getattr(material, "manufacturer", "") or "").strip()
        material_type = str(getattr(material, "material_type", "") or "").strip()
        extras = [value for value in (manufacturer, material_type) if value]
        if extras:
            label += f" [{', '.join(extras)}]"
        price = float(getattr(material, "price_pln_per_m2", 0.0) or 0.0)
        if price > 0.0:
            label += f" - {price:.2f} zl/m2"
        return label

    def _emit_material_changed(self, _index: int) -> None:
        if self._is_loading_material_editor:
            return
        self.sig_material_changed.emit(str(self.cb_part_material.currentData() or ""))

    def _set_material_editor_state(
        self,
        material_key: str,
        default_material_key: str = "",
        enabled: bool = False,
        override_active: bool = False,
    ) -> None:
        self._is_loading_material_editor = True
        try:
            current_key = str(material_key or default_material_key or "").strip()
            idx = self.cb_part_material.findData(current_key)
            if idx < 0 and default_material_key:
                idx = self.cb_part_material.findData(default_material_key)
            if idx < 0 and self.cb_part_material.count() > 0:
                idx = 0
            if idx >= 0:
                self.cb_part_material.setCurrentIndex(idx)

            self.cb_part_material.setEnabled(bool(enabled))
            self.btn_reset_part_material.setEnabled(bool(enabled and override_active))

            tooltip = ""
            if default_material_key:
                tooltip = f"Domyslny z grupy: {default_material_key}"
            self.btn_reset_part_material.setToolTip(tooltip)
        finally:
            self._is_loading_material_editor = False

    def clear_part(self) -> None:
        self.v_name.setText("-")
        self.v_mat.setText("-")
        self.v_dims.setText("-")
        self.v_edge.setText("-")
        self.v_offsets.setText("-")
        self._set_material_editor_state("", enabled=False, override_active=False)

    def _material_label(self, key: str) -> str:
        name = self._mat_name.get(key, "")
        if not name or name == key:
            return key or "-"
        return f"{key} - {name}"

    def set_part(self, part: PartDef, default_material_key: str = "") -> None:
        current_material_key = str(part.material_key or default_material_key or "-")
        override_key = str(getattr(part, "material_override_key", "") or "").strip()

        self.v_name.setText(part.name_pl or "-")
        self.v_mat.setText(self._material_label(current_material_key))
        d = part.dims_mm or {}
        self.v_dims.setText(f'{d.get("w","-")} x {d.get("h","-")} x {d.get("t","-")} mm')

        eb = part.edge_banding or {}
        if not eb:
            self.v_edge.setText("-")
        else:
            chunks = []
            for side, key in eb.items():
                name_pl = self._eb_name.get(key, key)
                chunks.append(f'{EDGE_SIDES_PL.get(side, side)}={name_pl}')
            self.v_edge.setText(", ".join(chunks))

        self._set_material_editor_state(
            material_key=current_material_key,
            default_material_key=default_material_key,
            enabled=True,
            override_active=bool(override_key) or (
                bool(default_material_key) and current_material_key != default_material_key
            ),
        )

    def set_module(self, m: ModuleDef) -> None:
        vp = set(getattr(m, "visible_parts", set()) or set())
        top_offset_mm = float(getattr(m, "top_rail_offset_mm", 0.0) or 0.0)
        bottom_offset_mm = float(getattr(m, "bottom_rail_offset_mm", 0.0) or 0.0)

        top_txt = f"gora {top_offset_mm:.1f} mm" if "top" in vp else "gora: brak"
        bottom_txt = f"dol {bottom_offset_mm:.1f} mm" if "bottom" in vp else "dol: brak"
        self.v_offsets.setText(f"{top_txt}, {bottom_txt}")

        breakdown = calculate_module_cost_breakdown(
            m,
            self._catalog,
            auto_double_front_width_mm=float(load_drawing_settings().auto_double_front_width_mm or 600.0),
        )

        if not breakdown.material_lines:
            self.v_sum.setText("-")
        else:
            lines = []
            for line in breakdown.material_lines:
                if line.priced:
                    lines.append(f"{line.label}: {line.count} szt, {line.area_m2:.3f} m2, {line.cost_pln:.2f} zl")
                else:
                    lines.append(f"{line.label}: {line.count} szt, {line.area_m2:.3f} m2")
            if any(line.priced for line in breakdown.material_lines):
                lines.append(f"RAZEM: {breakdown.material_total_pln:.2f} zl")
            self.v_sum.setText("\n".join(lines))

        if not breakdown.edgeband_lines:
            self.v_eb.setText("-")
        else:
            lines = []
            for line in breakdown.edgeband_lines:
                if line.priced:
                    lines.append(f"{line.label}: {line.length_m:.2f} mb, {line.cost_pln:.2f} zl")
                else:
                    lines.append(f"{line.label}: {line.length_m:.2f} mb")
            if any(line.priced for line in breakdown.edgeband_lines):
                lines.append(f"RAZEM: {breakdown.edgeband_total_pln:.2f} zl")
            self.v_eb.setText("\n".join(lines))

        if not breakdown.hardware_lines:
            self.v_hw.setText("-")
        else:
            lines = []
            for line in breakdown.hardware_lines:
                qty = float(line.quantity or 0.0)
                qty_txt = str(int(qty)) if abs(qty - round(qty)) < 0.001 else f"{qty:.2f}"
                label = line.label
                if line.manufacturer:
                    label += f" [{line.manufacturer}]"
                note = f", {line.note}" if line.note else ""
                if line.priced:
                    lines.append(f"{label}: {qty_txt} {line.unit}, {line.cost_pln:.2f} zl{note}")
                else:
                    lines.append(f"{label}: {qty_txt} {line.unit}{note}")

            if breakdown.hardware_lines:
                lines.append(f"RAZEM: {breakdown.hardware_total_pln:.2f} zl")
            self.v_hw.setText("\n".join(lines) if lines else "-")

        total_lines = [
            f"Materialy: {breakdown.material_total_pln:.2f} zl",
            f"Okleina: {breakdown.edgeband_total_pln:.2f} zl",
            f"Okucia: {breakdown.hardware_total_pln:.2f} zl",
            f"RAZEM: {breakdown.grand_total_pln:.2f} zl",
        ]
        self.v_total.setText("\n".join(total_lines))
# endregion


# ==========================================================
# region CENTER: Zoomable view
# ==========================================================
class ZoomGraphicsView(QGraphicsView):
    def wheelEvent(self, e):
        # zoom ko'kiem (zamiast przewijania)
        factor = 1.15
        if e.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        e.accept()
# endregion


# ==========================================================
# region CENTER: ViewsCanvas (klik formatki + front/plecy w rzucie z gory)
# ==========================================================
class ViewsCanvas(QWidget):
    sig_clicked_part = pyqtSignal(str)
    sig_front_zone_handle_clicked = pyqtSignal(str)
    sig_front_zone_handle_dragged = pyqtSignal(str, float)
    sig_rail_offset_handle_clicked = pyqtSignal(str)
    sig_rail_offset_handle_dragged = pyqtSignal(str, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.view = ZoomGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor("#ffffff"))
        self.view.setScene(self.scene)

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

    def _fit_scene_to_view(self) -> None:
        scene_rect = self.scene.sceneRect()
        if scene_rect.isNull() or scene_rect.isEmpty():
            return
        self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_scene_to_view()

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
        gap = max(140.0, H * 0.18)
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

                self.setPen(pen)
                self.setBrush(brush)
                self.setZValue(float(z))
                self.setToolTip(self.key)

                self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

                if self._canvas._is_preview_handle_key(self.key):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                    self.setAcceptHoverEvents(True)
                    self._apply_handle_style(active=self._active_handle, hot=False)

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

        # segmenty: jesli brak pionow -> 1 segment = ca'e swiat'o
        seg_w = inner_w
        if div_n > 0:
            clear = max(0.0, inner_w - div_n * t)
            seg_w = clear / (div_n + 1)

        # piony (klikane)
        for i in range(1, div_n + 1):
            key = div_keys[i - 1] if (i - 1) < len(div_keys) else f"divider_{i}"
            x = inner_x + seg_w * i + t * (i - 1)
            add_part_rect(key=key, rect=QRectF(x, inner_y, t, inner_h), dashed=False, z=6)

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
            seg_x = inner_x + seg_w * seg_idx + t * seg_idx
            seg_x = max(inner_x, min(inner_x + max(0.0, inner_w - seg_w), seg_x))

            for idx in range(1, shelf_n + 1):
                fallback_key = f"shelf_{idx}"
                if draw_both_sides:
                    fallback_key = f"shelf_{seg_side}_{idx}"
                key = shelf_by_slot.get((seg_side, idx), fallback_key)
                y_center = inner_y + (idx / (shelf_n + 1)) * inner_h
                y_top = max(inner_y, min(inner_y + inner_h - t, y_center - t / 2))
                add_part_rect(key=key, rect=QRectF(seg_x, y_top, seg_w, t), dashed=False, z=6)

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
        self.scene.setSceneRect(scene_bounds.adjusted(-40, -40, 40, 40))
        if fit:
            self._fit_scene_to_view()
# endregion


# ==========================================================
# region TAB: TabModul (CALY UKLAD - bez dubli)
# ==========================================================
class TabModul(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._store = ModuleStoreJson()
        self._catalog = CatalogStoreJson()

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

        self.zone_left = ZoneFrame("left", "STREFA LEWA", self, scrollable=True)
        self.zone_center = ZoneFrame("center", "STREFA SRODKOWA", self, scrollable=False)
        self.zone_right = ZoneFrame("right", "STREFA PRAWA", self, scrollable=True)

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
        self.blk_dims = CollapsibleBlock("Wymiary (L/W/H) + baza modulow")
        self.blk_dims.setObjectName("blk_dims")
        self.dim = DimensionsBlock()
        self.blk_dims.content_layout().addWidget(self.dim)
        self.zone_left.body_lay.addWidget(self.blk_dims)

        self.blk_mat = CollapsibleBlock("Materialy modulu")
        self.blk_mat.setObjectName("blk_mat")
        self.mat = MaterialsBlock(self._catalog)
        self.blk_mat.content_layout().addWidget(self.mat)
        self.zone_left.body_lay.addWidget(self.blk_mat)

        self.blk_fhw = CollapsibleBlock("Fronty i okucia")
        self.blk_fhw.setObjectName("blk_fhw")
        self.fhw = FrontHardwareBlock(self._catalog)
        self.blk_fhw.content_layout().addWidget(self.fhw)
        self.zone_left.body_lay.addWidget(self.blk_fhw)

        self.blk_joint = CollapsibleBlock("Laczenia korpusu")
        self.blk_joint.setObjectName("blk_joint")
        self.joint = CarcassJointsBlock()
        self.blk_joint.content_layout().addWidget(self.joint)
        self.zone_left.body_lay.addWidget(self.blk_joint)

        self.blk_shelves = CollapsibleBlock("Polki")
        self.blk_shelves.setObjectName("blk_shelves")
        self.shelves = ShelvesBlock()
        self.blk_shelves.content_layout().addWidget(self.shelves)
        self.zone_left.body_lay.addWidget(self.blk_shelves)

        self.blk_div = CollapsibleBlock("Piony")
        self.blk_div.setObjectName("blk_div")
        self.dividers = DividersBlock()
        self.blk_div.content_layout().addWidget(self.dividers)
        self.zone_left.body_lay.addWidget(self.blk_div)

        self.blk_ref = CollapsibleBlock("Punkt odniesienia")
        self.blk_ref.setObjectName("blk_ref")
        self.ref = ReferencePointBlock()
        self.blk_ref.content_layout().addWidget(self.ref)
        self.zone_left.body_lay.addWidget(self.blk_ref)

        self.blk_tree = CollapsibleBlock("Drzewo projektu")
        self.blk_tree.setObjectName("blk_tree")
        self.blk_tree.setMaximumHeight(240)
        self.tree = ProjectTreeBlock()
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
        self.quick_bar.setStyleSheet(
            "QFrame#modul_quick_bar {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )
        quick_lay = QHBoxLayout(self.quick_bar)
        quick_lay.setContentsMargins(8, 6, 8, 6)
        quick_lay.setSpacing(6)

        self.btn_q_save = QPushButton("Zapisz")
        self.btn_q_save.clicked.connect(self._shortcut_save_module)
        quick_lay.addWidget(self.btn_q_save)

        self.btn_q_overwrite = QPushButton("Nadpisz")
        self.btn_q_overwrite.clicked.connect(self._on_overwrite)
        quick_lay.addWidget(self.btn_q_overwrite)

        self.btn_q_load = QPushButton("Wczytaj")
        self.btn_q_load.clicked.connect(self._on_load)
        quick_lay.addWidget(self.btn_q_load)

        self.btn_q_new = QPushButton("Nowy")
        self.btn_q_new.clicked.connect(self.start_new_module)
        quick_lay.addWidget(self.btn_q_new)

        self.btn_q_focus_name = QPushButton("Nazwa")
        self.btn_q_focus_name.clicked.connect(self._shortcut_focus_module_name)
        quick_lay.addWidget(self.btn_q_focus_name)

        self.btn_q_doors = QPushButton("Drzwi")
        self.btn_q_doors.clicked.connect(lambda: self._set_facade_mode_quick("doors"))
        quick_lay.addWidget(self.btn_q_doors)

        self.btn_q_drawers = QPushButton("Szuflady")
        self.btn_q_drawers.clicked.connect(lambda: self._set_facade_mode_quick("drawers"))
        quick_lay.addWidget(self.btn_q_drawers)

        self.btn_q_shortcuts = QPushButton("Skroty")
        self.btn_q_shortcuts.clicked.connect(self._open_shortcuts_dialog)
        quick_lay.addWidget(self.btn_q_shortcuts)

        quick_lay.addStretch(1)
        self.zone_center.body_lay.addWidget(self.quick_bar, 0)

        self.canvas = ViewsCanvas()
        self.canvas.set_preview_mode(True)
        self.zone_center.body_lay.addWidget(self.canvas, 1)

        # ---------- RIGHT ----------
        blk_edge = CollapsibleBlock("Oklejanie formatki (klikaj na miniaturze)")
        self.edge = EdgeBandingBlock(self._catalog)
        blk_edge.content_layout().addWidget(self.edge)
        self.zone_right.body_lay.addWidget(blk_edge, 1)

        blk_bom = CollapsibleBlock("BOM")
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
            "load": ("Ctrl+L", self._on_load),
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
        """
        self._set_collapsible_block_body_visible(getattr(self, "blk_dims", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_mat", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_fhw", None), True)
        self._set_collapsible_block_body_visible(getattr(self, "blk_joint", None), True)

        self._set_collapsible_block_body_visible(getattr(self, "blk_shelves", None), False)
        self._set_collapsible_block_body_visible(getattr(self, "blk_div", None), False)

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
        self.canvas.sig_clicked_part.connect(self._on_canvas_part_clicked)

        if hasattr(self.canvas, "sig_front_zone_handle_clicked"):
            self.canvas.sig_front_zone_handle_clicked.connect(self._on_front_zone_handle_clicked)

        if hasattr(self.canvas, "sig_front_zone_handle_dragged"):
            self.canvas.sig_front_zone_handle_dragged.connect(self._on_front_zone_handle_dragged)

        if hasattr(self.canvas, "sig_rail_offset_handle_clicked"):
            self.canvas.sig_rail_offset_handle_clicked.connect(self._on_rail_offset_handle_clicked)

        if hasattr(self.canvas, "sig_rail_offset_handle_dragged"):
            self.canvas.sig_rail_offset_handle_dragged.connect(self._on_rail_offset_handle_dragged)

        # CRUD bazy modu'ow
        self.dim.sig_save.connect(self._on_dim_save_clicked)
        self.dim.sig_overwrite.connect(self._on_dim_overwrite_clicked)
        self.dim.sig_load.connect(self._on_load_from_base_preview)
        self.dim.sig_delete.connect(self._on_dim_delete_clicked)

        # zmiany wymiarow -> render
        self.dim.ed_name.textChanged.connect(self._on_any_change)
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
    # region HANDLERS: Zapisz / Nadpisz (baza modu'ow)
    # ---------------------------
    def _ensure_name_for_save(self) -> str:
        name = self.dim.ed_name.text().strip()
        if not name:
            # automatyczna nazwa jesli pusto
            w = int(self.dim.sp_w.value())
            d = int(self.dim.sp_d.value())
            h = int(self.dim.sp_h.value())
            name = f"MOD_{w}x{d}x{h}"
            self.dim.ed_name.setText(name)
        return name

    def _store_try(self, fn_name: str, *args) -> bool:
        if not hasattr(self._store, fn_name):
            return False
        fn = getattr(self._store, fn_name)

        # probujemy kilka wariantow sygnatur
        variants = []
        if len(args) == 2:
            name, m = args
            md = m.to_dict() if hasattr(m, "to_dict") else m
            variants = [
                (name, m),
                (name, md),
                (m,),
                (md,),
            ]
        else:
            variants = [args]

        last_exc = None
        for a in variants:
            try:
                fn(*a)
                return True
            except TypeError as e:
                last_exc = e
                continue
            except Exception as e:
                last_exc = e
                break

        if last_exc:
            raise last_exc
        return False

    def _on_dim_save_clicked(self) -> None:
        # 1) zaciagnij UI -> draft
        if hasattr(self, "_pull_ui_to_draft"):
            self._pull_ui_to_draft()

        # 2) upewnij sie, ze jest nazwa
        name = self._ensure_name_for_save()
        try:
            # jesli ModuleDef ma pole name - ustaw je spojnie
            if getattr(self._draft, "name", "") != name:
                self._draft.name = name
        except Exception:
            pass

        # 3) zapis do bazy (rozne mozliwe nazwy metod w store)
        ok = (
                self._store_try("save_new", name, self._draft)
                or self._store_try("save", name, self._draft)
                or self._store_try("create", name, self._draft)
                or self._store_try("insert", name, self._draft)
                or self._store_try("upsert", name, self._draft)
        )

        if not ok:
            # jesli store ma inna nazwe - pokazemy b'ad zamiast ciszy
            raise RuntimeError("Nie znaleziono metody zapisu w ModuleStoreJson (save_new/save/create/insert/upsert).")

        # 4) NAJWAZNIEJSZE: po zapisie od razu zapisz sesje (restart bedzie dzialal)
        if hasattr(self, "_session_save_now"):
            self._session_save_now()

    def _on_dim_overwrite_clicked(self) -> None:
        # 1) zaciagnij UI -> draft
        if hasattr(self, "_pull_ui_to_draft"):
            self._pull_ui_to_draft()

        name = self._ensure_name_for_save()
        try:
            if getattr(self._draft, "name", "") != name:
                self._draft.name = name
        except Exception:
            pass

        ok = (
                self._store_try("overwrite", name, self._draft)
                or self._store_try("update", name, self._draft)
                or self._store_try("replace", name, self._draft)
                or self._store_try("save_overwrite", name, self._draft)
                or self._store_try("save", name, self._draft)  # czasem save = overwrite
                or self._store_try("upsert", name, self._draft)
        )

        if not ok:
            raise RuntimeError(
                "Nie znaleziono metody nadpisu w ModuleStoreJson (overwrite/update/replace/save/upsert).")

        if hasattr(self, "_session_save_now"):
            self._session_save_now()

    # endregion


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
    def _session_save_request(self) -> None:
        if not getattr(self, "_session_ready", False):
            return
        # lekki debounce, zeby nie zapisywac pliku 1000 razy przy kreceniu spinboxem
        self._session_timer.start(250)

    def _session_save_now(self) -> None:
        if not getattr(self, "_session_ready", False):
            return
        try:
            ui = {
                "selected_part_key": self._selected_part_key,
            }
            save_last_session(self._draft, ui)
        except Exception:
            pass

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
        # region HANDLERS: baza modu'ow + zapis sesji
        # ==========================================================
        def _apply_module_and_refresh(self, m: ModuleDef) -> None:
            """Jedyny poprawny sposob: podmien draft -> rebuild -> push -> render -> zapisz sesje."""
            self._draft = m

            # zawsze przebuduj czesci wg aktualnej logiki
            if hasattr(self, "rebuild_parts"):
                self.rebuild_parts()
            else:
                self._rebuild_parts()

            self._push_draft_to_ui()

            # wybierz sensowny element
            if getattr(self._draft, "parts", None):
                if self._selected_part_key not in self._draft.parts:
                    self._selected_part_key = next(iter(self._draft.parts.keys()))
                self.tree.select_part(self._selected_part_key)

            self._render_right()
            self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)

            # -> TU jest klucz: restart bedzie OK, bo zapisujemy sesje NATYCHMIAST
            self._session_save_now()

        def _on_dim_save_clicked(self) -> None:
            """Klik 'Zapisz' -> po udanym zapisie do bazy, zapisz tez sesje."""
            # tu masz swoja istniejaca logike zapisu - jesli masz metode _on_save_to_base to ja wo'aj
            if hasattr(self, "_on_save_to_base"):
                self._on_save_to_base()
            elif hasattr(self, "_on_save_new"):
                self._on_save_new()
            else:
                # jesli nie masz jeszcze osobnej metody - nic nie robimy
                return

            # -> po zapisie: sesja
            self._session_save_now()

        def _on_dim_overwrite_clicked(self) -> None:
            """Klik 'Nadpisz' -> po udanym nadpisaniu, zapisz sesje."""
            if hasattr(self, "_on_overwrite_to_base"):
                self._on_overwrite_to_base()
            elif hasattr(self, "_on_overwrite"):
                self._on_overwrite()
            else:
                return

            # -> po nadpisaniu: sesja
            self._session_save_now()

        # endregion

        self._session_save_now()

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
    def _on_save_new(self) -> None:
        self._pull_ui_to_draft()
        if not self._draft.name:
            QMessageBox.warning(self, "Brak nazwy", "Podaj nazwe modulu przed zapisem.")
            return

        res = self._store.save_new(self._draft)
        QMessageBox.information(self, "Zapis", res.message_pl)

    def _on_overwrite(self) -> None:
        self._pull_ui_to_draft()
        if not self._draft.name:
            QMessageBox.warning(self, "Brak nazwy", "Podaj nazwe modulu przed nadpisaniem.")
            return

        res = self._store.overwrite(self._draft)
        QMessageBox.information(self, "Nadpisz", res.message_pl)

    def _on_load(self) -> None:
        name = self.dim.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Brak nazwy", "Wpisz nazwe modulu do wczytania.")
            return

        m = self._store.get(name)
        if m is None:
            QMessageBox.warning(self, "Brak w bazie", f'Nie znaleziono modulu "{name}".')
            return

        ans = QMessageBox.question(self, "Wczytac...", f'Wczytac modul "{name}"...')
        if ans != QMessageBox.StandardButton.Yes:
            return

        self._draft = m
        self._rebuild_parts()
        self._push_draft_to_ui()

        if self._draft.parts:
            if self._selected_part_key not in self._draft.parts:
                self._selected_part_key = next(iter(self._draft.parts.keys()))
            self.tree.select_part(self._selected_part_key)

        self._render_right()
        self.canvas.render_module(self._draft, fit=True, selected_part_key=self._selected_part_key)

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
        dlg = LoadModuleDialog(self, self._store)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        res = dlg.result_value()
        if res is None:
            return

        self._apply_loaded_module(res.module)

    def load_module_from_store_name(self, name: str) -> bool:
        module_name = str(name or "").strip()
        if not module_name:
            return False

        module = self._store.get(module_name) if hasattr(self._store, "get") else None
        if module is None:
            return False

        self._apply_loaded_module(module)
        return True

    def start_new_module(self) -> None:
        self._apply_loaded_module(build_default_module())

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
        if names:
            return name in names

        # fallback: probuj load/get
        for fn in ("load", "load_module", "get", "read"):
            if hasattr(self._store, fn):
                try:
                    getattr(self._store, fn)(name)
                    return True
                except Exception:
                    return False
        return False

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
        except Exception as e:
            if self._is_testing():
                raise
            QMessageBox.warning(self, "B'ad usuwania", str(e))
    # endregion
# endregion
