from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.app_settings import load_telegram_settings  # noqa: E402


@dataclass(frozen=True)
class _MediaItem:
    file_id: str
    file_unique_id: str
    message_id: int
    message_ts: int
    source_kind: str


def _api_base(bot_token: str) -> str:
    token = str(bot_token or "").strip()
    if not token:
        raise ValueError("Brak Telegram Bot Token.")
    return f"https://api.telegram.org/bot{token}"


def _json_request(url: str, timeout_s: int = 30) -> dict:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_s) as res:
            payload = res.read().decode("utf-8", errors="replace")
            obj = json.loads(payload) if payload else {}
            if not bool(obj.get("ok", False)):
                raise RuntimeError(str(obj.get("description", "Blad Telegram API")))
            result = obj.get("result")
            return result if isinstance(result, dict) else {"_items": result}
    except HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Brak polaczenia z Telegram: {exc.reason}") from exc


def _json_list_request(url: str, timeout_s: int = 30) -> list[dict]:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_s) as res:
            payload = res.read().decode("utf-8", errors="replace")
            obj = json.loads(payload) if payload else {}
            if not bool(obj.get("ok", False)):
                raise RuntimeError(str(obj.get("description", "Blad Telegram API")))
            result = obj.get("result")
            return result if isinstance(result, list) else []
    except HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Brak polaczenia z Telegram: {exc.reason}") from exc


def _download_bytes(url: str, timeout_s: int = 45) -> bytes:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_s) as res:
            return res.read()
    except HTTPError as exc:
        raise RuntimeError(f"Pobieranie pliku nieudane (HTTP {exc.code}: {exc.reason})") from exc
    except URLError as exc:
        raise RuntimeError(f"Pobieranie pliku nieudane ({exc.reason})") from exc


