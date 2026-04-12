from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.stable_record_id import ensure_record_id
from src.domain.client_models import ClientDef
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class ClientStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "clients.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_names(self) -> List[str]:
        return sorted(list(self._read_all().keys()))

    def list_clients(self) -> List[ClientDef]:
        raw_all = self._read_all()
        return [
            ClientDef.from_dict(raw_all[name])
            for name in sorted(raw_all.keys())
            if isinstance(raw_all.get(name), dict)
        ]

    def get(self, name: str) -> Optional[ClientDef]:
        raw = self._read_all().get(name)
        return ClientDef.from_dict(raw) if isinstance(raw, dict) else None

    def get_by_id(self, client_id: str) -> Optional[ClientDef]:
        wanted = str(client_id or "").strip()
        if not wanted:
            return None
        for raw in self._read_all().values():
            if not isinstance(raw, dict):
                continue
            rec_id = str(raw.get("id", "") or raw.get("client_id", "") or "").strip()
            if rec_id == wanted:
                return ClientDef.from_dict(raw)
        return None

    def save_new(self, client: ClientDef) -> StoreResult:
        data = self._read_all()
        if client.name in data:
            return StoreResult(False, f'Klient "{client.name}" juz istnieje. Uzyj "Nadpisz".')
        data[client.name] = self._build_record(client, previous=None)
        self._write_all(data)
        return StoreResult(True, f'Zapisano klienta: "{client.name}".')

    def overwrite(self, client: ClientDef) -> StoreResult:
        data = self._read_all()
        previous = data.get(client.name)
        data[client.name] = self._build_record(client, previous=previous if isinstance(previous, dict) else None)
        self._write_all(data)
        return StoreResult(True, f'Nadpisano klienta: "{client.name}".')

    def delete(self, name: str) -> StoreResult:
        data = self._read_all()
        if name not in data:
            return StoreResult(False, f'Nie ma klienta "{name}" w bazie.')
        data.pop(name, None)
        self._write_all(data)
        return StoreResult(True, f'Usunieto klienta: "{name}".')

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            if not isinstance(data, dict):
                return {}
            raw_items = data.get("items", data)
            items = raw_items if isinstance(raw_items, dict) else {}
            normalized, changed = self._normalize_records(items)
            if changed:
                self._write_all(normalized)
            return normalized
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_records(self, raw_items: Dict[str, Any]) -> tuple[Dict[str, dict], bool]:
        normalized: Dict[str, dict] = {}
        changed = False
        for name, raw in (raw_items or {}).items():
            key = str(name or "").strip()
            if not key or not isinstance(raw, dict):
                changed = True
                continue
            rec = self._normalize_single_record(key, raw)
            if rec != raw:
                changed = True
            normalized[key] = rec
        return normalized, changed

    def _normalize_single_record(self, name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(raw or {})
        payload["name"] = str(payload.get("name") or name)
        payload = ensure_record_id(payload, "cli", field_name="id")

        domain_id = str(payload.get("client_id", "") or "").strip()
        if not domain_id:
            payload["client_id"] = str(payload.get("id", "") or "")

        now_iso = self._now_iso()
        if not str(payload.get("created_at", "") or "").strip():
            payload["created_at"] = now_iso
        if not str(payload.get("updated_at", "") or "").strip():
            payload["updated_at"] = now_iso
        return payload

    def _build_record(self, client: ClientDef, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = dict(client.to_dict() or {})
        payload["name"] = str(getattr(client, "name", payload.get("name", "")) or payload.get("name", ""))

        if previous:
            prev = self._normalize_single_record(payload["name"], previous)
            if not str(payload.get("id", "") or "").strip():
                payload["id"] = str(prev.get("id", "") or "")
            if not str(payload.get("client_id", "") or "").strip():
                payload["client_id"] = str(prev.get("client_id", "") or "")
            if not str(payload.get("created_at", "") or "").strip():
                payload["created_at"] = str(prev.get("created_at", "") or "")

        payload = self._normalize_single_record(payload["name"], payload)
        payload["updated_at"] = self._now_iso()

        try:
            client.id = str(payload.get("id", "") or "")
            client.client_id = str(payload.get("client_id", "") or "")
            client.created_at = str(payload.get("created_at", "") or "")
            client.updated_at = str(payload.get("updated_at", "") or "")
        except Exception:
            pass

        return payload

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
