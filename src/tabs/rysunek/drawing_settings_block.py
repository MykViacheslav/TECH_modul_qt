from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QColorDialog,
)


class _ColorPickButton(QPushButton):
    sig_color_changed = pyqtSignal(str)

    def __init__(self, title_pl: str, initial_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title_pl = title_pl
        self._hex = initial_hex.strip() or "#000000"
        self.setFixedWidth(120)
        self.clicked.connect(self._pick)
        self._apply()

    def hex(self) -> str:
        return self._hex

    def set_hex(self, hex_color: str) -> None:
        self._hex = (hex_color or "").strip() or "#000000"
        self._apply()

    def _apply(self) -> None:
        c = QColor(self._hex)
        if not c.isValid():
            c = QColor("#000000")
            self._hex = "#000000"
        text = "#ffffff" if c.lightness() < 128 else "#000000"
        self.setText(self._hex)
        self.setStyleSheet(
            f"background-color: {self._hex}; color: {text}; border: 1px solid #666;"
        )

    def _pick(self) -> None:
        col = QColorDialog.getColor(QColor(self._hex), self, self._title_pl)
        if col.isValid():
            self.set_hex(col.name())
            self.sig_color_changed.emit(self._hex)


class DrawingSettingsBlock(QWidget):
    sig_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        lay = QFormLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ed_outline_color = QLineEdit("#000000")
        self.sp_outline_width = QSpinBox()
        self.sp_outline_width.setRange(1, 6)
        self.sp_outline_width.setValue(1)

        self.ed_dim_color = QLineEdit("#0066cc")
        self.sp_dim_width = QSpinBox()
        self.sp_dim_width.setRange(1, 6)
        self.sp_dim_width.setValue(1)

        self.chk_show_grid = QCheckBox("Pokaz siatke")
        self.chk_show_grid.setChecked(True)

        self.chk_show_front_part = QCheckBox("Pokaz front na rysunku")
        self.chk_show_front_part.setChecked(True)

        self.cb_front_mode = QComboBox()
        self.cb_front_mode.addItem("Nakladany", "external")
        self.cb_front_mode.addItem("Wewnetrzny", "internal")

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

        lay.addRow("Obrys: kolor", self.ed_outline_color)
        lay.addRow("Obrys: grubosc", self.sp_outline_width)

        lay.addRow("Wymiary: kolor", self.ed_dim_color)
        lay.addRow("Wymiary: grubosc", self.sp_dim_width)

        lay.addRow("", self.chk_show_grid)
        lay.addRow("", self.chk_show_front_part)
        lay.addRow("Typ frontu", self.cb_front_mode)
        lay.addRow("Offset zawiasu od brzegu", self.sp_hinge_edge_offset)
        lay.addRow("Auto 2 drzwi od szerokosci", self.sp_auto_double_front_width)

        self.ed_outline_color.editingFinished.connect(self.sig_changed.emit)
        self.sp_outline_width.valueChanged.connect(lambda _v: self.sig_changed.emit())

        self.ed_dim_color.editingFinished.connect(self.sig_changed.emit)
        self.sp_dim_width.valueChanged.connect(lambda _v: self.sig_changed.emit())

        self.chk_show_grid.toggled.connect(lambda _v: self.sig_changed.emit())
        self.chk_show_front_part.toggled.connect(lambda _v: self.sig_changed.emit())
        self.cb_front_mode.currentIndexChanged.connect(lambda _i: self.sig_changed.emit())

        self.sp_hinge_edge_offset.valueChanged.connect(lambda _v: self.sig_changed.emit())
        self.sp_auto_double_front_width.valueChanged.connect(lambda _v: self.sig_changed.emit())

    def get_values(self) -> dict:
        return {
            "rect_line_color": (self.ed_outline_color.text() or "#000000").strip() or "#000000",
            "rect_line_width_px": int(self.sp_outline_width.value()),
            "dim_line_color": (self.ed_dim_color.text() or "#0066cc").strip() or "#0066cc",
            "dim_line_width_px": int(self.sp_dim_width.value()),
            "grid_enabled": bool(self.chk_show_grid.isChecked()),
            "grid_step_mm": 50.0,
            "grid_color": "#dddddd",
            "grid_width_px": 1,
            "show_front_part": bool(self.chk_show_front_part.isChecked()),
            "front_mode": str(self.cb_front_mode.currentData() or "external"),
            "hinge_edge_offset_mm": float(self.sp_hinge_edge_offset.value()),
            "auto_double_front_width_mm": float(self.sp_auto_double_front_width.value()),
        }

    def set_values(self, data: dict) -> None:
        data = data or {}

        self.ed_outline_color.setText(str(data.get("rect_line_color", "#000000") or "#000000"))
        self.sp_outline_width.setValue(int(data.get("rect_line_width_px", 1) or 1))

        self.ed_dim_color.setText(str(data.get("dim_line_color", "#0066cc") or "#0066cc"))
        self.sp_dim_width.setValue(int(data.get("dim_line_width_px", 1) or 1))

        self.chk_show_grid.setChecked(bool(data.get("grid_enabled", True)))
        self.chk_show_front_part.setChecked(bool(data.get("show_front_part", True)))

        mode = str(data.get("front_mode", "external") or "external")
        idx = self.cb_front_mode.findData(mode)
        if idx >= 0:
            self.cb_front_mode.setCurrentIndex(idx)

        self.sp_hinge_edge_offset.setValue(
            float(data.get("hinge_edge_offset_mm", data.get("hinge_edge_offset", 12.0)) or 12.0)
        )
        self.sp_auto_double_front_width.setValue(
            float(data.get("auto_double_front_width_mm", data.get("auto_double_front_width", 600.0)) or 600.0)
        )

    def to_settings(self) -> dict:
        return self.get_values()

    def set_from_settings(self, data: dict) -> None:
        self.set_values(data)