from __future__ import annotations

from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


DEFAULT_ACCOUNTS: dict[str, dict[str, Any]] = {
    "admin": {
        "worker_name": "Viacheslav Mykytiuk",
        "role": "wlasciciel",
        "password": "1234",
        "tab_overrides": {},
        "ui_scale_override": None,
    },
    "IRYNA": {
        "worker_name": "Iryna Mykytiuk",
        "role": "biuro",
        "password": "1234",
        "tab_overrides": {},
        "ui_scale_override": None,
    },
    "ANDRII": {
        "worker_name": "Andrii Borshch",
        "role": "produkcja",
        "password": "1234",
        "tab_overrides": {},
        "ui_scale_override": None,
    },
    "EMILIA": {
        "worker_name": "Emilia Kmita",
        "role": "biuro",
        "password": "1234",
        "tab_overrides": {},
        "ui_scale_override": None,
    },
}


class AccessControlStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "access_control.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, {}, ensure_ascii=False, indent=2)
        self._ensure_defaults()

    def list_accounts(self) -> list[dict[str, Any]]:
        raw = self._read_accounts()
        preferred_order = {name.casefold(): idx for idx, name in enumerate(DEFAULT_ACCOUNTS.keys())}
        accounts: list[dict[str, Any]] = []
        for username in sorted(
            raw.keys(),
            key=lambda u: (preferred_order.get(str(u).strip().casefold(), 999), str(u).strip().casefold()),
        ):
            data = raw.get(username)
            if not isinstance(data, dict):
                continue
            accounts.append(
                {
                    "username": username,
                    "worker_name": str(data.get("worker_name", "") or ""),
                    "role": str(data.get("role", "produkcja") or "produkcja"),
                    "password": str(data.get("password", "1234") or "1234"),
                    "tab_overrides": dict(data.get("tab_overrides", {}) or {}),
                    "ui_scale_override": self._coerce_ui_scale(data.get("ui_scale_override")),
                }
            )
        return accounts

    def find_account(self, login_or_worker: str) -> dict[str, Any] | None:
        needle = str(login_or_worker or "").strip().lower()
        if not needle:
            return None
        for account in self.list_accounts():
            username = str(account.get("username", "") or "").strip().lower()
            worker_name = str(account.get("worker_name", "") or "").strip().lower()
            if needle in (username, worker_name):
                return account
        return None

    def verify_credentials(self, login_or_worker: str, password: str) -> dict[str, Any] | None:
        account = self.find_account(login_or_worker)
        if account is None:
            return None
        expected = str(account.get("password", "") or "")
        if str(password or "") != expected:
            return None
        return account

    def get_tab_override_for_worker(self, worker_name: str, tab_title: str) -> bool | None:
        worker_key = str(worker_name or "").strip().lower()
        tab_key = str(tab_title or "").strip()
        if not worker_key or not tab_key:
            return None
        for account in self.list_accounts():
            if str(account.get("worker_name", "") or "").strip().lower() != worker_key:
                continue
            overrides = account.get("tab_overrides", {})
            value = overrides.get(tab_key) if isinstance(overrides, dict) else None
            if isinstance(value, bool):
                return value
            return None
        return None

    def set_tab_overrides(self, username: str, overrides: dict[str, bool]) -> None:
        data = self._read_raw()
        accounts = data.get("accounts", {})
        if not isinstance(accounts, dict):
            accounts = {}
        key = self._resolve_account_key(accounts, username)
        if not key:
            return
        entry = accounts.get(key, {})
        if not isinstance(entry, dict):
            entry = {}
        entry["tab_overrides"] = {str(k): bool(v) for k, v in (overrides or {}).items()}
        accounts[key] = entry
        data["accounts"] = accounts
        self._write_raw(data)

    def update_role(self, username: str, role: str) -> None:
        data = self._read_raw()
        accounts = data.get("accounts", {})
        if not isinstance(accounts, dict):
            accounts = {}
        key = self._resolve_account_key(accounts, username)
        if not key:
            return
        entry = accounts.get(key, {})
        if not isinstance(entry, dict):
            entry = {}
        entry["role"] = str(role or "produkcja") or "produkcja"
        accounts[key] = entry
        data["accounts"] = accounts
        self._write_raw(data)

    def get_ui_scale_override_for_worker(self, worker_name: str) -> float | None:
        worker_key = str(worker_name or "").strip().lower()
        if not worker_key:
            return None
        for account in self.list_accounts():
            if str(account.get("worker_name", "") or "").strip().lower() != worker_key:
                continue
            return self._coerce_ui_scale(account.get("ui_scale_override"))
        return None

    def set_ui_scale_override(self, username: str, ui_scale: float | None) -> None:
        data = self._read_raw()
        accounts = data.get("accounts", {})
        if not isinstance(accounts, dict):
            accounts = {}
        key = self._resolve_account_key(accounts, username)
        if not key:
            return
        entry = accounts.get(key, {})
        if not isinstance(entry, dict):
            entry = {}
        entry["ui_scale_override"] = self._coerce_ui_scale(ui_scale)
        accounts[key] = entry
        data["accounts"] = accounts
        self._write_raw(data)

    def _ensure_defaults(self) -> None:
        data = self._read_raw()
        accounts = data.get("accounts", {})
        if not isinstance(accounts, dict):
            accounts = {}
        normalized_accounts: dict[str, dict[str, Any]] = {}
        for key, value in accounts.items():
            key_str = str(key or "").strip()
            if key_str and isinstance(value, dict):
                normalized_accounts[key_str] = value
        accounts = normalized_accounts

        changed = False
        for username, defaults in DEFAULT_ACCOUNTS.items():
            existing_key = self._resolve_account_key(accounts, username)
            if existing_key and existing_key != username and existing_key in accounts:
                existing_entry = accounts.pop(existing_key)
                if username not in accounts:
                    accounts[username] = existing_entry
                changed = True

            entry = accounts.get(username)
            if not isinstance(entry, dict):
                entry = {}
                changed = True
            for field in ("worker_name", "role", "password"):
                if not str(entry.get(field, "") or "").strip():
                    entry[field] = defaults[field]
                    changed = True
            if "tab_overrides" not in entry or not isinstance(entry.get("tab_overrides"), dict):
                entry["tab_overrides"] = {}
                changed = True
            if "ui_scale_override" not in entry:
                entry["ui_scale_override"] = self._coerce_ui_scale(defaults.get("ui_scale_override"))
                changed = True
            accounts[username] = entry
        if changed or "accounts" not in data:
            data["accounts"] = accounts
            self._write_raw(data)

    def _read_accounts(self) -> dict[str, dict[str, Any]]:
        raw = self._read_raw()
        accounts = raw.get("accounts", {})
        if not isinstance(accounts, dict):
            return {}
        result: dict[str, dict[str, Any]] = {}
        for key, value in accounts.items():
            if isinstance(value, dict):
                key_str = str(key).strip()
                if key_str:
                    result[key_str] = value
        return result

    @staticmethod
    def _resolve_account_key(accounts: dict[str, Any], username: str) -> str:
        desired = str(username or "").strip()
        if not desired:
            return ""
        desired_cf = desired.casefold()
        for key in accounts.keys():
            key_str = str(key or "").strip()
            if key_str.casefold() == desired_cf:
                return key_str
        return desired

    @staticmethod
    def _coerce_ui_scale(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            val = float(value)
        except Exception:
            return None
        if val <= 0:
            return None
        return max(0.35, min(1.0, val))

    def _read_raw(self) -> dict[str, Any]:
        return read_json_file(self._path, default={}, expected_type=dict)

    def _write_raw(self, raw: dict[str, Any]) -> None:
        write_json_atomic(self._path, raw, ensure_ascii=False, indent=2)
