"""
Gmail OAuth2 integration czyta nieprzeczytane emaile przez Gmail API.

Jak to dzia a:
1. U ytkownik wchodzi w Google Cloud Console i tworzy projekt + credentials (Client ID + Secret).
2. W aplikacji klika "Zaloguj przez Google" otwiera si przegl darka z ekranem logowania Google.
3. Po zalogowaniu Google przekierowuje na localhost:8080 z kodem autoryzacji.
4. Aplikacja wymienia kod na tokeny (access + refresh) i zapisuje je lokalnie.
5. Przy ka dym pobraniu emaili aplikacja u ywa access_token (od wie anego automatycznie).

Dane wra liwe (Client ID/Secret + tokeny) s przechowywane wy cznie lokalnie w data/.
"""
from __future__ import annotations

import json
import secrets
import threading
import urllib.parse
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List, Optional

from src.integrations.message_store import InboxMessage
from src.storage.data_paths import data_dir

# Google OAuth2 endpoints 
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
_REDIRECT = "http://localhost:8080"
_SNIPPET = 300


def _http_post_form_json(url: str, form: dict[str, str], timeout: int = 15) -> dict:
    body = urllib.parse.urlencode({k: str(v or "") for k, v in (form or {}).items()}).encode("utf-8")
    req = urllib.request.Request(
        str(url or "").strip(),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
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
        return json.loads(payload) if payload else {}
    except Exception as exc:
        raise RuntimeError("Odpowiedz API nie jest poprawnym JSON.") from exc


def _http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, object] | None = None,
    timeout: int = 15,
) -> dict:
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
        return json.loads(payload) if payload else {}
    except Exception as exc:
        raise RuntimeError("Odpowiedz API nie jest poprawnym JSON.") from exc


def _token_path(worker_name: str = "") -> Path:
    """ cie ka do tokenu globalna lub per-pracownik."""
    if worker_name:
        safe = worker_name.strip().lower().replace(" ", "_").replace("/", "_")
        return data_dir() / "gmail_tokens" / f"gmail_token_{safe}.json"
    return data_dir() / "gmail_token.json"


# Token storage 

