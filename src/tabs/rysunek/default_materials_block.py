"""
DefaultMaterialsBlock — blok ustawien domyslnych materialow dla nowych modulow.

Pozwala ustawic raz:
- material korpusu (Plyta biala 18mm)
- material frontu (Szary mat 16mm)
- material polki (opcjonalnie, domyslnie = korpus)
- material plecow (HDF 3mm)
- obrzeza korpusu i frontu
- wysokosc nozek
- typ laczenia korpusu

Zapis / odczyt przez load_default_material_settings / save_default_material_settings.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import (
    DefaultMaterialSettings,
    load_default_material_settings,
    save_default_material_settings,
)


# Predefiniowane profile materialowe (klucz: etykieta)
MATERIAL_PROFILES: dict[str, dict] = {
    "": "-- wlasne ustawienia --",
    "kuchnia_biala": "Kuchnia biala (Plyta biala + HDF)",
    "kuchnia_dab": "Kuchnia dab (Dab sonoma + HDF)",
    "lazienka_szara": "Lazienka szara (Szary mat + HDF)",
    "salon_antracyt": "Salon antracyt (Antracyt + HDF)",
}

PROFILE_PRESETS: dict[str, dict] = {
    "kuchnia_biala": {
        "carcass_material_key": "plyta_biala",
        "carcass_thickness_mm": 18.0,
        "front_material_key": "plyta_biala",
        "front_thickness_mm": 18.0,
        "shelf_material_key": "",
        "shelf_thickness_mm": 18.0,
        "back_material_key": "hdf",
        "back_thickness_mm": 3.0,
    },
    "kuchnia_dab": {
        "carcass_material_key": "dab_sonoma",
        "carcass_thickness_mm": 18.0,
        "front_material_key": "dab_sonoma",
        "front_thickness_mm": 18.0,
        "shelf_material_key": "",
        "shelf_thickness_mm": 18.0,
        "back_material_key": "hdf",
        "back_thickness_mm": 3.0,
    },
    "lazienka_szara": {
        "carcass_material_key": "plyta_biala",
        "carcass_thickness_mm": 18.0,
        "front_material_key": "szary_mat",
        "front_thickness_mm": 16.0,
        "shelf_material_key": "",
        "shelf_thickness_mm": 18.0,
        "back_material_key": "hdf",
        "back_thickness_mm": 3.0,
    },
    "salon_antracyt": {
        "carcass_material_key": "plyta_biala",
        "carcass_thickness_mm": 18.0,
        "front_material_key": "antracyt_mat",
        "front_thickness_mm": 18.0,
        "shelf_material_key": "",
        "shelf_thickness_mm": 18.0,
        "back_material_key": "hdf",
        "back_thickness_mm": 3.0,
    },
}

JOINT_TYPES: list[tuple[str, str]] = [
    ("type1", "Typ 1 — klasyczny (gorno-dolny)"),
    ("type2", "Typ 2 — boki zewnetrzne"),
    ("type3", "Typ 3 — boki wewnetrzne"),
]


def _spin(value: float, min_val: float, max_val: float, step: float = 1.0, suffix: str = " mm") -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(min_val, max_val)
    sb.setSingleStep(step)
    sb.setSuffix(suffix)
    sb.setDecimals(1)
    sb.setValue(value)
    return sb


class DefaultMaterialsBlock(QWidget):
    """Panel ustawien domyslnych materialow i obrze zy."""

    sig_saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = load_default_material_settings()
        self._building = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ── PROFIL ───────────────────────────────────────────────
        grp_profile = QGroupBox("Profil materialowy (preset)")
        profile_lay = QHBoxLayout(grp_profile)
        self.cb_profile = QComboBox()
        for key, label in MATERIAL_PROFILES.items():
            self.cb_profile.addItem(label, key)
        self.btn_apply_profile = QPushButton("Zastosuj profil")
        self.btn_apply_profile.setFixedWidth(140)
        profile_lay.addWidget(QLabel("Profil:"))
        profile_lay.addWidget(self.cb_profile, 1)
        profile_lay.addWidget(self.btn_apply_profile)
        root.addWidget(grp_profile)

        # ── MATERIALY ─────────────────────────────────────────────
        grp_mat = QGroupBox("Domyslne materialy")
        form = QFormLayout(grp_mat)
        form.setLabelAlignment(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        # Korpus
        row_carcass = QHBoxLayout()
        self.le_carcass_mat = _editable_line("plyta_biala")
        self.sp_carcass_thick = _spin(18.0, 3.0, 50.0)
        row_carcass.addWidget(self.le_carcass_mat, 1)
        row_carcass.addWidget(QLabel("Grub.:"))
        row_carcass.addWidget(self.sp_carcass_thick)
        form.addRow("Korpus:", row_carcass)

        # Front
        row_front = QHBoxLayout()
        self.le_front_mat = _editable_line("szary_mat")
        self.sp_front_thick = _spin(16.0, 3.0, 50.0)
        row_front.addWidget(self.le_front_mat, 1)
        row_front.addWidget(QLabel("Grub.:"))
        row_front.addWidget(self.sp_front_thick)
        form.addRow("Front:", row_front)

        # Polka
        row_shelf = QHBoxLayout()
        self.le_shelf_mat = _editable_line("")
        self.le_shelf_mat.setPlaceholderText("puste = jak korpus")
        self.sp_shelf_thick = _spin(18.0, 3.0, 50.0)
        row_shelf.addWidget(self.le_shelf_mat, 1)
        row_shelf.addWidget(QLabel("Grub.:"))
        row_shelf.addWidget(self.sp_shelf_thick)
        form.addRow("Polka:", row_shelf)

        # Plecy
        row_back = QHBoxLayout()
        self.le_back_mat = _editable_line("hdf")
        self.sp_back_thick = _spin(3.0, 1.0, 18.0)
        row_back.addWidget(self.le_back_mat, 1)
        row_back.addWidget(QLabel("Grub.:"))
        row_back.addWidget(self.sp_back_thick)
        form.addRow("Plecy:", row_back)

        root.addWidget(grp_mat)

        # ── OBRZEZA ───────────────────────────────────────────────
        grp_eb = QGroupBox("Domyslne obrzeza")
        form_eb = QFormLayout(grp_eb)
        form_eb.setSpacing(6)
        self.le_carcass_eb = _editable_line("")
        self.le_carcass_eb.setPlaceholderText("klucz obrzeza z katalogu")
        self.le_front_eb = _editable_line("")
        self.le_front_eb.setPlaceholderText("klucz obrzeza z katalogu")
        form_eb.addRow("Obrzeze korpusu:", self.le_carcass_eb)
        form_eb.addRow("Obrzeze frontu:", self.le_front_eb)
        root.addWidget(grp_eb)

        # ── MONTAZ ────────────────────────────────────────────────
        grp_mount = QGroupBox("Montaz i laczenia")
        form_mount = QFormLayout(grp_mount)
        form_mount.setSpacing(6)
        self.sp_leg_height = _spin(100.0, 0.0, 300.0)
        self.cb_joint = QComboBox()
        for key, label in JOINT_TYPES:
            self.cb_joint.addItem(label, key)
        form_mount.addRow("Wys. nozek:", self.sp_leg_height)
        form_mount.addRow("Typ laczenia:", self.cb_joint)
        root.addWidget(grp_mount)

        # ── PRZYCISKI ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz ustawienia materialow")
        self.btn_save.setFixedHeight(34)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #22c55e; font-size: 11px;")
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.lbl_status, 1)
        root.addLayout(btn_row)

        root.addStretch(1)

        # ── SYGNALY ───────────────────────────────────────────────
        self.btn_apply_profile.clicked.connect(self._on_apply_profile)
        self.btn_save.clicked.connect(self._on_save)

        # laduj biezace ustawienia
        self._load_to_ui()

    # ─────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────

    def reload(self) -> None:
        """Przeladuj z dysku."""
        self._settings = load_default_material_settings()
        self._load_to_ui()

    def current_settings(self) -> DefaultMaterialSettings:
        return self._read_from_ui()

    # ─────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────

    def _load_to_ui(self) -> None:
        s = self._settings
        self._building = True
        try:
            self.le_carcass_mat.setText(s.carcass_material_key)
            self.sp_carcass_thick.setValue(s.carcass_thickness_mm)
            self.le_front_mat.setText(s.front_material_key)
            self.sp_front_thick.setValue(s.front_thickness_mm)
            self.le_shelf_mat.setText(s.shelf_material_key)
            self.sp_shelf_thick.setValue(s.shelf_thickness_mm)
            self.le_back_mat.setText(s.back_material_key)
            self.sp_back_thick.setValue(s.back_thickness_mm)
            self.le_carcass_eb.setText(s.carcass_edgeband_key)
            self.le_front_eb.setText(s.front_edgeband_key)
            self.sp_leg_height.setValue(s.default_leg_height_mm)
            # joint type
            for i in range(self.cb_joint.count()):
                if self.cb_joint.itemData(i) == s.default_carcass_joint:
                    self.cb_joint.setCurrentIndex(i)
                    break
            # profil
            for i in range(self.cb_profile.count()):
                if self.cb_profile.itemData(i) == s.material_profile_key:
                    self.cb_profile.setCurrentIndex(i)
                    break
        finally:
            self._building = False

    def _read_from_ui(self) -> DefaultMaterialSettings:
        return DefaultMaterialSettings(
            carcass_material_key=self.le_carcass_mat.text().strip(),
            carcass_thickness_mm=self.sp_carcass_thick.value(),
            front_material_key=self.le_front_mat.text().strip(),
            front_thickness_mm=self.sp_front_thick.value(),
            shelf_material_key=self.le_shelf_mat.text().strip(),
            shelf_thickness_mm=self.sp_shelf_thick.value(),
            back_material_key=self.le_back_mat.text().strip(),
            back_thickness_mm=self.sp_back_thick.value(),
            carcass_edgeband_key=self.le_carcass_eb.text().strip(),
            front_edgeband_key=self.le_front_eb.text().strip(),
            default_leg_height_mm=self.sp_leg_height.value(),
            default_carcass_joint=self.cb_joint.currentData() or "type1",
            material_profile_key=self.cb_profile.currentData() or "",
        )

    def _on_apply_profile(self) -> None:
        profile_key = self.cb_profile.currentData() or ""
        preset = PROFILE_PRESETS.get(profile_key)
        if not preset:
            self.lbl_status.setText("Brak presetu dla wybranego profilu.")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
            return
        self._building = True
        try:
            self.le_carcass_mat.setText(preset.get("carcass_material_key", ""))
            self.sp_carcass_thick.setValue(preset.get("carcass_thickness_mm", 18.0))
            self.le_front_mat.setText(preset.get("front_material_key", ""))
            self.sp_front_thick.setValue(preset.get("front_thickness_mm", 18.0))
            self.le_shelf_mat.setText(preset.get("shelf_material_key", ""))
            self.sp_shelf_thick.setValue(preset.get("shelf_thickness_mm", 18.0))
            self.le_back_mat.setText(preset.get("back_material_key", "hdf"))
            self.sp_back_thick.setValue(preset.get("back_thickness_mm", 3.0))
        finally:
            self._building = False
        self.lbl_status.setText(f"Zaladowano profil: {self.cb_profile.currentText()}")
        self.lbl_status.setStyleSheet("color: #3b82f6; font-size: 11px;")

    def _on_save(self) -> None:
        s = self._read_from_ui()
        save_default_material_settings(s)
        self._settings = s
        self.lbl_status.setText("Zapisano ustawienia materialow.")
        self.lbl_status.setStyleSheet("color: #22c55e; font-size: 11px;")
        self.sig_saved.emit()


def _editable_line(default_text: str) -> "QLineEditCompat":
    from PyQt6.QtWidgets import QLineEdit
    le = QLineEdit()
    le.setText(default_text)
    le.setFixedHeight(26)
    return le
