from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout, QWidget
from src.app.app_settings import load_ui_theme_settings


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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = load_ui_theme_settings()
        self._is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        self._colors = {
            "title": "#e8efff" if self._is_tech else "#14263d",
            "subtitle": "#9bb2d3" if self._is_tech else "#5f6c7c",
            "section": "#cbdaf3" if self._is_tech else "#203047",
            "panel_border": "#2a4368" if self._is_tech else "#e6ebf1",
            "panel_bg": "#111b30" if self._is_tech else "#ffffff",
            "panel_title": "#dbe9ff" if self._is_tech else "#203047",
            "primary_border": "#3f64a1" if self._is_tech else "#d7dfeb",
            "primary_bg": "#1a2b4a" if self._is_tech else "#f7f9fc",
            "primary_bg_hover": "#24406f" if self._is_tech else "#eef3f9",
            "primary_text": "#eaf2ff" if self._is_tech else "#132640",
            "secondary_border": "#2f4f80" if self._is_tech else "#e1e7ef",
            "secondary_bg": "#13233f" if self._is_tech else "#ffffff",
            "secondary_bg_hover": "#1d335a" if self._is_tech else "#f7f9fc",
            "secondary_text": "#dce9ff" if self._is_tech else "#203047",
            "card_border": "#2e4b78" if self._is_tech else "#e3e9f1",
            "card_bg": "#15253f" if self._is_tech else "#fbfcfe",
            "badge_bg": "#274b82" if self._is_tech else "#dce8f6",
            "badge_text": "#f2f7ff" if self._is_tech else "#173355",
            "body_text": "#9cb1cf" if self._is_tech else "#667484",
            "info_title": "#dbe9ff" if self._is_tech else "#243243",
            "info_text": "#9bb0cd" if self._is_tech else "#5d6a79",
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        title = QLabel("PANEL STARTOWY")
        title.setStyleSheet(f"font-size: 26px; font-weight: 900; color:{self._colors['title']};")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Tu zaczynasz prace. Najpierw zakladasz zamowienie, potem przechodzisz dalej.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{self._colors['subtitle']}; font-size:14px;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        start_panel = self._make_panel()
        start_layout = QVBoxLayout(start_panel)
        start_layout.setContentsMargins(18, 18, 18, 18)
        start_layout.setSpacing(12)
        start_layout.addWidget(self._make_panel_title("Szybki start"))

        self.btn_new_order = self._make_primary_button("Nowe zamowienie", "Klient, pozycje do wyceny i start projektu.")
        self.btn_quote = self._make_primary_button("Wycena", "Koszt techniczny, cena handlowa i oferta.")
        self.btn_calendar = self._make_primary_button("Kalendarz", "Statusy, terminy i prowadzenie pracy.")
        self.btn_work_time = self._make_secondary_button("Czas pracy", "Godziny, dniowki i koszt ludzi.")
        self.btn_time_kiosk = self._make_secondary_button("Tablet QR", "Szybkie odbicia czasu pracy na tablecie.")

        start_actions = QVBoxLayout()
        start_actions.setContentsMargins(0, 0, 0, 0)
        start_actions.setSpacing(8)
        start_actions.addWidget(self.btn_new_order, 0)
        start_actions.addWidget(self.btn_quote, 0)
        start_actions.addWidget(self.btn_calendar, 0)
        start_actions.addWidget(self.btn_work_time, 0)
        start_actions.addWidget(self.btn_time_kiosk, 0)
        start_actions.addStretch(0)
        start_layout.addLayout(start_actions)
        root.addWidget(start_panel)

        section = QLabel("Pozostale narzedzia")
        section.setStyleSheet(f"font-size: 15px; font-weight: 800; color:{self._colors['section']};")
        root.addWidget(section, 0, Qt.AlignmentFlag.AlignLeft)

        tools_panel = self._make_panel()
        tools_layout = QVBoxLayout(tools_panel)
        tools_layout.setContentsMargins(18, 18, 18, 18)
        tools_layout.setSpacing(8)

        self.btn_clients = self._make_secondary_button("Klienci", "Baza klientow.")
        self.btn_sciana = self._make_secondary_button("Sciana", "Nowa sciana lub pomiar.")
        self.btn_komplet = self._make_secondary_button("Komplet", "Uklad modulow.")
        self.btn_modul = self._make_secondary_button("Modul", "Pojedynczy modul.")
        self.btn_bazy = self._make_secondary_button("Bazy", "Materialy, pracownicy i dane.")
        self.btn_settings = self._make_secondary_button("Ustawienia", "Rysunek i program.")

        self._set_button_icon(self.btn_new_order, QStyle.StandardPixmap.SP_FileIcon)
        self._set_button_icon(self.btn_quote, QStyle.StandardPixmap.SP_DialogApplyButton)
        self._set_button_icon(self.btn_calendar, QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self._set_button_icon(self.btn_work_time, QStyle.StandardPixmap.SP_BrowserReload)
        self._set_button_icon(self.btn_time_kiosk, QStyle.StandardPixmap.SP_DialogYesButton)
        self._set_button_icon(self.btn_clients, QStyle.StandardPixmap.SP_DirHomeIcon)
        self._set_button_icon(self.btn_sciana, QStyle.StandardPixmap.SP_FileDialogContentsView)
        self._set_button_icon(self.btn_komplet, QStyle.StandardPixmap.SP_DirOpenIcon)
        self._set_button_icon(self.btn_modul, QStyle.StandardPixmap.SP_FileDialogListView)
        self._set_button_icon(self.btn_bazy, QStyle.StandardPixmap.SP_DriveHDIcon)
        self._set_button_icon(self.btn_settings, QStyle.StandardPixmap.SP_FileDialogInfoView)

        tools_layout.addWidget(self.btn_clients, 0)
        tools_layout.addWidget(self.btn_sciana, 0)
        tools_layout.addWidget(self.btn_komplet, 0)
        tools_layout.addWidget(self.btn_modul, 0)
        tools_layout.addWidget(self.btn_bazy, 0)
        tools_layout.addWidget(self.btn_settings, 0)
        root.addWidget(tools_panel)

        root.addStretch(1)

        self.btn_new_order.clicked.connect(self.sig_new_order_requested.emit)
        self.btn_quote.clicked.connect(self.sig_open_quote_requested.emit)
        self.btn_clients.clicked.connect(self.sig_open_clients_requested.emit)
        self.btn_calendar.clicked.connect(self.sig_open_calendar_requested.emit)
        self.btn_work_time.clicked.connect(self.sig_open_work_time_requested.emit)
        self.btn_time_kiosk.clicked.connect(self.sig_open_time_kiosk_requested.emit)
        self.btn_sciana.clicked.connect(self.sig_new_wall_requested.emit)
        self.btn_komplet.clicked.connect(self.sig_new_assembly_requested.emit)
        self.btn_modul.clicked.connect(self.sig_new_module_requested.emit)
        self.btn_bazy.clicked.connect(self.sig_open_bazy_requested.emit)
        self.btn_settings.clicked.connect(self.sig_open_settings_requested.emit)

    def _make_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setStyleSheet(
            "QFrame {"
            f"border: 1px solid {self._colors['panel_border']};"
            "border-radius: 18px;"
            f"background: {self._colors['panel_bg']};"
            "}"
        )
        return panel

    def _make_panel_title(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setStyleSheet(f"font-size: 15px; font-weight: 800; color:{self._colors['panel_title']};")
        return label

    def _make_primary_button(self, title: str, description: str) -> QPushButton:
        btn = QPushButton(f"  {title}", self)
        btn.setToolTip(f"{title}\n{description}")
        btn.setAccessibleName(title)
        btn.setMinimumHeight(48)
        btn.setMaximumHeight(48)
        btn.setMinimumWidth(260)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "text-align: left;"
            "padding: 0 12px;"
            "border-radius: 12px;"
            f"border: 1px solid {self._colors['primary_border']};"
            f"background: {self._colors['primary_bg']};"
            f"color: {self._colors['primary_text']};"
            "font-size: 14px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover {"
            f"border-color: {self._colors['primary_border']};"
            f"background: {self._colors['primary_bg_hover']};"
            "}"
        )
        btn.setIconSize(QSize(22, 22))
        return btn

    def _make_secondary_button(self, title: str, description: str) -> QPushButton:
        btn = QPushButton(f"  {title}", self)
        btn.setToolTip(f"{title}\n{description}")
        btn.setAccessibleName(title)
        btn.setMinimumHeight(44)
        btn.setMaximumHeight(44)
        btn.setMinimumWidth(260)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "text-align: left;"
            "padding: 0 12px;"
            "border-radius: 12px;"
            f"border: 1px solid {self._colors['secondary_border']};"
            f"background: {self._colors['secondary_bg']};"
            f"color: {self._colors['secondary_text']};"
            "font-size: 13px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover {"
            f"border-color: {self._colors['secondary_border']};"
            f"background: {self._colors['secondary_bg_hover']};"
            "}"
        )
        btn.setIconSize(QSize(20, 20))
        return btn

    def _set_button_icon(self, button: QPushButton, icon_kind: QStyle.StandardPixmap) -> None:
        button.setIcon(self.style().standardIcon(icon_kind))

    def _make_step_card(self, number: str, title: str, description: str) -> QFrame:
        card = QFrame(self)
        card.setStyleSheet(
            "QFrame {"
            f"border: 1px solid {self._colors['card_border']};"
            "border-radius: 16px;"
            f"background: {self._colors['card_bg']};"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        badge = QLabel(number, card)
        badge.setFixedWidth(28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background:{self._colors['badge_bg']};"
            f"color:{self._colors['badge_text']};"
            "border-radius: 14px;"
            "font-weight: 800;"
            "padding: 4px 0;"
        )
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        label = QLabel(title, card)
        label.setStyleSheet(f"font-size: 15px; font-weight: 800; color:{self._colors['panel_title']};")
        layout.addWidget(label)
        text = QLabel(description, card)
        text.setWordWrap(True)
        text.setStyleSheet(f"color:{self._colors['body_text']};")
        layout.addWidget(text)
        return card

    def _make_info_card(self, title: str, description: str) -> QFrame:
        card = QFrame(self)
        card.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(title, card)
        label.setStyleSheet(f"font-weight: 800; color:{self._colors['info_title']};")
        text = QLabel(description, card)
        text.setWordWrap(True)
        text.setStyleSheet(f"color:{self._colors['info_text']};")
        layout.addWidget(label)
        layout.addWidget(text)
        return card
