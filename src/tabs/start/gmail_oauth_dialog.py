from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.app.app_settings import (
    GmailOAuthSettings, load_gmail_oauth_settings, save_gmail_oauth_settings,
)
from src.integrations.gmail_oauth import (
    clear_token, do_auth_flow, get_authenticated_email, is_authenticated,
)


class _AuthThread(QThread):
    sig_done = pyqtSignal(str) # email
    sig_error = pyqtSignal(str)

    def __init__(self, client_id: str, client_secret: str, worker_name: str = "") -> None:
        super().__init__()
        self._client_id = client_id
        self._client_secret = client_secret
        self._worker_name = worker_name

    def run(self) -> None:
        try:
            email = do_auth_flow(self._client_id, self._client_secret, self._worker_name)
            self.sig_done.emit(email)
        except Exception as exc:
            self.sig_error.emit(str(exc))


class GmailOAuthDialog(QDialog):
    """
    Dialog konfiguracji Gmail przez OAuth2.

    Wymaga Google Cloud credentials (Client ID + Client Secret).
    Instrukcja krok po kroku jest wbudowana w dialog.
    """

    def __init__(self, parent: QWidget | None = None, worker_name: str = "") -> None:
        super().__init__(parent)
        self._worker_name = worker_name
        self.setWindowTitle("Po czenie z Gmail (OAuth2)")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Instrukcja 
        steps = QLabel(
            "<b>Jak uzyska Client ID i Client Secret (raz, ~10 minut):</b><br><br>"
            "<b>1.</b> Wejd na <b>console.cloud.google.com</b> i zaloguj si <br>"
            "<b>2.</b> Kliknij <i>Select a project</i> <b>New Project</b> wpisz nazw np. <i>TECH_modul</i><br>"
            "<b>3.</b> W menu bocznym: <b>APIs &amp; Services Library</b><br>"
            " wyszukaj <b>Gmail API</b> kliknij <b>Enable</b><br>"
            "<b>4.</b> W menu bocznym: <b>APIs &amp; Services Credentials</b><br>"
            " <b>Create Credentials OAuth client ID</b><br>"
            " Application type: <b>Desktop app</b> <b>Create</b><br>"
            "<b>5.</b> Skopiuj <b>Client ID</b> i <b>Client Secret</b> wklej poni ej<br>"
            "<b>6.</b> Kliknij <b>Zaloguj przez Google</b> otworzy si przegl darka"
        )
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setStyleSheet(
            "background:#f0f6ff; border:1px solid #b8d4f0; border-radius:10px;"
            "padding:12px; color:#1a3550; font-size:12px; line-height:1.6;"
        )
        layout.addWidget(steps)

        self._enabled = QCheckBox("W cz integracj Gmail")
        layout.addWidget(self._enabled)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._client_id = QLineEdit()
        self._client_id.setPlaceholderText("123456789-abcdef.apps.googleusercontent.com")
        form.addRow("Client ID:", self._client_id)

        self._client_secret = QLineEdit()
        self._client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._client_secret.setPlaceholderText("GOCSPX-...")
        form.addRow("Client Secret:", self._client_secret)

        self._max_fetch = QSpinBox()
        self._max_fetch.setRange(1, 100)
        self._max_fetch.setValue(20)
        form.addRow("Max emaili:", self._max_fetch)

        layout.addLayout(form)

        # Status zalogowania 
        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("font-size:12px; color:#1a6e1a; font-weight:600;")
        layout.addWidget(self._status_lbl)

        # Przyciski akcji 
        btn_row = QWidget()
        btn_layout = QFormLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self._login_btn = QPushButton("Zaloguj przez Google ")
        self._login_btn.setMinimumHeight(36)
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.setStyleSheet(
            "QPushButton {"
            "background:#1a73e8; color:white; border:none; border-radius:8px;"
            "font-size:13px; font-weight:700; padding:0 16px;"
            "}"
            "QPushButton:hover { background:#1558b0; }"
            "QPushButton:disabled { background:#aaa; }"
        )
        self._login_btn.clicked.connect(self._start_auth)

        self._logout_btn = QPushButton("Wyloguj")
        self._logout_btn.setMinimumHeight(36)
        self._logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._logout_btn.setStyleSheet(
            "QPushButton { border:1px solid #c04040; border-radius:8px;"
            "color:#c04040; font-size:12px; padding:0 12px; }"
            "QPushButton:hover { background:#fff0f0; }"
        )
        self._logout_btn.clicked.connect(self._logout)

        btn_layout.addRow(self._login_btn, self._logout_btn)
        layout.addWidget(btn_row)

        # Fallback: wklej URL r cznie 
        fallback_lbl = QLabel(
            "Je li przegl darka pokazuje b d po czenia skopiuj ca y URL "
            "z paska adresu i wklej tutaj:"
        )
        fallback_lbl.setWordWrap(True)
        fallback_lbl.setStyleSheet("font-size:11px; color:#5a6a7a;")
        layout.addWidget(fallback_lbl)

        fallback_row = QWidget()
        fallback_layout = QFormLayout(fallback_row)
        fallback_layout.setContentsMargins(0, 0, 0, 0)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("http://localhost:8080/Emailstate=...&code=...")
        self._url_paste_btn = QPushButton("U yj tego URL")
        self._url_paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url_paste_btn.setStyleSheet(
            "QPushButton { border:1px solid #5a8a5a; border-radius:6px;"
            "color:#2a6a2a; font-size:12px; padding:4px 10px; }"
            "QPushButton:hover { background:#f0fff0; }"
        )
        self._url_paste_btn.clicked.connect(self._use_manual_url)
        fallback_layout.addRow(self._url_input, self._url_paste_btn)
        layout.addWidget(fallback_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._auth_thread: _AuthThread | None = None
        self._load()

    # Load / save 

    def _load(self) -> None:
        s = load_gmail_oauth_settings()
        self._enabled.setChecked(s.enabled)
        self._client_id.setText(s.client_id)
        self._client_secret.setText(s.client_secret)
        self._max_fetch.setValue(s.max_fetch)
        self._update_status()

    def _update_status(self) -> None:
        if is_authenticated(self._worker_name):
            email = get_authenticated_email(self._worker_name)
            label = f" Zalogowany jako: {email}"
            if self._worker_name:
                label += f" [{self._worker_name}]"
            self._status_lbl.setText(label)
            self._status_lbl.setStyleSheet("font-size:12px; color:#1a6e1a; font-weight:600;")
            self._login_btn.setText("Zaloguj ponownie ")
        else:
            self._status_lbl.setText("Nie zalogowany kliknij przycisk poni ej")
            self._status_lbl.setStyleSheet("font-size:12px; color:#8a6000;")

    # OAuth flow 

    def _start_auth(self) -> None:
        client_id = self._client_id.text().strip()
        client_secret = self._client_secret.text().strip()

        if not client_id or not client_secret:
            self._status_lbl.setText("Wpisz Client ID i Client Secret przed logowaniem.")
            self._status_lbl.setStyleSheet("font-size:12px; color:#c04040;")
            return

        self._login_btn.setEnabled(False)
        self._status_lbl.setText("Otwieram przegl dark zaloguj si w Google (max 2 min).")
        self._status_lbl.setStyleSheet("font-size:12px; color:#5a6000;")

        self._auth_thread = _AuthThread(client_id, client_secret, self._worker_name)
        self._auth_thread.sig_done.connect(self._on_auth_done)
        self._auth_thread.sig_error.connect(self._on_auth_error)
        self._auth_thread.start()

    def _on_auth_done(self, email: str) -> None:
        self._login_btn.setEnabled(True)
        self._update_status()

    def _on_auth_error(self, error: str) -> None:
        self._login_btn.setEnabled(True)
        self._status_lbl.setText(f"B d: {error[:150]}")
        self._status_lbl.setStyleSheet("font-size:12px; color:#c04040;")

    def _use_manual_url(self) -> None:
        """Wyci ga kod z URL wklejonego r cznie i wymienia na tokeny."""
        import urllib.parse
        raw_url = self._url_input.text().strip()
        if not raw_url:
            return
        try:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
            code = params.get("code", [None])[0]
            if not code:
                self._status_lbl.setText("B d: nie znaleziono kodu w URL.")
                self._status_lbl.setStyleSheet("font-size:12px; color:#c04040;")
                return

            from src.integrations.gmail_oauth import (
                exchange_code_for_tokens, get_authenticated_email, save_token,
            )
            from datetime import datetime, timezone, timedelta
            import requests as req

            client_id = self._client_id.text().strip()
            client_secret = self._client_secret.text().strip()
            token_data = exchange_code_for_tokens(client_id, client_secret, code)

            expires_in = int(token_data.get("expires_in", 3600))
            token = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                ).isoformat(),
                "client_id": client_id,
                "client_secret": client_secret,
                "email": "",
            }
            profile = req.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {token['access_token']}"},
                timeout=10,
            )
            if profile.ok:
                token["email"] = profile.json().get("emailAddress", "")
            save_token(token, self._worker_name)
            self._url_input.clear()
            self._update_status()
        except Exception as exc:
            self._status_lbl.setText(f"B d: {str(exc)[:120]}")
            self._status_lbl.setStyleSheet("font-size:12px; color:#c04040;")

    def _logout(self) -> None:
        clear_token(self._worker_name)
        self._update_status()

    # Save 

    def _save_and_accept(self) -> None:
        s = GmailOAuthSettings(
            enabled=self._enabled.isChecked(),
            client_id=self._client_id.text().strip(),
            client_secret=self._client_secret.text().strip(),
            max_fetch=self._max_fetch.value(),
        )
        save_gmail_oauth_settings(s)
        self.accept()
