from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from src.app.app_settings import EmailSettings, load_email_settings, save_email_settings


class EmailSettingsDialog(QDialog):
    """Dialog konfiguracji po czenia IMAP (email)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia Email (IMAP)")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Wpisz dane konta IMAP. Dla Gmail u yj has a aplikacji\n"
            "(Konto Google Bezpiecze stwo Has a do aplikacji)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#5a6a7a; font-size:12px;")
        layout.addWidget(info)

        self._enabled = QCheckBox("W cz integracj email")
        layout.addWidget(self._enabled)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._host = QLineEdit()
        self._host.setPlaceholderText("imap.gmail.com")
        form.addRow("Host IMAP:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(993)
        form.addRow("Port (SSL):", self._port)

        self._username = QLineEdit()
        self._username.setPlaceholderText("adres@gmail.com")
        form.addRow("Adres email:", self._username)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Has o aplikacji")
        form.addRow("Has o:", self._password)

        self._folder = QLineEdit()
        self._folder.setPlaceholderText("INBOX")
        form.addRow("Folder:", self._folder)

        self._max_fetch = QSpinBox()
        self._max_fetch.setRange(1, 100)
        self._max_fetch.setValue(20)
        form.addRow("Max wiadomo ci:", self._max_fetch)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self) -> None:
        s = load_email_settings()
        self._enabled.setChecked(s.enabled)
        self._host.setText(s.host)
        self._port.setValue(s.port)
        self._username.setText(s.username)
        self._password.setText(s.password)
        self._folder.setText(s.folder or "INBOX")
        self._max_fetch.setValue(s.max_fetch)

    def _save_and_accept(self) -> None:
        s = EmailSettings(
            enabled=self._enabled.isChecked(),
            host=self._host.text().strip() or "imap.gmail.com",
            port=self._port.value(),
            username=self._username.text().strip(),
            password=self._password.text(),
            folder=self._folder.text().strip() or "INBOX",
            max_fetch=self._max_fetch.value(),
        )
        save_email_settings(s)
        self.accept()
