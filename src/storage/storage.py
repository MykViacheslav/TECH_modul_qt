"""
Unified SQLite storage module.
Provides all stores using SQLite as primary storage.
"""
from __future__ import annotations

from src.storage.sqlite_db import get_database, init_database, Database
from src.storage.order_store_sqlite import OrderStore, StoreResult
from src.storage.client_store_sqlite import ClientStore, ClientDef
from src.storage.worker_store_sqlite import WorkerStore
from src.storage.calendar_event_store_sqlite import CalendarEventStore


class Storage:
    """
    Main storage facade providing access to all SQLite stores.
    
    Usage:
        storage = Storage()
        storage.orders.save_new(order)
        storage.clients.get("Jan Kowalski")
        storage.workers.get("Jan")
        storage.backup("backup.db")
    """
    
    _instance: "Storage | None" = None
    
    def __new__(cls) -> "Storage":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self._db = init_database()
        self._orders = OrderStore(self._db)
        self._clients = ClientStore(self._db)
        self._workers = WorkerStore(self._db)
        self._calendar_events = CalendarEventStore()
    
    @property
    def orders(self) -> OrderStore:
        """Access order store."""
        return self._orders
    
    @property
    def clients(self) -> ClientStore:
        """Access client store."""
        return self._clients
    
    @property
    def workers(self) -> WorkerStore:
        """Access worker store."""
        return self._workers
    
    @property
    def calendar_events(self) -> CalendarEventStore:
        """Access calendar event store."""
        return self._calendar_events
    
    @property
    def db(self) -> Database:
        """Access raw database."""
        return self._db
    
    def backup(self, path: str) -> None:
        """Create database backup."""
        self._db.backup(path)
    
    def vacuum(self) -> None:
        """Optimize database."""
        self._db.vacuum()
    
    def close(self) -> None:
        """Close database connection."""
        self._db.close()
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        return {
            "orders": self._orders.count(),
            "clients": self._clients.count(),
            "workers": self._workers.count(),
            "calendar_events": self._calendar_events.count(),
            "orders_by_status": self._orders.count_by_status(),
        }
    
    def migrate_from_json(self) -> dict:
        """
        Migrate all data from JSON files to SQLite.
        Returns statistics about migration.
        """
        from src.storage.migrate_to_sqlite import (
            migrate_orders,
            migrate_clients,
            migrate_materials,
            migrate_workers,
            migrate_calendar_events,
            migrate_alarms,
        )
        
        stats = {
            "orders": migrate_orders(),
            "clients": migrate_clients(),
            "materials": migrate_materials(),
            "workers": migrate_workers(),
            "calendar_events": migrate_calendar_events(),
            "alarms": migrate_alarms(),
        }
        
        return stats
    
    def export_all_json(self, directory: str | None = None) -> dict:
        """Export all data to JSON files. Returns paths."""
        from pathlib import Path
        from src.storage.data_paths import data_dir
        
        if directory is None:
            directory = str(data_dir())
        
        export_dir = Path(directory) / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        paths["orders"] = str(self._orders.export_to_json(export_dir / "orders.json"))
        paths["clients"] = str(self._clients.export_to_json(export_dir / "clients.json"))
        
        return paths


def get_storage() -> Storage:
    """Get global storage instance."""
    return Storage()
