from __future__ import annotations

import socket

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.widgets.qr_utils import qr_pixmap_from_text


class TabQrTelefon(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pack_scanner_url = ""
        self._time_kiosk_url = ""
        self._measure_mobile_url = ""
        self._pack_qr_label: QLabel | None = None
        self._time_qr_label: QLabel | None = None
        self._measure_qr_label: QLabel | None = None
        self._pack_url_label: QLabel | None = None
        self._time_url_label: QLabel | None = None
        self._measure_url_label: QLabel | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("QR TELEFON", self)
        title.setStyleSheet("font-size:24px; font-weight:900; color:#122033;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Podglad ekranow mobilnych: formatki, godziny pracy i pomiary ze zdjecia.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#556277; font-size:13px;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        host_row = QHBoxLayout()
        host_row.setSpacing(8)
        host_row.addWidget(QLabel("Adres serwera:", self), 0)
        self.ed_base_url = QLineEdit(self)
        self.ed_base_url.setPlaceholderText("http://192.168.1.100:8000")
        self.ed_base_url.setText(self._guess_phone_base_url())
        self.ed_base_url.setMinimumHeight(36)
        host_row.addWidget(self.ed_base_url, 1)
        btn_apply = QPushButton("Odswiez QR", self)
        btn_apply.setMinimumHeight(36)
        btn_apply.clicked.connect(self._refresh_urls_from_input)
        host_row.addWidget(btn_apply, 0)
        root.addLayout(host_row)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        cards.addWidget(
            self._build_card(
                title="QR do formatek",
                subtitle="Skaner paczek / formatek",
                accent="#0f766e",
                open_text="Otworz skaner formatek",
                kind="pack",
            ),
            0,
            0,
        )
        cards.addWidget(
            self._build_card(
                title="QR do godzin pracy",
                subtitle="Kiosk odbic czasu pracy",
                accent="#1d4ed8",
                open_text="Otworz kiosk czasu",
                kind="time",
            ),
            0,
            1,
        )
        cards.addWidget(
            self._build_card(
                title="QR do pomiarow",
                subtitle="Pomiary ze zdjecia na telefonie",
                accent="#b45309",
                open_text="Otworz pomiary mobilne",
                kind="measure",
            ),
            1,
            0,
            1,
            2,
        )
        root.addLayout(cards, 1)

        info = QLabel(
            "Telefon i komputer musza byc w tej samej sieci. Jesli strona sie nie otwiera, sprawdz czy serwer jest uruchomiony.",
            self,
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:transparent; border:1px solid #dbe4ee; border-radius:10px; padding:10px; color:#94a3b8;"
        )
        root.addWidget(info)

        self._refresh_urls_from_input()

    def _build_card(
        self,
        *,
        title: str,
        subtitle: str,
        accent: str,
        open_text: str,
        kind: str,
    ) -> QFrame:
        card = QFrame(self); card.setProperty("uiCard", True)
        card.setStyleSheet("QFrame { border:1px solid #e3e9f1; border-radius:16px; background:transparent; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_lab = QLabel(title, card)
        title_lab.setStyleSheet("font-size:15px; font-weight:900; color:#173355;")
        sub_lab = QLabel(subtitle, card)
        sub_lab.setWordWrap(True)
        sub_lab.setStyleSheet("font-size:12px; color:#5d6a79;")
        layout.addWidget(title_lab)
        layout.addWidget(sub_lab)

        phone_mock = QFrame(card)
        phone_mock.setMinimumHeight(190)
        phone_mock.setStyleSheet("QFrame { border:2px solid #243243; border-radius:20px; background:#fbfcfe; }")
        phone_mock_lay = QVBoxLayout(phone_mock)
        phone_mock_lay.setContentsMargins(10, 10, 10, 10)
        phone_mock_lay.setSpacing(6)

        header = QLabel("Podglad telefonu", phone_mock)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            f"font-size:11px; font-weight:800; color:#ffffff; background:{accent}; border-radius:8px; padding:4px;"
        )
        if kind == "measure":
            body_text = "1. Otworz link\n2. Dodaj zdjecie\n3. Skalibruj i zapisz wymiar"
        else:
            body_text = "1. Otworz link\n2. Pozwol na kamere\n3. Skanuj QR i zatwierdz"
        body = QLabel(body_text, phone_mock)
        body.setWordWrap(True)
        body.setStyleSheet("font-size:11px; color:#334155;")
        phone_mock_lay.addWidget(header)
        phone_mock_lay.addWidget(body)
        phone_mock_lay.addStretch(1)
        layout.addWidget(phone_mock)

        qr_lab = QLabel(card)
        qr_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_lab.setMinimumHeight(170)
        layout.addWidget(qr_lab)

        url_lab = QLabel("", card)
        url_lab.setWordWrap(True)
        url_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        url_lab.setStyleSheet("font-size:11px; color:#334155;")
        layout.addWidget(url_lab)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        btn_copy = QPushButton("Kopiuj link", card)
        btn_copy.setMinimumHeight(34)
        btn_open = QPushButton(open_text, card)
        btn_open.setMinimumHeight(34)
        btn_open.setStyleSheet(
            f"QPushButton {{ border:none; border-radius:10px; background:{accent}; color:#ffffff; font-weight:800; }}"
            f"QPushButton:hover {{ background:{self._darken_hex(accent)}; }}"
        )
        actions.addWidget(btn_copy, 0)
        actions.addWidget(btn_open, 1)
        layout.addLayout(actions)

        if kind == "pack":
            self._pack_qr_label = qr_lab
            self._pack_url_label = url_lab
            btn_copy.clicked.connect(lambda: self._copy_url(self._pack_scanner_url))
            btn_open.clicked.connect(lambda: self._open_url(self._pack_scanner_url))
        elif kind == "time":
            self._time_qr_label = qr_lab
            self._time_url_label = url_lab
            btn_copy.clicked.connect(lambda: self._copy_url(self._time_kiosk_url))
            btn_open.clicked.connect(lambda: self._open_url(self._time_kiosk_url))
        else:
            self._measure_qr_label = qr_lab
            self._measure_url_label = url_lab
            btn_copy.clicked.connect(lambda: self._copy_url(self._measure_mobile_url))
            btn_open.clicked.connect(lambda: self._open_url(self._measure_mobile_url))

        return card

    def _refresh_urls_from_input(self) -> None:
        base = str(self.ed_base_url.text() or "").strip()
        if not base:
            base = self._guess_phone_base_url()
            self.ed_base_url.setText(base)
        if not base.startswith("http://") and not base.startswith("https://"):
            base = f"http://{base}"
            self.ed_base_url.setText(base)
        base = base.rstrip("/")
        self._pack_scanner_url = f"{base}/pack-scanner"
        self._time_kiosk_url = f"{base}/kiosk-lite"
        self._measure_mobile_url = f"{base}/measure-mobile"
        self._refresh_cards()

    def _refresh_cards(self) -> None:
        if self._pack_qr_label is not None:
            self._pack_qr_label.setPixmap(qr_pixmap_from_text(self._pack_scanner_url, size=150))
        if self._time_qr_label is not None:
            self._time_qr_label.setPixmap(qr_pixmap_from_text(self._time_kiosk_url, size=150))
        if self._measure_qr_label is not None:
            self._measure_qr_label.setPixmap(qr_pixmap_from_text(self._measure_mobile_url, size=150))
        if self._pack_url_label is not None:
            self._pack_url_label.setText(self._pack_scanner_url)
        if self._time_url_label is not None:
            self._time_url_label.setText(self._time_kiosk_url)
        if self._measure_url_label is not None:
            self._measure_url_label.setText(self._measure_mobile_url)

    def _copy_url(self, url: str) -> None:
        if not url:
            return
        QGuiApplication.clipboard().setText(url)

    def _open_url(self, url: str) -> None:
        if not url:
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(self, "QR Telefon", f"Nie udalo sie otworzyc linku:\n{url}")

    def _guess_phone_base_url(self) -> str:
        ip = "127.0.0.1"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("8.8.8.8", 80))
                ip = str(sock.getsockname()[0] or ip).strip() or ip
            finally:
                sock.close()
        except Exception:
            pass
        return f"http://{ip}:8000"

    @staticmethod
    def _darken_hex(color: str) -> str:
        value = str(color or "").strip().lstrip("#")
        if len(value) != 6:
            return "#334155"
        try:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        except Exception:
            return "#334155"
        r = max(0, int(r * 0.85))
        g = max(0, int(g * 0.85))
        b = max(0, int(b * 0.85))
        return f"#{r:02x}{g:02x}{b:02x}"
