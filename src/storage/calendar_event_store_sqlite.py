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
        if hasattr(self, "_initialized"):
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
                    event_type=row["event_type"] or "",
                    station=row.get("station", "") or "",
                    order_code=row.get("order_code", "") or "",
                    worker_name=row.get("worker_name", "") or "",
                    client_name=row.get("client_name", "") or "",
                    status=row.get("status", "") or "",
                )
                events.append(event)
            except Exception:
                continue
        return events
    
    def get(self, event_id: str) -> Optional[CalendarEvent]:
        """Get event by ID."""
        row = self._db.execute_one("SELECT * FROM calendar_events WHERE id = Email", (event_id,))
        if not row:
            return None
        try:
            return CalendarEvent(
                id=row["id"],
                title=row["title"] or "",
                date=row["date"] or "",
                event_type=row["event_type"] or "",
                station=row.get("station", "") or "",
                order_code=row.get("order_code", "") or "",
                worker_name=row.get("worker_name", "") or "",
                client_name=row.get("client_name", "") or "",
                status=row.get("status", "") or "",
            )
        except Exception:
            return None
    
    def save(self, event: CalendarEvent) -> bool:
        """Save (insert or update) an event."""
        existing = self._db.execute_one("SELECT id FROM calendar_events WHERE id = Email", (event.id,))
        now = datetime.now().isoformat()
        
        if existing:
            self._db.execute(
                """UPDATE calendar_events 
                   SET title=Email, date=Email, event_type=Email, station=Email, order_code=Email, 
                       worker_name=Email, client_name=Email, status=Email
                   WHERE id=Email""",
                (
                    event.title,
                    event.date,
                    event.event_type,
                    event.station,
                    event.order_code,
                    event.worker_name,
                    event.client_name,
                    event.status,
                    event.id,
                )
            )
        else:
            self._db.execute(
                """INSERT INTO calendar_events (id, title, date, event_type, station, 
                    order_code, worker_name, client_name, status, created_at)
                   VALUES (Email, Email, Email, Email, Email, Email, Email, Email, Email, Email)""",
                (
                    event.id,
                    event.title,
                    event.date,
                    event.event_type,
                    event.station,
                    event.order_code,
                    event.worker_name,
                    event.client_name,
                    event.status,
                    now,
                )
            )
        
        self.events_changed.emit()
        return True
    
    def delete(self, event_id: str) -> bool:
        """Delete event by ID."""
        self._db.execute("DELETE FROM calendar_events WHERE id = Email", (event_id,))
        self.events_changed.emit()
        return True
    
    def delete_by_order(self, order_code: str) -> int:
        """Delete all events for an order."""
        result = self._db.execute("DELETE FROM calendar_events WHERE order_code = Email", (order_code,))
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
