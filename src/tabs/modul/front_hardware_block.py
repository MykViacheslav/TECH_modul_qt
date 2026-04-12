from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.domain.module_models import ModuleDef
from src.storage.catalog_store_json import CatalogStoreJson
from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog


class FrontHardwareBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, catalog: CatalogStoreJson | QWidget | None = None, parent: QWidget | None = None) -> None:
        if isinstance(catalog, QWidget) and parent is None:
            parent = catalog
            catalog = None
        super().__init__(parent)
        self._catalog = catalog if isinstance(catalog, CatalogStoreJson) else CatalogStoreJson()

        lay = QFormLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        lay.setVerticalSpacing(8)
        lay.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self.cb_front_layout = QComboBox()
        self.cb_front_layout.addItem("Nakladany", "overlay")
        self.cb_front_layout.addItem("Wewnetrzny", "inset")

        self.cb_front_height_mode = QComboBox()
        self.cb_front_height_mode.addItem("Pelna wysokosc modulu", "full")
        self.cb_front_height_mode.addItem("Do wienca", "to_top_rail")
        self.cb_front_height_mode.addItem("Strefa z offsetami", "offsets")

        self.cb_top_ref_mode = QComboBox()
        self.cb_top_ref_mode.addItem("Do konca wienca", "rail_end")
        self.cb_top_ref_mode.addItem("Do 1/2 wienca", "rail_center")
        self.cb_top_ref_mode.addItem("Do poczatku wienca", "rail_start")
        self.cb_top_ref_mode.addItem("Offset reczny", "custom")

        self.cb_bottom_ref_mode = QComboBox()
        self.cb_bottom_ref_mode.addItem("Do konca wienca", "rail_end")
        self.cb_bottom_ref_mode.addItem("Do 1/2 wienca", "rail_center")
        self.cb_bottom_ref_mode.addItem("Do poczatku wienca", "rail_start")
        self.cb_bottom_ref_mode.addItem("Offset reczny", "custom")

        self.sp_front_offset_top = QDoubleSpinBox()
        self.sp_front_offset_top.setRange(0.0, 5000.0)
        self.sp_front_offset_top.setDecimals(1)
        self.sp_front_offset_top.setSuffix(" mm")
        self.sp_front_offset_top.setValue(0.0)

        self.sp_front_offset_bottom = QDoubleSpinBox()
        self.sp_front_offset_bottom.setRange(0.0, 5000.0)
        self.sp_front_offset_bottom.setDecimals(1)
        self.sp_front_offset_bottom.setSuffix(" mm")
        self.sp_front_offset_bottom.setValue(0.0)

        def _gap_spin(default_mm: float = 0.0) -> QDoubleSpinBox:
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 20.0)
            sp.setDecimals(1)
            sp.setSuffix(" mm")
            sp.setValue(default_mm)
            return sp

        self.sp_gap_left = _gap_spin(0.0)
        self.sp_gap_right = _gap_spin(0.0)
        self.sp_gap_top = _gap_spin(0.0)
        self.sp_gap_bottom = _gap_spin(0.0)
        self.sp_gap_between_vertical = _gap_spin(0.0)

        self.box_front_gaps = QFrame()
        self.box_front_gaps.setObjectName("front_gaps_box")
        self.box_front_gaps.setFrameShape(QFrame.Shape.StyledPanel)
        self.box_front_gaps.setStyleSheet(
            "QFrame#front_gaps_box {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )

        gaps_lay = QVBoxLayout(self.box_front_gaps)
        gaps_lay.setContentsMargins(10, 8, 10, 8)
        gaps_lay.setSpacing(6)

        self.lab_front_gaps_title = QLabel("Luzy frontowe")
        self.lab_front_gaps_title.setStyleSheet("font-weight: 700;")
        gaps_lay.addWidget(self.lab_front_gaps_title)

        form_gaps = QFormLayout()
        form_gaps.setContentsMargins(0, 0, 0, 0)
        form_gaps.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_gaps.addRow("Luz lewy", self.sp_gap_left)
        form_gaps.addRow("Luz prawy", self.sp_gap_right)
        form_gaps.addRow("Luz gorny", self.sp_gap_top)
        form_gaps.addRow("Luz dolny", self.sp_gap_bottom)
        form_gaps.addRow("Luz miedzy frontami", self.sp_gap_between_vertical)

        gaps_lay.addLayout(form_gaps)

        lay.addRow("Luzy", self.box_front_gaps)

        self.zone_box = QFrame()
        self.zone_box.setObjectName("front_zone_box")
        self.zone_box.setFrameShape(QFrame.Shape.StyledPanel)
        self.zone_box.setStyleSheet(
            "QFrame#front_zone_box {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )

        zone_lay = QVBoxLayout(self.zone_box)
        zone_lay.setContentsMargins(10, 8, 10, 8)
        zone_lay.setSpacing(6)

        self.lab_zone_title = QLabel("Strefa frontu")
        self.lab_zone_title.setStyleSheet("font-weight: 700;")

        self.lab_zone_note = QLabel(
            "To okresla robocza wysokosc frontu w preview i w obliczeniach front zone."
        )
        self.lab_zone_note.setWordWrap(True)
        self.lab_zone_note.setStyleSheet("color:#666;")

        self.lab_zone_summary = QLabel("")
        self.lab_zone_summary.setWordWrap(True)
        self.lab_zone_summary.setStyleSheet("color:#333;")

        self.lab_zone_context = QLabel("")
        self.lab_zone_context.setWordWrap(True)
        self.lab_zone_context.setStyleSheet(
            "color:#0f4c81; font-weight:600; background:#eef6ff; "
            "border:1px solid #d6e8fb; border-radius:4px; padding:6px;"
        )

        self.btn_reset_front_zone = QPushButton("Resetuj strefe frontu")
        self.btn_reset_front_zone.clicked.connect(self._on_reset_front_zone_clicked)

        zone_lay.addWidget(self.lab_zone_title)
        zone_lay.addWidget(self.lab_zone_note)
        zone_lay.addWidget(self.lab_zone_summary)
        zone_lay.addWidget(self.lab_zone_context)
        zone_lay.addWidget(self.btn_reset_front_zone, 0, Qt.AlignmentFlag.AlignLeft)

        self.cb_facade_mode = QComboBox()
        self.cb_facade_mode.addItem("Drzwi", "doors")
        self.cb_facade_mode.addItem("Szuflady", "drawers")
        self.cb_facade_mode.addItem("Mieszany", "mixed")

        self.sp_drawer_count = QSpinBox()
        self.sp_drawer_count.setRange(1, 8)
        self.sp_drawer_count.setValue(3)

        self.cb_drawer_layout_mode = QComboBox()
        self.cb_drawer_layout_mode.addItem("Rowny podzial", "equal")
        self.cb_drawer_layout_mode.addItem("Mala u gory", "small_top")
        self.cb_drawer_layout_mode.addItem("Mala na dole", "small_bottom")

        self.sp_drawer_small_front_h = QDoubleSpinBox()
        self.sp_drawer_small_front_h.setRange(60.0, 1000.0)
        self.sp_drawer_small_front_h.setDecimals(1)
        self.sp_drawer_small_front_h.setSuffix(" mm")
        self.sp_drawer_small_front_h.setValue(140.0)

        self.cb_hinge_vendor = QComboBox()
        self.cb_drawer_vendor = QComboBox()
        self.reload_catalog(preserve_current=False)

        self.chk_tipon = QCheckBox("TIP-ON / push-to-open")

        self.sp_rear = QDoubleSpinBox()
        self.sp_rear.setRange(0.0, 100.0)
        self.sp_rear.setDecimals(1)
        self.sp_rear.setSuffix(" mm")
        self.sp_rear.setValue(10.0)

        self.sp_tip = QDoubleSpinBox()
        self.sp_tip.setRange(0.0, 100.0)
        self.sp_tip.setDecimals(1)
        self.sp_tip.setSuffix(" mm")
        self.sp_tip.setValue(20.0)

        self.summary_box = QFrame()
        self.summary_box.setObjectName("front_summary_box")
        self.summary_box.setFrameShape(QFrame.Shape.StyledPanel)
        self.summary_box.setStyleSheet(
            "QFrame#front_summary_box {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )

        summary_lay = QVBoxLayout(self.summary_box)
        summary_lay.setContentsMargins(10, 8, 10, 8)
        summary_lay.setSpacing(6)

        self.lab_front_summary_title = QLabel("Podsumowanie frontu")
        self.lab_front_summary_title.setStyleSheet("font-weight: 700;")

        self.lab_front_summary = QLabel("")
        self.lab_front_summary.setWordWrap(True)
        self.lab_front_summary.setStyleSheet("color:#333;")

        summary_lay.addWidget(self.lab_front_summary_title)
        summary_lay.addWidget(self.lab_front_summary)

        self.preview_box = QFrame()
        self.preview_box.setObjectName("front_preview_box")
        self.preview_box.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_box.setStyleSheet(
            "QFrame#front_preview_box {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )

        preview_lay = QVBoxLayout(self.preview_box)
        preview_lay.setContentsMargins(10, 8, 10, 8)
        preview_lay.setSpacing(6)

        self.lab_preview_title = QLabel("Podglad roboczy frontu")
        self.lab_preview_title.setStyleSheet("font-weight: 700;")

        self.lab_preview_note = QLabel(
            "Dziala tylko w tej zakladce i tylko w tym podgladzie. "
            "Nie zapisuje sie do modulu ani do ustawien rysunku."
        )
        self.lab_preview_note.setWordWrap(True)
        self.lab_preview_note.setStyleSheet("color:#666;")

        self.chk_temp_hide_front = QCheckBox("Ukryj front tylko w tym podgladzie")
        self.chk_temp_hide_front.setChecked(False)
        self.chk_temp_hide_front.setToolTip(
            "To dziala tylko roboczo w zakladce \"Modul\".\n"
            "Nie zapisuje sie do ustawien rysunku."
        )

        self.lab_temp_front_preview_state = QLabel("")
        self.lab_temp_front_preview_state.setWordWrap(True)
        self.lab_temp_front_preview_state.setStyleSheet("color:#444;")

        self.btn_temp_show_front_again = QPushButton("Pokaz front z powrotem")
        self.btn_temp_show_front_again.clicked.connect(
            lambda: self.chk_temp_hide_front.setChecked(False)
        )

        preview_lay.addWidget(self.lab_preview_title)
        preview_lay.addWidget(self.lab_preview_note)
        preview_lay.addWidget(self.chk_temp_hide_front)
        preview_lay.addWidget(self.lab_temp_front_preview_state)
        preview_lay.addWidget(self.btn_temp_show_front_again, 0, Qt.AlignmentFlag.AlignLeft)

        self.lab_hint = QLabel("")
        self.lab_hint.setWordWrap(True)
        self.lab_hint.setStyleSheet("color:#666;")

        lay.addRow("Typ frontu", self.cb_front_layout)
        lay.addRow("Wysokosc frontu", self.cb_front_height_mode)
        lay.addRow("Gora wzgledem wienca", self.cb_top_ref_mode)
        lay.addRow("Dol wzgledem wienca", self.cb_bottom_ref_mode)
        lay.addRow("Offset od gory", self.sp_front_offset_top)
        lay.addRow("Offset od dolu", self.sp_front_offset_bottom)
        lay.addRow("Strefa", self.zone_box)

        self.box_front_mode = QFrame()
        self.box_front_mode.setObjectName("front_mode_box")
        self.box_front_mode.setFrameShape(QFrame.Shape.StyledPanel)
        self.box_front_mode.setStyleSheet(
            "QFrame#front_mode_box {"
            "border: 1px solid #d8d8d8;"
            "border-radius: 6px;"
            "background: #fafafa;"
            "}"
        )

        mode_lay = QVBoxLayout(self.box_front_mode)
        mode_lay.setContentsMargins(10, 8, 10, 8)
        mode_lay.setSpacing(6)

        self.lab_front_mode_title = QLabel("Uklad i okucia frontu")
        self.lab_front_mode_title.setStyleSheet("font-weight: 700;")
        mode_lay.addWidget(self.lab_front_mode_title)

        form_mode = QFormLayout()
        form_mode.setContentsMargins(0, 0, 0, 0)
        form_mode.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_mode.addRow("Uklad frontow", self.cb_facade_mode)
        form_mode.addRow("Liczba szuflad", self.sp_drawer_count)
        form_mode.addRow("Uklad szuflad", self.cb_drawer_layout_mode)
        form_mode.addRow("Niski front szuflady", self.sp_drawer_small_front_h)
        form_mode.addRow("Producent zawiasow", self.cb_hinge_vendor)
        form_mode.addRow("Producent szuflad", self.cb_drawer_vendor)
        form_mode.addRow("", self.chk_tipon)
        form_mode.addRow("Luz za szuflada", self.sp_rear)
        form_mode.addRow("Luz TIP-ON", self.sp_tip)
        mode_lay.addLayout(form_mode)

        lay.addRow("Tryb i okucia", self.box_front_mode)
        lay.addRow("Front", self.summary_box)
        lay.addRow("Podglad", self.preview_box)
        lay.addRow("Podpowiedz", self.lab_hint)

        self._sticky_zone_context = ""

        self.cb_front_layout.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.cb_front_height_mode.currentIndexChanged.connect(self._on_front_height_mode_changed)
        self.cb_top_ref_mode.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.cb_bottom_ref_mode.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)

        self.sp_front_offset_top.valueChanged.connect(self._on_front_zone_value_changed)
        self.sp_front_offset_bottom.valueChanged.connect(self._on_front_zone_value_changed)

        self.sp_gap_left.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_gap_right.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_gap_top.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_gap_bottom.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_gap_between_vertical.valueChanged.connect(self._emit_changed_with_front_overview_refresh)

        self.cb_facade_mode.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_drawer_count.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.cb_drawer_layout_mode.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_drawer_small_front_h.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.cb_hinge_vendor.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.cb_drawer_vendor.currentIndexChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.chk_tipon.toggled.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_rear.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.sp_tip.valueChanged.connect(self._emit_changed_with_front_overview_refresh)
        self.chk_temp_hide_front.toggled.connect(self._on_temp_hide_front_toggled)

        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        self._refresh_temp_front_preview_ui()

    def _set_form_row_visible(self, field: QWidget, visible: bool) -> None:
        label = None
        try:
            label = self._form.labelForField(field)
        except Exception:
            label = None

        if label is not None:
            label.setVisible(visible)
            label.setHidden(not visible)

        field.setVisible(visible)
        field.setHidden(not visible)

    def _is_form_row_visible(self, field: QWidget) -> bool:
        label = None
        try:
            label = self._form.labelForField(field)
        except Exception:
            label = None

        if label is not None and label.isHidden():
            return False
        return not field.isHidden()

    @staticmethod
    def _vendor_label(vendor_key: str) -> str:
        key = str(vendor_key or "").strip()
        if not key:
            return "-"
        if key.lower() == "generic":
            return "Ogolne"
        return key[:1].upper() + key[1:]

    def _fill_vendor_combo(
        self,
        combo: QComboBox,
        category: str,
        current_key: str = "",
    ) -> None:
        vendors = list(self._catalog.list_hardware_manufacturers(category=category) or [])
        if not vendors:
            vendors = ["generic", "blum", "hettich"]

        normalized = []
        seen = set()
        for vendor in vendors:
            raw = str(vendor or "").strip()
            if not raw:
                continue
            key = raw.lower()
            if key in seen:
                continue
            normalized.append((raw, key))
            seen.add(key)

        if "generic" not in seen:
            normalized.insert(0, ("generic", "generic"))

        combo.blockSignals(True)
        combo.clear()
        for raw, key in normalized:
            combo.addItem(self._vendor_label(raw), key)

        idx = combo.findData(str(current_key or "").strip().lower())
        if idx < 0:
            idx = combo.findData("generic")
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def reload_catalog(self, preserve_current: bool = True) -> None:
        current_hinge = str(self.cb_hinge_vendor.currentData() or "generic") if preserve_current else "generic"
        current_drawer = str(self.cb_drawer_vendor.currentData() or "generic") if preserve_current else "generic"

        self._fill_vendor_combo(self.cb_hinge_vendor, "hinge", current_key=current_hinge)
        self._fill_vendor_combo(self.cb_drawer_vendor, "drawer_system", current_key=current_drawer)
        if hasattr(self, "lab_front_summary"):
            self._refresh_front_overview_ui()

    def _front_zone_min_face_height_mm(self) -> float:
        return 2.0

    def normalize_front_zone(
        self,
        module_height_mm: float,
        top_rail_thickness_mm: float = 18.0,
    ) -> bool:
        changed = False
        H = max(0.0, float(module_height_mm))
        top_rail = max(0.0, float(top_rail_thickness_mm))
        min_face_h = self._front_zone_min_face_height_mm()

        mode = str(self.cb_front_height_mode.currentData() or "full").strip().lower()

        top_val = max(0.0, float(self.sp_front_offset_top.value()))
        bottom_val = max(0.0, float(self.sp_front_offset_bottom.value()))

        if mode == "full":
            new_top = max(0.0, top_val)
            new_bottom = max(0.0, bottom_val)

        elif mode == "to_top_rail":
            max_bottom = max(0.0, H - top_rail - min_face_h)
            new_top = max(0.0, top_val)
            new_bottom = max(0.0, min(bottom_val, max_bottom))

        else:
            max_top = max(0.0, H - min_face_h)
            new_top = max(0.0, min(top_val, max_top))

            max_bottom = max(0.0, H - new_top - min_face_h)
            new_bottom = max(0.0, min(bottom_val, max_bottom))

            max_top_2 = max(0.0, H - new_bottom - min_face_h)
            new_top = max(0.0, min(new_top, max_top_2))

        if abs(new_top - self.sp_front_offset_top.value()) >= 0.1:
            self.sp_front_offset_top.blockSignals(True)
            self.sp_front_offset_top.setValue(new_top)
            self.sp_front_offset_top.blockSignals(False)
            changed = True

        if abs(new_bottom - self.sp_front_offset_bottom.value()) >= 0.1:
            self.sp_front_offset_bottom.blockSignals(True)
            self.sp_front_offset_bottom.setValue(new_bottom)
            self.sp_front_offset_bottom.blockSignals(False)
            changed = True

        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        return changed

    def _emit_changed_with_front_overview_refresh(self, *_args) -> None:
        self._refresh_front_overview_ui()
        self.sig_changed.emit()

    def _on_front_height_mode_changed(self, _i: int) -> None:
        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        self.sig_changed.emit()

    def _on_front_zone_value_changed(self, _v: float) -> None:
        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        self.sig_changed.emit()

    def _on_reset_front_zone_clicked(self) -> None:
        mode = str(self.cb_front_height_mode.currentData() or "full")

        if mode == "to_top_rail":
            self.sp_front_offset_bottom.setValue(0.0)
        else:
            self.sp_front_offset_top.setValue(0.0)
            self.sp_front_offset_bottom.setValue(0.0)

        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        self.sig_changed.emit()

    def _on_temp_hide_front_toggled(self, _checked: bool) -> None:
        self._refresh_temp_front_preview_ui()
        self.sig_changed.emit()

    def _refresh_temp_front_preview_ui(self) -> None:
        hidden = bool(self.chk_temp_hide_front.isChecked())
        if hidden:
            self.lab_temp_front_preview_state.setText(
                "Stan podgladu: front jest chwilowo ukryty. "
                "Latwiej klikniesz korpus i elementy wewnetrzne."
            )
        else:
            self.lab_temp_front_preview_state.setText(
                "Stan podgladu: front jest widoczny."
            )
        self.btn_temp_show_front_again.setEnabled(hidden)
        self.btn_temp_show_front_again.setVisible(hidden)

    def _refresh_front_zone_ui(self) -> None:
        mode = str(self.cb_front_height_mode.currentData() or "full")
        top_val = float(self.sp_front_offset_top.value())
        bottom_val = float(self.sp_front_offset_bottom.value())

        use_top_offset = mode == "offsets"
        use_bottom_offset = mode in ("offsets", "to_top_rail")

        use_ref_modes = mode == "to_top_rail"

        self.cb_top_ref_mode.setEnabled(use_ref_modes)
        self.cb_bottom_ref_mode.setEnabled(use_ref_modes)
        self.sp_front_offset_top.setEnabled(use_top_offset)
        self.sp_front_offset_bottom.setEnabled(use_bottom_offset)

        show_ref_modes = mode == "to_top_rail"
        show_top_offset = mode == "offsets"
        show_bottom_offset = mode in ("offsets", "to_top_rail")

        self._set_form_row_visible(self.cb_top_ref_mode, show_ref_modes)
        self._set_form_row_visible(self.cb_bottom_ref_mode, show_ref_modes)
        self._set_form_row_visible(self.sp_front_offset_top, show_top_offset)
        self._set_form_row_visible(self.sp_front_offset_bottom, show_bottom_offset)

        if mode == "full":
            self.lab_zone_summary.setText(
                "Tryb: pelna wysokosc modulu. "
                "Offsety i referencje nie ograniczaja strefy frontu."
            )
            self.lab_hint.setText(
                "Front idzie na pelna wysokosc wg wybranego typu frontu."
            )

        elif mode == "to_top_rail":
            top_ref_txt = str(self.cb_top_ref_mode.currentText() or "").strip()
            bottom_ref_txt = str(self.cb_bottom_ref_mode.currentText() or "").strip()

            self.lab_zone_summary.setText(
                f"Tryb: do wienca. "
                f"Gora: {top_ref_txt}. "
                f"Dol: {bottom_ref_txt}, offset dol = {bottom_val:.1f} mm."
            )
            self.lab_hint.setText(
                "Gorna granica strefy wynika z referencji do wienca.\n"
                "Dol strefy mozesz nadal regulowac offsetem."
            )

        else:
            self.lab_zone_summary.setText(
                f"Tryb: strefa z offsetami. "
                f"Gora = {top_val:.1f} mm, dol = {bottom_val:.1f} mm."
            )
            self.lab_hint.setText(
                "Front jest liczony jako strefa robocza z offsetem od gory i od dolu.\n"
                "To przygotowuje uklad np. pod piekarnik lub specjalne fronty."
            )

        self._apply_zone_context()

    def _refresh_front_overview_ui(self) -> None:
        layout_map = {
            "overlay": "nakladany",
            "inset": "wewnetrzny",
        }
        mode_map = {
            "full": "pelna wysokosc",
            "to_top_rail": "referencje wzgledem wienca",
            "offsets": "offsety",
        }
        facade_map = {
            "doors": "drzwi",
            "drawers": "szuflady",
            "mixed": "mieszany",
        }

        layout = str(self.cb_front_layout.currentData() or "overlay")
        mode = str(self.cb_front_height_mode.currentData() or "full")
        facade = str(self.cb_facade_mode.currentData() or "doors")

        layout_txt = layout_map.get(layout, layout)
        mode_txt = mode_map.get(mode, mode)
        facade_txt = facade_map.get(facade, facade)

        top_val = float(self.sp_front_offset_top.value())
        bottom_val = float(self.sp_front_offset_bottom.value())
        drawer_count = int(self.sp_drawer_count.value())
        drawer_layout_mode = str(self.cb_drawer_layout_mode.currentData() or "equal")
        drawer_small_h = float(self.sp_drawer_small_front_h.value())

        layout_mode_map = {
            "equal": "rowny",
            "small_top": "maly u gory",
            "small_bottom": "maly na dole",
        }

        if facade == "drawers":
            mode_txt = layout_mode_map.get(drawer_layout_mode, drawer_layout_mode)
            facade_detail = f"szuflady x {drawer_count}, uklad: {mode_txt}, niski front: {drawer_small_h:.1f} mm"
        elif facade == "mixed":
            mode_txt = layout_mode_map.get(drawer_layout_mode, drawer_layout_mode)
            facade_detail = f"mieszany, szuflady: {drawer_count}, uklad: {mode_txt}, niski front: {drawer_small_h:.1f} mm"
        else:
            facade_detail = "drzwi"

        if mode == "full":
            zone_detail = "pelna wysokosc"
        elif mode == "to_top_rail":
            zone_detail = (
                f"gora: {self.cb_top_ref_mode.currentText()}, "
                f"dol: {self.cb_bottom_ref_mode.currentText()}, "
                f"offset gora {top_val:.1f} mm, "
                f"offset dol {bottom_val:.1f} mm"
            )
        else:
            zone_detail = f"offsety: gora {top_val:.1f} mm, dol {bottom_val:.1f} mm"

        hinge_vendor_txt = str(self.cb_hinge_vendor.currentText() or "").strip()
        drawer_vendor_txt = str(self.cb_drawer_vendor.currentText() or "").strip()

        tipon_txt = "TIP-ON: tak" if self.chk_tipon.isChecked() else "TIP-ON: nie"

        gap_txt = (
            f"Luzy: L {self.sp_gap_left.value():.1f}, "
            f"P {self.sp_gap_right.value():.1f}, "
            f"G {self.sp_gap_top.value():.1f}, "
            f"D {self.sp_gap_bottom.value():.1f}, "
            f"miedzy frontami {self.sp_gap_between_vertical.value():.1f} mm"
        )

        self.lab_front_summary.setText(
            f"Typ: {layout_txt}\n"
            f"Strefa: {mode_txt} ({zone_detail})\n"
            f"Uklad: {facade_txt} ({facade_detail})\n"
            f"{gap_txt}\n"
            f"Okucia: zawiasy {hinge_vendor_txt}, szuflady {drawer_vendor_txt}\n"
            f"{tipon_txt}"
        )

    def set_hint(self, txt: str) -> None:
        self.lab_hint.setText(txt or "")

    def set_zone_context(self, txt: str) -> None:
        self._sticky_zone_context = str(txt or "").strip()
        self._apply_zone_context()

    def clear_zone_context(self) -> None:
        self._sticky_zone_context = ""
        self._apply_zone_context()

    def _apply_zone_context(self) -> None:
        txt = str(self._sticky_zone_context or "").strip()

        if not txt:
            mode = str(self.cb_front_height_mode.currentData() or "full")
            if mode == "full":
                txt = "Aktywna edycja: front jako pelna wysokosc modulu."
            elif mode == "to_top_rail":
                txt = "Aktywna edycja: referencje frontu wzgledem wienca."
            else:
                txt = "Aktywna edycja: strefa frontu z offsetami. Regulujesz gore i do' strefy."

        self.lab_zone_context.setText(txt)

    def set_from_module(self, m: ModuleDef) -> None:
        idx = self.cb_front_layout.findData(str(getattr(m, "front_layout", "overlay") or "overlay"))
        if idx >= 0:
            self.cb_front_layout.setCurrentIndex(idx)

        idx = self.cb_front_height_mode.findData(str(getattr(m, "front_height_mode", "full") or "full"))
        if idx >= 0:
            self.cb_front_height_mode.setCurrentIndex(idx)

        idx = self.cb_top_ref_mode.findData(str(getattr(m, "front_top_ref_mode", "rail_end") or "rail_end"))
        if idx >= 0:
            self.cb_top_ref_mode.setCurrentIndex(idx)

        idx = self.cb_bottom_ref_mode.findData(str(getattr(m, "front_bottom_ref_mode", "rail_end") or "rail_end"))
        if idx >= 0:
            self.cb_bottom_ref_mode.setCurrentIndex(idx)

        self.sp_front_offset_top.setValue(float(getattr(m, "front_offset_top_mm", 0.0) or 0.0))
        self.sp_front_offset_bottom.setValue(float(getattr(m, "front_offset_bottom_mm", 0.0) or 0.0))

        self.sp_gap_left.setValue(float(getattr(m, "front_gap_left_mm", 2.0) or 0.0))
        self.sp_gap_right.setValue(float(getattr(m, "front_gap_right_mm", 2.0) or 0.0))
        self.sp_gap_top.setValue(float(getattr(m, "front_gap_top_mm", 2.0) or 0.0))
        self.sp_gap_bottom.setValue(float(getattr(m, "front_gap_bottom_mm", 2.0) or 0.0))
        self.sp_gap_between_vertical.setValue(float(getattr(m, "front_gap_between_vertical_mm", 2.0) or 0.0))

        idx = self.cb_facade_mode.findData(str(getattr(m, "facade_mode", "doors") or "doors"))
        if idx >= 0:
            self.cb_facade_mode.setCurrentIndex(idx)

        self.sp_drawer_count.setValue(int(getattr(m, "drawer_count", 3) or 3))

        idx = self.cb_drawer_layout_mode.findData(str(getattr(m, "drawer_layout_mode", "equal") or "equal"))
        if idx >= 0:
            self.cb_drawer_layout_mode.setCurrentIndex(idx)

        self.sp_drawer_small_front_h.setValue(float(getattr(m, "drawer_small_front_height_mm", 140.0) or 140.0))

        idx = self.cb_hinge_vendor.findData(str(getattr(m, "hinge_vendor", "generic") or "generic"))
        if idx >= 0:
            self.cb_hinge_vendor.setCurrentIndex(idx)

        idx = self.cb_drawer_vendor.findData(str(getattr(m, "drawer_vendor", "generic") or "generic"))
        if idx >= 0:
            self.cb_drawer_vendor.setCurrentIndex(idx)

        self.chk_tipon.setChecked(bool(getattr(m, "drawer_tip_on", False)))
        self.sp_rear.setValue(float(getattr(m, "drawer_rear_clearance_mm", 10.0) or 10.0))
        self.sp_tip.setValue(float(getattr(m, "drawer_tip_on_clearance_mm", 20.0) or 20.0))

        self._refresh_front_zone_ui()
        self._refresh_front_overview_ui()
        self._refresh_temp_front_preview_ui()

    def apply_to_module(self, m: ModuleDef) -> ModuleDef:
        out = replace(
            m,
            front_layout=str(self.cb_front_layout.currentData() or "overlay"),
            front_height_mode=str(self.cb_front_height_mode.currentData() or "full"),
            front_offset_top_mm=float(self.sp_front_offset_top.value()),
            front_offset_bottom_mm=float(self.sp_front_offset_bottom.value()),
            facade_mode=str(self.cb_facade_mode.currentData() or "doors"),
            drawer_count=int(self.sp_drawer_count.value()),
            drawer_layout_mode=str(self.cb_drawer_layout_mode.currentData() or "equal"),
            drawer_small_front_height_mm=float(self.sp_drawer_small_front_h.value()),
            hinge_vendor=str(self.cb_hinge_vendor.currentData() or "generic"),
            drawer_vendor=str(self.cb_drawer_vendor.currentData() or "generic"),
            drawer_tip_on=bool(self.chk_tipon.isChecked()),
            drawer_rear_clearance_mm=float(self.sp_rear.value()),
            drawer_tip_on_clearance_mm=float(self.sp_tip.value()),
        )

        setattr(out, "front_top_ref_mode", str(self.cb_top_ref_mode.currentData() or "rail_end"))
        setattr(out, "front_bottom_ref_mode", str(self.cb_bottom_ref_mode.currentData() or "rail_end"))
        setattr(out, "front_gap_left_mm", float(self.sp_gap_left.value()))
        setattr(out, "front_gap_right_mm", float(self.sp_gap_right.value()))
        setattr(out, "front_gap_top_mm", float(self.sp_gap_top.value()))
        setattr(out, "front_gap_bottom_mm", float(self.sp_gap_bottom.value()))
        setattr(out, "front_gap_between_vertical_mm", float(self.sp_gap_between_vertical.value()))
        return out
