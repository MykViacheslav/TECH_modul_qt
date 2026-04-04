from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.storage.safe_json_io import read_json_file, write_json_atomic


MapMigrator = Callable[[str, dict[str, Any], int], dict[str, Any]]


def extract_versioned_map(data: Any) -> tuple[dict[str, dict[str, Any]], int]:
    """
    Return (items_map, schema_version) for either:
    - old format: { "<id>": {...} }
    - new format: { "schema_version": N, "items": { "<id>": {...} } }
    """
    if isinstance(data, dict) and isinstance(data.get("items"), dict):
        version_raw = data.get("schema_version", 1)
        try:
            version = int(version_raw)
        except Exception:
            version = 1
        items_raw = data.get("items", {})
        items = {
            str(key): value
            for key, value in items_raw.items()
            if isinstance(value, dict)
        }
        return items, max(1, version)

    if isinstance(data, dict):
        items = {
            str(key): value
            for key, value in data.items()
            if isinstance(value, dict)
        }
        return items, 1

    return {}, 1


def read_versioned_map_file(
    path: Path,
    *,
    current_version: int,
    migrate_record: MapMigrator | None = None,
) -> dict[str, dict[str, Any]]:
    raw = read_json_file(path, default={}, expected_type=dict)

    items, source_version = extract_versioned_map(raw)

    needs_write = source_version < int(current_version)
    normalized: dict[str, dict[str, Any]] = {}
    for key, value in items.items():
        migrated = dict(value)
        if migrate_record is not None:
            try:
                migrated = dict(migrate_record(key, migrated, source_version) or {})
            except Exception:
                migrated = dict(value)
        if migrated != value:
            needs_write = True
        normalized[str(key)] = migrated

    if not isinstance(raw, dict) or "schema_version" not in raw or "items" not in raw:
        needs_write = True

    if needs_write:
        write_versioned_map_file(path, normalized, current_version=current_version)

    return normalized


def write_versioned_map_file(
    path: Path,
    items: dict[str, dict[str, Any]],
    *,
    current_version: int,
) -> None:
    payload = {
        "schema_version": int(max(1, current_version)),
        "items": {
            str(key): value
            for key, value in (items or {}).items()
            if isinstance(value, dict)
        },
    }
    write_json_atomic(path, payload, ensure_ascii=False, indent=2, create_backup=True)
