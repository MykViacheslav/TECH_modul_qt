from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from src.domain.calendar_event import EVENT_TYPE_LABELS
from src.domain.permissions import normalize_role
from src.integrations.fetch_thread import MessageFetchThread
from src.integrations.message_store import InboxMessageStore
from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.order_store_json import OrderStoreJson

_DAYS_PL = [
    "Poniedzialek", "Wtorek", "Sroda", "Czwartek",
    "Piatek", "Sobota", "Niedziela",
]
_MONTHS_PL = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "wrzesnia", "pazdziernika", "listopada", "grudnia",
]

_DEADLINE_FIELDS: List[Tuple[str, str]] = [
    ("date_montaz", "Montaz"),
    ("date_produkcja", "Produkcja"),
    ("date_wycena", "Wycena"),
    ("date_zakup_mat", "Zakup mat."),
    ("date_poprawki", "Poprawki"),
]

# Terminy widoczne per-rola
_DEADLINE_FIELDS_BY_ROLE: Dict[str, List[str]] = {
    "wlasciciel": ["date_montaz", "date_produkcja", "date_wycena", "date_zakup_mat", "date_poprawki"],
    "biuro": ["date_montaz", "date_produkcja", "date_wycena", "date_poprawki"],
    "produkcja": ["date_montaz", "date_produkcja"],
    "magazyn": ["date_montaz", "date_produkcja", "date_zakup_mat"],
}

_HORIZON_DAYS = 7
_MAX_MESSAGES = 6

_ROLE_LABEL: Dict[str, str] = {
    "wlasciciel": "Wlasciciel",
    "biuro": "Biuro",
    "produkcja": "Produkcja",
    "magazyn": "Magazyn",
}


def _today_label() -> str:
    d = date.today()
    return f"{_DAYS_PL[d.weekday()]}, {d.day} {_MONTHS_PL[d.month - 1]} {d.year}"


def _date_tag(d: date) -> str:
    today = date.today()
    if d == today:
        return "dzis"
    if d == today + timedelta(days=1):
        return "jutro"
    return d.strftime("%d.%m")


