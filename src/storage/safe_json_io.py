from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class JsonFileError(RuntimeError):
    """Raised when a JSON file cannot be safely read or written."""


class JsonFileCorruptedError(JsonFileError):
    """Raised when a JSON file exists but has invalid content."""


_MISSING = object()


def _read_json_once(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.exception("Nie udalo sie odczytac pliku JSON: %s", path)
        raise JsonFileError(f"Nie udalo sie odczytac pliku JSON: {path}") from exc


def _parse_json_text(
    *,
    path: Path,
    raw_text: str,
    expected_type: type[Any] | tuple[type[Any], ...] | None,
) -> Any:
    if not raw_text.strip():
        return _MISSING

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.exception("Uszkodzony plik JSON (blad dekodowania): %s", path)
        raise JsonFileCorruptedError(f"Uszkodzony plik JSON: {path}") from exc
    except Exception as exc:
        logger.exception("Nie udalo sie sparsowac pliku JSON: %s", path)
        raise JsonFileError(f"Nie udalo sie sparsowac pliku JSON: {path}") from exc

    if expected_type is not None and not isinstance(data, expected_type):
        expected_name = (
            " | ".join(t.__name__ for t in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        logger.error(
            "Nieoczekiwany typ danych w JSON. path=%s expected=%s got=%s",
            path,
            expected_name,
            type(data).__name__,
        )
        raise JsonFileCorruptedError(
            f"Nieoczekiwany typ danych w pliku JSON: {path} (oczekiwano {expected_name})"
        )

    return data


def read_json_file(
    path: Path,
    *,
    default: Any,
    expected_type: type[Any] | tuple[type[Any], ...] | None = None,
    recover_from_backup: bool = True,
) -> Any:
    """
    Read JSON from file.

    Returns `default` only when file is missing or empty.
    Raises JsonFileCorruptedError for invalid JSON or unexpected root type.
    """
    if not path.exists():
        return default

    try:
        raw_text = _read_json_once(path)
        parsed = _parse_json_text(path=path, raw_text=raw_text, expected_type=expected_type)
        return default if parsed is _MISSING else parsed
    except JsonFileError:
        if not recover_from_backup:
            raise

        backup_path = path.with_name(f"{path.name}.bak")
        if not backup_path.exists():
            raise

        logger.warning("Proba odzyskania JSON z kopii zapasowej: %s -> %s", path, backup_path)
        backup_raw = _read_json_once(backup_path)
        backup_parsed = _parse_json_text(path=backup_path, raw_text=backup_raw, expected_type=expected_type)
        if backup_parsed is _MISSING:
            return default
        return backup_parsed


def write_json_atomic(
    path: Path,
    payload: Any,
    *,
    ensure_ascii: bool = False,
    indent: int = 2,
    create_backup: bool = True,
) -> None:
    """
    Write JSON atomically and keep a `.bak` copy before overwrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    backup_path = path.with_name(f"{path.name}.bak")

    try:
        if create_backup and path.exists():
            shutil.copy2(path, backup_path)
    except Exception as exc:
        logger.exception("Nie udalo sie utworzyc kopii zapasowej: %s", backup_path)
        raise JsonFileError(f"Nie udalo sie utworzyc kopii zapasowej: {backup_path}") from exc

    try:
        data = json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent)
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.exception("Nie udalo sie zapisac pliku JSON atomowo: %s", path)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise JsonFileError(f"Nie udalo sie zapisac pliku JSON: {path}") from exc
