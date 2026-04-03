from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import (
    TelegramSettings,
    load_telegram_settings,
    save_telegram_settings,
)
from src.integrations.telegram_sender import send_text_message


class TelegramSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia Telegram")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info = QLabel(
            "<b>Telegram Bot - szybka konfiguracja:</b><br>"
            "1. W Telegram otworz @BotFather i utworz bota (/newbot).<br>"
            "2. Skopiuj <b>bot token</b>.<br>"
            "3. Napisz do bota minimum 1 wiadomosc.<br>"
            "4. Ustal <b>chat_id</b> (np. przez getUpdates)."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setStyleSheet(
            "background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;"
            "padding:10px;color:#1e3a8a;font-size:12px;"
        )
        layout.addWidget(info)

        self._enabled = QCheckBox("Wlacz wysylke na Telegram")
        layout.addWidget(self._enabled)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._token = QLineEdit()
        self._token.setPlaceholderText("123456789:AA....")
        form.addRow("Bot token:", self._token)

        self._chat_id = QLineEdit()
        self._chat_id.setPlaceholderText("np. 123456789 lub -100...")
        form.addRow("Chat ID:", self._chat_id)
        layout.addLayout(form)

        test_row = QWidget()
        test_form = QFormLayout(test_row)
        test_form.setContentsMargins(0, 0, 0, 0)

        self._btn_test = QPushButton("Test polaczenia")
        self._btn_test.clicked.connect(self._test)
        self._lab_test = QLabel("")
        self._lab_test.setWordWrap(True)
        self._lab_test.setStyleSheet("font-size:11px;color:#334155;")
        test_form.addRow(self._btn_test, self._lab_test)
        layout.addWidget(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self) -> None:
        s = load_telegram_settings()
        self._enabled.setChecked(bool(s.enabled))
        self._token.setText(str(s.bot_token or ""))
        self._chat_id.setText(str(s.chat_id or ""))

    def _test(self) -> None:
        self._btn_test.setEnabled(False)
        self._lab_test.setText("Lacze z Telegram...")
        self._lab_test.setStyleSheet("font-size:11px;color:#b45309;")
        try:
            send_text_message(
                bot_token=self._token.text().strip(),
                chat_id=self._chat_id.text().strip(),
                text="TECH_modul: test polaczenia Telegram OK.",
            )
            self._lab_test.setText("OK - wiadomosc testowa wyslana.")
            self._lab_test.setStyleSheet("font-size:11px;color:#166534;")
        except Exception as exc:
            self._lab_test.setText(f"Blad: {str(exc)}")
            self._lab_test.setStyleSheet("font-size:11px;color:#991b1b;")
        finally:
            self._btn_test.setEnabled(True)

    def _save_and_accept(self) -> None:
        s = TelegramSettings(
            enabled=self._enabled.isChecked(),
            bot_token=self._token.text().strip(),
            chat_id=self._chat_id.text().strip(),
        )
        save_telegram_settings(s)
        self.accept()
