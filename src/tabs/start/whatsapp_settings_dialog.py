from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.app.app_settings import WhatsAppSettings, load_whatsapp_settings, save_whatsapp_settings


class WhatsAppSettingsDialog(QDialog):
    """Dialog konfiguracji po czenia WhatsApp przez Twilio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia WhatsApp (Twilio)")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Instrukcja krok po kroku
        info = QLabel(
            "<b>Jak skonfigurowa (5 minut):</b><br>"
            "1. Za konto na <b>twilio.com</b> (darmowe)<br>"
            "2. W konsoli skopiuj <b>Account SID</b> i <b>Auth Token</b><br>"
            "3. Wejd w <i>Messaging Try it out Send a WhatsApp message</i><br>"
            "4. Klienci wysy aj <b>join &lt;s owo&gt;</b> na <b>+14155238886</b><br>"
            "5. Wpisz sw j numer poni ej (format: <b>whatsapp:+48XXXXXXXXX</b>)"
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setStyleSheet(
            "background:#f0f8ff; border:1px solid #c0d8f0; border-radius:8px;"
            "padding:10px; color:#1a3550; font-size:12px;"
        )
        layout.addWidget(info)

        self._enabled = QCheckBox("W cz integracj WhatsApp")
        layout.addWidget(self._enabled)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._sid = QLineEdit()
        self._sid.setPlaceholderText("ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        form.addRow("Account SID:", self._sid)

        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._token.setPlaceholderText("Auth Token")
        form.addRow("Auth Token:", self._token)

        self._number = QLineEdit()
        self._number.setPlaceholderText("whatsapp:+48XXXXXXXXX")
        form.addRow("Tw j numer (To):", self._number)

        self._max_fetch = QSpinBox()
        self._max_fetch.setRange(1, 100)
        self._max_fetch.setValue(20)
        form.addRow("Max wiadomo ci:", self._max_fetch)

        layout.addLayout(form)

        # Test po czenia
        test_row = QWidget()
        test_layout = QFormLayout(test_row)
        test_layout.setContentsMargins(0, 0, 0, 0)
        self._test_btn = QPushButton("Testuj po czenie")
        self._test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_btn.clicked.connect(self._test_connection)
        self._test_lbl = QLabel("")
        self._test_lbl.setWordWrap(True)
        self._test_lbl.setStyleSheet("font-size:11px; color:#2a5a2a;")
        test_layout.addRow(self._test_btn, self._test_lbl)
        layout.addWidget(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self) -> None:
        s = load_whatsapp_settings()
        self._enabled.setChecked(s.enabled)
        self._sid.setText(s.account_sid)
        self._token.setText(s.auth_token)
        self._number.setText(s.to_number)
        self._max_fetch.setValue(s.max_fetch)

    def _test_connection(self) -> None:
        from src.integrations.whatsapp_reader import fetch_whatsapp_messages
        self._test_lbl.setText(" cz ")
        self._test_lbl.setStyleSheet("font-size:11px; color:#5a5a00;")
        self._test_btn.setEnabled(False)
        try:
            s = WhatsAppSettings(
                enabled=True,
                account_sid=self._sid.text().strip(),
                auth_token=self._token.text().strip(),
                to_number=self._number.text().strip(),
                max_fetch=5,
            )
            msgs = fetch_whatsapp_messages(s)
            self._test_lbl.setText(f"OK znaleziono {len(msgs)} wiadomo ci")
            self._test_lbl.setStyleSheet("font-size:11px; color:#1a6e1a;")
        except Exception as exc:
            self._test_lbl.setText(f"B d: {str(exc)[:120]}")
            self._test_lbl.setStyleSheet("font-size:11px; color:#8a0000;")
        finally:
            self._test_btn.setEnabled(True)

    def _save_and_accept(self) -> None:
        s = WhatsAppSettings(
            enabled=self._enabled.isChecked(),
            account_sid=self._sid.text().strip(),
            auth_token=self._token.text().strip(),
            to_number=self._number.text().strip(),
            max_fetch=self._max_fetch.value(),
        )
        save_whatsapp_settings(s)
        self.accept()
