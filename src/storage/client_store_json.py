from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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

    def save_new(self, client: ClientDef) -> StoreResult:
        data = self._read_all()
        if client.name in data:
            return StoreResult(False, f'Klient "{client.name}" juz istnieje. Uzyj "Nadpisz".')
        data[client.name] = client.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano klienta: "{client.name}".')

    def overwrite(self, client: ClientDef) -> StoreResult:
        data = self._read_all()
        data[client.name] = client.to_dict()
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
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
