from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_telegram_settings
from src.integrations.telegram_sender import send_text_message
from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.tabs.start.briefing_widget import DailyBriefingWidget
from src.tabs.zakupy.telegram_settings_dialog import TelegramSettingsDialog


class TabBriefing(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("BRIEFING")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color:#14263d;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Dzienny briefing firmy. Odswiezaj i wysylaj na Telegram.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#5f6c7c; font-size:13px;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_refresh = QPushButton("Odswiez briefing", self)
        self.btn_send_telegram = QPushButton("Wyslij briefing Telegram", self)
        self.btn_telegram_settings = QPushButton("Ustawienia Telegram", self)
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_send_telegram.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.btn_telegram_settings.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_telegram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_telegram_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        for btn in (self.btn_refresh, self.btn_send_telegram, self.btn_telegram_settings):
            btn.setMinimumHeight(36)
            root.addWidget(btn, 0)

        self._briefing = DailyBriefingWidget(
            order_store=OrderStoreJson(),
            calendar_store=CalendarEventStoreJson(),
            parent=self,
        )
        root.addWidget(self._briefing, 1)

        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_send_telegram.clicked.connect(self._send_briefing_to_telegram)
        self.btn_telegram_settings.clicked.connect(self._open_telegram_tools)

    def _refresh(self) -> None:
        self._briefing.refresh()

    def _open_telegram_tools(self) -> None:
        dlg = TelegramSettingsDialog(self)
        if not dlg.exec():
            return
        settings = load_telegram_settings()
        if not settings.enabled:
            QMessageBox.information(
                self,
                "Telegram",
                "Telegram zapisany, ale wysylka jest wylaczona.",
            )
            return
        if not str(settings.bot_token or "").strip() or not str(settings.chat_id or "").strip():
            QMessageBox.warning(
                self,
                "Telegram",
                "Brakuje bot token lub chat_id. Uzupelnij ustawienia Telegram.",
            )
            return
        try:
            send_text_message(
                bot_token=settings.bot_token,
                chat_id=settings.chat_id,
                text="TECH_modul: panel Briefing jest gotowy.",
            )
            QMessageBox.information(
                self,
                "Telegram",
                "Wyslano wiadomosc testowa z Briefingu.",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Telegram",
                f"Nie udalo sie wyslac testu Telegram: {exc}",
            )

    def _send_briefing_to_telegram(self) -> None:
        settings = load_telegram_settings()
        if not (settings.enabled and settings.bot_token and settings.chat_id):
            answer = QMessageBox.question(
                self,
                "Telegram",
                "Telegram nie jest skonfigurowany.\nOtworzyc ustawienia teraz?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._open_telegram_tools()
            settings = load_telegram_settings()
            if not (settings.enabled and settings.bot_token and settings.chat_id):
                return

        self._briefing.refresh()
        QApplication.processEvents()
        briefing_text = self._build_briefing_text_for_telegram()
        if not briefing_text.strip():
            briefing_text = "TECH_modul: briefing jest pusty."

        max_chars = 3900
        if len(briefing_text) > max_chars:
            briefing_text = briefing_text[: max_chars - 20].rstrip() + "\n...(skrocone)"

        try:
            send_text_message(
                bot_token=settings.bot_token,
                chat_id=settings.chat_id,
                text=briefing_text,
            )
            QMessageBox.information(
                self,
                "Telegram",
                "Wyslano briefing na Telegram.",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Telegram",
                f"Nie udalo sie wyslac briefingu: {exc}",
            )

    def _build_briefing_text_for_telegram(self) -> str:
        lines: list[str] = ["TECH_modul - Briefing dnia"]
        date_text = str(getattr(self._briefing, "_date_lbl", QLabel()).text() or "").strip()
        if date_text:
            lines.append(date_text)
        user_text = str(getattr(self._briefing, "_user_lbl", QLabel()).text() or "").strip()
        if user_text:
            lines.append(user_text)

        content_layout = getattr(self._briefing, "_content", None)
        if content_layout is None:
            return "\n".join(lines)

        extracted = self._collect_label_texts_from_layout(content_layout)
        if extracted:
            lines.append("")
            lines.extend(extracted)
        return "\n".join(lines).strip()

    def _collect_label_texts_from_layout(self, layout) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                for text in self._collect_label_texts_from_widget(widget):
                    key = text.strip()
                    if key and key not in seen:
                        seen.add(key)
                        out.append(key)
            elif child_layout is not None:
                for text in self._collect_label_texts_from_layout(child_layout):
                    key = text.strip()
                    if key and key not in seen:
                        seen.add(key)
                        out.append(key)
        return out

    def _collect_label_texts_from_widget(self, widget: QWidget) -> list[str]:
        out: list[str] = []
        if isinstance(widget, QLabel):
            text = str(widget.text() or "").replace("\u00a0", " ").strip()
            if text:
                out.append(text)
        layout = widget.layout()
        if layout is not None:
            out.extend(self._collect_label_texts_from_layout(layout))
        return out

    def set_current_user(self, worker_name: str, role: str) -> None:
        worker = str(worker_name or "").strip()
        role_name = str(role or "").strip().lower()
        if hasattr(self._briefing, "set_current_user"):
            self._briefing.set_current_user(worker, role_name)

