from __future__ import annotations

import asyncio

from src.api import main_api
from src.domain.calendar_event import CalendarEvent


class _FakeCalendarStore:
    def __init__(self) -> None:
        self._events: dict[str, CalendarEvent] = {}

    def get_all(self, limit: int = 500):
        events = list(self._events.values())
        return events[: max(1, int(limit))]

    def save(self, event: CalendarEvent) -> CalendarEvent:
        self._events[event.id] = event
        return event

    def get_by_id(self, event_id: str):
        return self._events.get(event_id)

    def delete(self, event_id: str) -> bool:
        if event_id not in self._events:
            return False
        del self._events[event_id]
        return True


def test_calendar_events_crud_supports_web_alias_fields(monkeypatch) -> None:
    store = _FakeCalendarStore()
    monkeypatch.setattr(main_api, "calendar_store", store)

    created = asyncio.run(
        main_api.create_calendar_event(
            main_api.CalendarEventCreate(
                title="Pomiar klienta K-21",
                type="measurement",
                start_at="2026-05-11T08:30",
                end_at="2026-05-11T10:00",
                all_day=False,
                client_name="Klient K-21",
                project_ref="PROJ-21",
                location="Warszawa",
                assigned_to="Ekipa A",
                notes="Wejscie od podworka",
                status="confirmed",
            )
        )
    )

    assert created["status"] == "ok"
    event = created["event"]
    assert event["title"] == "Pomiar klienta K-21"
    assert event["type"] == "measurement"
    assert event["start_at"] == "2026-05-11T08:30"
    assert event["end_at"] == "2026-05-11T10:00"
    assert event["assigned_to"] == "Ekipa A"
    assert event["project_ref"] == "PROJ-21"
    assert event["status"] == "confirmed"

    listed = asyncio.run(main_api.get_calendar_events(limit=50))
    assert listed["status"] == "ok"
    assert len(listed["events"]) == 1
    assert listed["events"][0]["id"] == event["id"]

    updated = asyncio.run(
        main_api.update_calendar_event(
            event["id"],
            main_api.CalendarEventUpdate(
                type="installation",
                start_at="2026-05-12T09:00",
                end_at="2026-05-12T13:30",
                assigned_to="Ekipa Montazowa",
                status="in_progress",
                location="Lodz",
            ),
        )
    )

    assert updated["status"] == "ok"
    updated_event = updated["event"]
    assert updated_event["type"] == "installation"
    assert updated_event["start_at"] == "2026-05-12T09:00"
    assert updated_event["end_at"] == "2026-05-12T13:30"
    assert updated_event["assigned_to"] == "Ekipa Montazowa"
    assert updated_event["location"] == "Lodz"
    assert updated_event["status"] == "in_progress"


def test_calendar_events_delete_removes_persisted_item(monkeypatch) -> None:
    store = _FakeCalendarStore()
    seeded = CalendarEvent.new(
        event_type="service",
        title="Serwis kuchni",
        date="2026-06-02",
        date_end="2026-06-02",
        worker_name="Serwis 1",
    )
    store.save(seeded)
    monkeypatch.setattr(main_api, "calendar_store", store)

    deleted = asyncio.run(main_api.delete_calendar_event(seeded.id))
    assert deleted["status"] == "ok"

    listed = asyncio.run(main_api.get_calendar_events(limit=20))
    assert listed["events"] == []
