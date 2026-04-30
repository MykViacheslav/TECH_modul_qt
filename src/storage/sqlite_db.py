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
from src import safe_mode


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

        # Phase 1 Safe Work Mode: bootstrap legacy prod DB on first prod start, then
        # use the env-driven canonical path. Tests are auto-routed to test DB.
        safe_mode.bootstrap_legacy_prod_db()
        self._db_path = safe_mode.get_db_path()
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = True

        # Backup prod DB before any schema-changing init. No-op in dev/test.
        safe_mode.backup_prod_db_or_die("sqlite_db_init")
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
                date_end TEXT,
                all_day INTEGER DEFAULT 1,
                event_type TEXT,
                station TEXT,
                order_code TEXT,
                worker_name TEXT,
                client_name TEXT,
                location TEXT,
                notes TEXT,
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
        
        # Manufacturers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manufacturers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE,
                website_url TEXT,
                country TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        # Material categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS material_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                code TEXT UNIQUE NOT NULL,
                name_pl TEXT NOT NULL,
                name_en TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (parent_id) REFERENCES material_categories(id)
            )
        """)

        # Producer collections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS producer_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer_id INTEGER NOT NULL,
                code TEXT,
                name TEXT NOT NULL,
                year_label TEXT,
                source_ref TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
            )
        """)

        # Catalog Items (The Central Registry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_code TEXT UNIQUE,
                producer_code TEXT,
                name TEXT NOT NULL,
                short_name TEXT,
                manufacturer_id INTEGER,
                collection_id INTEGER,
                category_id INTEGER,
                subcategory TEXT,
                item_type TEXT,
                base_unit TEXT DEFAULT 'pcs',
                default_thickness_mm REAL,
                color_name TEXT,
                decor_name TEXT,
                finish_name TEXT,
                surface_code TEXT,
                grain_direction_mode TEXT DEFAULT 'none',
                thumbnail_path TEXT,
                texture_path TEXT,
                preview_color_hex TEXT,
                description TEXT,
                producer_page_url TEXT,
                is_active INTEGER DEFAULT 1,
                is_favorite INTEGER DEFAULT 0,
                is_imported INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
                FOREIGN KEY (collection_id) REFERENCES producer_collections(id),
                FOREIGN KEY (category_id) REFERENCES material_categories(id)
            )
        """)

        # Catalog Item Variants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_item_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                variant_code TEXT,
                thickness_mm REAL,
                length_mm REAL,
                width_mm REAL,
                depth_mm REAL,
                height_mm REAL,
                capacity_kg REAL,
                finish_name TEXT,
                color_name TEXT,
                unit TEXT,
                is_default INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id)
            )
        """)

        # Usage Rules (FOR CONTEXT PICKER)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_item_usage_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                usage_type TEXT NOT NULL,
                allowed INTEGER DEFAULT 1,
                is_default INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id)
            )
        """)

        # Catalog Item Properties (Flexible Params)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_item_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                prop_key TEXT NOT NULL,
                prop_value TEXT,
                value_type TEXT DEFAULT 'string',
                unit TEXT,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id)
            )
        """)

        # Catalog Item Documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_item_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                doc_type TEXT,
                title TEXT NOT NULL,
                file_path TEXT,
                external_url TEXT,
                language TEXT DEFAULT 'pl',
                version_label TEXT,
                notes TEXT,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id)
            )
        """)

        # Knowledge Base Entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                entry_type TEXT,
                manufacturer_id INTEGER,
                related_catalog_item_id INTEGER,
                related_category_id INTEGER,
                content_md TEXT,
                summary TEXT,
                difficulty_level TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
                FOREIGN KEY (related_catalog_item_id) REFERENCES catalog_items(id),
                FOREIGN KEY (related_category_id) REFERENCES material_categories(id)
            )
        """)

        # Knowledge Base Attachments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_entry_id INTEGER NOT NULL,
                attachment_type TEXT,
                file_path TEXT,
                external_url TEXT,
                title TEXT,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (knowledge_entry_id) REFERENCES knowledge_entries(id)
            )
        """)

        # Suppliers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE,
                website TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Supplier Item Links
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_item_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                supplier_id INTEGER NOT NULL,
                supplier_code TEXT,
                supplier_name TEXT,
                pack_size REAL DEFAULT 1,
                unit TEXT DEFAULT 'pcs',
                min_order_qty REAL DEFAULT 0,
                lead_time_days INTEGER DEFAULT 0,
                is_preferred INTEGER DEFAULT 0,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        """)

        # Price History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_item_id INTEGER NOT NULL,
                supplier_id INTEGER,
                variant_id INTEGER,
                net_price REAL NOT NULL,
                vat_rate REAL DEFAULT 23,
                gross_price REAL,
                currency TEXT DEFAULT 'PLN',
                price_unit TEXT,
                valid_from TEXT,
                document_ref TEXT,
                notes TEXT,
                FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY (variant_id) REFERENCES catalog_item_variants(id)
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
        order_columns = {
            str(row[1] if isinstance(row, tuple) else row["name"])
            for row in cursor.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "code" in order_columns:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_code ON orders(code)")
        if "status" in order_columns:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarms_resolved ON alarms(is_resolved)")

        # Migrations
        try:
            cursor.execute("ALTER TABLE catalog_items ADD COLUMN is_deleted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

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
        upper_query = query.strip().upper()
        if upper_query.startswith("DELETE") or upper_query.startswith("DROP"):
            safe_mode.require_prod_confirmation(f"SQL_{upper_query.split()[0]}")
            
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


def get_calendar_event_store():
    """Lazy helper used by API layer to avoid import cycles."""
    from src.storage.calendar_event_store_sqlite import CalendarEventStore

    return CalendarEventStore()


def init_database() -> Database:
    """Initialize and return database."""
    return get_database()
