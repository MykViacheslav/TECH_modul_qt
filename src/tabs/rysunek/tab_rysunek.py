from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from src.app.app_settings import DrawingSettings, load_drawing_settings, save_drawing_settings
from src.tabs.rysunek.drawing_settings_block import DrawingSettingsBlock


class TabRysunek(QWidget):
    """
    Samodzielna zakladka / panel ustawien rysunku.

    Na tym etapie:
    - dziala niezaleznie,
    - korzysta z tego samego storage ustawien co dotychczas,
    - po zapisie emituje sygnal do odswiezenia innych zakladek.
    """

    sig_settings_saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.lbl_title = QLabel("Ustawienia rysunku")
        self.lbl_title.setObjectName("rysunek_title")
        root.addWidget(self.lbl_title)

        self.draw_settings = DrawingSettingsBlock(self)
        root.addWidget(self.draw_settings)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_load = QPushButton("Wczytaj ustawienia")
        self.btn_save = QPushButton("Zapisz ustawienia")
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.lbl_status, 1)

        root.addLayout(btn_row)
        root.addStretch(1)

        self.btn_load.clicked.connect(self._load_settings_to_ui)
        self.btn_save.clicked.connect(self._save_ui_to_settings)
        self.draw_settings.sig_changed.connect(self._on_ui_changed)

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

    def _load_settings_to_ui(self) -> None:
        settings_obj = load_drawing_settings()
        data = self._settings_to_dict(settings_obj)

        self.draw_settings.set_from_settings(data)
        self.lbl_status.setText("Wczytano ustawienia")

    def _save_ui_to_settings(self) -> None:
        values = self.draw_settings.to_settings()

        settings_obj = DrawingSettings(**values)
        save_drawing_settings(settings_obj)

        self.lbl_status.setText("Zapisano ustawienia")
        self.sig_settings_saved.emit()

    def get_values_dict(self) -> dict:
        return self.draw_settings.to_settings()