def _load_state(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _best_photo_variant(photo_variants: list[dict]) -> dict | None:
    if not isinstance(photo_variants, list) or not photo_variants:
        return None

    def _score(item: dict) -> int:
        if not isinstance(item, dict):
            return -1
        size = int(item.get("file_size", 0) or 0)
        width = int(item.get("width", 0) or 0)
        height = int(item.get("height", 0) or 0)
        return max(size, width * height)

    return max((x for x in photo_variants if isinstance(x, dict)), key=_score, default=None)


def _extract_media_items(message: dict) -> list[_MediaItem]:
    if not isinstance(message, dict):
        return []
    message_id = int(message.get("message_id", 0) or 0)
    message_ts = int(message.get("date", 0) or 0)
    out: list[_MediaItem] = []

    photo = _best_photo_variant(message.get("photo") or [])
    if isinstance(photo, dict):
        file_id = str(photo.get("file_id", "") or "").strip()
        file_unique_id = str(photo.get("file_unique_id", "") or "").strip()
        if file_id and file_unique_id:
            out.append(
                _MediaItem(
                    file_id=file_id,
                    file_unique_id=file_unique_id,
                    message_id=message_id,
                    message_ts=message_ts,
                    source_kind="photo",
                )
            )

    doc = message.get("document")
    if isinstance(doc, dict):
        mime_type = str(doc.get("mime_type", "") or "").strip().lower()
        if mime_type.startswith("image/"):
            file_id = str(doc.get("file_id", "") or "").strip()
            file_unique_id = str(doc.get("file_unique_id", "") or "").strip()
            if file_id and file_unique_id:
                out.append(
                    _MediaItem(
                        file_id=file_id,
                        file_unique_id=file_unique_id,
                        message_id=message_id,
                        message_ts=message_ts,
                        source_kind="document_image",
                    )
                )
    return out


def _message_from_update(update: dict) -> dict | None:
    if not isinstance(update, dict):
        return None
    for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
        maybe = update.get(key)
        if isinstance(maybe, dict):
            return maybe
    return None


def _chat_id_from_message(message: dict) -> str:
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return ""
    cid = chat.get("id")
    return str(cid).strip() if cid is not None else ""


def _ext_from_file_path(file_path: str, source_kind: str) -> str:
    suffix = Path(file_path).suffix.strip().lower()
    if suffix:
        return suffix
    return ".jpg" if source_kind in {"photo", "document_image"} else ".bin"


def run_download(
    bot_token: str,
    chat_id: str,
    output_dir: Path,
    state_path: Path,
    limit: int,
    all_history: bool,
) -> tuple[int, int]:
    base = _api_base(bot_token)
    output_dir.mkdir(parents=True, exist_ok=True)

    state = _load_state(state_path)
    state_key = chat_id if chat_id else "__all__"
    offset = None
    if not all_history:
        last_seen = int(state.get(state_key, 0) or 0)
        if last_seen > 0:
            offset = last_seen + 1

    params = {"limit": max(1, min(int(limit), 100))}
    if offset is not None:
        params["offset"] = offset
    updates_url = f"{base}/getUpdates?{urlencode(params)}"
    updates = _json_list_request(updates_url, timeout_s=40)
    updates_sorted = sorted(
        (x for x in updates if isinstance(x, dict)),
        key=lambda item: int(item.get("update_id", 0) or 0),
    )

    downloaded = 0
    skipped = 0
    max_update_id = 0
    seen_unique: set[str] = set()
    for upd in updates_sorted:
        update_id = int(upd.get("update_id", 0) or 0)
        if update_id > max_update_id:
            max_update_id = update_id
        message = _message_from_update(upd)
        if not isinstance(message, dict):
            continue

        msg_chat_id = _chat_id_from_message(message)
        if chat_id and msg_chat_id != chat_id:
            continue

        for media in _extract_media_items(message):
            if media.file_unique_id in seen_unique:
                skipped += 1
                continue
            seen_unique.add(media.file_unique_id)

            get_file_url = f"{base}/getFile?{urlencode({'file_id': media.file_id})}"
            result = _json_request(get_file_url, timeout_s=30)
            file_path = str(result.get("file_path", "") or "").strip()
            if not file_path:
                skipped += 1
                continue

            ext = _ext_from_file_path(file_path, media.source_kind)
            ts = datetime.fromtimestamp(max(0, media.message_ts)).strftime("%Y%m%d_%H%M%S")
            filename = f"tg_{ts}_{media.message_id}_{media.file_unique_id[:12]}{ext}"
            target = output_dir / filename
            if target.exists():
                skipped += 1
                continue

            file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            payload = _download_bytes(file_url, timeout_s=60)
            target.write_bytes(payload)
            downloaded += 1
            print(f"POBRANO: {target}")

    if max_update_id > 0:
        state[state_key] = max_update_id
        _save_state(state_path, state)

    return downloaded, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Pobiera zdjecia z Telegram Bot API.")
    parser.add_argument("--limit", type=int, default=100, help="Maksymalnie ile update'ow pobrac (1-100).")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ROOT / "pliki pobrane" / "telegram"),
        help="Folder docelowy na zdjecia.",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=str(ROOT / "data" / "telegram_photo_fetch_state.json"),
        help="Plik stanu z ostatnim update_id.",
    )
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="Pobierz od najstarszych dostepnych update'ow (bez offsetu ze stanu).",
    )
    parser.add_argument("--chat-id", type=str, default="", help="Nadpisz chat_id z ustawien aplikacji.")
    parser.add_argument("--bot-token", type=str, default="", help="Nadpisz bot token z ustawien aplikacji.")
    args = parser.parse_args()

    settings = load_telegram_settings()
    bot_token = str(args.bot_token or settings.bot_token or "").strip()
    chat_id = str(args.chat_id or settings.chat_id or "").strip()

    if not bot_token:
        print("Brak bot token. Ustaw Telegram w aplikacji lub podaj --bot-token.")
        return 2

    try:
        downloaded, skipped = run_download(
            bot_token=bot_token,
            chat_id=chat_id,
            output_dir=Path(args.output_dir),
            state_path=Path(args.state_file),
            limit=int(args.limit),
            all_history=bool(args.all_history),
        )
    except Exception as exc:
        print(f"BLAD: {exc}")
        return 1

    print(f"KONIEC: pobrano={downloaded}, pominieto={skipped}, folder={Path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
