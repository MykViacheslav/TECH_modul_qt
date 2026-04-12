from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ClientDef:
    id: str = ""
    name: str = ""
    phone: str = ""
    email: str = ""
    street: str = ""
    house_number: str = ""
    apartment_number: str = ""
    postal_code: str = ""
    city: str = ""
    notes: str = ""
    client_id: str = ""
    first_name: str = ""
    last_name: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "street": self.street,
            "house_number": self.house_number,
            "apartment_number": self.apartment_number,
            "postal_code": self.postal_code,
            "city": self.city,
            "notes": self.notes,
            "client_id": self.client_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientDef":
        data = data or {}
        raw_id = str(data.get("id", "") or "")
        raw_client_id = str(data.get("client_id", "") or "")
        return cls(
            id=raw_id or raw_client_id,
            name=str(data.get("name", "") or ""),
            phone=str(data.get("phone", "") or ""),
            email=str(data.get("email", "") or ""),
            street=str(data.get("street", "") or ""),
            house_number=str(data.get("house_number", "") or ""),
            apartment_number=str(data.get("apartment_number", "") or ""),
            postal_code=str(data.get("postal_code", "") or ""),
            city=str(data.get("city", "") or ""),
            notes=str(data.get("notes", "") or ""),
            client_id=raw_client_id or raw_id,
            first_name=str(data.get("first_name", "") or ""),
            last_name=str(data.get("last_name", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            updated_at=str(data.get("updated_at", "") or ""),
        )
