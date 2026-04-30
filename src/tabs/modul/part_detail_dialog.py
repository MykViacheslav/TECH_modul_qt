from __future__ import annotations

from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QCheckBox, QFrame,
    QGridLayout, QScrollArea, QWidget
)
from src.domain.module_models import PartDef
from src.storage.catalog_store_json import CatalogStoreJson
from src.tabs.modul.edge_preview_widget import EdgePreviewWidget, _key_to_color

class PartDetailDialog(QDialog):
    """
    Advanced Dialog for a single part (Formatka).
    Inspired by professional software (Corpus/Blum).
    Shows the part with grain, different edges, and lacquer/veneer options.
    """
    def __init__(self, part: PartDef, catalog: CatalogStoreJson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Detal formatki: {part.name_pl}")
        self.setMinimumSize(600, 450)
        self._part = part
        self._catalog = catalog
        
        # Result state
        self.new_edge_banding = dict(part.edge_banding or {})
        self.veneer_active = bool(getattr(part, "veneer_active", False))
        self.lacquer_active = bool(getattr(part, "lacquer_active", False))

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        main_lay = QHBoxLayout(self)
        
        # LEFT: 3D-ish Preview
        left_panel = QVBoxLayout()
        self.preview = EdgePreviewWidget()
        self.preview.setMinimumSize(300, 250)
        self.preview.setPartName(self._part.name_pl)
        left_panel.addWidget(self.preview)
        
        info_box = QFrame()
        info_box.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;")
        info_lay = QVBoxLayout(info_box)
        
        d = self._part.dims_mm
        self.lab_dims = QLabel(f"Wymiar: {d.get('w','?')} x {d.get('h','?')} x {d.get('t','?')} mm")
        self.lab_dims.setStyleSheet("font-weight: 600; color: #1e293b;")
        info_lay.addWidget(self.lab_dims)
        
        self.lab_area = QLabel(f"Powierzchnia: {(float(d.get('w',0))*float(d.get('h',0))/1000000.0):.3f} m2")
        info_lay.addWidget(self.lab_area)
        
        left_panel.addWidget(info_box)
        left_panel.addStretch()
        main_lay.addLayout(left_panel, 2)
        
        # RIGHT: Settings
        right_panel = QVBoxLayout()
        
        # 1. Edges
        edge_group = QFrame()
        edge_group.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 8px;")
        edge_lay = QVBoxLayout(edge_group)
        edge_lay.addWidget(QLabel("<b>OKLEJANIE KRAWĘDZI</b>"))
        
        self.edge_combos: Dict[str, QComboBox] = {}
        grid = QGridLayout()
        edge_list = [("top", "Góra"), ("bottom", "Dół"), ("left", "Lewa"), ("right", "Prawa")]
        
        edgebands = self._catalog.list_edgebands()
        
        for i, (key, label) in enumerate(edge_list):
            grid.addWidget(QLabel(label), i, 0)
            cb = QComboBox()
            cb.addItem("Brak", "Brak")
            for eb in edgebands:
                cb.addItem(f"{eb.name_pl} ({eb.thickness_mm}mm)", eb.key)
            self.edge_combos[key] = cb
            grid.addWidget(cb, i, 1)
            cb.currentIndexChanged.connect(self._on_edge_changed)
            
        edge_lay.addLayout(grid)
        right_panel.addWidget(edge_group)
        
        # 2. Surface Finishes (Veneer / Lacquer)
        surf_group = QFrame()
        surf_group.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px;")
        surf_lay = QVBoxLayout(surf_group)
        surf_lay.addWidget(QLabel("<b>WYKOŃCZENIE POWIERZCHNI</b>"))
        
        self.chk_veneer = QCheckBox("Fornir (dwustronnie)")
        self.chk_lacquer = QCheckBox("Lakierowanie")
        
        surf_lay.addWidget(self.chk_veneer)
        surf_lay.addWidget(self.chk_lacquer)
        
        self.lab_calc = QLabel("Kalkulacja: -")
        self.lab_calc.setStyleSheet("font-size: 10px; color: #64748b;")
        surf_lay.addWidget(self.lab_calc)
        
        right_panel.addWidget(surf_group)
        right_panel.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz")
        self.btn_save.setStyleSheet("background: #2563eb; color: white; font-weight: 700; padding: 8px;")
        self.btn_save.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.reject)
        
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        right_panel.addLayout(btns)
        
        main_lay.addLayout(right_panel, 3)

    def _load_data(self) -> None:
        eb = self._part.edge_banding or {}
        for key, combo in self.edge_combos.items():
            val = eb.get(key, "Brak")
            idx = combo.findData(val)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.chk_veneer.setChecked(self.veneer_active)
        self.chk_lacquer.setChecked(self.lacquer_active)
        self._update_preview()
        self._update_calcs()

    def _on_edge_changed(self) -> None:
        for key, combo in self.edge_combos.items():
            self.new_edge_banding[key] = combo.currentData()
        self._update_preview()
        self._update_calcs()

    def _update_preview(self) -> None:
        bands = {k: v for k, v in self.new_edge_banding.items() if v != "Brak"}
        self.preview.set_edge_banding(bands)

    def _update_calcs(self) -> None:
        d = self._part.dims_mm
        w = float(d.get('w', 0)) / 1000.0
        h = float(d.get('h', 0)) / 1000.0
        area = w * h
        
        lines = []
        if self.chk_veneer.isChecked():
            lines.append(f"Fornir: {area*2:.3f} m2")
        if self.chk_lacquer.isChecked():
            lines.append(f"Lakier: {area:.3f} m2 (front)")
            
        self.lab_calc.setText(" | ".join(lines) if lines else "Kalkulacja: brak wykończeń")

    def get_result(self) -> Dict[str, Any]:
        return {
            "edge_banding": self.new_edge_banding,
            "veneer_active": self.chk_veneer.isChecked(),
            "lacquer_active": self.chk_lacquer.isChecked(),
        }
