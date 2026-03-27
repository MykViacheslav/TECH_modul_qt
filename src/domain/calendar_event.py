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
    station: str      # one of STATIONS or ""
    title: str
    date: str         # YYYY-MM-DD
    date_end: str = ""  # YYYY-MM-DD (opcjonalnie dla zakresu)
    worker_name: str = ""
    order_code: str = ""
    notes: str = ""

    @staticmethod
    def new(
        event_type: str,
        station: str,
        title: str,
        date: str,
        date_end: str = "",
        worker_name: str = "",
        order_code: str = "",
        notes: str = "",
    ) -> "CalendarEvent":
        return CalendarEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            station=station,
            title=title,
            date=date,
            date_end=date_end,
            worker_name=worker_name,
            order_code=order_code,
            notes=notes,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "station": self.station,
            "title": self.title,
            "date": self.date,
            "date_end": self.date_end,
            "worker_name": self.worker_name,
            "order_code": self.order_code,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "CalendarEvent":
        raw_type = str(d.get("event_type") or "inne")
        # migrate old key
        if raw_type == "pomiar":
            raw_type = "pomiary"
        return CalendarEvent(
            id=str(d.get("id") or ""),
            event_type=raw_type,
            station=str(d.get("station") or ""),
            title=str(d.get("title") or ""),
            date=str(d.get("date") or ""),
            date_end=str(d.get("date_end") or ""),
            worker_name=str(d.get("worker_name") or ""),
            order_code=str(d.get("order_code") or ""),
            notes=str(d.get("notes") or ""),
        )