class DailyBriefingWidget(QFrame):
    def __init__(
        self,
        order_store: OrderStoreJson,
        calendar_store: CalendarEventStoreJson,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._order_store = order_store
        self._calendar_store = calendar_store
        self._invoice_store = InvoiceStoreJson()
        self._msg_store = InboxMessageStore()
        self._fetch_thread: MessageFetchThread | None = None
        self._source_statuses: Dict[str, str] = {}
        self._worker_name: str = ""
        self._role: str = "wlasciciel"

        self.setObjectName("BriefingFrame")
        self.setStyleSheet(
            "QFrame#BriefingFrame {"
            "border: 1px solid #cdddf0;"
            "border-radius: 18px;"
            "background: #eef6ff;"
            "}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(10)

        # Header 
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        title_lbl = QLabel("Briefing dnia")
        title_lbl.setStyleSheet(
            "font-size:14px; font-weight:800; color:#173355;"
            "background:transparent; border:none;"
        )
        header_row.addWidget(title_lbl)

        self._user_lbl = QLabel("")
        self._user_lbl.setStyleSheet(
            "font-size:11px; color:#1a3a60; font-weight:600;"
            "background:#d0e8ff; border:1px solid #a0c8f0;"
            "border-radius:8px; padding:1px 8px;"
        )
        self._user_lbl.hide()
        header_row.addWidget(self._user_lbl)
        header_row.addStretch()

        self._date_lbl = QLabel(_today_label())
        self._date_lbl.setStyleSheet(
            "font-size:12px; color:#4a6080;"
            "background:transparent; border:none;"
        )
        header_row.addWidget(self._date_lbl)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            "font-size:11px; color:#7a9ab8; background:transparent; border:none;"
        )
        header_row.addWidget(self._status_lbl)

        self._email_btn = self._make_action_btn("Email", self._open_email_settings)
        refresh_btn = self._make_action_btn("Odswiez", self.refresh)

        header_row.addWidget(self._email_btn)
        header_row.addWidget(refresh_btn)
        outer.addLayout(header_row)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background:#cdddf0; border:none;")
        outer.addWidget(div)

        self._content = QVBoxLayout()
        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(6)
        outer.addLayout(self._content)

        self.refresh()

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(5 * 60 * 1000)
        self._auto_refresh_timer.timeout.connect(self.refresh)
        self._auto_refresh_timer.start()

    # Public 

    def set_current_user(self, worker_name: str, role: str) -> None:
        """Ustaw zalogowanego uzytkownika - filtruje tresc briefingu wg roli."""
        self._worker_name = worker_name or ""
        self._role = normalize_role(role or "wlasciciel")
        self._source_statuses.clear()

        # Etykieta uzytkownika w naglowku
        if self._worker_name:
            role_label = _ROLE_LABEL.get(self._role, self._role.capitalize())
            first = self._worker_name.split()[0]
            self._user_lbl.setText(f"{first} - {role_label}")
            self._user_lbl.show()
        else:
            self._user_lbl.hide()

        self.refresh()

    def refresh(self) -> None:
        self._date_lbl.setText(_today_label())
        self._redraw()
        self._start_fetch()

    # Build sections 

    def _redraw(self) -> None:
        self._clear_content()
        self._build_deadlines()
        self._build_calendar()
        if self._can_see_invoices():
            self._build_invoices()
        if self._can_see_messages():
            self._build_messages()

    def _can_see_messages(self) -> bool:
        """Wiadomosci od klientow tylko dla Biuro i Wlasciciel."""
        return self._role in ("wlasciciel", "biuro")

    def _can_see_invoices(self) -> bool:
        return self._role in ("wlasciciel", "biuro", "magazyn")

    def _clear_content(self) -> None:
        while self._content.count():
            item = self._content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_deadlines(self) -> None:
        today = date.today()
        horizon = today + timedelta(days=_HORIZON_DAYS)

        allowed_fields = _DEADLINE_FIELDS_BY_ROLE.get(
            self._role, [f for f, _ in _DEADLINE_FIELDS]
        )
        active_fields = [(f, lbl) for f, lbl in _DEADLINE_FIELDS if f in allowed_fields]

        rows: List[Tuple[date, str]] = []
        for order in self._order_store.list_orders():
            for field_name, label in active_fields:
                raw = getattr(order, field_name, "")
                if not raw:
                    continue
                try:
                    d = date.fromisoformat(raw)
                except ValueError:
                    continue
                if today <= d <= horizon:
                    client = order.client_name or order.code
                    rows.append((d, f"{order.code} / {client} {label} {_date_tag(d)}"))

        rows.sort(key=lambda x: x[0])
        self._content.addWidget(self._make_section("Terminy (7 dni)"))
        if rows:
            for _, text in rows[:6]:
                self._content.addWidget(self._make_row(text))
        else:
            self._content.addWidget(self._make_row("Brak terminow", muted=True))

    def _build_calendar(self) -> None:
        today_str = date.today().isoformat()
        all_events = self._calendar_store.list_events()

        # Produkcja widzi tylko wpisy dotyczace siebie
        if self._role == "produkcja" and self._worker_name:
            events = [
                ev for ev in all_events
                if ev.date == today_str
                and (not ev.worker_name or ev.worker_name == self._worker_name)
            ]
        else:
            events = [ev for ev in all_events if ev.date == today_str]

        self._content.addWidget(self._make_section("Dzisiaj w kalendarzu"))
        if events:
            for ev in events[:6]:
                ev_type = EVENT_TYPE_LABELS.get(ev.event_type, ev.event_type)
                parts = [ev_type]
                if ev.title:
                    parts.append(ev.title)
                if ev.worker_name:
                    parts.append(f"({ev.worker_name})")
                self._content.addWidget(self._make_row(" - ".join(parts)))
        else:
            self._content.addWidget(self._make_row("Brak wydarzen na dzis", muted=True))

    def _build_invoices(self) -> None:
        self._content.addWidget(self._make_section("Faktury z maila"))

        status = str(self._source_statuses.get("invoices", "") or "").strip()
        if status:
            self._content.addWidget(self._make_row(f"Status: {status}", muted=False))

        try:
            pending = self._invoice_store.count_pending_export()
            invoices = self._invoice_store.list_invoices()
        except Exception as exc:
            self._content.addWidget(self._make_row(f"Blad bazy faktur: {exc}", muted=False))
            return

        self._content.addWidget(self._make_row(f"Oczekuje eksportu do magazynu: {pending}"))

        if not invoices:
            self._content.addWidget(self._make_row("Brak faktur w bazie", muted=True))
            return

        preview_rows = [row for row in invoices if not bool(row.get("exported_to_material", False))]
        if not preview_rows:
            preview_rows = invoices
        preview_rows = preview_rows[:3]

        for row in preview_rows:
            inv_no = str(row.get("invoice_number", "") or row.get("attachment_name", "") or "-").strip()
            supplier = str(row.get("supplier", "") or row.get("sender", "") or "-").strip()
            try:
                amount = float(row.get("total_amount", 0.0) or 0.0)
            except Exception:
                amount = 0.0
            self._content.addWidget(self._make_row(f"{inv_no} | {supplier} | {amount:.2f} zl"))

    def _build_messages(self) -> None:
        from src.app.app_settings import load_email_settings, load_gmail_oauth_settings, load_whatsapp_settings
        from src.integrations.gmail_oauth import is_authenticated

        gmail_cfg = load_gmail_oauth_settings()
        email_cfg = load_email_settings()
        # Token per-pracownik lub globalny
        gmail_on = gmail_cfg.enabled and (
            is_authenticated(self._worker_name) or is_authenticated("")
        )
        email_on = bool(gmail_on or email_cfg.enabled)
        wa_on = load_whatsapp_settings().enabled

        self._content.addWidget(self._make_section("Wiadomosci od klientow"))

        # Status zrodel
        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 0, 0, 0)
        status_row.setSpacing(16)

        def _src_badge(icon: str, label: str, enabled: bool, status: str) -> QLabel:
            if not enabled:
                text = f"{icon} {label}: nie skonfigurowany"
                color = "#aaaaaa"
            elif status.startswith("blad"):
                text = f"{icon} {label}: {status}"
                color = "#c04040"
            elif status.startswith("ok"):
                text = f"{icon} {label}: {status}"
                color = "#2a7a2a"
            else:
                text = f"{icon} {label}"
                color = "#8a9aaa"
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size:11px; color:{color}; background:transparent; border:none;"
            )
            return lbl

        email_status = self._source_statuses.get("email", "")
        wa_status = self._source_statuses.get("whatsapp", "")

        status_row.addWidget(_src_badge("E", "Email", email_on, email_status))
        status_row.addWidget(_src_badge("W", "WhatsApp", wa_on, wa_status))
        status_row.addStretch()

        sw = QWidget()
        sw.setStyleSheet("background:transparent; border:none;")
        sw.setLayout(status_row)
        self._content.addWidget(sw)

        unread = sorted(
            self._msg_store.list_unread(),
            key=lambda m: m.received_at,
            reverse=True,
        )[:_MAX_MESSAGES]

        if unread:
            for msg in unread:
                icon = "E" if msg.source == "email" else "W"
                sender = msg.sender[:28] + ("..." if len(msg.sender) > 28 else "")
                body = msg.snippet[:45] + ("..." if len(msg.snippet) > 45 else "")
                self._content.addWidget(self._make_row(f"{icon} {sender}: {body}"))
        elif email_on or wa_on:
            self._content.addWidget(self._make_row("Brak nowych wiadomosci", muted=True))

    # Fetch 

    def _start_fetch(self) -> None:
        from src.app.app_settings import load_email_settings, load_gmail_oauth_settings, load_whatsapp_settings

        gmail_enabled = bool(load_gmail_oauth_settings().enabled)
        imap_enabled = bool(load_email_settings().enabled)
        wa_enabled = bool(load_whatsapp_settings().enabled)

        should_fetch_messages = self._can_see_messages() and (gmail_enabled or imap_enabled or wa_enabled)
        should_fetch_invoices = self._can_see_invoices() and (gmail_enabled or imap_enabled)

        if not should_fetch_messages and not should_fetch_invoices:
            return
        if self._fetch_thread and self._fetch_thread.isRunning():
            return
        self._status_lbl.setText("pobieranie...")
        self._fetch_thread = MessageFetchThread(
            self._msg_store,
            self._worker_name,
            fetch_messages=should_fetch_messages,
            fetch_invoices=should_fetch_invoices,
        )
        self._fetch_thread.sig_done.connect(self._on_fetch_done)
        self._fetch_thread.sig_error.connect(self._on_fetch_error)
        self._fetch_thread.sig_source_status.connect(self._on_source_status)
        self._fetch_thread.start()

    def _on_source_status(self, source: str, status: str) -> None:
        self._source_statuses[source] = status

    def _on_fetch_done(self, added: int) -> None:
        self._status_lbl.setText(f"+{added} nowych" if added else "")
        self._redraw()

    def _on_fetch_error(self, error: str) -> None:
        short = error[:50] + ("..." if len(error) > 50 else "")
        self._status_lbl.setText(f"blad: {short}")

    # Settings dialogs 

    def _open_email_settings(self) -> None:
        from src.tabs.start.gmail_oauth_dialog import GmailOAuthDialog
        dlg = GmailOAuthDialog(self, worker_name=self._worker_name)
        if dlg.exec():
            self.refresh()

    # Helpers 

    def _make_action_btn(self, label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(28)
        btn.setMinimumWidth(76)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "border:1px solid #7aacd4; border-radius:7px;"
            "background:#c6dff5; color:#0f2a45;"
            "font-size:12px; font-weight:700; padding:0 10px;"
            "}"
            "QPushButton:hover { background:#a8ccec; border-color:#5590c0; }"
        )
        btn.clicked.connect(slot)
        return btn

    def _make_section(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            "font-size:9px; font-weight:800; color:#5a7a9a;"
            "letter-spacing:1px; background:transparent; border:none;"
        )
        return lbl

    def _make_row(self, text: str, muted: bool = False) -> QLabel:
        color = "#9ab0c5" if muted else "#1d3a55"
        lbl = QLabel(f" - {text}")
        lbl.setStyleSheet(
            f"font-size:12px; color:{color}; background:transparent; border:none;"
        )
        return lbl
