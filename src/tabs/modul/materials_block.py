from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.storage.catalog_store_json import CatalogStoreJson
from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog
from src.tabs.modul.material_grouping import resolve_group_edgeband_defaults


class MaterialsBlock(QWidget):
    sig_changed = pyqtSignal()
    sig_catalog_changed = pyqtSignal()
    sig_profile_selected = pyqtSignal(str)

    def __init__(self, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preview_hide_front = False
        self._catalog = catalog

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_profile = QComboBox()
        self.lab_profile_desc = QLabel("")
        self.lab_profile_desc.setWordWrap(True)
        self.lab_profile_desc.setStyleSheet("color:#666;")

        self.cb_carcass = QComboBox()
        self.cb_front = QComboBox()
        self.cb_back = QComboBox()

        self.cb_edge_carcass = QComboBox()
        self.cb_edge_front = QComboBox()
        self.cb_edge_back = QComboBox()

        self._fill_profiles()
        self._fill_materials()
        self._fill_edgebands()

        self.cb_profile.currentIndexChanged.connect(self._on_profile_changed)
        self.cb_carcass.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_front.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_back.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_carcass.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_front.currentIndexChanged.connect(self.sig_changed.emit)
        self.cb_edge_back.currentIndexChanged.connect(self.sig_changed.emit)

        form.addRow("Profil", self.cb_profile)
        form.addRow("", self.lab_profile_desc)
        form.addRow("Korpus", self.cb_carcass)
        form.addRow("Front", self.cb_front)
        form.addRow("Plecy", self.cb_back)
        form.addRow("Korpus - okleina", self.cb_edge_carcass)
        form.addRow("Front - okleina", self.cb_edge_front)
        form.addRow("Plecy - okleina", self.cb_edge_back)

        lay.addLayout(form)

        self.btn_edit_catalog = QPushButton("Edytuj baze cen")
        self.btn_edit_catalog.clicked.connect(self._open_catalog_editor)
        lay.addWidget(self.btn_edit_catalog, 0, Qt.AlignmentFlag.AlignLeft)

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
