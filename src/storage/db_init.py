"""
Database initialization module for TECH_modul.
Call init_database() at app startup to set up SQLite.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from src.storage.sqlite_db import init_database, get_database
from src.storage.data_paths import data_dir


def setup_database() -> None:
    """
    Initialize database at app startup.
    This should be called once when the application starts.
    """
    # Ensure data directory exists
    data_dir().mkdir(parents=True, exist_ok=True)
    
    # Initialize SQLite database
    db = init_database()
    
    # Check if we need to migrate from JSON
    db_path = data_dir() / "tech_modul.db"
    json_path = data_dir() / "orders.json"
    
    if json_path.exists() and db_path.stat().st_size < 1000:
        print("Migrating data from JSON to SQLite...")
        _run_migration()
    
    print(f"Database ready: {db_path}")


def _run_migration() -> None:
    """Run JSON to SQLite migration."""
    try:
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
        
        total = sum(stats.values())
        print(f"Migration complete: {total} records imported")
        for entity, count in stats.items():
            if count > 0:
                print(f"  - {entity}: {count}")
                
    except Exception as e:
        print(f"Migration warning: {e}")


def backup_database(backup_path: Optional[str] = None) -> str:
    """
    Create a backup of the database.
    
    Args:
        backup_path: Path for backup file. If None, uses timestamped name.
    
    Returns:
        Path to the backup file.
    """
    from datetime import datetime
    
    db = get_database()
    
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = str(data_dir() / f"backup_{timestamp}.db")
    
    db.backup(backup_path)
    print(f"Backup created: {backup_path}")
    return backup_path


def vacuum_database() -> None:
    """Optimize database by rebuilding and defragmenting."""
    db = get_database()
    db.vacuum()
    print("Database optimized")


def export_to_json(export_dir: Optional[str] = None) -> dict:
    """
    Export all data to JSON files.
    
    Args:
        export_dir: Directory for export files. If None, uses data/export/.
    
    Returns:
        Dictionary with paths to exported files.
    """
    from src.storage.storage import Storage
    
    storage = Storage()
    return storage.export_all_json(export_dir)


def import_from_json(json_dir: str, overwrite: bool = False) -> dict:
    """
    Import data from JSON files.
    
    Args:
        json_dir: Directory containing JSON files.
        overwrite: If True, overwrite existing records.
    
    Returns:
        Dictionary with import statistics.
    """
    from pathlib import Path
    from src.storage.order_store_sqlite import OrderStore
    from src.storage.client_store_sqlite import ClientStore
    
    json_path = Path(json_dir)
    stats = {}
    
    # Import orders
    orders_file = json_path / "orders.json"
    if orders_file.exists():
        store = OrderStore()
        imported, skipped = store.import_from_json(orders_file, overwrite)
        stats["orders"] = {"imported": imported, "skipped": skipped}
    
    # Import clients
    clients_file = json_path / "clients.json"
    if clients_file.exists():
        store = ClientStore()
        imported, skipped = store.import_from_json(clients_file, overwrite)
        stats["clients"] = {"imported": imported, "skipped": skipped}
    
    return stats


if __name__ == "__main__":
    # Command line interface for database operations
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            setup_database()
        elif command == "backup":
            path = sys.argv[2] if len(sys.argv) > 2 else None
            backup_database(path)
        elif command == "vacuum":
            vacuum_database()
        elif command == "export":
            path = sys.argv[2] if len(sys.argv) > 2 else None
            result = export_to_json(path)
            print(f"Exported to: {result}")
        elif command == "import":
            if len(sys.argv) > 2:
                path = sys.argv[2]
                overwrite = "--overwrite" in sys.argv
                result = import_from_json(path, overwrite)
                print(f"Import result: {result}")
            else:
                print("Usage: python db_init.py import <directory> [--overwrite]")
        else:
            print("Commands: init, backup, vacuum, export, import")
    else:
        setup_database()
