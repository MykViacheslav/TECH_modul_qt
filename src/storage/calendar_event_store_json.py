from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from src.domain.calendar_event import CalendarEvent
from src.storage.data_paths import data_dir


class CalendarEventStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "calendar_events.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_events(self) -> List[CalendarEvent]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [CalendarEvent.from_dict(d) for d in raw if isinstance(d, dict)]
        except Exception:
            pass
        return []

    def get(self, event_id: str) -> Optional[CalendarEvent]:
        for ev in self.list_events():
            if ev.id == event_id:
                return ev
        return None

    def save(self, event: CalendarEvent) -> None:
        events = self.list_events()
        for i, ev in enumerate(events):
            if ev.id == event.id:
                events[i] = event
                break
        else:
            events.append(event)
        self._write(events)

    def delete(self, event_id: str) -> None:
        events = [ev for ev in self.list_events() if ev.id != event_id]
        self._write(events)

    def _write(self, events: List[CalendarEvent]) -> None:
        self._path.write_text(
            json.dumps([ev.to_dict() for ev in events], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
