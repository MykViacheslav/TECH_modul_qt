from __future__ import annotations

import base64
import email
import email.header
import imaplib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from src.app.app_settings import load_email_settings, load_gmail_oauth_settings


_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_ALLOWED_INVOICE_EXTS = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
_ALLOWED_IMAGE_MIME = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
)


def _http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, object] | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    base = str(url or "").strip()
    if params:
        query = urllib.parse.urlencode({k: str(v) for k, v in params.items()}, doseq=True)
        if query:
            sep = "&" if "?" in base else "?"
            base = f"{base}{sep}{query}"
    req = urllib.request.Request(base, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=int(timeout)) as res:
            payload = res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8", errors="replace")
        except Exception:
            details = ""
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {details[:180]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Brak polaczenia: {exc.reason}") from exc
    try:
        obj = json.loads(payload) if payload else {}
    except Exception as exc:
        raise RuntimeError("Odpowiedz API nie jest poprawnym JSON.") from exc
    return obj if isinstance(obj, dict) else {}


@dataclass(frozen=True)
class InvoiceMailAttachment:
    source: str
    message_id: str
    subject: str
    sender: str
    received_at: str
    filename: str
    payload: bytes


def _decode_header_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    chunks = email.header.decode_header(value)
    out: list[str] = []
    for chunk, charset in chunks:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out).strip()


