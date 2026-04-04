from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _api_base(bot_token: str) -> str:
    token = str(bot_token or "").strip()
    if not token:
        raise ValueError("Brak Telegram Bot Token.")
    return f"https://api.telegram.org/bot{token}"


def send_text_message(bot_token: str, chat_id: str, text: str) -> None:
    base = _api_base(bot_token)
    payload = json.dumps(
        {
            "chat_id": str(chat_id or "").strip(),
            "text": str(text or "").strip(),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = Request(
        f"{base}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8", errors="replace")
            obj = json.loads(body) if body else {}
            if not bool(obj.get("ok", False)):
                raise RuntimeError(str(obj.get("description", "Blad Telegram API")))
    except HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Brak polaczenia z Telegram: {exc.reason}") from exc


def send_document(bot_token: str, chat_id: str, file_path: str | Path, caption: str = "") -> None:
    base = _api_base(bot_token)
    chat = str(chat_id or "").strip()
    if not chat:
        raise ValueError("Brak Telegram chat_id.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku: {path}")

    file_bytes = path.read_bytes()
    filename = path.name
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    boundary = f"----TECHMODUL{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def _field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    _field("chat_id", chat)
    if str(caption or "").strip():
        _field("caption", str(caption).strip())

    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode("utf-8")
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    parts.append(file_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    req = Request(
        f"{base}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=35) as res:
            payload = res.read().decode("utf-8", errors="replace")
            obj = json.loads(payload) if payload else {}
            if not bool(obj.get("ok", False)):
                raise RuntimeError(str(obj.get("description", "Blad Telegram API")))
    except HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Brak polaczenia z Telegram: {exc.reason}") from exc


def send_pdf_document(bot_token: str, chat_id: str, pdf_path: str | Path, caption: str = "") -> None:
    send_document(bot_token=bot_token, chat_id=chat_id, file_path=pdf_path, caption=caption)
