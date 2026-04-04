from __future__ import annotations

"""
Odczyt wiadomości WhatsApp przez Twilio REST API.

Jak to działa:
1. Klienci piszą na Twój numer WhatsApp (Twilio Sandbox lub produkcyjny).
2. Twilio przechowuje wszystkie wiadomości w swojej chmurze.
3. Ten moduł odpytuje Twilio API i pobiera wiadomości przysłane DO Twojego numeru.
4. Nie wymaga publicznego URL ani serwera — działa jako polling.

Konfiguracja (w aplikacji → ⚙ → WhatsApp):
  - Account SID   : z https://console.twilio.com
  - Auth Token    : z https://console.twilio.com
  - Twój numer WA : np. whatsapp:+48... (lub sandbox: whatsapp:+14155238886)

Sandbox (darmowe testy):
  - Klient wysyła "join <słowo>" na +14155238886 przez WhatsApp
  - Twilio łączy klienta z Twoim sandboxem
  - Wiadomości pojawiają się w panelu: https://console.twilio.com/us1/develop/sms/overview
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List

from src.app.app_settings import WhatsAppSettings
from src.integrations.message_store import InboxMessage

_TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
_SNIPPET_LEN = 300


def fetch_whatsapp_messages(settings: WhatsAppSettings) -> List[InboxMessage]:
    """
    Pobiera wiadomości WhatsApp przysłane DO Twojego numeru przez Twilio REST API.
    Zwraca listę InboxMessage. Rzuca wyjątek przy błędzie połączenia.
    """
    if not settings.enabled or not settings.account_sid or not settings.auth_token:
        return []

    import requests  # lazy import — zainstalowane w venv

    url = _TWILIO_API.format(sid=settings.account_sid)
    params: dict = {
        "PageSize": settings.max_fetch,
        "To": settings.to_number or None,
    }
    # Usuń None params
    params = {k: v for k, v in params.items() if v is not None}

    resp = requests.get(
        url,
        params=params,
        auth=(settings.account_sid, settings.auth_token),
        timeout=15,
    )
    resp.raise_for_status()

    data = resp.json()
    raw_messages = data.get("messages", [])

    result: List[InboxMessage] = []
    for m in raw_messages:
        direction = str(m.get("direction", ""))
        # Interesują nas tylko wiadomości przychodzące (od klientów)
        if direction not in ("inbound", ""):
            continue

        from_raw = str(m.get("from", "") or "")
        body = str(m.get("body", "") or "")
        sid = str(m.get("sid", "") or "")
        date_sent = str(m.get("date_sent") or m.get("date_created") or "")

        # Czyść prefix whatsapp:
        sender = from_raw.replace("whatsapp:", "").strip()

        # Stable ID na podstawie Twilio SID
        stable_id = sid if sid else str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{from_raw}:{body[:50]}:{date_sent}")
        )

        # Parsuj datę
        received_at = _parse_twilio_date(date_sent)

        result.append(InboxMessage(
            id=stable_id,
            source="whatsapp",
            sender=sender,
            subject="WhatsApp",
            snippet=body[:_SNIPPET_LEN],
            received_at=received_at,
            read=False,
        ))

    return result


def _parse_twilio_date(raw: str) -> str:
    """Parsuje datę Twilio (RFC 2822) do ISO UTC."""
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    # Twilio format: "Thu, 29 Mar 2026 07:00:00 +0000"
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(raw)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()
