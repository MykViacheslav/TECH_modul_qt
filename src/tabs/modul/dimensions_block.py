from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.domain.module_base_group import BASE_GROUP_LABELS_PL, BASE_GROUP_ORDER


class DimensionsBlock(QWidget):
    sig_save = pyqtSignal()
    sig_load = pyqtSignal()
    sig_overwrite = pyqtSignal()
    sig_delete = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("np. MOD_800x500x720")

        self.cb_base_group = QComboBox()
        for key in BASE_GROUP_ORDER:
            self.cb_base_group.addItem(BASE_GROUP_LABELS_PL.get(key, key), key)

        self.sp_w = QDoubleSpinBox()
        self.sp_w.setRange(1, 10000)
        self.sp_w.setDecimals(1)
        self.sp_w.setSuffix(" mm")

        self.sp_d = QDoubleSpinBox()
        self.sp_d.setRange(1, 10000)
        self.sp_d.setDecimals(1)
        self.sp_d.setSuffix(" mm")

        self.sp_h = QDoubleSpinBox()
        self.sp_h.setRange(1, 10000)
        self.sp_h.setDecimals(1)
        self.sp_h.setSuffix(" mm")

        self.sp_top_rail_offset = QDoubleSpinBox()
        self.sp_top_rail_offset.setRange(0.0, 10000.0)
        self.sp_top_rail_offset.setDecimals(1)
        self.sp_top_rail_offset.setSuffix(" mm")
        self.sp_top_rail_offset.setValue(0.0)

        self.sp_bottom_rail_offset = QDoubleSpinBox()
        self.sp_bottom_rail_offset.setRange(0.0, 10000.0)
        self.sp_bottom_rail_offset.setDecimals(1)
        self.sp_bottom_rail_offset.setSuffix(" mm")
        self.sp_bottom_rail_offset.setValue(0.0)

        self.sp_hinge_edge_offset = QDoubleSpinBox()
        self.sp_hinge_edge_offset.setRange(0.0, 100.0)
        self.sp_hinge_edge_offset.setDecimals(1)
        self.sp_hinge_edge_offset.setSuffix(" mm")
        self.sp_hinge_edge_offset.setValue(12.0)

        self.sp_auto_double_front_width = QDoubleSpinBox()
        self.sp_auto_double_front_width.setRange(200.0, 2000.0)
        self.sp_auto_double_front_width.setDecimals(1)
        self.sp_auto_double_front_width.setSuffix(" mm")
        self.sp_auto_double_front_width.setValue(600.0)

        form.addRow("Nazwa modulu", self.ed_name)
        form.addRow("Grupa bazy", self.cb_base_group)
        form.addRow("Szerokosc (L)", self.sp_w)
        form.addRow("Glebokosc (W)", self.sp_d)
        form.addRow("Wysokosc (H)", self.sp_h)
        form.addRow("Offset wienca gornego", self.sp_top_rail_offset)
        form.addRow("Offset wienca dolnego", self.sp_bottom_rail_offset)

        form.addRow("Offset zawiasu od brzegu", self.sp_hinge_edge_offset)
        form.addRow("Auto 2 drzwi od szerokosci", self.sp_auto_double_front_width)

        lab_hinge = form.labelForField(self.sp_hinge_edge_offset)
        if lab_hinge is not None:
            lab_hinge.hide()
        self.sp_hinge_edge_offset.hide()

        lab_auto = form.labelForField(self.sp_auto_double_front_width)
        if lab_auto is not None:
            lab_auto.hide()
        self.sp_auto_double_front_width.hide()

        lay.addLayout(form)

        btns = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz")
        self.btn_load = QPushButton("Wczytaj")
        self.btn_over = QPushButton("Nadpisz")
        self.btn_del = QPushButton("Usun")

        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_load)
        btns.addWidget(self.btn_over)
        btns.addWidget(self.btn_del)
        lay.addLayout(btns)

        self.btn_save.clicked.connect(self.sig_save.emit)
        self.btn_load.clicked.connect(self.sig_load.emit)
        self.btn_over.clicked.connect(self.sig_overwrite.emit)
        self.btn_del.clicked.connect(self.sig_delete.emit)
