from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from src.storage.catalog_store_json import CatalogStoreJson
from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog
from src.tabs.modul.material_grouping import resolve_group_edgeband_defaults

# ── Style ────────────────────────────────────────────────────────────────────
_SS_ROW_LBL = (
    "QLabel{color:#475569;font-size:11px;font-weight:700;"
    "padding:0;min-width:52px;max-width:52px;}"
)
_SS_HDR_LBL = (
    "QLabel{color:#94a3b8;font-size:9px;font-weight:700;"
    "letter-spacing:0.07em;padding:6px 0 2px 0;}"
)
_SS_COMBO = (
    "QComboBox{font-size:11px;padding:2px 4px;min-height:24px;}"
)
_SS_COMBO_EDGE = (
    "QComboBox{font-size:10px;padding:2px 3px;min-height:24px;color:#64748b;}"
)
_SS_DIVIDER = "QFrame{background:#e2e8f0;max-height:1px;margin:4px 0;}"
_SS_SECTION = "QFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;}"
_SS_SECTION_TITLE = "QLabel{color:#334155;font-size:10px;font-weight:800;letter-spacing:0.04em;padding:0;}"
# ─────────────────────────────────────────────────────────────────────────────


class MaterialsBlock(QWidget):
    """
    CORPUS-style panel materialow:

    PROFIL: [dropdown]
    [opis profilu]

    ──────────────────────────────────
           Material        Okleina
    Korpus [PB18...    ▼] [ABS 0,8 ▼]
    Front  [MDF19...   ▼] [ABS 0,8 ▼]
    Plecy  [HDF2.5...  ▼] [ABS 0,8 ▼]
    ──────────────────────────────────
    [Edytuj baze cen]
    """

    sig_changed = pyqtSignal()
    sig_catalog_changed = pyqtSignal()
    sig_profile_selected = pyqtSignal(str)

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preview_hide_front = False
        self._catalog = catalog

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── helpers ──────────────────────────────────────────────────────────
        def _hdr(text: str) -> QLabel:
            l = QLabel(text); l.setStyleSheet(_SS_HDR_LBL); return l

        def _row_lbl(text: str) -> QLabel:
            l = QLabel(text); l.setStyleSheet(_SS_ROW_LBL)
            l.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            return l

        def _cb(edge: bool = False) -> QComboBox:
            c = QComboBox()
            c.setStyleSheet(_SS_COMBO_EDGE if edge else _SS_COMBO)
            c.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            c.setMinimumContentsLength(9 if edge else 11)
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return c

        def _divider() -> QFrame:
            f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet(_SS_DIVIDER); return f

        def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
            frame = QFrame(self)
            frame.setStyleSheet(_SS_SECTION)
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(8, 6, 8, 8)
            lay.setSpacing(6)
            lab = QLabel(title, frame)
            lab.setStyleSheet(_SS_SECTION_TITLE)
            lay.addWidget(lab, 0)
            return frame, lay

        # ── Profil (pełna szerokość) ──────────────────────────────────────────
        profile_section, profile_lay = _section("Profil")
        self.cb_profile = _cb()
        profile_lay.addWidget(self.cb_profile)

        self.lab_profile_desc = QLabel("")
        self.lab_profile_desc.setWordWrap(True)
        self.lab_profile_desc.setStyleSheet(
            "color:#94a3b8;font-size:10px;font-style:italic;padding:2px 0 4px 0;"
        )
        profile_lay.addWidget(self.lab_profile_desc)
        root.addWidget(profile_section)

        # ── Siatka 3×3: Etykieta | Material | Okleina ─────────────────────────
        self.cb_carcass      = _cb()
        self.cb_front        = _cb()
        self.cb_back         = _cb()
        self.cb_edge_carcass = _cb(edge=True)
        self.cb_edge_front   = _cb(edge=True)
        self.cb_edge_back    = _cb(edge=True)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        grid.setHorizontalSpacing(6)

        # nagłówki kolumn
        grid.addWidget(_hdr(""),          0, 0)
        grid.addWidget(_hdr("MATERIAL"),  0, 1)
        grid.addWidget(_hdr("OKLEINA"),   0, 2)

        # wiersze: Korpus / Front / Plecy
        for row, (label, cb_mat, cb_edge) in enumerate([
            ("Korpus", self.cb_carcass,  self.cb_edge_carcass),
            ("Front",  self.cb_front,    self.cb_edge_front),
            ("Plecy",  self.cb_back,     self.cb_edge_back),
        ], start=1):
            grid.addWidget(_row_lbl(label), row, 0)
            grid.addWidget(cb_mat,          row, 1)
            grid.addWidget(cb_edge,         row, 2)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 2)
        materials_section, materials_lay = _section("Material i okleina")
        materials_lay.addWidget(grid_w)
        root.addWidget(materials_section)

        # ── Edytuj bazę cen ───────────────────────────────────────────────────
        self.btn_edit_catalog = QPushButton("Edytuj baze cen")
        self.btn_edit_catalog.setStyleSheet("margin-top:2px;font-size:11px;")
        self.btn_edit_catalog.clicked.connect(self._open_catalog_editor)
        catalog_section, catalog_lay = _section("Baza cen")
        catalog_lay.addWidget(self.btn_edit_catalog, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(catalog_section)

        # ── Wypełnij dane i podłącz sygnały ───────────────────────────────────
        self._fill_profiles()
        self._fill_materials()
        self._fill_edgebands()

        all_cbs = [
            self.cb_profile, self.cb_carcass, self.cb_front, self.cb_back,
            self.cb_edge_carcass, self.cb_edge_front, self.cb_edge_back,
        ]
        for _c in all_cbs:
            _c.currentIndexChanged.connect(
                lambda _, c=_c: c.setToolTip(c.currentText())
            )
            _c.setToolTip(_c.currentText())

        self.cb_profile.currentIndexChanged.connect(self._on_profile_changed)
        self.cb_carcass.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_front.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_back.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_carcass.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_front.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_back.currentIndexChanged.connect(self.sig_changed.emit)

    def _default_edgeband_key(self) -> str:
        edgebands = self._catalog.list_edgebands() or []
        for edgeband in edgebands:
            key = str(getattr(edgeband, "key", "") or "").strip()
            if key and key.lower() != "brak":
                return key
        return "Brak"

    def _fill_profiles(self) -> None:
        current_key = str(self.cb_profile.currentData() or "")
        profiles = self._catalog.list_material_profiles()

        self.cb_profile.blockSignals(True)
        self.cb_profile.clear()
        for profile in profiles:
            self.cb_profile.addItem(f"{profile.name_pl} ({profile.key})", profile.key)

        idx = self.cb_profile.findData(current_key)
        if idx < 0:
            idx = self.cb_profile.findData("STD_WHITE")
        self.cb_profile.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_profile.blockSignals(False)
        self._update_profile_description()

    def _update_profile_description(self) -> None:
        profile_key = str(self.cb_profile.currentData() or "STD_WHITE")
        profile = self._catalog.get_material_profile(profile_key)
        self.lab_profile_desc.setText(str(profile.description or "").strip())

    def _on_profile_changed(self, _index: int) -> None:
        self._update_profile_description()
        self.sig_profile_selected.emit(str(self.cb_profile.currentData() or "STD_WHITE"))

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

    def _edgeband_label(self, edgeband) -> str:
        label = f"{edgeband.name_pl}"
        extras: list[str] = []
        manufacturer = str(getattr(edgeband, "manufacturer", "") or "").strip()
        band_type = str(getattr(edgeband, "edgeband_type", "") or "").strip()
        if manufacturer:
            extras.append(manufacturer)
        if band_type:
            extras.append(band_type)
        if extras:
            label += f" [{', '.join(extras)}]"
        thickness = float(getattr(edgeband, "thickness_mm", 0.0) or 0.0)
        price = float(getattr(edgeband, "price_pln_per_m", 0.0) or 0.0)
        if thickness > 0.0:
            label += f" ({thickness:g} mm)"
        if price > 0.0:
            label += f" - {price:.2f} zl/mb"
        return label

    def _fill_materials(self) -> None:
        mats = self._catalog.list_materials()

        def fill(cb: QComboBox) -> None:
            cb.clear()
            for material in mats:
                cb.addItem(self._material_label(material), material.key)

        fill(self.cb_carcass)
        fill(self.cb_front)
        fill(self.cb_back)

    def _fill_edgebands(self) -> None:
        edgebands = self._catalog.list_edgebands() or []

        def fill(cb: QComboBox) -> None:
            cb.clear()
            for edgeband in edgebands:
                cb.addItem(self._edgeband_label(edgeband), edgeband.key)

            default_key = self._default_edgeband_key()
            idx = cb.findData(default_key)
            if idx < 0:
                idx = cb.findData("Brak")
            cb.setCurrentIndex(idx if idx >= 0 else 0)

        fill(self.cb_edge_carcass)
        fill(self.cb_edge_front)
        fill(self.cb_edge_back)

    def set_materials(self, materials: Dict[str, str]) -> None:
        def set_cb(cb: QComboBox, key: str) -> None:
            idx = cb.findData(key)
            cb.setCurrentIndex(idx if idx >= 0 else 0)

        self.cb_carcass.blockSignals(True)
        self.cb_front.blockSignals(True)
        self.cb_back.blockSignals(True)

        set_cb(self.cb_carcass, materials.get("carcass", "PB18"))
        set_cb(self.cb_front, materials.get("front", "MDF19"))
        set_cb(self.cb_back, materials.get("back", "HDF2.5"))

        self.cb_carcass.blockSignals(False)
        self.cb_front.blockSignals(False)
        self.cb_back.blockSignals(False)

    def set_edgebands(self, edgebands: Dict[str, str]) -> None:
        group_defaults = resolve_group_edgeband_defaults(
            edgebands,
            fallback_key=self._default_edgeband_key(),
        )

        def set_cb(cb: QComboBox, key: str) -> None:
            idx = cb.findData(key)
            cb.setCurrentIndex(idx if idx >= 0 else 0)

        self.cb_edge_carcass.blockSignals(True)
        self.cb_edge_front.blockSignals(True)
        self.cb_edge_back.blockSignals(True)

        set_cb(self.cb_edge_carcass, group_defaults.get("carcass", self._default_edgeband_key()))
        set_cb(self.cb_edge_front, group_defaults.get("front", self._default_edgeband_key()))
        set_cb(self.cb_edge_back, group_defaults.get("back", self._default_edgeband_key()))

        self.cb_edge_carcass.blockSignals(False)
        self.cb_edge_front.blockSignals(False)
        self.cb_edge_back.blockSignals(False)

    def get_materials(self) -> Dict[str, str]:
        return {
            "carcass": str(self.cb_carcass.currentData() or "PB18"),
            "front": str(self.cb_front.currentData() or "MDF19"),
            "back": str(self.cb_back.currentData() or "HDF2.5"),
        }

    def get_edgebands(self) -> Dict[str, str]:
        return {
            "carcass": str(self.cb_edge_carcass.currentData() or self._default_edgeband_key()),
            "front": str(self.cb_edge_front.currentData() or self._default_edgeband_key()),
            "back": str(self.cb_edge_back.currentData() or self._default_edgeband_key()),
        }

    def set_profile_key(self, profile_key: str) -> None:
        normalized = str(profile_key or "STD_WHITE").strip() or "STD_WHITE"
        idx = self.cb_profile.findData(normalized)
        if idx < 0:
            idx = self.cb_profile.findData("STD_WHITE")
        self.cb_profile.blockSignals(True)
        self.cb_profile.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_profile.blockSignals(False)
        self._update_profile_description()

    def get_profile_key(self) -> str:
        return str(self.cb_profile.currentData() or "STD_WHITE")

    def reload_catalog(self) -> None:
        current_profile = self.get_profile_key()
        current_materials = self.get_materials()
        current_edgebands = self.get_edgebands()

        self._fill_profiles()
        self._fill_materials()
        self._fill_edgebands()
        self.set_profile_key(current_profile)
        self.set_materials(current_materials)
        self.set_edgebands(current_edgebands)

    def _open_catalog_editor(self) -> None:
        dlg = CatalogEditorDialog(self, self._catalog)
        if dlg.exec():
            self.reload_catalog()
            self.sig_catalog_changed.emit()
