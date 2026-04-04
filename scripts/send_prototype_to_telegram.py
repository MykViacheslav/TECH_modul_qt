from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.app_settings import load_telegram_settings  # noqa: E402
from src.integrations.telegram_sender import send_document, send_text_message  # noqa: E402


ARTIFACT_EXTENSIONS = {".exe", ".msi", ".zip", ".pkg", ".7z", ".rar"}


def find_latest_artifact(root: Path) -> Path | None:
    search_dirs = [root / "dist", root / "build"]
    candidates: list[Path] = []
    for base in search_dirs:
        if not base.exists():
            continue
        for item in base.rglob("*"):
            if not item.is_file():
                continue
            if item.suffix.lower() in ARTIFACT_EXTENSIONS:
                candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def zip_directory(source_dir: Path, output_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"prototype_{ts}.zip"
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED, compresslevel=6) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(source_dir)
                zf.write(path, arcname=str(arcname))
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Wysyla prototyp aplikacji do Telegram bota.")
    parser.add_argument("--path", type=str, default="", help="Sciezka do pliku lub katalogu prototypu.")
    parser.add_argument("--zip-dir", action="store_true", help="Jesli --path wskazuje katalog, spakuj go do ZIP.")
    parser.add_argument("--caption", type=str, default="", help="Opis pliku w Telegram.")
    parser.add_argument("--notify-text", type=str, default="", help="Dodatkowa wiadomosc tekstowa po wysylce.")
    args = parser.parse_args()

    settings = load_telegram_settings()
    bot_token = str(settings.bot_token or "").strip()
    chat_id = str(settings.chat_id or "").strip()
    if not bot_token or not chat_id:
        print("Brak Telegram bot_token/chat_id w ustawieniach aplikacji.")
        return 2

    file_path: Path | None = None
    if str(args.path or "").strip():
        candidate = Path(str(args.path).strip())
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        if candidate.is_dir():
            if not bool(args.zip_dir):
                print("Podana sciezka to katalog. Uzyj --zip-dir albo podaj plik.")
                return 2
            file_path = zip_directory(candidate, ROOT / "build")
            print(f"Spakowano katalog: {file_path}")
        else:
            file_path = candidate
    else:
        file_path = find_latest_artifact(ROOT)
        if file_path is None:
            print("Nie znaleziono artefaktu prototypu (.exe/.msi/.zip/.pkg).")
            return 2

    if file_path is None or not file_path.exists():
        print("Brak pliku do wysylki.")
        return 2

    caption = str(args.caption or "").strip()
    if not caption:
        caption = f"TECH_modul prototyp: {file_path.name}"

    try:
        send_document(
            bot_token=bot_token,
            chat_id=chat_id,
            file_path=file_path,
            caption=caption,
        )
        print(f"Wyslano plik: {file_path}")
        if str(args.notify_text or "").strip():
            send_text_message(
                bot_token=bot_token,
                chat_id=chat_id,
                text=str(args.notify_text).strip(),
            )
            print("Wyslano dodatkowa wiadomosc.")
        return 0
    except Exception as exc:
        print(f"BLAD: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
