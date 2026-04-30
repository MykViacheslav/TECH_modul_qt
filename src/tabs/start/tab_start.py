from __future__ import annotations
import traceback
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QStyle, QVBoxLayout, QWidget, QGridLayout, QScrollArea,
    QGraphicsDropShadowEffect,
)


class ActionCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title: str, description: str, icon_kind: QStyle.StandardPixmap, parent=None):
        super().__init__(parent)
        self.setProperty("uiCard", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(280, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        self.setStyleSheet("""
            ActionCard {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            ActionCard:hover {
                border-color: #3b82f6;
                background: #f8fafc;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        header = QHBoxLayout()
        icon_label = QLabel(self._get_emoji_for_kind(icon_kind))
        icon_label.setStyleSheet("font-size: 28px;")
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 19px; font-weight: 800; color: #0f172a; margin-left: 8px;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; color: #475569; line-height: 1.4;")
        layout.addWidget(desc_label)

        layout.addStretch()

    def _get_emoji_for_kind(self, kind: QStyle.StandardPixmap) -> str:
        mapping = {
            QStyle.StandardPixmap.SP_FileIcon: "📄",
            QStyle.StandardPixmap.SP_DialogApplyButton: "🏷️",
            QStyle.StandardPixmap.SP_FileDialogDetailedView: "📅",
            QStyle.StandardPixmap.SP_DriveHDIcon: "🗄️",
        }
        return mapping.get(kind, "✨")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


_ONBOARDING_STEPS = [
    "Dodaj pierwszego klienta",
    "Utwórz zamówienie",
    "Otwórz wycenę",
    "Skonfiguruj materiały",
    "Zatwierdź i wyślij ofertę",
]


class TabStart(QWidget):
    sig_new_order_requested = pyqtSignal()
    sig_open_quote_requested = pyqtSignal()
    sig_open_calendar_requested = pyqtSignal()
    sig_open_work_time_requested = pyqtSignal()
    sig_open_time_kiosk_requested = pyqtSignal()
    sig_open_clients_requested = pyqtSignal()
    sig_new_wall_requested = pyqtSignal()
    sig_new_assembly_requested = pyqtSignal()
    sig_new_module_requested = pyqtSignal()
    sig_open_bazy_requested = pyqtSignal()
    sig_open_settings_requested = pyqtSignal()
    sig_instruction_mode_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer_root = QVBoxLayout(self)
        outer_root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content_widget)
        root.setContentsMargins(40, 60, 40, 40)
        root.setSpacing(40)
        root.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        container = QWidget()
        container.setMaximumWidth(1100)
        root.addWidget(container)

        c_lay = QVBoxLayout(container)
        c_lay.setSpacing(40)

        # --- HEADER ---
        header_layout = QVBoxLayout()
        welcome = QLabel("SYSTEM OPERACYJNY GIBLAB")
        welcome.setStyleSheet("font-size: 13px; font-weight: 900; color: #2563eb; letter-spacing: 3px;")
        header_layout.addWidget(welcome)

        title = QLabel("Twoje Centrum Dowodzenia")
        title.setStyleSheet("font-size: 42px; font-weight: 900; color: #0f172a; margin-top: 4px;")
        header_layout.addWidget(title)
        c_lay.addLayout(header_layout)

        # --- ACTION CARDS ---
        grid = QGridLayout()
        grid.setSpacing(20)

        self.card_new_order = ActionCard(
            "Nowe Zamówienie", "Rozpocznij proces od klienta i wyceny.",
            QStyle.StandardPixmap.SP_FileIcon,
        )
        self.card_quote = ActionCard(
            "Centrum Wycen", "Zarządzaj kosztami i ofertami handlowymi.",
            QStyle.StandardPixmap.SP_DialogApplyButton,
        )
        self.card_calendar = ActionCard(
            "Harmonogram", "Sprawdź terminy montaży i statusy prac.",
            QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        self.card_bazy = ActionCard(
            "Bazy i Zasoby", "Zarządzaj materiałami, okuciami i ludźmi.",
            QStyle.StandardPixmap.SP_DriveHDIcon,
        )

        grid.addWidget(self.card_new_order, 0, 0)
        grid.addWidget(self.card_quote, 0, 1)
        grid.addWidget(self.card_calendar, 1, 0)
        grid.addWidget(self.card_bazy, 1, 1)
        c_lay.addLayout(grid)

        # --- TOOL BUTTONS ---
        tools_label = QLabel("NARZĘDZIA EKSPERCKIE")
        tools_label.setStyleSheet("font-size: 13px; font-weight: 900; color: #94a3b8; letter-spacing: 2px; margin-top: 20px;")
        c_lay.addWidget(tools_label)

        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(20)

        self.btn_sciana = self._make_tool_btn("🧱 System Ścian", QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.btn_komplet = self._make_tool_btn("📦 Zestawy", QStyle.StandardPixmap.SP_DirOpenIcon)
        self.btn_modul = self._make_tool_btn("📐 Konstruktor", QStyle.StandardPixmap.SP_FileDialogListView)
        self.btn_settings = self._make_tool_btn("⚙️ System", QStyle.StandardPixmap.SP_FileDialogInfoView)

        tools_layout.addWidget(self.btn_sciana)
        tools_layout.addWidget(self.btn_komplet)
        tools_layout.addWidget(self.btn_modul)
        tools_layout.addWidget(self.btn_settings)
        tools_layout.addStretch()
        c_lay.addLayout(tools_layout)

        # --- ONBOARDING ---
        onboarding_label = QLabel("ONBOARDING")
        onboarding_label.setStyleSheet("font-size: 13px; font-weight: 900; color: #94a3b8; letter-spacing: 2px;")
        c_lay.addWidget(onboarding_label)

        ob_status_row = QHBoxLayout()
        self.lab_onboarding_global_status = QLabel("nieaktywny")
        self.lab_onboarding_progress = QLabel("0/5")
        ob_status_row.addWidget(self.lab_onboarding_global_status)
        ob_status_row.addStretch()
        ob_status_row.addWidget(self.lab_onboarding_progress)
        c_lay.addLayout(ob_status_row)

        self._onboarding_checks: list[QCheckBox] = []
        for step in _ONBOARDING_STEPS:
            cb = QCheckBox(step)
            cb.stateChanged.connect(self._update_onboarding_progress)
            self._onboarding_checks.append(cb)
            c_lay.addWidget(cb)

        ob_btn_row = QHBoxLayout()
        self.btn_onboarding_start = QPushButton("Rozpocznij")
        self.btn_onboarding_next = QPushButton("Dalej")
        self.btn_onboarding_stop = QPushButton("Zakończ")
        self.btn_onboarding_next.setEnabled(False)
        self.btn_onboarding_stop.setEnabled(False)
        ob_btn_row.addWidget(self.btn_onboarding_start)
        ob_btn_row.addWidget(self.btn_onboarding_next)
        ob_btn_row.addWidget(self.btn_onboarding_stop)
        ob_btn_row.addStretch()
        c_lay.addLayout(ob_btn_row)

        # --- INSTRUCTION LIBRARY ---
        instr_label = QLabel("BIBLIOTEKA INSTRUKCJI")
        instr_label.setStyleSheet("font-size: 13px; font-weight: 900; color: #94a3b8; letter-spacing: 2px;")
        c_lay.addWidget(instr_label)

        instr_controls = QHBoxLayout()
        self.btn_instruction_mode = QPushButton("Tryb instrukcji: WYLACZONY")
        self.btn_instruction_mode.setCheckable(True)
        self.btn_instruction_mode.toggled.connect(self._on_instruction_mode_toggled)

        self.cb_instruction_filter = QComboBox()
        self._populate_instruction_filter()
        self.cb_instruction_filter.currentIndexChanged.connect(self._on_filter_changed)

        instr_controls.addWidget(self.btn_instruction_mode)
        instr_controls.addWidget(self.cb_instruction_filter)
        instr_controls.addStretch()
        c_lay.addLayout(instr_controls)

        self.lst_instruction_cards = QListWidget()
        self._load_instruction_cards()
        c_lay.addWidget(self.lst_instruction_cards)

        root.addStretch()

        scroll.setWidget(content_widget)
        outer_root.addWidget(scroll)

        # Signals
        self.card_new_order.clicked.connect(self.sig_new_order_requested.emit)
        self.card_quote.clicked.connect(self.sig_open_quote_requested.emit)
        self.card_calendar.clicked.connect(self.sig_open_calendar_requested.emit)
        self.card_bazy.clicked.connect(self.sig_open_bazy_requested.emit)

        self.btn_sciana.clicked.connect(self.sig_new_wall_requested.emit)
        self.btn_komplet.clicked.connect(self.sig_new_assembly_requested.emit)
        self.btn_modul.clicked.connect(self.sig_new_module_requested.emit)
        self.btn_settings.clicked.connect(self.sig_open_settings_requested.emit)

    # ------------------------------------------------------------------
    # Instruction library
    # ------------------------------------------------------------------

    def _populate_instruction_filter(self) -> None:
        self.cb_instruction_filter.clear()
        self.cb_instruction_filter.addItem("Wszystkie", None)
        try:
            from src.storage.instruction_store_json import InstructionStoreJson
            categories = sorted(set(c.category for c in InstructionStoreJson().list_cards()))
            for cat in categories:
                self.cb_instruction_filter.addItem(cat.upper(), cat)
        except Exception:
            traceback.print_exc()

    def _load_instruction_cards(self, category: str = "") -> None:
        self.lst_instruction_cards.clear()
        try:
            from src.storage.instruction_store_json import InstructionStoreJson
            cards = InstructionStoreJson().list_cards(category=category)
            for card in cards:
                self.lst_instruction_cards.addItem(f"[{card.category.upper()}] {card.title}")
        except Exception:
            traceback.print_exc()

    def _on_filter_changed(self) -> None:
        cat = self.cb_instruction_filter.currentData() or ""
        self._load_instruction_cards(category=cat)

    def _on_instruction_mode_toggled(self, checked: bool) -> None:
        self.btn_instruction_mode.setText(
            "Tryb instrukcji: WLACZONY" if checked else "Tryb instrukcji: WYLACZONY"
        )
        self.sig_instruction_mode_toggled.emit(checked)

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    def _update_onboarding_progress(self) -> None:
        done = sum(1 for cb in self._onboarding_checks if cb.isChecked())
        total = len(self._onboarding_checks)
        self.lab_onboarding_progress.setText(f"{done}/{total}")

    def set_onboarding_status(
        self,
        active: bool,
        current_step: int = 0,
        total_steps: int = 0,
        current_title: str = "",
    ) -> None:
        if active:
            self.lab_onboarding_global_status.setText(
                f"Krok {current_step}/{total_steps}: {current_title}"
            )
            self.btn_onboarding_start.setEnabled(False)
            self.btn_onboarding_next.setEnabled(True)
            self.btn_onboarding_stop.setEnabled(True)
        else:
            self.lab_onboarding_global_status.setText("nieaktywny")
            self.btn_onboarding_start.setEnabled(True)
            self.btn_onboarding_next.setEnabled(False)
            self.btn_onboarding_stop.setEnabled(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_tool_btn(self, text: str, icon_kind: QStyle.StandardPixmap) -> QPushButton:
        btn = QPushButton(text)
        btn.setIcon(self.style().standardIcon(icon_kind))
        btn.setIconSize(QSize(20, 20))
        btn.setMinimumHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                color: #475569;
                font-weight: 640;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.1);
                border-color: #3b82f6;
                color: #f8fafc;
            }
        """)
        return btn