def _parse_date(raw_value: str) -> str:
    if raw_value:
        try:
            parsed = parsedate_to_datetime(raw_value)
            return parsed.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def _decode_base64url(data: str) -> bytes:
    text = str(data or "").strip()
    if not text:
        return b""
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _iter_gmail_parts(part: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [part]
    for child in list(part.get("parts", []) or []):
        if isinstance(child, dict):
            out.extend(_iter_gmail_parts(child))
    return out


def _gmail_headers_to_map(payload: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for header in list(payload.get("headers", []) or []):
        if not isinstance(header, dict):
            continue
        key = str(header.get("name", "") or "").strip().lower()
        value = str(header.get("value", "") or "").strip()
        if key:
            out[key] = value
    return out


def _fetch_gmail_invoice_pdf_attachments(max_messages: int, worker_name: str) -> list[InvoiceMailAttachment]:
    from src.integrations.gmail_oauth import (
        get_valid_access_token,
        is_authenticated,
        load_token,
    )

    gmail_cfg = load_gmail_oauth_settings()
    if not gmail_cfg.enabled:
        return []

    token_owner = worker_name
    if not is_authenticated(token_owner):
        token_owner = ""
    if not is_authenticated(token_owner):
        return []

    token = load_token(token_owner)
    client_id = str(token.get("client_id", "") or "")
    client_secret = str(token.get("client_secret", "") or "")
    if not client_id or not client_secret:
        raise RuntimeError("Brak client_id/client_secret w zapisanym tokenie Gmail.")

    access_token = get_valid_access_token(client_id, client_secret, token_owner)
    headers = {"Authorization": f"Bearer {access_token}"}
    invoice_query = "(filename:pdf OR filename:jpg OR filename:jpeg OR filename:png OR filename:webp OR filename:bmp OR filename:tif OR filename:tiff)"
    # 1) unread only, 2) fallback: recent inbox invoice-like attachments (also read).
    queries = (
        f"is:unread in:inbox has:attachment {invoice_query}",
        f"in:inbox has:attachment newer_than:365d {invoice_query}",
    )
    seen_ids: set[str] = set()
    messages: list[dict[str, Any]] = []
    for query in queries:
        data = _http_get_json(
            f"{_GMAIL_API}/messages",
            headers=headers,
            params={"q": query, "maxResults": int(max_messages)},
            timeout=20,
        )
        batch = list(data.get("messages", []) or [])
        for row in batch:
            if not isinstance(row, dict):
                continue
            msg_id = str(row.get("id", "") or "").strip()
            if not msg_id or msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            messages.append(row)
            if len(messages) >= int(max_messages):
                break
        if len(messages) >= int(max_messages):
            break

    out: list[InvoiceMailAttachment] = []
    for msg in messages:
        msg_id = str((msg or {}).get("id", "") or "").strip()
        if not msg_id:
            continue

        try:
            data = _http_get_json(
                f"{_GMAIL_API}/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
                timeout=20,
            )
        except Exception:
            continue
        payload = data.get("payload", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict):
            continue
        header_map = _gmail_headers_to_map(payload)
        subject = _decode_header_text(header_map.get("subject", ""))
        sender = _decode_header_text(header_map.get("from", ""))
        received_at = _parse_date(str(header_map.get("date", "") or ""))

        parts = _iter_gmail_parts(payload)
        for part in parts:
            filename = _decode_header_text(part.get("filename", ""))
            mime_type = str(part.get("mimeType", "") or "").lower()
            file_ext = ""
            if filename:
                file_ext = "." + filename.lower().split(".")[-1] if "." in filename else ""
            is_pdf = mime_type == "application/pdf" or file_ext == ".pdf"
            is_image = mime_type in _ALLOWED_IMAGE_MIME or file_ext in _ALLOWED_INVOICE_EXTS[1:]
            if not filename and not is_pdf and not is_image:
                continue
            if filename and not (is_pdf or is_image):
                continue

            body = part.get("body", {}) if isinstance(part, dict) else {}
            if not isinstance(body, dict):
                continue

            attachment_id = str(body.get("attachmentId", "") or "").strip()
            data64 = str(body.get("data", "") or "").strip()
            payload_bytes = b""

            if data64:
                try:
                    payload_bytes = _decode_base64url(data64)
                except Exception:
                    payload_bytes = b""
            elif attachment_id:
                try:
                    att_obj = _http_get_json(
                        f"{_GMAIL_API}/messages/{msg_id}/attachments/{attachment_id}",
                        headers=headers,
                        timeout=20,
                    )
                except Exception:
                    continue
                att_data = str(att_obj.get("data", "") or "").strip()
                if not att_data:
                    continue
                try:
                    payload_bytes = _decode_base64url(att_data)
                except Exception:
                    payload_bytes = b""

            if not payload_bytes:
                continue

            out.append(
                InvoiceMailAttachment(
                    source="gmail",
                    message_id=f"gmail_{msg_id}",
                    subject=subject,
                    sender=sender,
                    received_at=received_at,
                    filename=filename or ("attachment.pdf" if is_pdf else "attachment.jpg"),
                    payload=payload_bytes,
                )
            )
    return out


def _fetch_imap_invoice_pdf_attachments(max_messages: int) -> list[InvoiceMailAttachment]:
    settings = load_email_settings()
    if not settings.enabled:
        return []
    if not settings.username or not settings.password:
        return []

    conn = imaplib.IMAP4_SSL(settings.host, settings.port)
    try:
        conn.login(settings.username, settings.password)
        conn.select(settings.folder, readonly=True)
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            # Fallback for cases where messages were already opened in mailbox UI.
            status, data = conn.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

        msg_ids = data[0].split()
        msg_ids = msg_ids[-int(max_messages) :]
        out: list[InvoiceMailAttachment] = []

        for uid in msg_ids:
            status, raw = conn.fetch(uid, "(RFC822)")
            if status != "OK" or not raw or not raw[0]:
                continue
            msg_bytes = raw[0][1] if isinstance(raw[0], tuple) else None
            if not isinstance(msg_bytes, bytes):
                continue

            msg = email.message_from_bytes(msg_bytes)
            subject = _decode_header_text(msg.get("Subject", ""))
            from_raw = _decode_header_text(msg.get("From", ""))
            sender_name, sender_addr = parseaddr(from_raw)
            sender = _decode_header_text(sender_name) or sender_addr or from_raw
            received_at = _parse_date(str(msg.get("Date", "") or ""))
            message_id = str(msg.get("Message-ID", "") or "").strip() or f"imap_{uid.decode(errors='ignore')}"

            for part in msg.walk():
                content_type = str(part.get_content_type() or "").lower()
                filename_raw = part.get_filename()
                filename = _decode_header_text(filename_raw)
                lower_name = filename.lower()
                is_pdf = content_type == "application/pdf" or lower_name.endswith(".pdf")
                is_image = content_type in _ALLOWED_IMAGE_MIME or any(lower_name.endswith(ext) for ext in _ALLOWED_INVOICE_EXTS[1:])
                if filename and not (is_pdf or is_image):
                    continue
                if not filename and not is_pdf and not is_image:
                    continue

                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                out.append(
                    InvoiceMailAttachment(
                        source="imap",
                        message_id=message_id,
                        subject=subject,
                        sender=sender,
                        received_at=received_at,
                        filename=filename or ("attachment.pdf" if is_pdf else "attachment.jpg"),
                        payload=payload,
                    )
                )
        return out
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def fetch_invoice_pdf_attachments(worker_name: str = "", max_messages: int = 20) -> list[InvoiceMailAttachment]:
    """Fetch unread invoice attachments (PDF and scan images) from configured mail source."""
    count = max(1, int(max_messages or 20))

    gmail_error: Exception | None = None
    try:
        gmail_attachments = _fetch_gmail_invoice_pdf_attachments(count, worker_name)
        if gmail_attachments:
            return gmail_attachments
    except Exception as exc:
        gmail_error = exc

    imap_error: Exception | None = None
    try:
        imap_attachments = _fetch_imap_invoice_pdf_attachments(count)
        if imap_attachments:
            return imap_attachments
    except Exception as exc:
        imap_error = exc

    if gmail_error is not None:
        raise RuntimeError(f"Gmail: {gmail_error}")
    if imap_error is not None:
        raise RuntimeError(f"Email IMAP: {imap_error}")
    return []
