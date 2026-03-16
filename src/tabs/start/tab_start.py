from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TabStart(QWidget):
    sig_new_order_requested = pyqtSignal()
    sig_open_quote_requested = pyqtSignal()
    sig_open_calendar_requested = pyqtSignal()
    sig_open_work_time_requested = pyqtSignal()
    sig_open_clients_requested = pyqtSignal()
    sig_new_wall_requested = pyqtSignal()
    sig_new_assembly_requested = pyqtSignal()
    sig_new_module_requested = pyqtSignal()
    sig_open_bazy_requested = pyqtSignal()
    sig_open_settings_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        hero = QFrame(self)
        hero.setStyleSheet(
            "QFrame {"
            "border: 1px solid #ddd2bf;"
            "border-radius: 22px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fffdf9, stop:1 #f4ecdf);"
            "}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(18)

        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(10)

        title = QLabel("START")
        title.setStyleSheet("font-size: 28px; font-weight: 900; letter-spacing: 0.8px; color:#10233f;")
        hero_copy.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Zacznij od nowego zamowienia, a potem przechodz krok po kroku przez klienta, sciane, komplet i modul."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #556172; font-size: 14px;")
        hero_copy.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        pitch = QLabel(
            "Ta aplikacja ma prowadzic firme od szkicu i wyceny, przez komplet i sciane, az do planu pracy, czasu ludzi i finalnej oferty dla klienta."
        )
        pitch.setWordWrap(True)
        pitch.setStyleSheet("color:#324153; font-size:14px; line-height:1.35;")
        hero_copy.addWidget(pitch, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_new_order = self._make_card(
            "Nowe zamowienie",
            "Pierwszy krok pracy. Otwiera zamowienie z klientem, pracownikiem, oferta i podpieciem do dalszych etapow.",
            primary=True,
        )
        self.btn_new_order.setMinimumWidth(360)
        hero_copy.addWidget(self.btn_new_order, 0, Qt.AlignmentFlag.AlignLeft)
        hero_copy.addStretch(1)
        hero_layout.addLayout(hero_copy, 3)

        hero_side = QGridLayout()
        hero_side.setHorizontalSpacing(12)
        hero_side.setVerticalSpacing(12)
        hero_side.addWidget(
            self._make_focus_card("Klient", "Szybkie zamowienie, zalaczniki architekta, pozycje do wyceny."),
            0,
            0,
        )
        hero_side.addWidget(
            self._make_focus_card("Finanse", "Wycena, rata klienta, koszt techniczny i cena handlowa."),
            0,
            1,
        )
        hero_side.addWidget(
            self._make_focus_card("Pracownicy", "Kalendarz, czas pracy, etapy, obciazenie i statusy."),
            1,
            0,
        )
        hero_side.addWidget(
            self._make_focus_card("Projekt", "Sciana, Komplet i Modul jako szybki konfigurator do pracy."),
            1,
            1,
        )
        hero_layout.addLayout(hero_side, 2)
        root.addWidget(hero)

        section = QLabel("Obszary pracy")
        section.setStyleSheet("font-weight: 800; color: #243243; font-size:15px;")
        root.addWidget(section, 0, Qt.AlignmentFlag.AlignLeft)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.btn_quote = self._make_card("Wycena", "Policz cene, koszty i oferte klienta.", primary=False)
        self.btn_clients = self._make_card("Klienci", "Przejdz do bazy klientow.", primary=False)
        self.btn_calendar = self._make_card("Kalendarz", "Sprawdz statusy i terminy projektow.", primary=False)
        self.btn_work_time = self._make_card("Czas pracy", "Godziny, dniowki, dodatki i koszt pracy.", primary=False)
        self.btn_sciana = self._make_card("Sciana", "Zacznij nowa sciane lub pomiar.", primary=False)
        self.btn_komplet = self._make_card("Komplet", "Zbuduj komplet modulow.", primary=False)
        self.btn_modul = self._make_card("Modul", "Edytuj lub zbuduj pojedynczy modul.", primary=False)
        self.btn_bazy = self._make_card("Bazy i magazyn", "Moduly, materialy, pracownicy i przyszly magazyn.", primary=False)
        self.btn_settings = self._make_card("Ustawienia", "Przejdz do ustawien rysunku i programu.", primary=False)

        grid.addWidget(self.btn_quote, 0, 0)
        grid.addWidget(self.btn_calendar, 0, 1)
        grid.addWidget(self.btn_work_time, 1, 0)
        grid.addWidget(self.btn_clients, 1, 1)
        grid.addWidget(self.btn_sciana, 2, 0)
        grid.addWidget(self.btn_komplet, 2, 1)
        grid.addWidget(self.btn_modul, 3, 0)
        grid.addWidget(self.btn_bazy, 3, 1)
        grid.addWidget(self.btn_settings, 4, 0)

        root.addLayout(grid)

        footer = QFrame(self)
        footer.setStyleSheet(
            "QFrame {"
            "border: 1px solid #e2d8c9;"
            "border-radius: 18px;"
            "background: #fffdfa;"
            "}"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 14, 18, 14)
        footer_layout.setSpacing(18)
        footer_layout.addWidget(
            self._make_plain_note(
                "Przeplyw",
                "Szkic od architekta -> szybka wycena -> komplet/sciana -> oferta -> kalendarz i praca.",
            ),
            1,
        )
        footer_layout.addWidget(
            self._make_plain_note(
                "Cel",
                "Nie kolejny surowy panel techniczny, tylko narzedzie do prowadzenia projektu i firmy.",
            ),
            1,
        )
        root.addWidget(footer)
        root.addStretch(1)

        self.btn_new_order.clicked.connect(self.sig_new_order_requested.emit)
        self.btn_quote.clicked.connect(self.sig_open_quote_requested.emit)
        self.btn_clients.clicked.connect(self.sig_open_clients_requested.emit)
        self.btn_calendar.clicked.connect(self.sig_open_calendar_requested.emit)
        self.btn_work_time.clicked.connect(self.sig_open_work_time_requested.emit)
        self.btn_sciana.clicked.connect(self.sig_new_wall_requested.emit)
        self.btn_komplet.clicked.connect(self.sig_new_assembly_requested.emit)
        self.btn_modul.clicked.connect(self.sig_new_module_requested.emit)
        self.btn_bazy.clicked.connect(self.sig_open_bazy_requested.emit)
        self.btn_settings.clicked.connect(self.sig_open_settings_requested.emit)

    def _make_card(self, title: str, description: str, primary: bool) -> QPushButton:
        btn = QPushButton(f"{title}\n{description}", self)
        btn.setMinimumSize(280, 112 if primary else 98)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            (
                "QPushButton {"
                "text-align: left;"
                "padding: 16px 18px;"
                "border-radius: 18px;"
                "border: 1px solid #ddd2bf;"
                "background: #fffdfa;"
                "color: #1f2d3d;"
                "font-size: 14px;"
                "font-weight: 700;"
                "}"
                "QPushButton:hover {"
                "border-color: #bda583;"
                "background: #f7efe3;"
                "}"
            )
            if not primary
            else (
                "QPushButton {"
                "text-align: left;"
                "padding: 18px 20px;"
                "border-radius: 20px;"
                "border: 1px solid #c6ac86;"
                "background: #fff5e6;"
                "color: #10233f;"
                "font-size: 15px;"
                "font-weight: 800;"
                "}"
                "QPushButton:hover {"
                "background: #fbe7c6;"
                "border-color: #af8a53;"
                "}"
            )
        )
        return btn

    def _make_focus_card(self, title: str, description: str) -> QFrame:
        card = QFrame(self)
        card.setMinimumWidth(220)
        card.setStyleSheet(
            "QFrame {"
            "border: 1px solid rgba(168, 143, 106, 0.28);"
            "border-radius: 16px;"
            "background: rgba(255, 255, 255, 0.78);"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        label = QLabel(title, card)
        label.setStyleSheet("font-size: 15px; font-weight: 800; color:#10233f;")
        layout.addWidget(label)
        text = QLabel(description, card)
        text.setWordWrap(True)
        text.setStyleSheet("color:#556172; line-height:1.35;")
        layout.addWidget(text)
        return card

    def _make_plain_note(self, title: str, description: str) -> QFrame:
        card = QFrame(self)
        card.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(title, card)
        label.setStyleSheet("font-weight: 800; color:#243243;")
        text = QLabel(description, card)
        text.setWordWrap(True)
        text.setStyleSheet("color:#5d6a79;")
        layout.addWidget(label)
        layout.addWidget(text)
        return card
