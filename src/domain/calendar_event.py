from __future__ import annotations

import uuid
from dataclasses import dataclass

EVENT_TYPES: tuple[str, ...] = (
    "zlecenie",
    "montaz",
    "pomiary",
    "wstepna_wycena",
    "zamowienie_mat",
    "poprawki",
    "badania",
    "bhp",
    "urlop",
    "delegacja",
    "inne",
)

EVENT_TYPE_LABELS: dict[str, str] = {
    "zlecenie": "Zlecenie",
    "montaz": "Montaż",
    "pomiary": "Pomiary",
    "wstepna_wycena": "Wstępna wycena",
    "zamowienie_mat": "Zam. materiałów",
    "poprawki": "Poprawki",
    "badania": "Badania",
    "bhp": "BHP",
    "urlop": "Urlop",
    "delegacja": "Delegacja",
    "inne": "Inne",
}

EVENT_COLORS: dict[str, str] = {
    "zlecenie": "#2563eb",
    "montaz": "#16a34a",
    "pomiary": "#ea580c",
    "wstepna_wycena": "#0891b2",
    "zamowienie_mat": "#65a30d",
    "poprawki": "#b45309",
    "badania": "#7c3aed",
    "bhp": "#dc2626",
    "urlop": "#0ea5e9",
    "delegacja": "#78716c",
    "inne": "#475569",
}

WEB_EVENT_TYPE_ALIASES: dict[str, str] = {
    "measurement": "measurement",
    "installation": "installation",
    "meeting": "meeting",
    "transport": "transport",
    "production": "production",
    "service": "service",
    "other": "other",
    "pomiar": "measurement",
    "pomiary": "measurement",
    "montaz": "installation",
    "montaż": "installation",
    "meeting_internal": "meeting",
    "transport_material": "transport",
    "produkcja": "production",
    "serwis": "service",
    "inne": "other",
    "zlecenie": "other",
    "wstepna_wycena": "meeting",
    "zamowienie_mat": "transport",
    "poprawki": "service",
    "badania": "other",
    "bhp": "other",
    "urlop": "other",
    "delegacja": "transport",
}


def normalize_web_event_type(raw: str) -> str:
    key = str(raw or "").strip().lower()
    return WEB_EVENT_TYPE_ALIASES.get(key, "other")

STATIONS: tuple[str, ...] = (
    "Lakiernia",
    "CNC",
    "Skladanie",
    "Biuro",
    "LAKIERNIA",
    "OKLEJANIE",
    "ZBORKA",
)


@dataclass
class CalendarEvent:
    id: str
    event_type: str   # one of EVENT_TYPES
    title: str
    date: str         # YYYY-MM-DD
    date_end: str = ""  # YYYY-MM-DD or HH:MM
    all_day: bool = True
    station: str = ""      # one of STATIONS or ""
    worker_name: str = ""
    order_code: str = ""
    client_name: str = ""
    location: str = ""
    notes: str = ""
    status: str = "planned"

    @staticmethod
    def new(
        event_type: str,
        title: str,
        date: str,
        date_end: str = "",
        all_day: bool = True,
        station: str = "",
        worker_name: str = "",
        order_code: str = "",
        client_name: str = "",
        location: str = "",
        notes: str = "",
        status: str = "planned",
    ) -> "CalendarEvent":
        return CalendarEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            title=title,
            date=date,
            date_end=date_end,
            all_day=all_day,
            station=station,
            worker_name=worker_name,
            order_code=order_code,
            client_name=client_name,
            location=location,
            notes=notes,
            status=status,
        )

    def to_dict(self) -> dict:
        normalized_type = normalize_web_event_type(self.event_type)
        return {
            "id": self.id,
            "event_type": self.event_type,
            "type": normalized_type,
            "title": self.title,
            "date": self.date,
            "date_end": self.date_end,
            "start_at": self.date,
            "end_at": self.date_end,
            "all_day": self.all_day,
            "station": self.station,
            "worker_name": self.worker_name,
            "assigned_to": self.worker_name,
            "order_code": self.order_code,
            "project_ref": self.order_code,
            "client_name": self.client_name,
            "location": self.location,
            "notes": self.notes,
            "status": self.status,
        }

    @staticmethod
    def from_dict(d: dict) -> "CalendarEvent":
        raw_type = str(d.get("event_type") or d.get("type") or "inne")
        # migrate old key
        if raw_type == "pomiar":
            raw_type = "pomiary"
        
        return CalendarEvent(
            id=str(d.get("id") or ""),
            event_type=raw_type,
            title=str(d.get("title") or ""),
            date=str(d.get("date") or d.get("start_at") or ""),
            date_end=str(d.get("date_end") or d.get("end_at") or ""),
            all_day=bool(d.get("all_day", True)),
            station=str(d.get("station") or ""),
            worker_name=str(d.get("worker_name") or d.get("assigned_to") or ""),
            order_code=str(d.get("order_code") or d.get("project_ref") or ""),
            client_name=str(d.get("client_name") or ""),
            location=str(d.get("location") or ""),
            notes=str(d.get("notes") or ""),
            status=str(d.get("status") or "planned"),
        )

