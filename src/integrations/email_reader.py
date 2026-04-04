from __future__ import annotations

import email
import email.header
import imaplib
import uuid
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import List

from src.app.app_settings import EmailSettings
from src.integrations.message_store import InboxMessage

_SNIPPET_LEN = 300


def _decode_header_str(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parts = email.header.decode_header(raw)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(chunk)
    return "".join(decoded).strip()


def _extract_snippet(msg: email.message.Message) -> str:
    """Zwraca pierwsze _SNIPPET_LEN znaków treści tekstowej."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")[:_SNIPPET_LEN]
        # fallback: text/html
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    # strip tags roughly
                    import re
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = re.sub(r"\s+", " ", text).strip()
                    return text[:_SNIPPET_LEN]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")[:_SNIPPET_LEN]
    return ""


def _parse_date(msg: email.message.Message) -> str:
    """Zwraca ISO datetime string z nagłówka Date."""
    raw_date = msg.get("Date", "")
    if raw_date:
        try:
            dt = parsedate_to_datetime(raw_date)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def fetch_unread_emails(settings: EmailSettings) -> List[InboxMessage]:
    """
    Łączy się przez IMAP SSL, pobiera nieprzeczytane wiadomości.
    Zwraca listę InboxMessage. Rzuca wyjątek przy błędzie połączenia.
    """
    if not settings.enabled or not settings.username or not settings.password:
        return []

    conn = imaplib.IMAP4_SSL(settings.host, settings.port)
    try:
        conn.login(settings.username, settings.password)
        conn.select(settings.folder, readonly=True)

        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []

        ids = data[0].split()
        # Pobierz tylko max_fetch najnowszych
        ids = ids[-settings.max_fetch:]

        messages: List[InboxMessage] = []
        for uid in ids:
            status, raw = conn.fetch(uid, "(RFC822)")
            if status != "OK" or not raw or not raw[0]:
                continue
            raw_bytes = raw[0][1] if isinstance(raw[0], tuple) else None
            if not isinstance(raw_bytes, bytes):
                continue

            msg = email.message_from_bytes(raw_bytes)

            from_raw = msg.get("From", "")
            display_name, addr = parseaddr(from_raw)
            sender = _decode_header_str(display_name) or addr or from_raw

            subject = _decode_header_str(msg.get("Subject", "(brak tematu)"))
            snippet = _extract_snippet(msg)
            received_at = _parse_date(msg)

            # Stable ID: Message-ID nagłówek lub hash
            msg_id_header = msg.get("Message-ID", "").strip()
            stable_id = msg_id_header if msg_id_header else str(uuid.uuid5(uuid.NAMESPACE_URL, f"{addr}:{subject}:{received_at}"))

            messages.append(InboxMessage(
                id=stable_id,
                source="email",
                sender=sender,
                subject=subject,
                snippet=snippet,
                received_at=received_at,
                read=False,
            ))

        return messages
    finally:
        try:
            conn.logout()
        except Exception:
            pass
