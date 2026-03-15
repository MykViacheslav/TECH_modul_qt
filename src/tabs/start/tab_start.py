from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TabStart(QWidget):
    sig_new_order_requested = pyqtSignal()
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
        root.setSpacing(18)

        title = QLabel("START")
        title.setStyleSheet("font-size: 24px; font-weight: 800; letter-spacing: 1px;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Zacznij od nowego zamowienia, a potem przechodz krok po kroku przez klienta, sciane, komplet i modul."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #555555; font-size: 13px;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_new_order = self._make_card(
            "Nowe zamowienie",
            "Pierwszy krok pracy. Otwiera osobna karte zamowienia z klientem, pracownikiem i zapisem do baz.",
            primary=True,
        )
        root.addWidget(self.btn_new_order, 0, Qt.AlignmentFlag.AlignLeft)

        section = QLabel("Dalsze kroki")
        section.setStyleSheet("font-weight: 700; color: #333333;")
        root.addWidget(section, 0, Qt.AlignmentFlag.AlignLeft)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.btn_clients = self._make_card("Klienci", "Przejdz do bazy klientow.", primary=False)
        self.btn_sciana = self._make_card("Sciana", "Zacznij nowa sciane lub pomiar.", primary=False)
        self.btn_komplet = self._make_card("Komplet", "Zbuduj komplet modulow.", primary=False)
        self.btn_modul = self._make_card("Modul", "Edytuj lub zbuduj pojedynczy modul.", primary=False)
        self.btn_bazy = self._make_card("Bazy", "Zarzadzaj zapisanymi danymi.", primary=False)
        self.btn_settings = self._make_card("Ustawienia", "Przejdz do ustawien rysunku i programu.", primary=False)

        grid.addWidget(self.btn_clients, 0, 0)
        grid.addWidget(self.btn_sciana, 0, 1)
        grid.addWidget(self.btn_komplet, 1, 0)
        grid.addWidget(self.btn_modul, 1, 1)
        grid.addWidget(self.btn_bazy, 2, 0)
        grid.addWidget(self.btn_settings, 2, 1)

        root.addLayout(grid)
        root.addStretch(1)

        self.btn_new_order.clicked.connect(self.sig_new_order_requested.emit)
        self.btn_clients.clicked.connect(self.sig_open_clients_requested.emit)
        self.btn_sciana.clicked.connect(self.sig_new_wall_requested.emit)
        self.btn_komplet.clicked.connect(self.sig_new_assembly_requested.emit)
        self.btn_modul.clicked.connect(self.sig_new_module_requested.emit)
        self.btn_bazy.clicked.connect(self.sig_open_bazy_requested.emit)
        self.btn_settings.clicked.connect(self.sig_open_settings_requested.emit)

    def _make_card(self, title: str, description: str, primary: bool) -> QPushButton:
        btn = QPushButton(f"{title}\n{description}", self)
        btn.setMinimumSize(260, 110 if primary else 96)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            (
                "QPushButton {"
                "text-align: left;"
                "padding: 16px 18px;"
                "border-radius: 16px;"
                "border: 2px solid #d8e2ec;"
                "background: #ffffff;"
                "color: #1f1f1f;"
                "font-size: 14px;"
                "font-weight: 700;"
                "}"
                "QPushButton:hover {"
                "border-color: #1f6ed4;"
                "background: #f4f8ff;"
                "}"
            )
            if not primary
            else (
                "QPushButton {"
                "text-align: left;"
                "padding: 18px 20px;"
                "border-radius: 18px;"
                "border: 2px solid #1f6ed4;"
                "background: #eaf4ff;"
                "color: #0f2d57;"
                "font-size: 15px;"
                "font-weight: 800;"
                "}"
                "QPushButton:hover {"
                "background: #dcecff;"
                "border-color: #1454a3;"
                "}"
            )
        )
        return btn
