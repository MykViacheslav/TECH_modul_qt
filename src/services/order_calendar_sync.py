"""
Order -> calendar synchronization helpers.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from typing import Optional

from src.domain.calendar_event import CalendarEvent
from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.order_store_json import OrderStoreJson


_STATUS_STAGE_ORDER: tuple[str, ...] = (
    "nowe",
    "wycena",
    "wycena szybka",
    "oczekiwanie na klienta",
    "wstrzymane",
    "zaakceptowane",
    "zakup materialow",
    "w produkcji",
    "lakiernia",
    "montaz",
    "poprawki",
    "gotowe",
    "anulowane",
    "zakonczone",
    "zamkniete",
)

_STAGE_TO_STATUS_KEY: dict[str, str] = {
    "projekt": "nowe",
    "wycena": "wycena",
    "zakup materialow": "zakup materialow",
    "produkcja": "w produkcji",
    "lakiernia": "lakiernia",
    "montaz": "montaz",
    "poprawki": "poprawki",
    "probki": "wycena szybka",
}

_STAGE_TO_EVENT_TYPE: dict[str, str] = {
    "projekt": "zlecenie",
    "wycena": "wstepna_wycena",
    "zakup materialow": "zamowienie_mat",
    "produkcja": "zlecenie",
    "lakiernia": "zlecenie",
    "montaz": "montaz",
    "poprawki": "poprawki",
    "probki": "inne",
}

_STAGE_TO_STATION: dict[str, str] = {
    "projekt": "Biuro",
    "wycena": "Biuro",
    "zakup materialow": "Biuro",
    "produkcja": "CNC",
    "lakiernia": "Lakiernia",
    "montaz": "Skladanie",
    "poprawki": "Skladanie",
    "probki": "Biuro",
}

# (order field, stage title shown in calendar, internal stage key)
_ORDER_STAGE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("date_projekt", "Projekt", "projekt"),
    ("date_wycena", "Wycena", "wycena"),
    ("date_zakup_mat", "Zakup materialow", "zakup materialow"),
    ("date_produkcja", "Produkcja", "produkcja"),
    ("date_montaz", "Montaz", "montaz"),
    ("date_poprawki", "Poprawki", "poprawki"),
    ("date_probki", "Probki", "probki"),
)


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("ą", "a")
        .replace("ć", "c")
        .replace("ę", "e")
        .replace("ł", "l")
        .replace("ń", "n")
        .replace("ó", "o")
        .replace("ś", "s")
        .replace("ż", "z")
        .replace("ź", "z")
    )
    # Handles odd unicode forms safely.
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    return text


class OrderCalendarSync:
    def __init__(self) -> None:
        self._order_store = OrderStoreJson()
        self._calendar_store = CalendarEventStoreJson()

    @staticmethod
    def _get_stage_index(status: str) -> int:
        key = _normalize_text(status)
        try:
            return _STATUS_STAGE_ORDER.index(key)
        except ValueError:
            return -1

    def sync_all(self, worker_filter: Optional[str] = None) -> int:
        touched = 0
        orders = list(self._order_store.list_orders())
        existing_codes = {str(getattr(order, "code", "") or "").strip() for order in orders}

        for order in orders:
            touched += self._sync_order(order, worker_filter=worker_filter)

        # Cleanup stale auto-generated events for deleted orders.
        all_events = list(self._calendar_store.list_events())
        for event in all_events:
            if not str(getattr(event, "id", "") or "").startswith("order_"):
                continue
            order_code = str(getattr(event, "order_code", "") or "").strip()
            if order_code and order_code not in existing_codes:
                self._calendar_store.delete(str(getattr(event, "id", "") or ""))
                touched += 1

        return touched

    def sync_order(self, order_code: str) -> int:
        order = self._order_store.get(str(order_code or "").strip())
        if order is None:
            return 0
        return self._sync_order(order)

    def _sync_order(self, order, worker_filter: Optional[str] = None) -> int:
        touched = 0
        order_code = str(getattr(order, "code", "") or "").strip()
        if not order_code:
            return 0

        worker_name = str(getattr(order, "worker_name", "") or "").strip()
        if worker_filter and worker_name != worker_filter:
            return 0

        client_name = str(getattr(order, "client_name", "") or "").strip()
        order_status = str(getattr(order, "status", "") or "").strip()
        order_status_key = _normalize_text(order_status)
        order_stage_idx = self._get_stage_index(order_status)
        hold_stage_idx = self._get_stage_index("Wstrzymane")

        # Build expected events from order stage dates.
        expected_ids: set[str] = set()
        existing_for_order: dict[str, CalendarEvent] = {
            ev.id: ev
            for ev in self._calendar_store.list_events()
            if str(getattr(ev, "order_code", "") or "").strip() == order_code
            and str(getattr(ev, "id", "") or "").startswith("order_")
        }

        for field_name, stage_title, stage_key in _ORDER_STAGE_FIELDS:
            date_str = str(getattr(order, field_name, "") or "").strip()
            if not date_str:
                continue

            event_id = f"order_{order_code}_{stage_key}_{date_str}"
            expected_ids.add(event_id)
            stage_status_idx = self._get_stage_index(_STAGE_TO_STATUS_KEY.get(stage_key, stage_key))

            if order_status_key == "anulowane":
                stage_status = "anulowany"
            elif order_status_key == "wstrzymane":
                if stage_status_idx < hold_stage_idx:
                    stage_status = "zakonczony"
                else:
                    stage_status = "wstrzymany"
            elif stage_status_idx < order_stage_idx:
                stage_status = "zakonczony"
            elif stage_status_idx == order_stage_idx:
                stage_status = "w_trakcie"
            else:
                stage_status = "zaplanowany"

            payload = {
                "source": "order_sync",
                "status": stage_status,
                "order_status": order_status,
                "stage": stage_title,
            }
            notes = json.dumps(payload, ensure_ascii=False)
            title = f"{order_code} - {stage_title}"
            if client_name:
                title += f" ({client_name})"

            new_event = CalendarEvent(
                id=event_id,
                event_type=_STAGE_TO_EVENT_TYPE.get(stage_key, "inne"),
                station=_STAGE_TO_STATION.get(stage_key, ""),
                title=title,
                date=date_str,
                worker_name=worker_name,
                order_code=order_code,
                notes=notes,
            )

            old = existing_for_order.get(event_id)
            if old is None:
                self._calendar_store.save(new_event)
                touched += 1
            else:
                if old.to_dict() != new_event.to_dict():
                    self._calendar_store.save(new_event)
                    touched += 1

        # Remove stale stage events for this order (e.g., changed date/status flow).
        for event_id in list(existing_for_order.keys()):
            if event_id not in expected_ids:
                self._calendar_store.delete(event_id)
                touched += 1

        return touched

    def cleanup_past_events(self, days_old: int = 30) -> int:
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=max(0, int(days_old)))).strftime("%Y-%m-%d")
        touched = 0
        for event in list(self._calendar_store.list_events()):
            event_id = str(getattr(event, "id", "") or "")
            event_date = str(getattr(event, "date", "") or "").strip()
            if not event_id.startswith("order_"):
                continue
            if event_date and event_date < cutoff:
                self._calendar_store.delete(event_id)
                touched += 1
        return touched


def sync_orders_to_calendar() -> int:
    return OrderCalendarSync().sync_all()


def sync_single_order(order_code: str) -> int:
    return OrderCalendarSync().sync_order(order_code)
