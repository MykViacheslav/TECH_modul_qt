"""
SQLite database connection and schema for TECH_modul.
Provides a single shared database file with all data.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.storage.data_paths import data_dir


class Database:
    """SQLite database connection with thread safety."""
    
    _instance: Optional['Database'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'Database':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if hasattr(self, '_initialized'):
            return
        
        self._db_path = data_dir() / "tech_modul.db"
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = True
        
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Performance optimizations
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = NORMAL")
            self._connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
            self._connection.execute("PRAGMA temp_store = MEMORY")
        
        return self._connection
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                client_name TEXT,
                worker_name TEXT,
                status TEXT DEFAULT 'Nowe',
                created_at TEXT,
                updated_at TEXT,
                date_projekt TEXT,
                date_zakup_mat TEXT,
                date_produkcja TEXT,
                date_lakiernia TEXT,
                date_montaz TEXT,
                data TEXT
            )
        """)
        
        # Materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                material_id TEXT,
                quantity REAL DEFAULT 0,
                unit TEXT DEFAULT 'szt',
                category TEXT,
                supplier TEXT,
                price REAL DEFAULT 0,
                updated_at TEXT
            )
        """)
        
        # Material transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS material_transactions (
                id TEXT PRIMARY KEY,
                transaction_type TEXT NOT NULL,
                material_id TEXT,
                material_name TEXT,
                quantity REAL,
                unit TEXT DEFAULT 'szt',
                order_code TEXT,
                worker_name TEXT,
                notes TEXT,
                status TEXT DEFAULT 'oczekuje',
                supplier TEXT,
                expected_date TEXT,
                price_per_unit REAL DEFAULT 0,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        
        # Calendar events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT,
                event_type TEXT,
                station TEXT,
                order_code TEXT,
                worker_name TEXT,
                client_name TEXT,
                status TEXT DEFAULT 'zaplanowany',
                created_at TEXT
            )
        """)
        
        # Workers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'operator',
                phone TEXT,
                email TEXT,
                position TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        
        # Clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                email TEXT,
                nip TEXT,
                created_at TEXT
            )
        """)
        
        # Alarms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id TEXT PRIMARY KEY,
                category TEXT,
                severity TEXT,
                title TEXT NOT NULL,
                description TEXT,
                is_resolved INTEGER DEFAULT 0,
                related_order TEXT,
                related_material TEXT,
                related_worker TEXT,
                due_date TEXT,
                created_at TEXT,
                resolved_at TEXT
            )
        """)
        
        # Settings table (key-value)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_code ON orders(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarms_resolved ON alarms(is_resolved)")
        
        conn.commit()
    
    def execute(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Execute a query and return one result as dict."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute insert and return last row id."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute update/delete and return affected rows."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    
    def vacuum(self) -> None:
        """Optimize database."""
        conn = self._get_connection()
        conn.isolation_level = None  # Autocommit mode
        try:
            conn.execute("VACUUM")
        finally:
            conn.isolation_level = ''  # Restore default
    
    def backup(self, path: str) -> None:
        """Create backup of database."""
        conn = self._get_connection()
        backup_conn = sqlite3.connect(path)
        conn.backup(backup_conn)
        backup_conn.close()
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Global instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_database() -> Database:
    """Initialize and return database."""
    return get_database()
