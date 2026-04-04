from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


def new_alarm_id() -> str:
    return str(uuid.uuid4())[:8].upper()


ALARM_CATEGORIES = (
    "materialy",
    "platnosci",
    "kasa",
    "pracownicy",
    "terminy",
    "faktury",
    "projekty",
    "produkcja",
    "inne",
)

ALARM_SEVERITY = (
    "krytyczny",
    "ostrzezenie",
    "info",
)

ALARM_CATEGORY_LABELS = {
    "materialy": "Materiały",
    "platnosci": "Płatności",
    "kasa": "Kasa",
    "pracownicy": "Pracownicy",
    "terminy": "Terminy",
    "faktury": "Faktury",
    "projekty": "Projekty",
    "produkcja": "Produkcja",
    "inne": "Inne",
}

ALARM_SEVERITY_LABELS = {
    "krytyczny": "🔴 Krytyczny",
    "ostrzezenie": "🟡 Ostrzeżenie",
    "info": "🔵 Informacja",
}


@dataclass
class AlarmDef:
    alarm_id: str = ""
    category: str = "inne"
    severity: str = "info"
    title: str = ""
    description: str = ""
    related_order: str = ""
    related_client: str = ""
    related_worker: str = ""
    related_material: str = ""
    created_at: str = ""
    due_date: str = ""
    is_resolved: bool = False
    resolved_at: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alarm_id": self.alarm_id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "related_order": self.related_order,
            "related_client": self.related_client,
            "related_worker": self.related_worker,
            "related_material": self.related_material,
            "created_at": self.created_at,
            "due_date": self.due_date,
            "is_resolved": bool(self.is_resolved),
            "resolved_at": self.resolved_at,
            "extra": dict(self.extra or {}),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlarmDef":
        data = data or {}
        return cls(
            alarm_id=str(data.get("alarm_id", "") or ""),
            category=str(data.get("category", "inne") or "inne"),
            severity=str(data.get("severity", "info") or "info"),
            title=str(data.get("title", "") or ""),
            description=str(data.get("description", "") or ""),
            related_order=str(data.get("related_order", "") or ""),
            related_client=str(data.get("related_client", "") or ""),
            related_worker=str(data.get("related_worker", "") or ""),
            related_material=str(data.get("related_material", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            due_date=str(data.get("due_date", "") or ""),
            is_resolved=bool(data.get("is_resolved", False)),
            resolved_at=str(data.get("resolved_at", "") or ""),
            extra=dict(data.get("extra", {}) or {}),
        )
