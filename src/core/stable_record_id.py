from __future__ import annotations

from secrets import token_hex
from typing import Any, Dict

RECORD_PREFIXES: Dict[str, str] = {
    "module": "mod",
    "client": "cli",
    "order": "ord",
    "employee": "emp",
    "finance_document": "fdc",
    "finance_payment": "fpt",
    "vat_entry": "vat",
    "cash_operation": "csh",
}


def _normalize_prefix(prefix: str) -> str:
    value = str(prefix or "").strip().lower()
    if not value or not value.isascii() or not value.isalnum():
        raise ValueError(f"Nieprawidlowy prefiks ID: {prefix!r}")
    return value


def new_record_id(prefix: str) -> str:
    normalized = _normalize_prefix(prefix)
    return f"{normalized}_{token_hex(6)}"


def new_typed_record_id(record_type: str) -> str:
    key = str(record_type or "").strip().lower()
    prefix = RECORD_PREFIXES.get(key)
    if not prefix:
        raise ValueError(f"Nieznany typ rekordu dla ID: {record_type!r}")
    return new_record_id(prefix)


def ensure_record_id(data: Dict[str, Any], prefix: str, field_name: str = "id") -> Dict[str, Any]:
    payload = dict(data or {})
    existing = str(payload.get(field_name, "") or "").strip()
    expected_prefix = f"{_normalize_prefix(prefix)}_"
    if not existing.startswith(expected_prefix):
        payload[field_name] = new_record_id(prefix)
    return payload


def ensure_module_record_id(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data or {})
    # migracja legacy: module_id -> id
    legacy_module_id = str(payload.get("module_id", "") or "").strip()
    id_value = str(payload.get("id", "") or "").strip()

    if legacy_module_id.startswith("mod_"):
        payload["id"] = legacy_module_id
        payload["module_id"] = legacy_module_id
        return payload

    if id_value.startswith("mod_"):
        payload["module_id"] = id_value
        return payload

    payload = ensure_record_id(payload, "mod", field_name="id")
    payload["module_id"] = str(payload.get("id", "") or "")
    return payload

