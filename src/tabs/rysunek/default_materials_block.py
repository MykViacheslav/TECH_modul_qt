"""
DefaultMaterialsBlock — blok ustawien domyslnych materialow dla nowych modulow.

Pozwala ustawic raz:
- material korpusu (boki, wiencce)
- material frontu
- material polki (puste = jak korpus)
- material plecow
- obrzeza korpusu i frontu
- wysokosc nozek i typ laczenia korpusu

Zapis / odczyt przez load_default_material_settings / save_default_material_settings.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import (
    DefaultMaterialSettings,
    load_default_material_settings,
    save_default_material_settings,
)


# Predefiniowane profile (klucz: opis)
MATERIAL_PROFILES: list[tuple[str, str]] = [
    ("", "-- wlasne ustawienia --"),
    ("kuchnia_biala",   "Kuchnia biala (Plyta biala + HDF)"),
    ("kuchnia_dab",     "Kuchnia dab (Dab sonoma + HDF)"),
    ("lazienka_szara",  "Lazienka szara (Szary mat + HDF)"),
    ("salon_antracyt",  "Salon antracyt (Antracyt + HDF)"),
]

PROFILE_PRESETS: dict[str, dict] = {
    "kuchnia_biala":  dict(carcass="PB18",      front="PB18",       back="HDF2.5", carcass_t=18.0, front_t=18.0, back_t=3.0),
    "kuchnia_dab":    dict(carcass="dab_sonoma", front="dab_sonoma", back="HDF2.5", carcass_t=18.0, front_t=18.0, back_t=3.0),
    "lazienka_szara": dict(carcass="PB18",       front="szary_mat",  back="HDF2.5", carcass_t=18.0, front_t=16.0, back_t=3.0),
    "salon_antracyt": dict(carcass="PB18",       front="antracyt",   back="HDF2.5", carcass_t=18.0, front_t=18.0, back_t=3.0),
}

JOINT_TYPES: list[tuple[str, str]] = [
    ("type1", "Typ 1 — klasyczny (gorno-dolny)"),
    ("type2", "Typ 2 — boki zewnetrzne"),
    ("type3", "Typ 3 — boki wewnetrzne"),
]


def _spin(value: float, mn: float, mx: float, step: float = 1.0) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(mn, mx)
    sb.setSingleStep(step)
    sb.setSuffix(" mm")
    sb.setDecimals(1)
    sb.setValue(value)
    sb.setFixedWidth(90)
    return sb


class _MaterialCombo(QWidget):
    """QComboBox z materialami + fallback LineEdit gdy katalog jest pusty."""

    def __init__(self, label: str, placeholder: str = "", parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.cb = QComboBox()
        self.cb.setEditable(False)
        self.cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.le = QLineEdit()
        self.le.setPlaceholderText(placeholder or label)
        self.le.setFixedHeight(26)

        lay.addWidget(self.cb, 1)
        lay.addWidget(self.le, 1)

        self._catalog_keys: list[str] = []
        self._show_combo(False)

    def populate(self, items: list[tuple[str, str]]) -> None:
        """items: [(key, label), ...]"""
        self.cb.clear()
        self.cb.addItem("-- brak --", "")
        for key, label in items:
            self.cb.addItem(label, key)
        self._catalog_keys = [k for k, _ in items]
        has_items = bool(items)
        self._show_combo(has_items)

    def _show_combo(self, use_combo: bool) -> None:
        self.cb.setVisible(use_combo)
        self.le.setVisible(not use_combo)

    def get_key(self) -> str:
        if self.cb.isVisible():
            return str(self.cb.currentData() or "")
        return self.le.text().strip()

    def set_key(self, key: str) -> None:
        if self.cb.isVisible():
            idx = self.cb.findData(key)
            self.cb.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.le.setText(key)


class DefaultMaterialsBlock(QWidget):
    """Panel ustawien domyslnych materialow i obrze zy dla nowych modulow."""

    sig_saved = pyqtSignal()

    def __init__(self, catalog=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._settings = load_default_material_settings()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ── PROFIL ───────────────────────────────────────────────
        grp_profile = QGroupBox("Profil materialowy (preset)")
        profile_lay = QHBoxLayout(grp_profile)
        self.cb_profile = QComboBox()
        for key, label in MATERIAL_PROFILES:
            self.cb_profile.addItem(label, key)
        self.btn_apply_profile = QPushButton("Zastosuj profil")
        self.btn_apply_profile.setFixedWidth(140)
        self.btn_apply_profile.setToolTip("Autouzupelnia wszystkie pola ponizej")
        profile_lay.addWidget(QLabel("Profil:"))
        profile_lay.addWidget(self.cb_profile, 1)
        profile_lay.addWidget(self.btn_apply_profile)
        root.addWidget(grp_profile)

        # ── MATERIALY ─────────────────────────────────────────────
        grp_mat = QGroupBox("Domyslne materialy")
        form = QFormLayout(grp_mat)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self.mat_carcass = _MaterialCombo("Korpus", "np. PB18")
        self.sp_carcass_t = _spin(18.0, 3.0, 50.0)
        self.mat_front   = _MaterialCombo("Front",  "np. MDF19")
        self.sp_front_t  = _spin(18.0, 3.0, 50.0)
        self.mat_shelf   = _MaterialCombo("Polka",  "puste = jak korpus")
        self.sp_shelf_t  = _spin(18.0, 3.0, 50.0)
        self.mat_back    = _MaterialCombo("Plecy",  "np. HDF2.5")
        self.sp_back_t   = _spin(3.0, 1.0, 18.0)

        def _row(mat_widget, spin_widget) -> QHBoxLayout:
            hl = QHBoxLayout()
            hl.addWidget(mat_widget, 1)
            hl.addWidget(QLabel("Gr.:"))
            hl.addWidget(spin_widget)
            return hl

        form.addRow("Korpus:", _row(self.mat_carcass, self.sp_carcass_t))
        form.addRow("Front:", _row(self.mat_front, self.sp_front_t))
        form.addRow("Polka:", _row(self.mat_shelf, self.sp_shelf_t))
        form.addRow("Plecy:", _row(self.mat_back, self.sp_back_t))
        root.addWidget(grp_mat)

        # ── OBRZEZA ───────────────────────────────────────────────
        grp_eb = QGroupBox("Domyslne obrzeza")
        form_eb = QFormLayout(grp_eb)
        form_eb.setSpacing(6)
        self.eb_carcass = _MaterialCombo("Obrzeze korpusu", "klucz z katalogu")
        self.eb_front   = _MaterialCombo("Obrzeze frontu",  "klucz z katalogu")
        form_eb.addRow("Korpus:", self.eb_carcass)
        form_eb.addRow("Front:", self.eb_front)
        root.addWidget(grp_eb)

        # ── MONTAZ ────────────────────────────────────────────────
        grp_mount = QGroupBox("Montaz i laczenia")
        form_mount = QFormLayout(grp_mount)
        form_mount.setSpacing(6)
        self.sp_leg = _spin(100.0, 0.0, 300.0)
        self.cb_joint = QComboBox()
        for key, label in JOINT_TYPES:
            self.cb_joint.addItem(label, key)
        form_mount.addRow("Wys. nozek:", self.sp_leg)
        form_mount.addRow("Typ laczenia:", self.cb_joint)
        root.addWidget(grp_mount)

        # ── STATUS + ZAPISZ ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz ustawienia materialow")
        self.btn_save.setFixedHeight(32)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size:10px;")
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.lbl_status, 1)
        root.addLayout(btn_row)

        root.addStretch(1)

        # ── SYGNALY ───────────────────────────────────────────────
        self.btn_apply_profile.clicked.connect(self._on_apply_profile)
        self.btn_save.clicked.connect(self._on_save)

        # wypelnij katalog jesli podany
        if catalog is not None:
            self._populate_from_catalog(catalog)

        self._load_to_ui()

    # ─────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────

    def set_catalog(self, catalog) -> None:
        """Podaj CatalogStoreJson — wypelni QComboBox-y materialami i obrze zami."""
        self._catalog = catalog
        self._populate_from_catalog(catalog)
        self._load_to_ui()

    def reload(self) -> None:
        self._settings = load_default_material_settings()
        self._load_to_ui()

    def current_settings(self) -> DefaultMaterialSettings:
        return self._read_from_ui()

    # ─────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────

    def _populate_from_catalog(self, catalog) -> None:
        try:
            mats = [(m.key, f"{m.name_pl} ({m.thickness_mm:g}mm)") for m in (catalog.list_materials() or [])]
            for w in (self.mat_carcass, self.mat_front, self.mat_shelf, self.mat_back):
                w.populate(mats)
        except Exception:
            pass

        try:
            ebs = [(e.key, e.name_pl) for e in (catalog.list_edgebands() or [])]
            for w in (self.eb_carcass, self.eb_front):
                w.populate(ebs)
        except Exception:
            pass

    def _load_to_ui(self) -> None:
        s = self._settings
        self.mat_carcass.set_key(s.carcass_material_key)
        self.sp_carcass_t.setValue(s.carcass_thickness_mm)
        self.mat_front.set_key(s.front_material_key)
        self.sp_front_t.setValue(s.front_thickness_mm)
        self.mat_shelf.set_key(s.shelf_material_key)
        self.sp_shelf_t.setValue(s.shelf_thickness_mm)
        self.mat_back.set_key(s.back_material_key)
        self.sp_back_t.setValue(s.back_thickness_mm)
        self.eb_carcass.set_key(s.carcass_edgeband_key)
        self.eb_front.set_key(s.front_edgeband_key)
        self.sp_leg.setValue(s.default_leg_height_mm)
        for i in range(self.cb_joint.count()):
            if self.cb_joint.itemData(i) == s.default_carcass_joint:
                self.cb_joint.setCurrentIndex(i)
                break
        for i in range(self.cb_profile.count()):
            if self.cb_profile.itemData(i) == s.material_profile_key:
                self.cb_profile.setCurrentIndex(i)
                break

    def _read_from_ui(self) -> DefaultMaterialSettings:
        joint = self.cb_joint.currentData() or "type1"
        profile = self.cb_profile.currentData() or ""
        return DefaultMaterialSettings(
            carcass_material_key=self.mat_carcass.get_key(),
            carcass_thickness_mm=self.sp_carcass_t.value(),
            front_material_key=self.mat_front.get_key(),
            front_thickness_mm=self.sp_front_t.value(),
            shelf_material_key=self.mat_shelf.get_key(),
            shelf_thickness_mm=self.sp_shelf_t.value(),
            back_material_key=self.mat_back.get_key(),
            back_thickness_mm=self.sp_back_t.value(),
            carcass_edgeband_key=self.eb_carcass.get_key(),
            front_edgeband_key=self.eb_front.get_key(),
            default_leg_height_mm=self.sp_leg.value(),
            default_carcass_joint=joint,
            material_profile_key=profile,
        )

    def _on_apply_profile(self) -> None:
        key = self.cb_profile.currentData() or ""
        preset = PROFILE_PRESETS.get(key)
        if not preset:
            self._set_status("Brak presetu dla tego profilu.", ok=False)
            return
        self.mat_carcass.set_key(preset.get("carcass", ""))
        self.sp_carcass_t.setValue(float(preset.get("carcass_t", 18.0)))
        self.mat_front.set_key(preset.get("front", ""))
        self.sp_front_t.setValue(float(preset.get("front_t", 18.0)))
        self.mat_back.set_key(preset.get("back", ""))
        self.sp_back_t.setValue(float(preset.get("back_t", 3.0)))
        self._set_status(f"Zaladowano: {self.cb_profile.currentText()}", ok=True)

    def _on_save(self) -> None:
        s = self._read_from_ui()
        save_default_material_settings(s)
        self._settings = s
        self._set_status("Zapisano.", ok=True)
        self.sig_saved.emit()

    def _set_status(self, msg: str, ok: bool = True) -> None:
        color = "#22c55e" if ok else "#f59e0b"
        self.lbl_status.setStyleSheet(f"font-size:10px; color:{color};")
        self.lbl_status.setText(msg)
