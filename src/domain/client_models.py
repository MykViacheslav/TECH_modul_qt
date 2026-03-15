from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ClientDef:
    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "city": self.city,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientDef":
        data = data or {}
        return cls(
            name=str(data.get("name", "") or ""),
            phone=str(data.get("phone", "") or ""),
            email=str(data.get("email", "") or ""),
            city=str(data.get("city", "") or ""),
            notes=str(data.get("notes", "") or ""),
        )
