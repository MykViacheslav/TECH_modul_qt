from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import (
    DrawingSettings,
    load_drawing_settings,
    load_ui_font_scale,
    load_ui_theme_settings,
    save_drawing_settings,
    save_ui_font_scale,
    save_ui_theme_settings,
)
from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock
from src.tabs.rysunek.default_materials_block import DefaultMaterialsBlock
from src.widgets.network_settings import NetworkSettingsWidget


class TabRysunek(QWidget):
    """
    Samodzielna zakladka / panel ustawien.
    
    Zawiera:
    - Ustawienia rysunku
    - Motyw UI
    - Ustawienia sieci (praca zespołowa)
    """

    sig_settings_saved = pyqtSignal()
    sig_ui_theme_changed = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Use scroll area for all settings
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        scroll.setWidget(content)
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
        
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(12)

        # === USTAWIENIA RYSUNKU ===
        self.lbl_title = QLabel("Ustawienia rysunku")
        self.lbl_title.setObjectName("rysunek_title")
        content_layout.addWidget(self.lbl_title)

        self.draw_settings = DrawingSettingsBlock(self)
        content_layout.addWidget(self.draw_settings)

        # === MOTYW UI ===
        self.theme_panel = self._build_theme_panel()
        content_layout.addWidget(self.theme_panel)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_load = QPushButton("Wczytaj ustawienia")
        self.btn_save = QPushButton("Zapisz ustawienia")
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.lbl_status, 1)

        content_layout.addLayout(btn_row)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator)
        
        # === DOMYSLNE MATERIALY ===
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator2)

        mat_title = QLabel("Domyslne materialy dla nowych modulow")
        mat_title.setObjectName("rysunek_title")
        content_layout.addWidget(mat_title)

        self.default_materials = DefaultMaterialsBlock(self)
        content_layout.addWidget(self.default_materials)

        # === SIEĆ (PRACA ZESPOŁOWA) ===
        network_title = QLabel("Sieć - praca zespołowa")
        network_title.setObjectName("rysunek_title")
        content_layout.addWidget(network_title)
        
        network_info = QLabel(
            "Skonfiguruj połączenie z serwerem, aby pracować na wspólnych danych\n"
            "z 3-4 komputerów w sieci lokalnej."
        )
        network_info.setStyleSheet("color: #666; font-size: 11px;")
        network_info.setWordWrap(True)
        content_layout.addWidget(network_info)
        
        self.network_settings = NetworkSettingsWidget(self)
        content_layout.addWidget(self.network_settings)
        
        content_layout.addStretch(1)

        self.btn_load.clicked.connect(self._load_settings_to_ui)
        self.btn_save.clicked.connect(self._save_ui_to_settings)
        self.btn_apply_theme.clicked.connect(self._apply_theme_from_ui)
        self.draw_settings.sig_changed.connect(self._on_ui_changed)

        self.btn_load.setAccessibleName("settings_load")
        self.btn_save.setAccessibleName("settings_save")
        self.cb_mode.setAccessibleName("theme_mode")
        self.cb_motif.setAccessibleName("theme_motif")
        self.cb_font_scale.setAccessibleName("theme_font_scale")
        self.btn_apply_theme.setAccessibleName("theme_apply")

        self._load_settings_to_ui()

    def _settings_to_dict(self, settings_obj: object) -> dict:
        if settings_obj is None:
            return {}

        if hasattr(settings_obj, "to_dict"):
            try:
                data = settings_obj.to_dict()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        data = getattr(settings_obj, "__dict__", None)
        if isinstance(data, dict):
            return dict(data)

        return {}

    def _on_ui_changed(self) -> None:
        self.lbl_status.setText("Zmodyfikowano")

    def _build_theme_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setStyleSheet(
            "QFrame {"
            "border: 1px solid #d7cfbf;"
            "border-radius: 10px;"
            "background: transparent;"
            "}"
        )
        row = QHBoxLayout(panel)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        lbl_mode = QLabel("Tryb:", panel)
        self.cb_mode = QComboBox(panel)
        self.cb_mode.addItem("Dzienny", "day")
        self.cb_mode.addItem("Nocny", "night")

        lbl_motif = QLabel("Motyw:", panel)
        self.cb_motif = QComboBox(panel)
        self.cb_motif.addItem("Kremowy", "cream")
        self.cb_motif.addItem("Niebieski", "blue")
        self.cb_motif.addItem("Szary", "gray")
        self.cb_motif.addItem("Zielony", "green")
        self.cb_motif.addItem("Kontrastowy", "contrast")

        lbl_font_scale = QLabel("Skala czcionki:", panel)
        self.cb_font_scale = QComboBox(panel)
        self.cb_font_scale.addItem("85%", 0.85)
        self.cb_font_scale.addItem("90%", 0.90)
        self.cb_font_scale.addItem("100%", 1.00)
        self.cb_font_scale.addItem("110%", 1.10)
        self.cb_font_scale.addItem("120%", 1.20)

        self.btn_apply_theme = QPushButton("Zastosuj motyw", panel)

        row.addWidget(lbl_mode, 0)
        row.addWidget(self.cb_mode, 0)
        row.addSpacing(8)
        row.addWidget(lbl_motif, 0)
        row.addWidget(self.cb_motif, 0)
        row.addSpacing(8)
        row.addWidget(lbl_font_scale, 0)
        row.addWidget(self.cb_font_scale, 0)
        row.addStretch(1)
        row.addWidget(self.btn_apply_theme, 0)
        return panel

    def _set_theme_to_ui(self, mode: str, motif: str) -> None:
        mode_index = self.cb_mode.findData(str(mode or "day"))
        if mode_index >= 0:
            self.cb_mode.setCurrentIndex(mode_index)
        motif_index = self.cb_motif.findData(str(motif or "cream"))
        if motif_index >= 0:
            self.cb_motif.setCurrentIndex(motif_index)

    def _theme_from_ui(self) -> tuple[str, str]:
        mode = str(self.cb_mode.currentData() or "day")
        motif = str(self.cb_motif.currentData() or "cream")
        return mode, motif

    def _set_font_scale_to_ui(self, value: float) -> None:
        normalized = max(0.85, min(1.20, float(value)))
        best_idx = 0
        best_diff = 999.0
        for idx in range(self.cb_font_scale.count()):
            item_val = self.cb_font_scale.itemData(idx)
            try:
                diff = abs(float(item_val) - normalized)
            except Exception:
                continue
            if diff < best_diff:
                best_diff = diff
                best_idx = idx
        self.cb_font_scale.setCurrentIndex(best_idx)

    def _font_scale_from_ui(self) -> float:
        raw = self.cb_font_scale.currentData()
        try:
            value = float(raw)
        except Exception:
            value = 1.0
        return max(0.85, min(1.20, value))

    def _apply_theme_from_ui(self) -> None:
        mode, motif = self._theme_from_ui()
        font_scale = self._font_scale_from_ui()
        save_ui_theme_settings(mode, motif)
        save_ui_font_scale(font_scale)
        self.sig_ui_theme_changed.emit(mode, motif)
        self.lbl_status.setText("Zastosowano motyw")

    def _load_settings_to_ui(self) -> None:
        settings_obj = load_drawing_settings()
        data = self._settings_to_dict(settings_obj)
        ui_theme = load_ui_theme_settings()

        self.draw_settings.set_from_settings(data)
        self._set_theme_to_ui(ui_theme.mode, ui_theme.motif)
        self._set_font_scale_to_ui(load_ui_font_scale(default=1.0))
        self.lbl_status.setText("Wczytano ustawienia")

    def _save_ui_to_settings(self) -> None:
        values = self.draw_settings.to_settings()

        settings_obj = DrawingSettings(**values)
        save_drawing_settings(settings_obj)
        mode, motif = self._theme_from_ui()
        font_scale = self._font_scale_from_ui()
        save_ui_theme_settings(mode, motif)
        save_ui_font_scale(font_scale)
        self.sig_ui_theme_changed.emit(mode, motif)

        self.lbl_status.setText("Zapisano ustawienia")
        self.sig_settings_saved.emit()

    def get_values_dict(self) -> dict:
        return self.draw_settings.to_settings()
