"""
Migrate data from JSON files to SQLite database.
Run this once to move all data to the new SQLite format.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir
from src.storage.sqlite_db import get_database


def load_json(path: Path) -> Any:
    """Load JSON with BOM support."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        text = path.read_text(encoding="utf-8")
    return json.loads(text)


def migrate_orders() -> int:
    """Migrate orders from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "orders.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    orders = data if isinstance(data, list) else data.get("orders", [])
    
    count = 0
    for order in orders:
        if not isinstance(order, dict):
            continue
        
        code = order.get("code", "")
        if not code:
            continue
        
        # Check if already exists
        existing = db.execute_one("SELECT code FROM orders WHERE code = ?", (code,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO orders (code, client_name, worker_name, status, created_at, updated_at,
                date_projekt, date_zakup_mat, date_produkcja, date_lakiernia, date_montaz, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code,
            order.get("client_name", ""),
            order.get("worker_name", ""),
            order.get("status", "Nowe"),
            order.get("created_at", ""),
            order.get("updated_at", ""),
            order.get("date_projekt", ""),
            order.get("date_zakup_mat", ""),
            order.get("date_produkcja", ""),
            order.get("date_lakiernia", ""),
            order.get("date_montaz", ""),
            json.dumps(order, ensure_ascii=False)
        ))
        count += 1
    
    return count


def migrate_materials() -> int:
    """Migrate materials from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "baza_materialu.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    rows = data.get("rows", []) if isinstance(data, dict) else data
    
    count = 0
    for mat in rows:
        if not isinstance(mat, dict):
            continue
        
        name = mat.get("nazwa", "")
        if not name:
            continue
        
        existing = db.execute_one("SELECT name FROM materials WHERE name = ?", (name,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO materials (name, material_id, quantity, unit, category, supplier, price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            mat.get("id", ""),
            float(mat.get("ilosc_magazyn", 0) or mat.get("ilosc", 0) or 0),
            mat.get("jednostka", "szt"),
            mat.get("kategoria", ""),
            mat.get("dostawca", ""),
            float(mat.get("cena", 0) or 0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        count += 1
    
    return count


def migrate_workers() -> int:
    """Migrate workers from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "pracownicy.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    workers = data if isinstance(data, list) else data.get("workers", [])
    
    count = 0
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        
        name = worker.get("name", "")
        if not name:
            continue
        
        existing = db.execute_one("SELECT name FROM workers WHERE name = ?", (name,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO workers (name, role, phone, email, position, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            worker.get("role", "operator"),
            worker.get("phone", ""),
            worker.get("email", ""),
            worker.get("position", ""),
            1 if worker.get("active", True) else 0,
            worker.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        count += 1
    
    return count


def migrate_alarms() -> int:
    """Migrate alarms from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "alarms.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    alarms = data if isinstance(data, list) else data.get("alarms", [])
    
    count = 0
    for alarm in alarms:
        if not isinstance(alarm, dict):
            continue
        
        alarm_id = alarm.get("alarm_id", "")
        if not alarm_id:
            continue
        
        existing = db.execute_one("SELECT id FROM alarms WHERE id = ?", (alarm_id,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO alarms (id, category, severity, title, description, is_resolved,
                related_order, related_material, related_worker, due_date, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alarm_id,
            alarm.get("category", "inne"),
            alarm.get("severity", "info"),
            alarm.get("title", ""),
            alarm.get("description", ""),
            1 if alarm.get("is_resolved", False) else 0,
            alarm.get("related_order", ""),
            alarm.get("related_material", ""),
            alarm.get("related_worker", ""),
            alarm.get("due_date", ""),
            alarm.get("created_at", ""),
            alarm.get("resolved_at", "")
        ))
        count += 1
    
    return count


def migrate_calendar_events() -> int:
    """Migrate calendar events from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "calendar_events.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    events = data if isinstance(data, list) else data.get("events", [])
    
    count = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        
        event_id = event.get("id", "")
        if not event_id:
            continue
        
        existing = db.execute_one("SELECT id FROM calendar_events WHERE id = ?", (event_id,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO calendar_events (id, title, date, event_type, station, order_code,
                worker_name, client_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            event.get("title", ""),
            event.get("date", ""),
            event.get("event_type", ""),
            event.get("station", ""),
            event.get("order_code", ""),
            event.get("worker_name", ""),
            event.get("client_name", ""),
            event.get("status", "zaplanowany"),
            event.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        count += 1
    
    return count


def migrate_clients() -> int:
    """Migrate clients from JSON to SQLite."""
    db = get_database()
    path = data_dir() / "klienci.json"
    if not path.exists():
        return 0
    
    data = load_json(path)
    clients = data if isinstance(data, list) else data.get("clients", [])
    
    count = 0
    for client in clients:
        if not isinstance(client, dict):
            continue
        
        name = client.get("name", "")
        if not name:
            continue
        
        existing = db.execute_one("SELECT name FROM clients WHERE name = ?", (name,))
        if existing:
            continue
        
        db.execute("""
            INSERT INTO clients (name, address, phone, email, nip, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            client.get("address", ""),
            client.get("phone", ""),
            client.get("email", ""),
            client.get("nip", ""),
            client.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        count += 1
    
    return count


def migrate_all() -> dict:
    """Migrate all data from JSON to SQLite."""
    print("Starting migration to SQLite...")
    print(f"Source: {data_dir()}")
    print(f"Database: {get_database()._db_path}")
    print()
    
    results = {}
    
    print("Migrating orders...")
    results["orders"] = migrate_orders()
    print(f"  -> {results['orders']} orders migrated")
    
    print("Migrating materials...")
    results["materials"] = migrate_materials()
    print(f"  -> {results['materials']} materials migrated")
    
    print("Migrating workers...")
    results["workers"] = migrate_workers()
    print(f"  -> {results['workers']} workers migrated")
    
    print("Migrating alarms...")
    results["alarms"] = migrate_alarms()
    print(f"  -> {results['alarms']} alarms migrated")
    
    print("Migrating calendar events...")
    results["calendar_events"] = migrate_calendar_events()
    print(f"  -> {results['calendar_events']} events migrated")
    
    print("Migrating clients...")
    results["clients"] = migrate_clients()
    print(f"  -> {results['clients']} clients migrated")
    
    print()
    print("Optimizing database...")
    get_database().vacuum()
    
    total = sum(results.values())
    print(f"Migration complete! {total} records total.")
    
    return results


if __name__ == "__main__":
    migrate_all()
