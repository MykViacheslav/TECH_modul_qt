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
    pay_mode: str = "Godzinowa"
    hourly_rate: float = 0.0
    daily_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "phone": self.phone,
            "email": self.email,
            "notes": self.notes,
            "pay_mode": self.pay_mode,
            "hourly_rate": float(self.hourly_rate or 0.0),
            "daily_rate": float(self.daily_rate or 0.0),
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
            pay_mode=str(data.get("pay_mode", "Godzinowa") or "Godzinowa"),
            hourly_rate=float(data.get("hourly_rate", 0.0) or 0.0),
            daily_rate=float(data.get("daily_rate", 0.0) or 0.0),
        )
