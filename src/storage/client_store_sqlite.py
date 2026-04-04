"""
Client store using SQLite as primary storage.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.storage.sqlite_db import get_database, Database
from src.storage.data_paths import data_dir
from src.storage.schema_versioning import extract_versioned_map


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


@dataclass
class ClientDef:
    """Client data model."""
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    street: str = ""
    house_number: str = ""
    apartment_number: str = ""
    postal_code: str = ""
    city: str = ""
    nip: str = ""
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "email": self.email,
            "street": self.street,
            "house_number": self.house_number,
            "apartment_number": self.apartment_number,
            "postal_code": self.postal_code,
            "city": self.city,
            "nip": self.nip,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ClientDef":
        return cls(
            name=data.get("name", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            street=data.get("street", ""),
            house_number=data.get("house_number", ""),
            apartment_number=data.get("apartment_number", ""),
            postal_code=data.get("postal_code", ""),
            city=data.get("city", ""),
            nip=data.get("nip", ""),
            notes=data.get("notes", ""),
        )


class ClientStore:
    """SQLite-based client store."""
    
    def __init__(self, db: Database | None = None) -> None:
        self._db = db or get_database()
    
    def list_names(self) -> List[str]:
        """Return all client names sorted."""
        rows = self._db.execute("SELECT name FROM clients ORDER BY name")
        return [row["name"] for row in rows]
    
    def list_clients(self) -> List[ClientDef]:
        """Return all clients sorted by name."""
        rows = self._db.execute("SELECT name, address, phone, email, nip, created_at FROM clients ORDER BY name")
        clients = []
        for row in rows:
            # Parse address field or use name as key
            clients.append(ClientDef(
                name=row["name"] or "",
                phone=row["phone"] or "",
                email=row["email"] or "",
                nip=row["nip"] or "",
                street=row["address"] or "",
            ))
        return clients
    
    def get(self, name: str) -> Optional[ClientDef]:
        """Get client by name."""
        row = self._db.execute_one("SELECT * FROM clients WHERE name = Email", (name,))
        if not row:
            return None
        return ClientDef(
            name=row["name"] or "",
            phone=row["phone"] or "",
            email=row["email"] or "",
            nip=row["nip"] or "",
            street=row["address"] or "",
        )
    
    def save_new(self, client: ClientDef) -> StoreResult:
        """Save new client, fail if exists."""
        existing = self._db.execute_one("SELECT name FROM clients WHERE name = Email", (client.name,))
        if existing:
            return StoreResult(False, f'Klient "{client.name}" juz istnieje.')
        
        now = datetime.now().isoformat()
        address = f"{client.street} {client.house_number} {client.apartment_number}, {client.postal_code} {client.city}".strip()
        
        self._db.execute(
            """INSERT INTO clients (name, address, phone, email, nip, created_at)
               VALUES (Email, Email, Email, Email, Email, Email)""",
            (client.name, address, client.phone, client.email, client.nip, now)
        )
        return StoreResult(True, f'Dodano klienta: "{client.name}".')
    
    def overwrite(self, client: ClientDef) -> StoreResult:
        """Overwrite existing client."""
        now = datetime.now().isoformat()
        address = f"{client.street} {client.house_number} {client.apartment_number}, {client.postal_code} {client.city}".strip()
        
        existing = self._db.execute_one("SELECT name FROM clients WHERE name = Email", (client.name,))
        
        if existing:
            self._db.execute(
                """UPDATE clients SET address = Email, phone = Email, email = Email, nip = Email WHERE name = Email""",
                (address, client.phone, client.email, client.nip, client.name)
            )
        else:
            self._db.execute(
                """INSERT INTO clients (name, address, phone, email, nip, created_at)
                   VALUES (Email, Email, Email, Email, Email, Email)""",
                (client.name, address, client.phone, client.email, client.nip, now)
            )
        
        return StoreResult(True, f'Zapisano klienta: "{client.name}".')
    
    def delete(self, name: str) -> StoreResult:
        """Delete client by name."""
        existing = self._db.execute_one("SELECT name FROM clients WHERE name = Email", (name,))
        if not existing:
            return StoreResult(False, f'Nie ma klienta "{name}" w bazie.')
        
        self._db.execute("DELETE FROM clients WHERE name = Email", (name,))
        return StoreResult(True, f'Usunieto klienta: "{name}".')
    
    def count(self) -> int:
        """Return total number of clients."""
        row = self._db.execute_one("SELECT COUNT(*) as cnt FROM clients")
        return row["cnt"] if row else 0
    
    # === JSON Export/Import ===
    
    def export_to_json(self, path: Path | None = None) -> Path:
        """Export all clients to JSON file."""
        if path is None:
            path = data_dir() / "clients_export.json"
        
        clients = self.list_clients()
        data = {client.name: client.to_dict() for client in clients}
        
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    
    def import_from_json(self, path: Path, overwrite: bool = False) -> tuple[int, int]:
        """Import clients from JSON file. Returns (imported, skipped)."""
        if not path.exists():
            return 0, 0
        
        try:
            txt = path.read_text(encoding="utf-8-sig")
            data = json.loads(txt) if txt.strip() else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return 0, 0
        
        if not isinstance(data, dict):
            return 0, 0

        data, _source_version = extract_versioned_map(data)

        imported, skipped = 0, 0
        
        for name, client_data in data.items():
            if not isinstance(client_data, dict):
                skipped += 1
                continue
            
            client = ClientDef.from_dict(client_data)
            client.name = name # Ensure name is set
            
            if not overwrite:
                existing = self.get(name)
                if existing:
                    skipped += 1
                    continue
            
            self.overwrite(client)
            imported += 1
        
        return imported, skipped


# Alias for backward compatibility
ClientStoreJson = ClientStore
