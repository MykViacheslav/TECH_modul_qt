"""
Calendar event store using SQLite.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal, QObject

from src.storage.sqlite_db import get_database, Database
from src.storage.data_paths import data_dir
from src.domain.calendar_event import CalendarEvent


class CalendarEventStore(QObject):
    """SQLite-based calendar event store."""
    
    events_changed = pyqtSignal()
    
    _instance: Optional["CalendarEventStore"] = None
    
    def __new__(cls) -> "CalendarEventStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if self.__dict__.get("_initialized"):
            return
        super().__init__()
        self._initialized = True
        self._db = get_database()
    
    def list_events(self) -> List[CalendarEvent]:
        """Return all calendar events."""
        rows = self._db.execute("SELECT * FROM calendar_events ORDER BY date")
        events = []
        for row in rows:
            try:
                event = CalendarEvent(
                    id=row["id"],
                    title=row["title"] or "",
                    date=row["date"] or "",
                    date_end=row.get("date_end", "") or "",
                    all_day=bool(row.get("all_day", 1)),
                    event_type=row["event_type"] or "",
                    station=row.get("station", "") or "",
                    order_code=row.get("order_code", "") or "",
                    worker_name=row.get("worker_name", "") or "",
                    client_name=row.get("client_name", "") or "",
                    location=row.get("location", "") or "",
                    notes=row.get("notes", "") or "",
                    status=row.get("status", "") or "planned",
                )
                events.append(event)
            except Exception:
                continue
        return events

    def get_all(self, limit: int = 500) -> List[CalendarEvent]:
        events = self.list_events()
        try:
            safe_limit = max(1, int(limit))
        except Exception:
            safe_limit = 500
        return events[:safe_limit]
    
    def get(self, event_id: str) -> Optional[CalendarEvent]:
        """Get event by ID."""
        row = self._db.execute_one("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        if not row:
            return None
        try:
            return CalendarEvent(
                id=row["id"],
                title=row["title"] or "",
                date=row["date"] or "",
                date_end=row.get("date_end", "") or "",
                all_day=bool(row.get("all_day", 1)),
                event_type=row["event_type"] or "",
                station=row.get("station", "") or "",
                order_code=row.get("order_code", "") or "",
                worker_name=row.get("worker_name", "") or "",
                client_name=row.get("client_name", "") or "",
                location=row.get("location", "") or "",
                notes=row.get("notes", "") or "",
                status=row.get("status", "") or "planned",
            )
        except Exception:
            return None

    def get_by_id(self, event_id: str) -> Optional[CalendarEvent]:
        return self.get(event_id)
    
    def save(self, event: CalendarEvent) -> CalendarEvent:
        """Save (insert or update) an event."""
        existing = self._db.execute_one("SELECT id FROM calendar_events WHERE id = ?", (event.id,))
        now = datetime.now().isoformat()
        
        if existing:
            self._db.execute(
                """UPDATE calendar_events 
                   SET title=?, date=?, date_end=?, all_day=?, event_type=?, station=?, order_code=?, 
                       worker_name=?, client_name=?, location=?, notes=?, status=?
                   WHERE id=?""",
                (
                    event.title,
                    event.date,
                    event.date_end,
                    1 if event.all_day else 0,
                    event.event_type,
                    event.station,
                    event.order_code,
                    event.worker_name,
                    event.client_name,
                    event.location,
                    event.notes,
                    event.status,
                    event.id,
                )
            )
        else:
            self._db.execute(
                """INSERT INTO calendar_events (id, title, date, date_end, all_day, event_type, station, 
                    order_code, worker_name, client_name, location, notes, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.id,
                    event.title,
                    event.date,
                    event.date_end,
                    1 if event.all_day else 0,
                    event.event_type,
                    event.station,
                    event.order_code,
                    event.worker_name,
                    event.client_name,
                    event.location,
                    event.notes,
                    event.status,
                    now,
                )
            )
        
        self.events_changed.emit()
        return event
    
    def delete(self, event_id: str) -> bool:
        """Delete event by ID."""
        self._db.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        self.events_changed.emit()
        return True
    
    def delete_by_order(self, order_code: str) -> int:
        """Delete all events for an order."""
        result = self._db.execute("DELETE FROM calendar_events WHERE order_code = ?", (order_code,))
        count = len(result) if result else 0
        if count > 0:
            self.events_changed.emit()
        return count

    
    def count(self) -> int:
        """Return total number of events."""
        row = self._db.execute_one("SELECT COUNT(*) as cnt FROM calendar_events")
        return row["cnt"] if row else 0


# Alias for backward compatibility
CalendarEventStoreJson = CalendarEventStore
