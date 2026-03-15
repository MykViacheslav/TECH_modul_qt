from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WorkerDef:
    name: str = ""
    role: str = ""
    phone: str = ""
    email: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "phone": self.phone,
            "email": self.email,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerDef":
        data = data or {}
        return cls(
            name=str(data.get("name", "") or ""),
            role=str(data.get("role", "") or ""),
            phone=str(data.get("phone", "") or ""),
            email=str(data.get("email", "") or ""),
            notes=str(data.get("notes", "") or ""),
        )
