from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


def new_worker_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def new_worker_pin() -> str:
    # Krótki awaryjny PIN do ręcznego wpisu na tablecie.
    return f"{uuid.uuid4().int % 1000000:06d}"


@dataclass
class WorkerDef:
    # Dane osobowe
    name: str = ""          # pełna nazwa (używana jako klucz w storage)
    first_name: str = ""    # imię (opcjonalne — wypełniane z name jeśli puste)
    last_name: str = ""     # nazwisko (opcjonalne — wypełniane z name jeśli puste)
    worker_id: str = ""
    pin_code: str = ""
    role: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    exam_status: str = ""
    notes: str = ""

    # Rozliczenia
    pay_mode: str = "Godzinowa"
    hourly_rate: float = 0.0
    daily_rate: float = 0.0
    overtime_multiplier: float = 1.0
    delegation_day_addon_pln: float = 0.0
    montage_hour_addon_pln: float = 0.0
    onsite_hour_addon_pln: float = 0.0
    lacquer_hour_addon_pln: float = 0.0

    # Nowe pola
    bhp_valid_until: str = ""        # data ważności BHP
    medical_exam_until: str = ""     # data ważności badań lekarskich
    advance_pln: float = 0.0         # zaliczka
    payout_pln: float = 0.0          # wypłata
    hours_worked: float = 0.0        # napracowane godziny
    errors_notes: str = ""           # poprawki i błędy

    def get_first_name(self) -> str:
        if self.first_name:
            return self.first_name
        parts = str(self.name or "").split(" ", 1)
        return parts[0]

    def get_last_name(self) -> str:
        if self.last_name:
            return self.last_name
        parts = str(self.name or "").split(" ", 1)
        return parts[1] if len(parts) > 1 else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "worker_id": self.worker_id,
            "pin_code": self.pin_code,
            "role": self.role,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "exam_status": self.exam_status,
            "notes": self.notes,
            "pay_mode": self.pay_mode,
            "hourly_rate": float(self.hourly_rate or 0.0),
            "daily_rate": float(self.daily_rate or 0.0),
            "overtime_multiplier": float(self.overtime_multiplier or 1.0),
            "delegation_day_addon_pln": float(self.delegation_day_addon_pln or 0.0),
            "montage_hour_addon_pln": float(self.montage_hour_addon_pln or 0.0),
            "onsite_hour_addon_pln": float(self.onsite_hour_addon_pln or 0.0),
            "lacquer_hour_addon_pln": float(self.lacquer_hour_addon_pln or 0.0),
            "bhp_valid_until": self.bhp_valid_until,
            "medical_exam_until": self.medical_exam_until,
            "advance_pln": float(self.advance_pln or 0.0),
            "payout_pln": float(self.payout_pln or 0.0),
            "hours_worked": float(self.hours_worked or 0.0),
            "errors_notes": self.errors_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerDef":
        data = data or {}
        return cls(
            name=str(data.get("name", "") or ""),
            first_name=str(data.get("first_name", "") or ""),
            last_name=str(data.get("last_name", "") or ""),
            worker_id=str(data.get("worker_id", "") or ""),
            pin_code=str(data.get("pin_code", "") or ""),
            role=str(data.get("role", "") or ""),
            phone=str(data.get("phone", "") or ""),
            email=str(data.get("email", "") or ""),
            address=str(data.get("address", "") or ""),
            exam_status=str(data.get("exam_status", "") or ""),
            notes=str(data.get("notes", "") or ""),
            pay_mode=str(data.get("pay_mode", "Godzinowa") or "Godzinowa"),
            hourly_rate=float(data.get("hourly_rate", 0.0) or 0.0),
            daily_rate=float(data.get("daily_rate", 0.0) or 0.0),
            overtime_multiplier=float(data.get("overtime_multiplier", 1.0) or 1.0),
            delegation_day_addon_pln=float(data.get("delegation_day_addon_pln", 0.0) or 0.0),
            montage_hour_addon_pln=float(data.get("montage_hour_addon_pln", 0.0) or 0.0),
            onsite_hour_addon_pln=float(data.get("onsite_hour_addon_pln", 0.0) or 0.0),
            lacquer_hour_addon_pln=float(data.get("lacquer_hour_addon_pln", 0.0) or 0.0),
            bhp_valid_until=str(data.get("bhp_valid_until", "") or ""),
            medical_exam_until=str(data.get("medical_exam_until", "") or ""),
            advance_pln=float(data.get("advance_pln", 0.0) or 0.0),
            payout_pln=float(data.get("payout_pln", 0.0) or 0.0),
            hours_worked=float(data.get("hours_worked", 0.0) or 0.0),
            errors_notes=str(data.get("errors_notes", "") or ""),
        )
