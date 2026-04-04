from __future__ import annotations

from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from src.app.app_settings import (
    load_email_settings,
    load_gmail_oauth_settings,
    load_whatsapp_settings,
)
from src.integrations.email_reader import fetch_unread_emails
from src.integrations.message_store import InboxMessage, InboxMessageStore
from src.integrations.whatsapp_reader import fetch_whatsapp_messages


class MessageFetchThread(QThread):
    """
    Background fetch for inbox messages and invoice attachments.
    """

    sig_done = pyqtSignal(int)  # total new inbox messages
    sig_error = pyqtSignal(str)
    sig_source_status = pyqtSignal(str, str)  # (source, status)

    def __init__(
        self,
        store: InboxMessageStore,
        worker_name: str = "",
        *,
        fetch_messages: bool = True,
        fetch_invoices: bool = False,
    ) -> None:
        super().__init__()
        self._store = store
        self._worker_name = worker_name
        self._fetch_messages = bool(fetch_messages)
        self._fetch_invoices = bool(fetch_invoices)

    def _fetch_inbox_messages(self) -> int:
        total_added = 0
        all_messages: List[InboxMessage] = []

        gmail_cfg = load_gmail_oauth_settings()
        if gmail_cfg.enabled:
            try:
                from src.integrations.gmail_oauth import fetch_unread_gmail, is_authenticated

                wname = self._worker_name
                if not is_authenticated(wname):
                    wname = ""
                msgs = fetch_unread_gmail(gmail_cfg.max_fetch, wname)
                all_messages.extend(msgs)
                self.sig_source_status.emit("email", f"ok ({len(msgs)} nieprzeczytanych)")
            except Exception as exc:
                self.sig_source_status.emit("email", f"blad: {str(exc)[:80]}")
                self.sig_error.emit(f"Gmail: {exc}")
        else:
            email_cfg = load_email_settings()
            if email_cfg.enabled:
                try:
                    msgs = fetch_unread_emails(email_cfg)
                    all_messages.extend(msgs)
                    self.sig_source_status.emit("email", f"ok ({len(msgs)} nieprzeczytanych)")
                except Exception as exc:
                    self.sig_source_status.emit("email", f"blad: {str(exc)[:80]}")
                    self.sig_error.emit(f"Email: {exc}")

        wa_cfg = load_whatsapp_settings()
        if wa_cfg.enabled:
            try:
                msgs = fetch_whatsapp_messages(wa_cfg)
                all_messages.extend(msgs)
                self.sig_source_status.emit("whatsapp", f"ok ({len(msgs)} wiadomosci)")
            except Exception as exc:
                self.sig_source_status.emit("whatsapp", f"blad: {str(exc)[:80]}")
                self.sig_error.emit(f"WhatsApp: {exc}")

        if all_messages:
            total_added = self._store.upsert_many(all_messages)

        return total_added

    def _fetch_invoice_mail(self) -> None:
        try:
            from src.services.invoice_workflow_service import sync_invoices_from_mail

            summary = sync_invoices_from_mail(
                worker_name=self._worker_name,
                max_messages=20,
                send_telegram_notifications=True,
            )
            self.sig_source_status.emit(
                "invoices",
                f"ok (+{summary.created_invoices} nowe, oczekuje eksportu {summary.pending_export})",
            )
            if summary.telegram_error:
                self.sig_error.emit(f"Telegram faktury: {summary.telegram_error}")
        except Exception as exc:
            self.sig_source_status.emit("invoices", f"blad: {str(exc)[:80]}")
            self.sig_error.emit(f"Faktury: {exc}")

    def run(self) -> None:
        total_added = 0

        if self._fetch_messages:
            total_added = self._fetch_inbox_messages()

        if self._fetch_invoices:
            self._fetch_invoice_mail()

        self.sig_done.emit(total_added)


EmailFetchThread = MessageFetchThread
