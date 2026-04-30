from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import time as _time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_PERF_ENABLED: bool = os.environ.get("TECH_PERF") == "1"
_load_counts: dict[str, int] = {}

# mtime-based read cache: resolved_path -> (mtime_ns, parsed_data)
_read_cache: dict[Path, tuple[int, Any]] = {}


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
    Read JSON from file with mtime-based caching.

    Returns `default` only when file is missing or empty.
    Raises JsonFileCorruptedError for invalid JSON or unexpected root type.
    """
    _t0 = _time.perf_counter_ns() if _PERF_ENABLED else 0
    try:
        if not path.exists():
            _read_cache.pop(path, None)
            return default

        # Cache lookup by mtime
        try:
            current_mtime = path.stat().st_mtime_ns
        except OSError:
            current_mtime = 0

        cached = _read_cache.get(path)
        if cached is not None and cached[0] == current_mtime and current_mtime > 0:
            data = cached[1]
            if expected_type is None or isinstance(data, expected_type):
                return copy.deepcopy(data)

        # Normal read path
        try:
            raw_text = _read_json_once(path)
            parsed = _parse_json_text(path=path, raw_text=raw_text, expected_type=expected_type)
            result = default if parsed is _MISSING else parsed
        except JsonFileError:
            if not recover_from_backup:
                raise

            backup_path = path.with_name(f"{path.name}.bak")
            if not backup_path.exists():
                raise

            logger.warning("Proba odzyskania JSON z kopii zapasowej: %s -> %s", path, backup_path)
            backup_raw = _read_json_once(backup_path)
            backup_parsed = _parse_json_text(path=backup_path, raw_text=backup_raw, expected_type=expected_type)
            result = default if backup_parsed is _MISSING else backup_parsed

        # Update cache
        if current_mtime > 0 and result is not default:
            _read_cache[path] = (current_mtime, copy.deepcopy(result))

        return result
    finally:
        if _PERF_ENABLED:
            _key = path.name if isinstance(path, Path) else str(path)
            _ms = (_time.perf_counter_ns() - _t0) / 1_000_000
            _load_counts[_key] = _load_counts.get(_key, 0) + 1
            if _ms > 1.0 or _load_counts[_key] > 1:
                print(f"[PERF] store.load.{_key}={_ms:.1f}ms count={_load_counts[_key]}")


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
    _t0 = _time.perf_counter_ns() if _PERF_ENABLED else 0
    try:
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

            # Update read cache with freshly written data
            try:
                new_mtime = path.stat().st_mtime_ns
                _read_cache[path] = (new_mtime, copy.deepcopy(payload))
            except OSError:
                _read_cache.pop(path, None)
        except Exception as exc:
            logger.exception("Nie udalo sie zapisac pliku JSON atomowo: %s", path)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise JsonFileError(f"Nie udalo sie zapisac pliku JSON: {path}") from exc
    finally:
        if _PERF_ENABLED:
            _key = path.name if isinstance(path, Path) else str(path)
            _ms = (_time.perf_counter_ns() - _t0) / 1_000_000
            print(f"[PERF] store.save.{_key}={_ms:.1f}ms")


def clear_json_cache() -> None:
    """Clear all cached JSON reads. For testing or manual invalidation."""
    _read_cache.clear()
