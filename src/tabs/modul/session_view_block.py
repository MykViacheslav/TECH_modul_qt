from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

from src.app.app_settings import load_drawing_settings


class SessionAndViewBlock(QWidget):
    sig_clear_last = pyqtSignal()
    sig_hide_front_changed = pyqtSignal(bool)
    sig_set_current_as_default = pyqtSignal()
    sig_clear_default = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        settings = load_drawing_settings()
        self.chk_hide_front = QCheckBox("Ukryj front na rysunku")
        self.chk_hide_front.setChecked(not bool(getattr(settings, "show_front_part", True)))
        lay.addWidget(self.chk_hide_front)

        self.chk_hide_front.hide()

        self.btn_set_default = QPushButton("Ustaw biezace jako startowe")
        self.btn_set_default.setStyleSheet("padding:6px;")
        lay.addWidget(self.btn_set_default)

        self.btn_clear_default = QPushButton("Usun startowe (wroc do fabrycznych)")
        self.btn_clear_default.setStyleSheet("padding:6px; background:#fff3cd; border:1px solid #d6b36a;")
        lay.addWidget(self.btn_clear_default)

        self.btn_clear = QPushButton("Wyczysc ostatni stan")
        self.btn_clear.setStyleSheet("padding:6px; background:#ffeeee; border:1px solid #cc9999;")
        lay.addWidget(self.btn_clear)

        self.lab_hint = QLabel(
            "- Startowe = uzyte po starcie, gdy nie ma sesji albo po Wyczysc ostatni stan.\n"
            "- Usun startowe kasuje data/default_module.json.\n"
            "- Wyczysc ostatni stan usuwa data/session_last.json (nie dotyka bazy)."
        )
        self.lab_hint.setWordWrap(True)
        self.lab_hint.setStyleSheet("color:#666; font-size:11px;")
        lay.addWidget(self.lab_hint)

        self.lab_hint.hide()

        self.chk_hide_front.stateChanged.connect(
            lambda _s2: self.sig_hide_front_changed.emit(self.chk_hide_front.isChecked())
        )
        self.btn_clear.clicked.connect(self.sig_clear_last.emit)
        self.btn_set_default.clicked.connect(self.sig_set_current_as_default.emit)
        self.btn_clear_default.clicked.connect(self.sig_clear_default.emit)