def load_token(worker_name: str = "") -> dict:
    p = _token_path(worker_name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_token(token: dict, worker_name: str = "") -> None:
    p = _token_path(worker_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_token(worker_name: str = "") -> None:
    p = _token_path(worker_name)
    if p.exists():
        p.unlink()


def is_authenticated(worker_name: str = "") -> bool:
    t = load_token(worker_name)
    return bool(t.get("refresh_token"))


def get_authenticated_email(worker_name: str = "") -> str:
    return load_token(worker_name).get("email", "")


# Local callback server 

class _OAuthCallbackServer:
    """Nas uchuje na localhost:8080 na callback OAuth2."""

    def __init__(self) -> None:
        self.code: Optional[str] = None
        self.error: Optional[str] = None
        self._event = threading.Event()
        self._server: Optional[HTTPServer] = None

    def start(self) -> None:
        instance = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)

                if "code" in params:
                    instance.code = params["code"][0]
                    body = (
                        "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        "<h2 style='color:#1a6e1a'> Zalogowano pomy lnie!</h2>"
                        "<p>Mo esz zamkn t kart i wr ci do aplikacji.</p>"
                        "</body></html>"
                    ).encode("utf-8")
                elif "error" in params:
                    instance.error = params.get("error", ["unknown"])[0]
                    body = (
                        "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        "<h2 style='color:#8a0000'> B d autoryzacji</h2>"
                        "<p>Wr do aplikacji i spr buj ponownie.</p>"
                        "</body></html>"
                    ).encode("utf-8")
                else:
                    body = b"OK"

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                instance._event.set()

            def log_message(self, *args: object) -> None:
                pass # wycisz logi

        self._server = HTTPServer(("127.0.0.1", 8080), Handler)
        t = threading.Thread(target=self._server.serve_forever, daemon=True)
        t.start()

    def wait(self, timeout: float = 120.0) -> bool:
        return self._event.wait(timeout)

    def stop(self) -> None:
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass


# OAuth2 flow 

def build_auth_url(client_id: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": _REDIRECT,
        "response_type": "code",
        "scope": _SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
) -> dict:
    """Wymienia kod autoryzacji na access_token + refresh_token."""
    return _http_post_form_json(
        _TOKEN_URL,
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _REDIRECT,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Od wie a access_token u ywaj c refresh_token."""
    return _http_post_form_json(
        _TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )


def get_valid_access_token(client_id: str, client_secret: str, worker_name: str = "") -> str:
    """Zwraca wa ny access_token, od wie aj c go je li wygas ."""
    token = load_token(worker_name)
    if not token.get("refresh_token"):
        raise RuntimeError("Brak autoryzacji Gmail. Zaloguj si przez Google.")

    # Sprawd czy access_token jest wa ny (z 60s marginesem)
    expires_at_str = token.get("expires_at", "")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) < expires_at - timedelta(seconds=60):
                return token["access_token"]
        except Exception:
            pass

    # Od wie token
    new_data = refresh_access_token(client_id, client_secret, token["refresh_token"])
    expires_in = int(new_data.get("expires_in", 3600))
    token["access_token"] = new_data["access_token"]
    token["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()
    save_token(token, worker_name)
    return token["access_token"]


def do_auth_flow(client_id: str, client_secret: str, worker_name: str = "") -> str:
    """
    Pe ny flow OAuth2:
    1. Uruchamia lokalny serwer callback
    2. Otwiera przegl dark 
    3. Czeka na kod (max 2 minuty)
    4. Wymienia kod na tokeny i zapisuje je
    Zwraca email zalogowanego u ytkownika.
    """
    state = secrets.token_urlsafe(16)
    server = _OAuthCallbackServer()
    server.start()

    try:
        url = build_auth_url(client_id, state)
        webbrowser.open(url)

        got_response = server.wait(timeout=120.0)
        if not got_response:
            raise TimeoutError("Up yn czas oczekiwania na logowanie (2 minuty).")
        if server.error:
            raise RuntimeError(f"Google odm wi dost pu: {server.error}")
        if not server.code:
            raise RuntimeError("Nie otrzymano kodu autoryzacji.")

        token_data = exchange_code_for_tokens(client_id, client_secret, server.code)

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

        # Pobierz email zalogowanego u ytkownika
        try:
            profile = _http_get_json(
                f"{_GMAIL_API}/profile",
                headers={"Authorization": f"Bearer {token['access_token']}"},
                timeout=10,
            )
            token["email"] = str(profile.get("emailAddress", "") or "")
        except Exception:
            pass

        save_token(token, worker_name)
        return token["email"]
    finally:
        server.stop()


# Gmail API odczyt wiadomo ci 

def fetch_unread_gmail(max_results: int = 20, worker_name: str = "") -> List[InboxMessage]:
    """
    Pobiera nieprzeczytane wiadomo ci z Gmail API.
    U ywa przechowanych token w. Rzuca wyj tek przy b dzie.
    """
    token = load_token(worker_name)
    if not token.get("client_id") or not token.get("refresh_token"):
        raise RuntimeError("Gmail nie skonfigurowany. Zaloguj si przez Google.")

    access_token = get_valid_access_token(token["client_id"], token["client_secret"], worker_name)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Lista nieprzeczytanych wiadomo ci
    list_data = _http_get_json(
        f"{_GMAIL_API}/messages",
        headers=headers,
        params={"q": "is:unread in:inbox", "maxResults": int(max_results)},
        timeout=15,
    )
    msg_list = list_data.get("messages", []) or []

    messages: List[InboxMessage] = []
    for item in msg_list:
        msg_id = item["id"]
        try:
            data = _http_get_json(
                f"{_GMAIL_API}/messages/{msg_id}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                timeout=10,
            )
        except Exception:
            continue

        hdrs = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
        snippet = data.get("snippet", "")[:_SNIPPET]

        from_raw = hdrs.get("From", "")
        # Usu format "Imi Nazwisko <email@gmail.com>" "Imi Nazwisko"
        if "<" in from_raw:
            sender = from_raw.split("<")[0].strip().strip('"')
        else:
            sender = from_raw

        subject = hdrs.get("Subject", "(brak tematu)")
        date_raw = hdrs.get("Date", "")
        received_at = _parse_gmail_date(date_raw)

        messages.append(InboxMessage(
            id=f"gmail_{msg_id}",
            source="email",
            sender=sender or from_raw,
            subject=subject,
            snippet=snippet,
            received_at=received_at,
            read=False,
        ))

    return messages


def _parse_gmail_date(raw: str) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()
