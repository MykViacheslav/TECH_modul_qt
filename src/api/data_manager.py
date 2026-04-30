import sqlite3
import os
import json
import hashlib
import re
from typing import List, Dict, Optional, Any

from src import safe_mode


class TechModulDataManager:
    def __init__(self, db_path: Optional[str] = None):
        # Phase 1 Safe Work Mode: when no explicit db_path is given, resolve from
        # safe_mode (env-driven prod/dev/test selection). Tests that pass an explicit
        # path still work; ad-hoc instantiation in prod/dev gets the right file.
        if db_path is None:
            safe_mode.bootstrap_legacy_prod_db()
            db_path = str(safe_mode.get_db_path())
        else:
            safe_mode.assert_test_isolation(db_path)
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):  # noqa: F841 (Phase 1 Safe Work Mode hook below)
        # Phase 1 Safe Work Mode: backup prod DB before any schema-changing call.
        # No-op in dev/test. Raises BackupFailedError if the backup cannot be written.
        safe_mode.backup_prod_db_or_die("init_db")
        return self._init_db_impl()

    def _init_db_impl(self):
        """Inicjalizacja struktury bazy danych dla TECH MODUĹ Pro."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela ProjektĂłw
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    client_name TEXT,
                    status TEXT DEFAULT 'Wycena',
                    total_price REAL DEFAULT 0,
                    margin INTEGER DEFAULT 30,
                    obstacles_json TEXT DEFAULT '[]',
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_name TEXT,
                    action TEXT NOT NULL,
                    target_type TEXT,
                    target_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    metadata_json TEXT DEFAULT '{}'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_wall_config (
                    project_id INTEGER PRIMARY KEY,
                    width_mm REAL DEFAULT 3250.0,
                    height_mm REAL DEFAULT 2500.0,
                    depth_mm REAL DEFAULT 3200.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela ModuĹ‚Ăłw (Szafek) w projektach
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    module_name TEXT,
                    width INTEGER,
                    height INTEGER,
                    depth INTEGER,
                    material_id INTEGER,
                    spec_json TEXT DEFAULT '{}',
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
            ''')
            
            # Tabela Materiałów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    price_per_m2 REAL,
                    thickness INTEGER,
                    material_code TEXT DEFAULT '',
                    category TEXT DEFAULT 'boards',
                    material_kind TEXT DEFAULT 'other',
                    unit TEXT DEFAULT 'm2',
                    is_library BOOLEAN DEFAULT 1,
                    stock_quantity REAL DEFAULT 0.0,
                    min_stock REAL DEFAULT 0.0,
                    purchase_type TEXT DEFAULT 'nothing',
                    supplier TEXT DEFAULT '',
                    wholesaler TEXT DEFAULT '',
                    format_length_mm REAL DEFAULT 0.0,
                    format_width_mm REAL DEFAULT 0.0,
                    pack_size REAL DEFAULT 0.0,
                    parameter_json TEXT DEFAULT '{}',
                    texture_url TEXT DEFAULT '',
                    color_hex TEXT DEFAULT '#ffffff',
                    is_deleted INTEGER DEFAULT 0
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    client_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    deadline TEXT,
                    deadline_from TEXT DEFAULT '',
                    deadline_to TEXT DEFAULT '',
                    budget REAL DEFAULT 0,
                    status TEXT DEFAULT 'DRAFT',
                    spec_json TEXT DEFAULT '{}',
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL UNIQUE,
                    project_id INTEGER NOT NULL,
                    event_type TEXT DEFAULT 'montaz',
                    title TEXT NOT NULL,
                    date_from TEXT NOT NULL,
                    date_to TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(order_id) REFERENCES orders(id),
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    location TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    type TEXT DEFAULT 'person',
                    status TEXT DEFAULT 'active',
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migrations for Soft Delete on existing tables
            for table in ["projects", "materials", "orders", "clients"]:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_deleted INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Migrations for Technicians (Auth)
            for col in [("is_active", "INTEGER DEFAULT 1"), ("password_hash", "TEXT DEFAULT ''")]:
                try:
                    cursor.execute(f"ALTER TABLE technicians ADD COLUMN {col[0]} {col[1]}")
                except sqlite3.OperationalError:
                    pass

            # Tabela Pracowników (do wyboru użytkownika)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    role TEXT DEFAULT 'produkcja',
                    pin_code TEXT DEFAULT '',
                    avatar_color TEXT DEFAULT '#3b82f6',
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    password_hash TEXT DEFAULT ''
                )
            ''')
            # Tabela Sesji Auth
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            self._ensure_login_users(cursor)
            
            # NOWA: Tabela Faktur Przychodowych (Koszty)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_nr TEXT,
                    date TEXT,
                    nip TEXT,
                    supplier TEXT DEFAULT '',
                    currency TEXT DEFAULT 'PLN',
                    net_amount REAL DEFAULT 0,
                    vat_amount REAL DEFAULT 0,
                    gross_amount REAL DEFAULT 0,
                    folder TEXT,
                    payload_hash TEXT DEFAULT '',
                    invoice_signature TEXT DEFAULT '',
                    source_filename TEXT DEFAULT '',
                    parse_method TEXT DEFAULT '',
                    parse_confidence REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'DRAFT',
                    duplicate_of_invoice_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_line_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    line_no INTEGER DEFAULT 0,
                    raw_line TEXT DEFAULT '',
                    name_raw TEXT DEFAULT '',
                    name_norm TEXT DEFAULT '',
                    quantity REAL DEFAULT 0.0,
                    unit TEXT DEFAULT '',
                    unit_price_net REAL DEFAULT 0.0,
                    unit_price_gross REAL DEFAULT 0.0,
                    total_net REAL DEFAULT 0.0,
                    total_gross REAL DEFAULT 0.0,
                    vat_rate TEXT DEFAULT '',
                    material_type TEXT DEFAULT '',
                    thickness_mm TEXT DEFAULT '',
                    parse_source TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.0,
                    review_status TEXT DEFAULT 'needs_review',
                    selected_material_id INTEGER,
                    selected_material_name TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                    FOREIGN KEY(selected_material_id) REFERENCES materials(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL,
                    supplier TEXT DEFAULT '',
                    invoice_id INTEGER,
                    invoice_line_item_id INTEGER,
                    purchase_date TEXT DEFAULT '',
                    unit TEXT DEFAULT '',
                    net_price REAL DEFAULT 0.0,
                    gross_price REAL DEFAULT 0.0,
                    currency TEXT DEFAULT 'PLN',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(material_id) REFERENCES materials(id),
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                    FOREIGN KEY(invoice_line_item_id) REFERENCES invoice_line_items(id)
                )
            ''')


            # Tabela Dostaw (Magazyn)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arrivals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER,
                    order_id INTEGER,
                    quantity REAL DEFAULT 0,
                    unit TEXT DEFAULT 'm2',
                    purchase_type TEXT DEFAULT 'nothing',
                    document_nr TEXT,
                    supplier TEXT DEFAULT '',
                    wholesaler TEXT DEFAULT '',
                    unit_price_net REAL DEFAULT 0.0,
                    unit_price_gross REAL DEFAULT 0.0,
                    price_total REAL DEFAULT 0,
                    invoice_id INTEGER,
                    invoice_line_item_id INTEGER,
                    date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(material_id) REFERENCES materials(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id),
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                    FOREIGN KEY(invoice_line_item_id) REFERENCES invoice_line_items(id)
                )
            ''')
            
            # --- Inventory + Order Cost Write-Off tables ---

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS purchase_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_name TEXT NOT NULL DEFAULT '',
                    document_number TEXT NOT NULL DEFAULT '',
                    document_date TEXT NOT NULL,
                    document_type TEXT DEFAULT 'invoice',
                    currency TEXT DEFAULT 'PLN',
                    total_net REAL DEFAULT 0.0,
                    total_gross REAL DEFAULT 0.0,
                    payment_status TEXT DEFAULT 'unpaid',
                    payment_method TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS purchase_document_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    purchase_document_id INTEGER NOT NULL,
                    material_id INTEGER,
                    description_snapshot TEXT DEFAULT '',
                    qty REAL NOT NULL DEFAULT 0,
                    unit TEXT DEFAULT 'pcs',
                    unit_price_net REAL DEFAULT 0.0,
                    vat_rate REAL DEFAULT 23.0,
                    line_total_net REAL DEFAULT 0.0,
                    line_total_gross REAL DEFAULT 0.0,
                    is_stock_item INTEGER DEFAULT 1,
                    order_id INTEGER,
                    note TEXT DEFAULT '',
                    FOREIGN KEY(purchase_document_id) REFERENCES purchase_documents(id),
                    FOREIGN KEY(material_id) REFERENCES materials(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL,
                    movement_type TEXT NOT NULL CHECK(movement_type IN ('IN','RESERVED','OUT','RETURN','SCRAP','CORRECTION')),
                    qty REAL NOT NULL DEFAULT 0,
                    unit TEXT DEFAULT 'pcs',
                    unit_cost_net REAL,
                    total_cost_net REAL,
                    location TEXT DEFAULT 'main',
                    order_id INTEGER,
                    purchase_document_id INTEGER,
                    purchase_document_line_id INTEGER,
                    related_movement_id INTEGER,
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT '',
                    FOREIGN KEY(material_id) REFERENCES materials(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id),
                    FOREIGN KEY(purchase_document_id) REFERENCES purchase_documents(id),
                    FOREIGN KEY(purchase_document_line_id) REFERENCES purchase_document_lines(id),
                    FOREIGN KEY(related_movement_id) REFERENCES inventory_movements(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL UNIQUE,
                    location TEXT DEFAULT 'main',
                    qty_on_hand REAL DEFAULT 0.0,
                    qty_reserved REAL DEFAULT 0.0,
                    qty_available REAL DEFAULT 0.0,
                    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(material_id) REFERENCES materials(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cash_bank_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movement_type TEXT NOT NULL CHECK(movement_type IN ('CASH_OUT','BANK_OUT','CASH_IN','BANK_IN','PAYABLE','SETTLED','REFUND')),
                    amount REAL NOT NULL DEFAULT 0.0,
                    currency TEXT DEFAULT 'PLN',
                    payment_method TEXT DEFAULT '',
                    supplier_name TEXT DEFAULT '',
                    purchase_document_id INTEGER,
                    order_id INTEGER,
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT '',
                    FOREIGN KEY(purchase_document_id) REFERENCES purchase_documents(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS procurement_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL,
                    order_id INTEGER,
                    qty_target REAL DEFAULT 0.0,
                    qty_ordered REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'missing',
                    owner_name TEXT,
                    supplier_name TEXT,
                    due_date TEXT,
                    priority TEXT DEFAULT 'normalny',
                    note TEXT,
                    purchase_document_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    FOREIGN KEY(material_id) REFERENCES materials(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id),
                    FOREIGN KEY(purchase_document_id) REFERENCES purchase_documents(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_cost_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    cost_type TEXT NOT NULL DEFAULT 'MATERIAL' CHECK(cost_type IN ('MATERIAL','LABOR','SERVICE','TRANSPORT','INSTALLATION','OTHER_DIRECT')),
                    source_type TEXT DEFAULT '',
                    source_id INTEGER,
                    amount_net REAL DEFAULT 0.0,
                    vat_rate REAL DEFAULT 23.0,
                    amount_gross REAL DEFAULT 0.0,
                    qty REAL,
                    unit TEXT,
                    description TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT '',
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            ''')

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_cost_entries_order ON order_cost_entries(order_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_procurement_items_material ON procurement_items(material_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_procurement_items_order ON procurement_items(order_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_procurement_items_status ON procurement_items(status)")

            # Dodanie domyślnych użytkowników jeśli tabela jest pusta.
            # Phase 1 Safe Work Mode: demo seed only in dev/test, never in prod.
            cursor.execute("SELECT count(*) FROM technicians")
            if cursor.fetchone()[0] == 0 and not safe_mode.is_prod():
                cursor.execute(
                    "INSERT INTO technicians (name, role, pin_code, avatar_color) VALUES (?, ?, ?, ?)",
                    ("Administrator", "wlasciciel", "1111", "#1e3a5f")
                )
                cursor.execute(
                    "INSERT INTO technicians (name, role, pin_code, avatar_color) VALUES (?, ?, ?, ?)",
                    ("Jan Design", "biuro", "", "#1e4d2b")
                )
                cursor.execute(
                    "INSERT INTO technicians (name, role, pin_code, avatar_color) VALUES (?, ?, ?, ?)",
                    ("Marek Produkcja", "produkcja", "", "#3b1f6b")
                )

            # Migracje kolumn dla starszych baz:
            def add_col(table, col, def_val):
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {def_val}")
                except sqlite3.OperationalError:
                    pass

            add_col("materials", "category", "TEXT DEFAULT 'boards'")
            add_col("materials", "unit", "TEXT DEFAULT 'm2'")
            add_col("materials", "is_library", "INTEGER DEFAULT 1")
            add_col("materials", "stock_quantity", "REAL DEFAULT 0.0")
            add_col("materials", "min_stock", "REAL DEFAULT 0.0")
            add_col("materials", "purchase_type", "TEXT DEFAULT 'nothing'")
            add_col("materials", "supplier", "TEXT DEFAULT ''")
            add_col("materials", "wholesaler", "TEXT DEFAULT ''")
            add_col("materials", "material_code", "TEXT DEFAULT ''")
            add_col("materials", "material_kind", "TEXT DEFAULT 'other'")
            add_col("materials", "format_length_mm", "REAL DEFAULT 0.0")
            add_col("materials", "format_width_mm", "REAL DEFAULT 0.0")
            add_col("materials", "pack_size", "REAL DEFAULT 0.0")
            add_col("materials", "parameter_json", "TEXT DEFAULT '{}'")
            add_col("materials", "texture_url", "TEXT DEFAULT ''")
            add_col("materials", "color_hex", "TEXT DEFAULT '#ffffff'")
            add_col("arrivals", "order_id", "INTEGER")
            add_col("arrivals", "supplier", "TEXT DEFAULT ''")
            add_col("arrivals", "wholesaler", "TEXT DEFAULT ''")
            add_col("arrivals", "unit_price_net", "REAL DEFAULT 0.0")
            add_col("arrivals", "unit_price_gross", "REAL DEFAULT 0.0")
            add_col("arrivals", "invoice_id", "INTEGER")
            add_col("arrivals", "invoice_line_item_id", "INTEGER")
            add_col("invoices", "supplier", "TEXT DEFAULT ''")
            add_col("invoices", "currency", "TEXT DEFAULT 'PLN'")
            add_col("invoices", "payload_hash", "TEXT DEFAULT ''")
            add_col("invoices", "invoice_signature", "TEXT DEFAULT ''")
            add_col("invoices", "source_filename", "TEXT DEFAULT ''")
            add_col("invoices", "parse_method", "TEXT DEFAULT ''")
            add_col("invoices", "parse_confidence", "REAL DEFAULT 0.0")
            add_col("invoices", "duplicate_of_invoice_id", "INTEGER")
            
            add_col("projects", "obstacles_json", "TEXT DEFAULT '[]'")

            cursor.execute("PRAGMA table_info(orders)")
            order_columns = {str(row[1]) for row in cursor.fetchall()}
            if "deadline_from" not in order_columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN deadline_from TEXT DEFAULT ''")
            if "deadline_to" not in order_columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN deadline_to TEXT DEFAULT ''")

            cursor.execute("PRAGMA table_info(clients)")
            client_columns = {str(row[1]) for row in cursor.fetchall()}
            if "address" not in client_columns:
                cursor.execute("ALTER TABLE clients ADD COLUMN address TEXT DEFAULT ''")
            if "email" not in client_columns:
                cursor.execute("ALTER TABLE clients ADD COLUMN email TEXT DEFAULT ''")
            if "phone" not in client_columns:
                cursor.execute("ALTER TABLE clients ADD COLUMN phone TEXT DEFAULT ''")
            
            cursor.execute("PRAGMA table_info(projects)")
            project_columns = {str(row[1]) for row in cursor.fetchall()}
            if "obstacles_json" not in project_columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN obstacles_json TEXT DEFAULT '[]'")
            
            # --- Migracje project_modules ---
            cursor.execute("PRAGMA table_info(project_modules)")
            mod_columns = {str(row[1]) for row in cursor.fetchall()}
            if "x" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN x REAL DEFAULT 0.0")
            if "y" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN y REAL DEFAULT 0.0")
            if "z" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN z REAL DEFAULT 0.0")
            if "rotation" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN rotation REAL DEFAULT 0.0")
            if "module_family" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN module_family TEXT DEFAULT 'kitchen_lower'")
            if "name" not in mod_columns and "module_name" in mod_columns:
                # Synchronizacja nazwy jeśli trzeba
                cursor.execute("ALTER TABLE project_modules ADD COLUMN name TEXT DEFAULT ''")
                cursor.execute("UPDATE project_modules SET name = module_name")
            if "spec_json" not in mod_columns:
                cursor.execute("ALTER TABLE project_modules ADD COLUMN spec_json TEXT DEFAULT '{}'")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_payload_hash ON invoices(payload_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_signature ON invoices(invoice_signature)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_arrivals_invoice_id ON arrivals(invoice_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_arrivals_invoice_line_item_id ON arrivals(invoice_line_item_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_material_date ON price_history(material_id, purchase_date)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_arrivals_invoice_line_item ON arrivals(invoice_line_item_id) WHERE invoice_line_item_id IS NOT NULL")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_price_history_invoice_line_item ON price_history(invoice_line_item_id) WHERE invoice_line_item_id IS NOT NULL")
            
            conn.commit()

    def get_all_projects(self, include_deleted: bool = False) -> List[Dict]:
        """Pobiera wszystkie projekty dla Dashboardu."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM projects"
            if not include_deleted:
                query += " WHERE is_deleted = 0"
            query += " ORDER BY created_at DESC"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def update_module_property(self, module_id: int, key: str, value: Any):
        """Aktualizuje pojedynczÄ… wĹ‚asnoĹ›Ä‡ moduĹ‚u w bazie danych."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Upewniamy siÄ™, ĹĽe klucz jest bezpieczny (whitelist lub parametryzacja nazw kolumn nie jest bezpoĹ›rednio wsparta)
            # Dla bezpieczeĹ„stwa używamy prostej mapy dozwolonych pĂłl
            allowed_cols = {"name", "width", "height", "depth", "x", "y", "z", "rotation", "material_id", "status"}
            if key not in allowed_cols:
                raise ValueError(f"Pole {key} nie jest dozwolone do bezpoĹ›redniej aktualizacji")
            
            cursor.execute(f"UPDATE project_modules SET {key} = ? WHERE id = ?", (value, module_id))
            conn.commit()

    def update_project_obstacles(self, project_id: int, obstacles_json: str):
        """Aktualizuje listę przeszkód (gniazdka, rury itp.) dla projektu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET obstacles_json = ? WHERE id = ?", (obstacles_json, project_id))
            conn.commit()

    def get_project_assembly_summary(self, project_id: int) -> Dict:
        """Zwraca podsumowanie modulow projektu liczone po stronie backend."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT "
                "COUNT(*) AS modules_count, "
                "COALESCE(SUM(width), 0) AS total_width_mm, "
                "COALESCE(SUM(height), 0) AS total_height_mm, "
                "COALESCE(SUM(depth), 0) AS total_depth_mm, "
                "COALESCE(SUM(width * height * depth), 0) AS total_volume_mm3, "
                "COALESCE(AVG(width), 0) AS avg_width_mm, "
                "COALESCE(AVG(height), 0) AS avg_height_mm, "
                "COALESCE(AVG(depth), 0) AS avg_depth_mm "
                "FROM project_modules WHERE project_id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "project_id": int(project_id),
                    "modules_count": 0,
                    "total_width_mm": 0.0,
                    "total_height_mm": 0.0,
                    "total_depth_mm": 0.0,
                    "total_volume_l": 0.0,
                    "avg_width_mm": 0.0,
                    "avg_height_mm": 0.0,
                    "avg_depth_mm": 0.0,
                }
            total_volume_mm3 = float(row["total_volume_mm3"] or 0.0)
            return {
                "project_id": int(project_id),
                "modules_count": int(row["modules_count"] or 0),
                "total_width_mm": float(row["total_width_mm"] or 0.0),
                "total_height_mm": float(row["total_height_mm"] or 0.0),
                "total_depth_mm": float(row["total_depth_mm"] or 0.0),
                "total_volume_l": round(total_volume_mm3 / 1_000_000.0, 2),
                "avg_width_mm": round(float(row["avg_width_mm"] or 0.0), 2),
                "avg_height_mm": round(float(row["avg_height_mm"] or 0.0), 2),
                "avg_depth_mm": round(float(row["avg_depth_mm"] or 0.0), 2),
            }

    def get_project_workspace_summary(self, project_id: int) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, client_name FROM projects WHERE id = ?",
                (int(project_id),),
            )
            project = cursor.fetchone()
            if project is None:
                return {
                    "project_id": int(project_id),
                    "project_title": "",
                    "client_name": "",
                    "modules_count": 0,
                    "orders_count": 0,
                    "draft_orders_count": 0,
                    "total_budget": 0.0,
                    "latest_deadline": "",
                }

            cursor.execute(
                "SELECT "
                "COALESCE((SELECT COUNT(*) FROM project_modules WHERE project_id = ?), 0) AS modules_count, "
                "COALESCE((SELECT COUNT(*) FROM orders WHERE project_id = ?), 0) AS orders_count, "
                "COALESCE((SELECT COUNT(*) FROM orders WHERE project_id = ? AND UPPER(status) = 'DRAFT'), 0) AS draft_orders_count, "
                "COALESCE((SELECT SUM(budget) FROM orders WHERE project_id = ?), 0) AS total_budget, "
                "COALESCE((SELECT MAX(deadline) FROM orders WHERE project_id = ?), '') AS latest_deadline",
                (int(project_id), int(project_id), int(project_id), int(project_id), int(project_id)),
            )
            stats = cursor.fetchone()
            return {
                "project_id": int(project_id),
                "project_title": str(project["title"] or ""),
                "client_name": str(project["client_name"] or ""),
                "modules_count": int(stats["modules_count"] or 0),
                "orders_count": int(stats["orders_count"] or 0),
                "draft_orders_count": int(stats["draft_orders_count"] or 0),
                "total_budget": float(stats["total_budget"] or 0.0),
                "latest_deadline": str(stats["latest_deadline"] or ""),
            }

    def get_project_finance_summary(self, project_id: int) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, client_name, margin, total_price FROM projects WHERE id = ?",
                (int(project_id),),
            )
            project = cursor.fetchone()
            if project is None:
                return {
                    "project_id": int(project_id),
                    "project_title": "",
                    "client_name": "",
                    "margin": 30,
                    "base_cost": 0.0,
                    "total_net": 0.0,
                    "vat": 0.0,
                    "total_gross": 0.0,
                    "profit": 0.0,
                    "orders_count": 0,
                }

            cursor.execute(
                "SELECT pm.width, pm.height, pm.depth, m.price_per_m2 "
                "FROM project_modules pm "
                "LEFT JOIN materials m ON pm.material_id = m.id "
                "WHERE pm.project_id = ?",
                (int(project_id),),
            )
            modules = cursor.fetchall()
            
            # Obliczamy koszt z modułów (powierzchnia płyt * cena m2)
            calculated_cost = 0.0
            for m in modules:
                w, h, d = (m[0] or 0) / 1000.0, (m[1] or 0) / 1000.0, (m[2] or 0) / 1000.0
                price_m2 = float(m[3] or 45.0) # Fallback do ceny dębu jeśli brak materiału
                # Uproszczony wzór na powierzchnię (6 ścianek)
                surface = 2 * (w*h + w*d + h*d)
                calculated_cost += surface * price_m2

            cursor.execute(
                "SELECT COALESCE(SUM(budget), 0) AS total_budget, COUNT(*) AS orders_count "
                "FROM orders WHERE project_id = ?",
                (int(project_id),),
            )
            orders = cursor.fetchone()
            orders_total_budget = float(orders["total_budget"] or 0.0)
            orders_count = int(orders["orders_count"] or 0)

            margin = int(project["margin"] or 30)
            # Jeśli mamy zamówienia, bierzemy ich sumę. Jeśli nie, liczymy z modułów (Komplet).
            # Jeśli moduły puste, fallback do ręcznego total_price.
            if orders_total_budget > 0:
                base_cost = orders_total_budget
            elif calculated_cost > 0:
                base_cost = calculated_cost
            else:
                base_cost = float(project["total_price"] or 0.0)

            total_net = base_cost * (1.0 + margin / 100.0)
            vat = total_net * 0.23
            total_gross = total_net + vat
            profit = total_net - base_cost

            return {
                "project_id": int(project_id),
                "project_title": str(project["title"] or ""),
                "client_name": str(project["client_name"] or ""),
                "margin": margin,
                "base_cost": round(base_cost, 2),
                "total_net": round(total_net, 2),
                "vat": round(vat, 2),
                "total_gross": round(total_gross, 2),
                "profit": round(profit, 2),
                "orders_count": orders_count,
            }

    def create_project(self, title: str, client_name: str) -> int:
        """Tworzy nowe zlecenie w systemie TECH MODUĹ."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (title, client_name) VALUES (?, ?)",
                (title, client_name)
            )
            conn.commit()
            return cursor.lastrowid

    def get_project_wall_config(self, project_id: int) -> Optional[Dict]:
        """Zwraca zapisane wymiary pokoju/sciany dla projektu (jesli istnieja)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT project_id, width_mm, height_mm, depth_mm, updated_at "
                "FROM project_wall_config WHERE project_id = ?",
                (int(project_id),),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_project_wall_config(
        self,
        project_id: int,
        width_mm: float,
        height_mm: float,
        depth_mm: float,
    ) -> Dict:
        """Tworzy lub aktualizuje konfiguracje wymiarow pokoju/sciany dla projektu."""
        safe_width = max(1000.0, float(width_mm or 0.0))
        safe_height = max(1000.0, float(height_mm or 0.0))
        safe_depth = max(1200.0, float(depth_mm or 0.0))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO project_wall_config (project_id, width_mm, height_mm, depth_mm, updated_at) "
                "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(project_id) DO UPDATE SET "
                "width_mm = excluded.width_mm, "
                "height_mm = excluded.height_mm, "
                "depth_mm = excluded.depth_mm, "
                "updated_at = CURRENT_TIMESTAMP",
                (int(project_id), safe_width, safe_height, safe_depth),
            )
            conn.commit()
        return self.get_project_wall_config(int(project_id)) or {
            "project_id": int(project_id),
            "width_mm": safe_width,
            "height_mm": safe_height,
            "depth_mm": safe_depth,
        }

    def create_order(
        self,
        project_id: int,
        client_name: str,
        title: str,
        deadline: str = "",
        deadline_from: str = "",
        deadline_to: str = "",
        budget: float = 0.0,
        status: str = "DRAFT",
        spec_json: str = "{}",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (project_id, client_name, title, deadline, deadline_from, deadline_to, budget, status, spec_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(project_id),
                    str(client_name or "").strip(),
                    str(title or "").strip(),
                    str(deadline or "").strip(),
                    str(deadline_from or "").strip(),
                    str(deadline_to or "").strip(),
                    float(budget or 0.0),
                    str(status or "DRAFT").strip() or "DRAFT",
                    str(spec_json or "{}").strip() or "{}",
                ),
            )
            conn.commit()
            order_id = int(cursor.lastrowid or 0)

        self.upsert_order_calendar_event(
            order_id=order_id,
            project_id=int(project_id),
            title=str(title or "").strip(),
            date_from=str(deadline_from or deadline or "").strip(),
            date_to=str(deadline_to or "").strip(),
        )
        return order_id

    def upsert_order_calendar_event(
        self,
        order_id: int,
        project_id: int,
        title: str,
        date_from: str,
        date_to: str = "",
        event_type: str = "montaz",
    ) -> int:
        normalized_from = str(date_from or "").strip()
        if not normalized_from:
            return 0
        normalized_to = str(date_to or "").strip()
        if normalized_to and normalized_to < normalized_from:
            normalized_to = normalized_from

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM order_calendar_events WHERE order_id = ?",
                (int(order_id),),
            )
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    "INSERT INTO order_calendar_events (order_id, project_id, event_type, title, date_from, date_to) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        int(order_id),
                        int(project_id),
                        str(event_type or "montaz").strip() or "montaz",
                        str(title or "").strip() or f"Order #{int(order_id)}",
                        normalized_from,
                        normalized_to,
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid or 0)

            cursor.execute(
                "UPDATE order_calendar_events "
                "SET project_id = ?, event_type = ?, title = ?, date_from = ?, date_to = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE order_id = ?",
                (
                    int(project_id),
                    str(event_type or "montaz").strip() or "montaz",
                    str(title or "").strip() or f"Order #{int(order_id)}",
                    normalized_from,
                    normalized_to,
                    int(order_id),
                ),
            )
            conn.commit()
            return int(existing["id"] or 0)

    def get_project_calendar_events(self, project_id: int, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, order_id, project_id, event_type, title, date_from, date_to, created_at, updated_at "
                "FROM order_calendar_events "
                "WHERE project_id = ? "
                "ORDER BY date_from ASC, id ASC LIMIT ?",
                (int(project_id), int(limit)),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_orders(self, limit: int = 50, project_id: int | None = None, include_deleted: bool = False) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            where_clauses = []
            if not include_deleted:
                where_clauses.append("is_deleted = 0")
            if project_id is not None:
                where_clauses.append(f"project_id = {int(project_id)}")
            
            where_stmt = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            query = f"SELECT id, project_id, client_name, title, deadline, deadline_from, deadline_to, budget, status, spec_json, created_at FROM orders {where_stmt} ORDER BY id DESC LIMIT ?"
            cursor.execute(query, (int(limit),))
            return [dict(row) for row in cursor.fetchall()]

    def update_order_status(self, order_id: int, new_status: str) -> bool:
        status_text = str(new_status or "").strip()
        if not status_text:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, project_id, title, deadline, deadline_from, deadline_to FROM orders WHERE id = ?",
                (int(order_id),),
            )
            existing = cursor.fetchone()
            if existing is None:
                return False

            cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status_text, int(order_id)))
            updated = cursor.rowcount > 0
            conn.commit()

        if updated:
            status_key = status_text.lower()
            if status_key in {"w_trakcie", "realizacja", "produkcja"}:
                event_type = "produkcja"
            elif status_key in {"montaz", "montaż", "gotowe_do_montazu"}:
                event_type = "montaz"
            elif status_key in {"pomiar"}:
                event_type = "pomiar"
            else:
                event_type = "inne"

            deadline_from = str(existing["deadline_from"] or existing["deadline"] or "").strip()
            deadline_to = str(existing["deadline_to"] or "").strip()
            self.upsert_order_calendar_event(
                order_id=int(existing["id"]),
                project_id=int(existing["project_id"] or 0),
                title=str(existing["title"] or "").strip() or f"Order #{int(existing['id'])}",
                date_from=deadline_from,
                date_to=deadline_to,
                event_type=event_type,
            )
        return updated

    def create_client(
        self,
        name: str,
        location: str = "",
        address: str = "",
        email: str = "",
        phone: str = "",
        client_type: str = "person",
        status: str = "active",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO clients (name, location, address, email, phone, type, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(name or "").strip(),
                    str(location or "").strip(),
                    str(address or "").strip(),
                    str(email or "").strip(),
                    str(phone or "").strip(),
                    str(client_type or "person").strip() or "person",
                    str(status or "active").strip() or "active",
                ),
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def get_clients(self, limit: int = 200, include_deleted: bool = False) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT id, name, location, address, email, phone, type, status, created_at FROM clients"
            if not include_deleted:
                query += " WHERE is_deleted = 0"
            query += " ORDER BY id DESC LIMIT ?"
            cursor.execute(query, (int(limit),))
            return [dict(row) for row in cursor.fetchall()]

    def get_materials(self, include_deleted: bool = False) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT id, name, price_per_m2, thickness, material_code, category, material_kind, unit, is_library, stock_quantity, min_stock, purchase_type, supplier, wholesaler, format_length_mm, format_width_mm, pack_size, parameter_json, texture_url, color_hex FROM materials"
            if not include_deleted:
                query += " WHERE is_deleted = 0"
            query += " ORDER BY id"
            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                {
                    "id": int(row["id"]),
                    "name": str(row["name"] or ""),
                    "price": float(row["price_per_m2"] or 0.0),
                    "thickness": int(row["thickness"] or 0),
                    "material_code": str(row["material_code"] or ""),
                    "category": str(row["category"] or "boards"),
                    "material_kind": str(row["material_kind"] or "other"),
                    "unit": str(row["unit"] or "m2"),
                    "is_library": bool(row["is_library"]),
                    "stock_quantity": float(row["stock_quantity"] or 0.0),
                    "min_stock": float(row["min_stock"] or 0.0),
                    "is_low_stock": (float(row["min_stock"] or 0.0) > 0.0 and float(row["stock_quantity"] or 0.0) <= float(row["min_stock"] or 0.0)),
                    "purchase_type": str(row["purchase_type"] or "nothing"),
                    "supplier": str(row["supplier"] or ""),
                    "wholesaler": str(row["wholesaler"] or ""),
                    "format_length_mm": float(row["format_length_mm"] or 0.0),
                    "format_width_mm": float(row["format_width_mm"] or 0.0),
                    "pack_size": float(row["pack_size"] or 0.0),
                    "parameter_json": str(row["parameter_json"] or "{}"),
                    "texture_url": str(row["texture_url"] or ""),
                    "color_hex": str(row["color_hex"] or "#ffffff"),
                }
                for row in rows
            ]

    def create_material(self, name: str, price_per_m2: float, thickness: int, 
                        category: str = "boards", unit: str = "m2", 
                        material_kind: str = "other",
                        is_library: bool = True, stock_quantity: float = 0.0,
                        min_stock: float = 0.0,
                        purchase_type: str = "nothing",
                        supplier: str = "",
                        wholesaler: str = "",
                        material_code: str = "",
                        format_length_mm: float = 0.0,
                        format_width_mm: float = 0.0,
                        pack_size: float = 0.0,
                        parameter_json: str = "{}",
                        texture_url: str = "", color_hex: str = "#ffffff") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO materials (name, price_per_m2, thickness, material_code, category, material_kind, unit, is_library, stock_quantity, min_stock, purchase_type, supplier, wholesaler, format_length_mm, format_width_mm, pack_size, parameter_json, texture_url, color_hex) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(name or "").strip(),
                    float(price_per_m2 or 0.0),
                    int(thickness or 0),
                    str(material_code or "").strip(),
                    str(category or "boards"),
                    str(material_kind or "other").strip() or "other",
                    str(unit or "m2"),
                    bool(is_library),
                    float(stock_quantity or 0.0),
                    float(min_stock or 0.0),
                    str(purchase_type or "nothing"),
                    str(supplier or "").strip(),
                    str(wholesaler or "").strip(),
                    float(format_length_mm or 0.0),
                    float(format_width_mm or 0.0),
                    float(pack_size or 0.0),
                    str(parameter_json or "{}"),
                    str(texture_url or ""),
                    str(color_hex or "#ffffff")
                ),
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def update_material(self, material_id: int, updates: Dict[str, Any]) -> bool:
        allowed_map = {
            "name": "name",
            "price_per_m2": "price_per_m2",
            "thickness": "thickness",
            "material_code": "material_code",
            "category": "category",
            "material_kind": "material_kind",
            "unit": "unit",
            "min_stock": "min_stock",
            "purchase_type": "purchase_type",
            "supplier": "supplier",
            "wholesaler": "wholesaler",
            "parameter_json": "parameter_json",
            "format_length_mm": "format_length_mm",
            "format_width_mm": "format_width_mm",
            "pack_size": "pack_size",
        }
        set_parts: list[str] = []
        params: list[Any] = []
        for key, column in allowed_map.items():
            if key not in updates:
                continue
            value = updates.get(key)
            if key in {"price_per_m2", "min_stock", "format_length_mm", "format_width_mm", "pack_size"}:
                value = float(value or 0.0)
            elif key in {"thickness"}:
                value = int(value or 0)
            elif key in {"name", "material_code", "category", "material_kind", "unit", "purchase_type", "supplier", "wholesaler", "parameter_json"}:
                value = str(value or "").strip()
            set_parts.append(f"{column} = ?")
            params.append(value)
        if not set_parts:
            return False
        params.append(int(material_id))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE materials SET {', '.join(set_parts)} WHERE id = ?",
                tuple(params),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_low_stock_materials(self, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, category, material_kind, unit, stock_quantity, min_stock, supplier, wholesaler "
                "FROM materials "
                "WHERE min_stock > 0 AND stock_quantity <= min_stock "
                "ORDER BY (min_stock - stock_quantity) DESC, name ASC LIMIT ?",
                (int(limit),),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": int(row["id"]),
                    "name": str(row["name"] or ""),
                    "category": str(row["category"] or ""),
                    "material_kind": str(row["material_kind"] or ""),
                    "unit": str(row["unit"] or "m2"),
                    "stock_quantity": float(row["stock_quantity"] or 0.0),
                    "min_stock": float(row["min_stock"] or 0.0),
                    "missing_qty": max(0.0, float(row["min_stock"] or 0.0) - float(row["stock_quantity"] or 0.0)),
                    "supplier": str(row["supplier"] or ""),
                    "wholesaler": str(row["wholesaler"] or ""),
                }
                for row in rows
            ]

    # --- ZAKUPY I DOSTAWY (ETAP 4) ---
    def add_arrival(
        self,
        material_id: int,
        quantity: float,
        unit: str,
        purchase_type: str,
        document_nr: str,
        price_total: float,
        arrival_date: str,
        order_id: int | None = None,
        unit_price_net: float = 0.0,
        unit_price_gross: float = 0.0,
        supplier: str = "",
        wholesaler: str = "",
        invoice_id: int | None = None,
        invoice_line_item_id: int | None = None,
    ) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO arrivals (material_id, order_id, quantity, unit, purchase_type, document_nr, supplier, wholesaler, unit_price_net, unit_price_gross, price_total, invoice_id, invoice_line_item_id, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(material_id),
                    int(order_id) if order_id else None,
                    float(quantity),
                    str(unit),
                    str(purchase_type),
                    str(document_nr),
                    str(supplier or "").strip(),
                    str(wholesaler or "").strip(),
                    float(unit_price_net or 0.0),
                    float(unit_price_gross or 0.0),
                    float(price_total),
                    int(invoice_id) if invoice_id else None,
                    int(invoice_line_item_id) if invoice_line_item_id else None,
                    str(arrival_date),
                )
            )
            cursor.execute(
                "UPDATE materials SET stock_quantity = stock_quantity + ?, is_library = 0 WHERE id = ?",
                (float(quantity), int(material_id))
            )
            conn.commit()
            return True

    def get_arrivals(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*, m.name as material_name, o.title as order_title
                FROM arrivals a 
                JOIN materials m ON a.material_id = m.id 
                LEFT JOIN orders o ON a.order_id = o.id
                ORDER BY a.date DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def update_arrival(self, arrival_id: int, updates: Dict[str, Any]) -> bool:
        allowed_map = {
            "material_id": "material_id",
            "order_id": "order_id",
            "quantity": "quantity",
            "unit": "unit",
            "purchase_type": "purchase_type",
            "document_nr": "document_nr",
            "supplier": "supplier",
            "wholesaler": "wholesaler",
            "unit_price_net": "unit_price_net",
            "unit_price_gross": "unit_price_gross",
            "price_total": "price_total",
            "invoice_id": "invoice_id",
            "invoice_line_item_id": "invoice_line_item_id",
            "date": "date",
        }
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, material_id, quantity FROM arrivals WHERE id = ?", (int(arrival_id),))
            existing = cursor.fetchone()
            if existing is None:
                return False

            old_material_id = int(existing["material_id"] or 0)
            old_quantity = float(existing["quantity"] or 0.0)

            new_material_id = int(updates.get("material_id", old_material_id) or old_material_id)
            new_quantity = float(updates.get("quantity", old_quantity) or 0.0)

            set_parts: list[str] = []
            params: list[Any] = []
            for key, column in allowed_map.items():
                if key not in updates:
                    continue
                value = updates.get(key)
                if key in {"material_id", "order_id", "invoice_id", "invoice_line_item_id"}:
                    value = int(value) if value is not None else None
                elif key in {"quantity", "unit_price_net", "unit_price_gross", "price_total"}:
                    value = float(value or 0.0)
                elif key in {"unit", "purchase_type", "document_nr", "supplier", "wholesaler", "date"}:
                    value = str(value or "").strip()
                set_parts.append(f"{column} = ?")
                params.append(value)
            if not set_parts:
                return False

            params.append(int(arrival_id))
            cursor.execute(
                f"UPDATE arrivals SET {', '.join(set_parts)} WHERE id = ?",
                tuple(params),
            )
            arrival_updated = cursor.rowcount > 0

            if old_material_id == new_material_id:
                delta = new_quantity - old_quantity
                if abs(delta) > 1e-9:
                    cursor.execute(
                        "UPDATE materials SET stock_quantity = stock_quantity + ? WHERE id = ?",
                        (float(delta), int(old_material_id)),
                    )
            else:
                cursor.execute(
                    "UPDATE materials SET stock_quantity = stock_quantity - ? WHERE id = ?",
                    (float(old_quantity), int(old_material_id)),
                )
                cursor.execute(
                    "UPDATE materials SET stock_quantity = stock_quantity + ? WHERE id = ?",
                    (float(new_quantity), int(new_material_id)),
                )

            conn.commit()
            return arrival_updated

    def get_material_by_name(self, name: str) -> Optional[Dict]:
        """Szuka materiału po nazwie."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, price_per_m2 as price, thickness FROM materials WHERE name = ?",
                (name.strip(),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_db_overview(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM materials")
            materials_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM clients")
            clients_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM projects")
            projects_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM project_modules")
            modules_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM orders")
            orders_count = int(cursor.fetchone()[0] or 0)
            return {
                "materials_count": materials_count,
                "clients_count": clients_count,
                "projects_count": projects_count,
                "modules_count": modules_count,
                "orders_count": orders_count,
            }

    def update_project_margin(self, project_id: int, margin: int):
        """Aktualizuje marĹĽÄ™ dla wyceny precyzyjnej."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET margin = ? WHERE id = ?",
                (margin, project_id)
            )
            conn.commit()

    def get_project_obstacles(self, project_id: int) -> List[Dict]:
        """Pobiera przeszkody (okna, drzwi itp.) dla projektu."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT obstacles_json FROM projects WHERE id = ?", (int(project_id),))
            row = cursor.fetchone()
            if row and row["obstacles_json"]:
                try:
                    return json.loads(row["obstacles_json"])
                except:
                    return []
            return []

    def update_project_obstacles(self, project_id: int, obstacles: List[Dict]) -> bool:
        """Zapisuje listę przeszkód dla projektu."""
        obstacles_json = json.dumps(obstacles)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET obstacles_json = ? WHERE id = ?",
                (obstacles_json, int(project_id))
            )
            conn.commit()
            return cursor.rowcount > 0

    # --- MODUĹY PROJEKTU ---
    def get_project_modules(self, project_id: int) -> List[Dict]:
        """Lista moduĹ‚Ăłw (szafek) dla danego projektu wraz z nazwami materiaĹ‚Ăłw."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pm.id, pm.name, pm.width, pm.height, pm.depth, "
                "pm.x, pm.y, pm.z, pm.rotation, pm.module_family, "
                "pm.material_id, m.name as material_name "
                "FROM project_modules pm "
                "LEFT JOIN materials m ON pm.material_id = m.id "
                "WHERE pm.project_id = ? ORDER BY pm.id",
                (project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_project_material_summary(self, project_id: int) -> List[Dict]:
        """Zwraca podsumowanie zuzycia materialow dla projektu."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT m.name, COUNT(pm.id) as count, "
                "SUM(2 * (pm.width*pm.height + pm.width*pm.depth + pm.height*pm.depth) / 1000000.0) as total_area_m2 "
                "FROM project_modules pm "
                "JOIN materials m ON pm.material_id = m.id "
                "WHERE pm.project_id = ? "
                "GROUP BY m.id",
                (project_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_module_dimension(self, module_id: int, param: str, value: int) -> bool:
        """Zmienia JEDEN wymiar (width|height|depth) dla modułu.

        Zabezpieczenie: param jest whiteliste'owany, by nie było SQL injection
        przez interpolację nazwy kolumny.
        """
        if param not in {"width", "height", "depth"}:
            raise ValueError(f"Nieobsługiwany parametr: {param}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE project_modules SET {param} = ? WHERE id = ?",
                (value, module_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_module_spec(self, module_id: int, spec_json: str) -> bool:
        """Zapisuje pełną specyfikację modułu (JSON) w bazie."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE project_modules SET spec_json = ? WHERE id = ?",
                (spec_json, int(module_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_module_material(self, module_id: int, material_id: int) -> bool:
        """Aktualizuje ID materiału dla modułu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE project_modules SET material_id = ? WHERE id = ?",
                (material_id, module_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_project_module(self, project_id: int, name: str, width: int, height: int, depth: int, material_id: int | None = None) -> int:
        """Dodaje nową szafkę do projektu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO project_modules (project_id, module_name, width, height, depth, material_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, name, width, height, depth, material_id)
            )
            conn.commit()
            return cursor.lastrowid

    def seed_demo_modules_if_empty(self, project_id: int = 1):
        """Na potrzeby dev: tworzy projekt demo + 2 szafki, jeĹ›li baza jest pusta."""
        safe_mode.assert_not_prod("seed_demo_modules_if_empty")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM project_modules")
            if cursor.fetchone()[0] > 0:
                return
            cursor.execute("SELECT COUNT(*) FROM projects")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO projects (id, title, client_name) VALUES (?, ?, ?)",
                    (project_id, "Projekt demo", "Klient demo"),
                )
            cursor.execute(
                "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
                (project_id, "Szafka D60", 600, 720, 500),
            )
            cursor.execute(
                "INSERT INTO project_modules (project_id, module_name, width, height, depth) VALUES (?, ?, ?, ?, ?)",
                (project_id, "Szafka D80", 800, 720, 500),
            )
            conn.commit()

    def seed_demo_materials_if_empty(self):
        safe_mode.assert_not_prod("seed_demo_materials_if_empty")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM materials")
            if cursor.fetchone()[0] > 0:
                return
            cursor.execute(
                "INSERT INTO materials (name, price_per_m2, thickness, color_hex, category) VALUES (?, ?, ?, ?, ?)",
                ("Biały Diament", 22.50, 18, "#ffffff", "boards"),
            )
            cursor.execute(
                "INSERT INTO materials (name, price_per_m2, thickness, color_hex, category) VALUES (?, ?, ?, ?, ?)",
                ("Dąb Craft Złoty", 45.00, 18, "#c19a6b", "boards"),
            )
            cursor.execute(
                "INSERT INTO materials (name, price_per_m2, thickness, color_hex, category) VALUES (?, ?, ?, ?, ?)",
                ("Antracyt Metalic", 35.00, 18, "#3c3c3c", "boards"),
            )
            conn.commit()

    def seed_demo_clients_if_empty(self):
        safe_mode.assert_not_prod("seed_demo_clients_if_empty")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            if cursor.fetchone()[0] > 0:
                return
            cursor.execute(
                "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
                ("Nowak Piotr", "ul. Polna 12, Warszawa", "person", "active"),
            )
            cursor.execute(
                "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
                ("Analityka Meble Sp. z o.o.", "Partner B2B", "b2b", "vip"),
            )
            cursor.execute(
                "INSERT INTO clients (name, location, type, status) VALUES (?, ?, ?, ?)",
                ("Kowalski Jan", "ul. Lesna 3, Krakow", "person", "archived"),
            )
            conn.commit()

    def _ensure_login_users(self, cursor):
        allowed_users = [
            ("Admin", "wlasciciel", "#1e3a5f"),
            ("В'ячеслав Микитюк", "wlasciciel", "#2563eb"),
            ("Ірина Микитюк", "biuro", "#16a34a"),
            ("Андрій Борщ", "produkcja", "#f97316"),
            ("Емілія Кміта", "biuro", "#a855f7"),
        ]
        allowed_names = [name for name, _role, _color in allowed_users]
        placeholders = ",".join("?" for _ in allowed_names)
        cursor.execute(
            f"UPDATE technicians SET is_active = 0 WHERE name NOT IN ({placeholders})",
            tuple(allowed_names),
        )
        for name, role, color in allowed_users:
            cursor.execute(
                """
                INSERT INTO technicians (name, role, pin_code, avatar_color, is_active, password_hash)
                VALUES (?, ?, '1', ?, 1, '')
                ON CONFLICT(name) DO UPDATE SET
                    role = excluded.role,
                    pin_code = '1',
                    avatar_color = excluded.avatar_color,
                    is_active = 1,
                    password_hash = ''
                """,
                (name, role, color),
            )

    def get_technicians(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, role, avatar_color, last_active, is_active FROM technicians ORDER BY name")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # --- AUTHENTICATION & SESSIONS ---
    
    def _hash_password(self, password: str) -> str:
        import hashlib
        import os
        # We use pbkdf2_hmac with a fixed salt for simplicity, or we can store salt with hash.
        # Format: pbkdf2:sha256:iterations$salt$hash
        salt = os.urandom(16)
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return f"pbkdf2:sha256:100000${salt.hex()}${hash_bytes.hex()}"

    def _verify_password(self, password: str, hash_string: str) -> bool:
        if not hash_string or not hash_string.startswith("pbkdf2:sha256:"):
            return False
        import hashlib
        try:
            _, _, iterations_str, salt_hex, hash_hex = hash_string.split("$")[0].split(":") + hash_string.split("$")[1:]
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, int(iterations_str))
            import hmac
            return hmac.compare_digest(expected_hash, actual_hash)
        except Exception:
            return False
            
    def set_user_password(self, user_id: int, password: str) -> bool:
        pass_hash = self._hash_password(password)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE technicians SET password_hash = ? WHERE id = ?", (pass_hash, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def authenticate_user(self, username: str, password: str = "") -> Dict | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, role, is_active FROM technicians WHERE name = ? LIMIT 1", (username,))
            row = cursor.fetchone()
            if not row or not row["is_active"]:
                return None
                
            # PIN logic removed as per user request to streamline access.
            # We just return the user data if they exist and are active.
            return {"id": row["id"], "name": row["name"], "role": row["role"]}

    def create_session(self, user_id: int) -> str:
        import secrets
        from datetime import datetime, timedelta
        
        token = secrets.token_hex(32)
        expires = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, expires)
            )
            conn.commit()
        return token

    def get_user_by_token(self, token: str) -> Dict | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.name, t.role, t.is_active
                FROM sessions s
                JOIN technicians t ON s.user_id = t.id
                WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
            """, (token,))
            row = cursor.fetchone()
            if row and row["is_active"]:
                return {"id": row["id"], "name": row["name"], "role": row["role"]}
            return None

    def logout_user(self, token: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            
    # --- ADMIN USER MANAGEMENT ---
    def admin_create_user(self, name: str, role: str, password: str) -> int:
        pass_hash = self._hash_password(password) if password else ""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO technicians (name, role, password_hash, is_active) VALUES (?, ?, ?, 1)",
                (name, role, pass_hash)
            )
            conn.commit()
            return cursor.lastrowid
            
    def admin_update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        allowed_keys = {"name", "role", "is_active", "password"}
        set_parts = []
        params = []
        for key, value in updates.items():
            if key not in allowed_keys: continue
            if key == "password":
                set_parts.append("password_hash = ?")
                params.append(self._hash_password(value))
            elif key == "is_active":
                set_parts.append("is_active = ?")
                params.append(int(value))
            else:
                set_parts.append(f"{key} = ?")
                params.append(value)
                
        if not set_parts: return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE technicians SET {', '.join(set_parts)} WHERE id = ?", tuple(params + [user_id]))
            conn.commit()
            return cursor.rowcount > 0

    def create_invoice(self, nr: str, date: str, nip: str, net: float, vat: float, gross: float, folder: str = "Projekt") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO invoices (invoice_nr, date, nip, net_amount, vat_amount, gross_amount, folder) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nr, date, nip, float(net), float(vat), float(gross), folder)
            )
            conn.commit()
            return cursor.lastrowid

    def _normalize_invoice_number(self, value: str) -> str:
        return "".join(ch for ch in str(value or "").upper() if ch.isalnum())

    def _normalize_text(self, value: str) -> str:
        return str(value or "").strip().lower()

    def _normalize_date(self, value: str) -> str:
        text = str(value or "").strip()
        if len(text) >= 10:
            return text[:10]
        return text

    def _build_invoice_signature(
        self,
        *,
        invoice_nr: str,
        invoice_date: str,
        supplier: str,
        gross_amount: float,
        currency: str,
    ) -> str:
        payload = "|".join(
            [
                self._normalize_invoice_number(invoice_nr),
                self._normalize_date(invoice_date),
                self._normalize_text(supplier),
                f"{float(gross_amount or 0.0):.2f}",
                str(currency or "PLN").strip().upper(),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def import_invoice_with_lines(
        self,
        *,
        invoice_nr: str,
        invoice_date: str,
        nip: str,
        supplier: str,
        currency: str,
        total_net: float,
        total_vat: float,
        total_gross: float,
        payload_hash: str,
        source_filename: str,
        parse_method: str,
        parse_confidence: float,
        line_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        invoice_nr = str(invoice_nr or "").strip()
        invoice_date = str(invoice_date or "").strip()
        nip = str(nip or "").strip()
        supplier = str(supplier or "").strip()
        currency = str(currency or "PLN").strip().upper() or "PLN"
        payload_hash = str(payload_hash or "").strip().lower()
        signature = self._build_invoice_signature(
            invoice_nr=invoice_nr,
            invoice_date=invoice_date,
            supplier=supplier,
            gross_amount=float(total_gross or 0.0),
            currency=currency,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if payload_hash:
                cursor.execute("SELECT id FROM invoices WHERE payload_hash = ? LIMIT 1", (payload_hash,))
                existing = cursor.fetchone()
                if existing is not None:
                    return {"invoice_id": int(existing["id"]), "is_duplicate": True, "duplicate_reason": "payload_hash"}

            cursor.execute(
                "SELECT id FROM invoices WHERE invoice_signature = ? AND invoice_signature <> '' LIMIT 1",
                (signature,),
            )
            existing_sig = cursor.fetchone()
            if existing_sig is not None:
                return {"invoice_id": int(existing_sig["id"]), "is_duplicate": True, "duplicate_reason": "invoice_signature"}

            cursor.execute(
                """
                INSERT INTO invoices (
                    invoice_nr, date, nip, supplier, currency, net_amount, vat_amount, gross_amount,
                    folder, payload_hash, invoice_signature, source_filename, parse_method, parse_confidence, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_nr,
                    invoice_date,
                    nip,
                    supplier,
                    currency,
                    float(total_net or 0.0),
                    float(total_vat or 0.0),
                    float(total_gross or 0.0),
                    "Upload",
                    payload_hash,
                    signature,
                    str(source_filename or "").strip(),
                    str(parse_method or "").strip(),
                    float(parse_confidence or 0.0),
                    "IMPORTED",
                ),
            )
            invoice_id = int(cursor.lastrowid or 0)

            for idx, row in enumerate(line_items or [], start=1):
                cursor.execute(
                    """
                    INSERT INTO invoice_line_items (
                        invoice_id, line_no, raw_line, name_raw, name_norm, quantity, unit,
                        unit_price_net, unit_price_gross, total_net, total_gross, vat_rate,
                        material_type, thickness_mm, parse_source, confidence, review_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        idx,
                        str(row.get("raw_line", "") or "").strip(),
                        str(row.get("name", "") or "").strip(),
                        self._normalize_text(str(row.get("name", "") or "")),
                        float(row.get("quantity", 0.0) or 0.0),
                        str(row.get("unit", "") or "").strip(),
                        float(row.get("unit_price_net", 0.0) or 0.0),
                        float(row.get("unit_price_gross", 0.0) or 0.0),
                        float(row.get("total_price_net", 0.0) or 0.0),
                        float(row.get("total_price_gross", 0.0) or 0.0),
                        str(row.get("vat_rate", "") or "").strip(),
                        str(row.get("material_type", "") or "").strip(),
                        str(row.get("thickness_mm", "") or "").strip(),
                        str(row.get("parse_source", "") or "").strip(),
                        float(row.get("confidence", 0.0) or 0.0),
                        "needs_review",
                    ),
                )

            conn.commit()
            return {"invoice_id": invoice_id, "is_duplicate": False, "duplicate_reason": ""}

    def get_invoices_with_line_stats(self, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT i.*,
                       COUNT(li.id) AS line_items_total,
                       SUM(CASE WHEN li.review_status IN ('confirmed', 'exported') THEN 1 ELSE 0 END) AS line_items_reviewed,
                       SUM(CASE WHEN li.review_status = 'exported' THEN 1 ELSE 0 END) AS line_items_exported
                FROM invoices i
                LEFT JOIN invoice_line_items li ON li.invoice_id = i.id
                GROUP BY i.id
                ORDER BY i.created_at DESC, i.id DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_invoice_line_items(self, invoice_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT li.*
                FROM invoice_line_items li
                WHERE li.invoice_id = ?
                ORDER BY li.line_no ASC, li.id ASC
                """,
                (int(invoice_id),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_invoice_line_item(
        self,
        *,
        invoice_id: int,
        line_item_id: int,
        updates: Dict[str, Any],
    ) -> bool:
        allowed_map = {
            "review_status": "review_status",
            "selected_material_id": "selected_material_id",
            "selected_material_name": "selected_material_name",
            "notes": "notes",
            "quantity": "quantity",
            "unit": "unit",
            "unit_price_net": "unit_price_net",
            "unit_price_gross": "unit_price_gross",
            "total_net": "total_net",
            "total_gross": "total_gross",
        }
        set_parts: list[str] = []
        params: list[Any] = []
        for key, column in allowed_map.items():
            if key not in updates:
                continue
            value = updates.get(key)
            if key in {"selected_material_id"}:
                value = int(value) if value is not None else None
            elif key in {"quantity", "unit_price_net", "unit_price_gross", "total_net", "total_gross"}:
                value = float(value or 0.0)
            else:
                value = str(value or "").strip()
            set_parts.append(f"{column} = ?")
            params.append(value)
        if not set_parts:
            return False
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([int(line_item_id), int(invoice_id)])
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE invoice_line_items SET {', '.join(set_parts)} WHERE id = ? AND invoice_id = ?",
                tuple(params),
            )
            conn.commit()
            return cursor.rowcount > 0

    def confirm_invoice_to_arrivals(
        self,
        *,
        invoice_id: int,
        line_item_ids: List[int] | None = None,
    ) -> Dict[str, Any]:
        selected_ids = [int(x) for x in (line_item_ids or []) if int(x) > 0]
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("BEGIN")
            try:
                cursor.execute("SELECT * FROM invoices WHERE id = ?", (int(invoice_id),))
                invoice = cursor.fetchone()
                if invoice is None:
                    raise ValueError("Nie znaleziono faktury")

                if selected_ids:
                    placeholders = ",".join("?" for _ in selected_ids)
                    cursor.execute(
                        f"""
                        SELECT li.*
                        FROM invoice_line_items li
                        WHERE li.invoice_id = ? AND li.id IN ({placeholders})
                        ORDER BY li.id ASC
                        """,
                        tuple([int(invoice_id)] + selected_ids),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT li.*
                        FROM invoice_line_items li
                        WHERE li.invoice_id = ?
                        ORDER BY li.id ASC
                        """,
                        (int(invoice_id),),
                    )
                rows = cursor.fetchall()

                arrivals_created = 0
                price_history_written = 0
                skipped = 0
                for row in rows:
                    review_status = str(row["review_status"] or "").strip().lower()
                    material_id = row["selected_material_id"]
                    confidence = float(row["confidence"] or 0.0)
                    unit = str(row["unit"] or "").strip()
                    if (
                        review_status != "confirmed"
                        or material_id is None
                        or confidence < 0.60
                        or not unit
                    ):
                        skipped += 1
                        continue

                    line_id = int(row["id"])
                    cursor.execute(
                        "SELECT id FROM arrivals WHERE invoice_line_item_id = ? LIMIT 1",
                        (line_id,),
                    )
                    if cursor.fetchone() is not None:
                        skipped += 1
                        continue

                    quantity = float(row["quantity"] or 0.0)
                    net_price = float(row["unit_price_net"] or 0.0)
                    gross_price = float(row["unit_price_gross"] or 0.0)
                    total_gross = float(row["total_gross"] or 0.0)
                    total_net = float(row["total_net"] or 0.0)
                    price_total = total_gross if total_gross > 0 else (total_net if total_net > 0 else (gross_price * quantity))

                    cursor.execute(
                        """
                        INSERT INTO arrivals (
                            material_id, order_id, quantity, unit, purchase_type, document_nr,
                            supplier, wholesaler, unit_price_net, unit_price_gross, price_total,
                            invoice_id, invoice_line_item_id, date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(material_id),
                            None,
                            float(quantity),
                            unit,
                            "invoice",
                            str(invoice["invoice_nr"] or "").strip(),
                            str(invoice["supplier"] or "").strip(),
                            "",
                            float(net_price),
                            float(gross_price),
                            float(price_total),
                            int(invoice_id),
                            line_id,
                            str(invoice["date"] or "").strip(),
                        ),
                    )
                    cursor.execute(
                        "UPDATE materials SET stock_quantity = stock_quantity + ?, is_library = 0 WHERE id = ?",
                        (float(quantity), int(material_id)),
                    )
                    arrivals_created += 1

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO price_history (
                            material_id, supplier, invoice_id, invoice_line_item_id, purchase_date,
                            unit, net_price, gross_price, currency, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(material_id),
                            str(invoice["supplier"] or "").strip(),
                            int(invoice_id),
                            line_id,
                            str(invoice["date"] or "").strip(),
                            unit,
                            float(net_price),
                            float(gross_price),
                            str(invoice["currency"] or "PLN").strip().upper() or "PLN",
                            "invoice_confirm_export",
                        ),
                    )
                    if cursor.rowcount > 0:
                        price_history_written += 1

                    cursor.execute(
                        "UPDATE invoice_line_items SET review_status = 'exported', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (line_id,),
                    )

                cursor.execute(
                    """
                    SELECT
                      SUM(CASE WHEN review_status = 'exported' THEN 1 ELSE 0 END) AS exported_count,
                      SUM(CASE WHEN review_status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_count,
                      COUNT(*) AS total_count
                    FROM invoice_line_items
                    WHERE invoice_id = ?
                    """,
                    (int(invoice_id),),
                )
                status_row = cursor.fetchone()
                exported_count = int(status_row["exported_count"] or 0)
                confirmed_count = int(status_row["confirmed_count"] or 0)
                total_count = int(status_row["total_count"] or 0)
                next_status = str(invoice["status"] or "IMPORTED")
                if total_count > 0 and exported_count == total_count:
                    next_status = "CONFIRMED"
                elif exported_count > 0 or confirmed_count > 0:
                    next_status = "PARTIAL"
                else:
                    next_status = "IMPORTED"
                cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (next_status, int(invoice_id)))

                conn.commit()
                return {
                    "invoice_id": int(invoice_id),
                    "arrivals_created": arrivals_created,
                    "price_history_written": price_history_written,
                    "skipped_lines": skipped,
                    "status": next_status,
                }
            except Exception:
                conn.rollback()
                raise

    def get_invoices(self, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM invoices ORDER BY date DESC, id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tax_summary(self) -> Dict:
        """Oblicza saldo VAT: VAT z zamówień (sprzedaż) - VAT z faktur (koszty)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # VAT ze sprzedaży (Zamówienia) - zakładamy 23% od budget (Net)
            cursor.execute("SELECT SUM(budget) FROM orders")
            total_sales_net = float(cursor.fetchone()[0] or 0.0)
            vat_collected = total_sales_net * 0.23

            # VAT z kosztów (Faktury)
            cursor.execute("SELECT SUM(vat_amount), SUM(net_amount), SUM(gross_amount) FROM invoices")
            res = cursor.fetchone()
            vat_paid = float(res[0] or 0.0)
            costs_net = float(res[1] or 0.0)
            costs_gross = float(res[2] or 0.0)

            tax_balance = vat_collected - vat_paid

            return {
                "sales_net": round(total_sales_net, 2),
                "vat_collected": round(vat_collected, 2),
                "costs_net": round(costs_net, 2),
                "vat_paid": round(vat_paid, 2),
                "costs_gross": round(costs_gross, 2),
                "tax_balance": round(tax_balance, 2),
                "recommendation": "Do zapłaty" if tax_balance > 0 else "Nadpłata / Zwrot"
            }

    def login_technician(self, name: str, pin: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM technicians WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            user = dict(row)
            if user["pin_code"] == pin:
                cursor.execute("UPDATE technicians SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
                conn.commit()
                return user
            return None


    # =====================================================================
    # Inventory + Order Cost Write-Off — CRUD methods
    # =====================================================================

    # --- Purchase Documents ---

    def create_purchase_document(
        self,
        supplier_name: str,
        document_number: str,
        document_date: str,
        document_type: str = "invoice",
        currency: str = "PLN",
        total_net: float = 0.0,
        total_gross: float = 0.0,
        payment_status: str = "unpaid",
        payment_method: str = "",
        note: str = "",
        created_by: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO purchase_documents
                   (supplier_name, document_number, document_date, document_type,
                    currency, total_net, total_gross, payment_status, payment_method, note)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(supplier_name),
                    str(document_number),
                    str(document_date),
                    str(document_type),
                    str(currency),
                    float(total_net),
                    float(total_gross),
                    str(payment_status),
                    str(payment_method),
                    str(note),
                ),
            )
            doc_id = cursor.lastrowid
            conn.commit()
            self.log_action(
                user_name=created_by,
                action="PURCHASE_DOC_CREATE",
                target_type="purchase_document",
                target_id=str(doc_id),
                details=f"Supplier: {supplier_name}, No: {document_number}",
                metadata={"total_net": total_net, "total_gross": total_gross}
            )
            return doc_id

    def create_purchase_document_line(
        self,
        purchase_document_id: int,
        material_id: Optional[int],
        description_snapshot: str = "",
        qty: float = 0.0,
        unit: str = "pcs",
        unit_price_net: float = 0.0,
        vat_rate: float = 23.0,
        line_total_net: float = 0.0,
        line_total_gross: float = 0.0,
        is_stock_item: bool = True,
        order_id: Optional[int] = None,
        note: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO purchase_document_lines
                   (purchase_document_id, material_id, description_snapshot, qty, unit,
                    unit_price_net, vat_rate, line_total_net, line_total_gross,
                    is_stock_item, order_id, note)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(purchase_document_id),
                    int(material_id) if material_id is not None else None,
                    str(description_snapshot),
                    float(qty),
                    str(unit),
                    float(unit_price_net),
                    float(vat_rate),
                    float(line_total_net),
                    float(line_total_gross),
                    1 if is_stock_item else 0,
                    int(order_id) if order_id is not None else None,
                    str(note),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_purchase_documents(self, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM purchase_documents ORDER BY document_date DESC, id DESC LIMIT ?",
                (int(limit),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_purchase_document(self, doc_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM purchase_documents WHERE id = ?", (int(doc_id),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_purchase_document_lines(self, doc_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT pdl.*, m.name AS material_name
                   FROM purchase_document_lines pdl
                   LEFT JOIN materials m ON pdl.material_id = m.id
                   WHERE pdl.purchase_document_id = ?
                   ORDER BY pdl.id""",
                (int(doc_id),),
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Inventory Movements ---

    def create_inventory_movement(
        self,
        material_id: int,
        movement_type: str,
        qty: float,
        unit: str = "pcs",
        unit_cost_net: Optional[float] = None,
        total_cost_net: Optional[float] = None,
        location: str = "main",
        order_id: Optional[int] = None,
        purchase_document_id: Optional[int] = None,
        purchase_document_line_id: Optional[int] = None,
        related_movement_id: Optional[int] = None,
        note: str = "",
        created_by: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inventory_movements
                   (material_id, movement_type, qty, unit, unit_cost_net, total_cost_net,
                    location, order_id, purchase_document_id, purchase_document_line_id,
                    related_movement_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(material_id),
                    str(movement_type),
                    float(qty),
                    str(unit),
                    float(unit_cost_net) if unit_cost_net is not None else None,
                    float(total_cost_net) if total_cost_net is not None else None,
                    str(location),
                    int(order_id) if order_id is not None else None,
                    int(purchase_document_id) if purchase_document_id is not None else None,
                    int(purchase_document_line_id) if purchase_document_line_id is not None else None,
                    int(related_movement_id) if related_movement_id is not None else None,
                    str(note),
                    str(created_by),
                ),
            )
            movement_id = cursor.lastrowid
            conn.commit()
            
            # Audit log for inventory changes
            self.log_action(
                user_name=created_by,
                action=f"INV_{movement_type}",
                target_type="material",
                target_id=str(material_id),
                details=f"{movement_type} {qty} {unit}. {note}",
                metadata={
                    "movement_id": movement_id,
                    "order_id": order_id,
                    "type": movement_type,
                    "qty": qty
                }
            )
            return movement_id

    def get_inventory_movements(
        self, material_id: Optional[int] = None, order_id: Optional[int] = None, limit: int = 500
    ) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            where_parts: list = []
            params: list = []
            if material_id is not None:
                where_parts.append("im.material_id = ?")
                params.append(int(material_id))
            if order_id is not None:
                where_parts.append("im.order_id = ?")
                params.append(int(order_id))
            where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            params.append(int(limit))
            cursor.execute(
                f"""SELECT im.*, m.name AS material_name, o.title AS order_title, o.client_name AS order_client_name
                    FROM inventory_movements im
                    LEFT JOIN materials m ON im.material_id = m.id
                    LEFT JOIN orders o ON im.order_id = o.id
                    {where_clause}
                    ORDER BY im.created_at DESC, im.id DESC
                    LIMIT ?""",
                tuple(params),
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Inventory Balances ---

    def rebuild_inventory_balance(self, material_id: int) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN movement_type IN ('IN','RETURN','CORRECTION') THEN qty ELSE 0 END), 0)
                     - COALESCE(SUM(CASE WHEN movement_type IN ('OUT','SCRAP') THEN qty ELSE 0 END), 0)
                       AS qty_on_hand,
                       COALESCE(SUM(CASE WHEN movement_type = 'RESERVED' THEN qty ELSE 0 END), 0)
                       AS qty_reserved
                   FROM inventory_movements
                   WHERE material_id = ?""",
                (int(material_id),),
            )
            row = cursor.fetchone()
            qty_on_hand = float(row["qty_on_hand"]) if row else 0.0
            qty_reserved = float(row["qty_reserved"]) if row else 0.0
            qty_available = qty_on_hand - qty_reserved

            cursor.execute(
                """INSERT INTO inventory_balances (material_id, qty_on_hand, qty_reserved, qty_available, last_updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(material_id) DO UPDATE SET
                       qty_on_hand = excluded.qty_on_hand,
                       qty_reserved = excluded.qty_reserved,
                       qty_available = excluded.qty_available,
                       last_updated_at = CURRENT_TIMESTAMP""",
                (int(material_id), qty_on_hand, qty_reserved, qty_available),
            )
            conn.commit()
            return {
                "material_id": int(material_id),
                "qty_on_hand": qty_on_hand,
                "qty_reserved": qty_reserved,
                "qty_available": qty_available,
            }

    def get_inventory_balances(self, limit: int = 500) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ib.*, m.name AS material_name, m.unit AS material_unit
                   FROM inventory_balances ib
                   LEFT JOIN materials m ON ib.material_id = m.id
                   ORDER BY m.name
                   LIMIT ?""",
                (int(limit),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_procurement_data(self) -> List[Dict]:
        """Calculates material availability, shortages, and purchase suggestions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Get all materials and current balances
            cursor.execute("""
                SELECT m.id, m.name, m.material_code, m.unit, m.min_stock, m.category,
                       ib.qty_on_hand, ib.qty_reserved, ib.qty_available
                FROM materials m
                LEFT JOIN inventory_balances ib ON m.id = ib.material_id
                WHERE m.is_deleted = 0
            """)
            materials = [dict(row) for row in cursor.fetchall()]
            
            # 2. Get incoming quantities (Purchased but not arrived)
            # We look at purchase_document_lines and subtract any linked arrivals
            cursor.execute("""
                SELECT pdl.material_id, 
                       SUM(pdl.qty) as purchased_qty,
                       COALESCE(SUM(arr_sum.arrived_qty), 0) as received_qty
                FROM purchase_document_lines pdl
                LEFT JOIN (
                    SELECT purchase_document_line_id, SUM(quantity) as arrived_qty
                    FROM arrivals
                    GROUP BY purchase_document_line_id
                ) arr_sum ON pdl.id = arr_sum.purchase_document_line_id
                WHERE pdl.material_id IS NOT NULL
                GROUP BY pdl.material_id
            """)
            incoming_map = {row["material_id"]: max(0, row["purchased_qty"] - row["received_qty"]) for row in cursor.fetchall()}
            
            # 3. Get detailed demand (who needs what)
            cursor.execute("""
                SELECT im.material_id, im.order_id, o.title as order_title, o.client_name, SUM(im.qty) as reserved_qty
                FROM inventory_movements im
                JOIN orders o ON im.order_id = o.id
                WHERE im.movement_type = 'RESERVED'
                GROUP BY im.material_id, im.order_id
            """)
            demand_details = {}
            for row in cursor.fetchall():
                mid = row["material_id"]
                if mid not in demand_details: demand_details[mid] = []
                demand_details[mid].append({
                    "order_id": row["order_id"],
                    "order_title": row["order_title"],
                    "client_name": row["client_name"],
                    "qty": row["reserved_qty"]
                })
                
            # 4. Assemble final rows
            results = []
            for m in materials:
                mid = m["id"]
                on_hand = m["qty_on_hand"] or 0.0
                reserved = m["qty_reserved"] or 0.0
                min_stock = m["min_stock"] or 0.0
                incoming = incoming_map.get(mid, 0.0)
                
                # Shortage is when (On Hand + Incoming) < (Reserved + Min Stock)
                total_need = reserved + min_stock
                total_supply = on_hand + incoming
                shortage = max(0.0, total_need - total_supply)
                
                status = "OK"
                if shortage > 0:
                    status = "SHORTAGE"
                    if on_hand < reserved:
                        status = "CRITICAL"
                
                results.append({
                    "material_id": mid,
                    "name": m["name"],
                    "code": m["material_code"],
                    "unit": m["unit"],
                    "category": m["category"],
                    "qty_on_hand": on_hand,
                    "qty_reserved": reserved,
                    "qty_incoming": incoming,
                    "qty_available": on_hand - reserved,
                    "min_stock": min_stock,
                    "shortage": shortage,
                    "status": status,
                    "demand_orders": demand_details.get(mid, [])
                })
                
            return results

    # --- Cash / Bank Movements ---

    def create_cash_bank_movement(
        self,
        movement_type: str,
        amount: float,
        currency: str = "PLN",
        payment_method: str = "",
        supplier_name: str = "",
        purchase_document_id: Optional[int] = None,
        order_id: Optional[int] = None,
        note: str = "",
        created_by: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cash_bank_movements
                   (movement_type, amount, currency, payment_method, supplier_name,
                    purchase_document_id, order_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    str(movement_type),
                    float(amount),
                    str(currency),
                    str(payment_method),
                    str(supplier_name),
                    int(purchase_document_id) if purchase_document_id is not None else None,
                    int(order_id) if order_id is not None else None,
                    str(note),
                    str(created_by),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_cash_bank_movements(self, limit: int = 500) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM cash_bank_movements ORDER BY created_at DESC, id DESC LIMIT ?",
                (int(limit),),
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Order Cost Entries ---

    def create_order_cost_entry(
        self,
        order_id: int,
        cost_type: str = "MATERIAL",
        source_type: str = "",
        source_id: Optional[int] = None,
        amount_net: float = 0.0,
        vat_rate: float = 23.0,
        amount_gross: float = 0.0,
        qty: Optional[float] = None,
        unit: Optional[str] = None,
        description: str = "",
        note: str = "",
        created_by: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO order_cost_entries
                   (order_id, cost_type, source_type, source_id, amount_net,
                    vat_rate, amount_gross, qty, unit, description, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(order_id),
                    str(cost_type),
                    str(source_type),
                    int(source_id) if source_id is not None else None,
                    float(amount_net),
                    float(vat_rate),
                    float(amount_gross),
                    float(qty) if qty is not None else None,
                    str(unit) if unit is not None else None,
                    str(description),
                    str(note),
                    str(created_by),
                ),
            )
            entry_id = cursor.lastrowid
            conn.commit()
            
            # Audit log for cost entry
            self.log_action(
                user_name=created_by,
                action="COST_ENTRY_CREATE",
                target_type="order",
                target_id=str(order_id),
                details=f"New {cost_type} entry: {amount_net} PLN. {description}",
                metadata={
                    "entry_id": entry_id,
                    "cost_type": cost_type,
                    "amount_net": amount_net
                }
            )
            return entry_id

    def get_order_cost_entries(self, order_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM order_cost_entries WHERE order_id = ? ORDER BY created_at DESC, id DESC",
                (int(order_id),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_order_cost_summary(self, order_id: int) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT cost_type, COUNT(*) AS entries, SUM(amount_net) AS total_net, SUM(amount_gross) AS total_gross
                   FROM order_cost_entries WHERE order_id = ? GROUP BY cost_type""",
                (int(order_id),),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            total_net = sum(float(r.get("total_net", 0) or 0) for r in rows)
            total_gross = sum(float(r.get("total_gross", 0) or 0) for r in rows)
            return {
                "order_id": int(order_id),
                "by_type": rows,
                "total_net": round(total_net, 2),
                "total_gross": round(total_gross, 2),
            }

    # --- Stage 3: Reservation + Issue-to-Order + Cost Assignment ---

    def get_material_unit_cost(self, material_id: int) -> float:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT SUM(qty) AS total_qty, SUM(total_cost_net) AS total_cost
                   FROM inventory_movements
                   WHERE material_id = ? AND movement_type = 'IN'
                     AND unit_cost_net IS NOT NULL AND qty > 0""",
                (int(material_id),),
            )
            row = cursor.fetchone()
            total_qty = float(row["total_qty"] or 0) if row else 0.0
            total_cost = float(row["total_cost"] or 0) if row else 0.0
            if total_qty > 0 and total_cost > 0:
                return round(total_cost / total_qty, 4)
            cursor.execute(
                """SELECT unit_cost_net FROM inventory_movements
                   WHERE material_id = ? AND movement_type = 'IN'
                     AND unit_cost_net IS NOT NULL AND unit_cost_net > 0
                   ORDER BY created_at DESC, id DESC LIMIT 1""",
                (int(material_id),),
            )
            row2 = cursor.fetchone()
            if row2:
                return float(row2["unit_cost_net"])
            return 0.0

    def reserve_material_for_order(
        self,
        material_id: int,
        order_id: int,
        qty: float,
        unit: str = "pcs",
        note: str = "",
        created_by: str = "",
    ) -> Dict:
        if qty <= 0:
            raise ValueError("Reservation qty must be positive")
        balance = self.rebuild_inventory_balance(material_id)
        if balance["qty_available"] < qty:
            raise ValueError(
                f"Insufficient available stock: {balance['qty_available']} {unit} available, {qty} requested"
            )
        movement_id = self.create_inventory_movement(
            material_id=material_id,
            movement_type="RESERVED",
            qty=qty,
            unit=unit,
            order_id=order_id,
            note=note or f"Reservation for order #{order_id}",
            created_by=created_by,
        )
        new_balance = self.rebuild_inventory_balance(material_id)
        return {
            "status": "reserved",
            "movement_id": movement_id,
            "material_id": material_id,
            "order_id": order_id,
            "qty_reserved": qty,
            "balance": new_balance,
        }

    def cancel_reservation(
        self, reservation_movement_id: int, created_by: str = ""
    ) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM inventory_movements WHERE id = ?",
                (int(reservation_movement_id),),
            )
            orig = cursor.fetchone()
            if not orig:
                raise ValueError(f"Movement {reservation_movement_id} not found")
            orig = dict(orig)
            if orig["movement_type"] != "RESERVED":
                raise ValueError(f"Movement {reservation_movement_id} is not a RESERVED movement")
            if float(orig["qty"] or 0) <= 0:
                raise ValueError(f"Movement {reservation_movement_id} already cancelled")

        cancel_id = self.create_inventory_movement(
            material_id=int(orig["material_id"]),
            movement_type="RESERVED",
            qty=-float(orig["qty"]),
            unit=str(orig.get("unit", "pcs")),
            order_id=orig.get("order_id"),
            related_movement_id=reservation_movement_id,
            note=f"Cancellation of reservation #{reservation_movement_id}",
            created_by=created_by,
        )
        new_balance = self.rebuild_inventory_balance(int(orig["material_id"]))
        return {
            "status": "cancelled",
            "cancel_movement_id": cancel_id,
            "original_movement_id": reservation_movement_id,
            "balance": new_balance,
        }

    def _auto_cancel_reservation_for_issue(
        self, cursor, material_id: int, order_id: int, issue_qty: float, created_by: str
    ) -> int:
        cursor.execute(
            """SELECT id, qty FROM inventory_movements
               WHERE material_id = ? AND order_id = ? AND movement_type = 'RESERVED' AND qty > 0
               ORDER BY created_at ASC""",
            (int(material_id), int(order_id)),
        )
        remaining = issue_qty
        cancelled = 0
        for row in cursor.fetchall():
            if remaining <= 0:
                break
            res_id = int(row[0])
            res_qty = float(row[1])
            cancel_qty = min(res_qty, remaining)
            cursor.execute(
                """INSERT INTO inventory_movements
                   (material_id, movement_type, qty, unit, order_id,
                    related_movement_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    int(material_id),
                    "RESERVED",
                    -cancel_qty,
                    "pcs",
                    int(order_id),
                    res_id,
                    f"Auto-cancel reservation #{res_id} on issue",
                    str(created_by),
                ),
            )
            remaining -= cancel_qty
            cancelled += 1
        return cancelled

    def issue_material_to_order(
        self,
        material_id: int,
        order_id: int,
        qty: float,
        unit: str = "pcs",
        unit_cost_override: Optional[float] = None,
        note: str = "",
        created_by: str = "",
    ) -> Dict:
        if qty <= 0:
            raise ValueError("Issue qty must be positive")
        balance = self.rebuild_inventory_balance(material_id)
        if balance["qty_on_hand"] < qty:
            raise ValueError(
                f"Insufficient on-hand stock: {balance['qty_on_hand']} {unit} on hand, {qty} requested"
            )

        if unit_cost_override is not None and unit_cost_override >= 0:
            unit_cost = float(unit_cost_override)
        else:
            unit_cost = self.get_material_unit_cost(material_id)

        total_cost = round(qty * unit_cost, 2)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inventory_movements
                   (material_id, movement_type, qty, unit, unit_cost_net, total_cost_net,
                    order_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    int(material_id),
                    "OUT",
                    float(qty),
                    str(unit),
                    unit_cost,
                    total_cost,
                    int(order_id),
                    note or f"Issue to order #{order_id}",
                    str(created_by),
                ),
            )
            out_movement_id = cursor.lastrowid
            self.log_action(
                user_name=created_by,
                action="INVENTORY_ISSUE",
                target_type="material",
                target_id=str(material_id),
                details=f"Issued {qty} {unit} to order #{order_id}",
                metadata={"order_id": order_id, "movement_id": out_movement_id}
            )

            self._auto_cancel_reservation_for_issue(
                cursor, material_id, order_id, qty, created_by
            )

            vat_rate = 23.0
            amount_gross = round(total_cost * (1.0 + vat_rate / 100.0), 2)
            cursor.execute(
                """INSERT INTO order_cost_entries
                   (order_id, cost_type, source_type, source_id, amount_net,
                    vat_rate, amount_gross, qty, unit, description, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(order_id),
                    "MATERIAL",
                    "inventory_issue",
                    out_movement_id,
                    total_cost,
                    vat_rate,
                    amount_gross,
                    float(qty),
                    str(unit),
                    f"Material issue #{out_movement_id}",
                    note,
                    str(created_by),
                ),
            )
            cost_entry_id = cursor.lastrowid
            conn.commit()

        new_balance = self.rebuild_inventory_balance(material_id)
        return {
            "status": "issued",
            "out_movement_id": out_movement_id,
            "cost_entry_id": cost_entry_id,
            "material_id": material_id,
            "order_id": order_id,
            "qty": qty,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "balance": new_balance,
        }

    # --- Stage 4: Return / Scrap / Correction ---

    def return_material_from_order(
        self,
        material_id: int,
        order_id: int,
        qty: float,
        unit: str = "pcs",
        related_issue_movement_id: Optional[int] = None,
        note: str = "",
        created_by: str = "",
    ) -> Dict:
        if qty <= 0:
            raise ValueError("Return qty must be positive")

        unit_cost = 0.0
        if related_issue_movement_id:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT unit_cost_net FROM inventory_movements WHERE id = ? AND movement_type = 'OUT'",
                    (int(related_issue_movement_id),),
                )
                row = cursor.fetchone()
                if row and row["unit_cost_net"]:
                    unit_cost = float(row["unit_cost_net"])
        if unit_cost <= 0:
            unit_cost = self.get_material_unit_cost(material_id)

        total_cost = round(qty * unit_cost, 2)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inventory_movements
                   (material_id, movement_type, qty, unit, unit_cost_net, total_cost_net,
                    order_id, related_movement_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(material_id),
                    "RETURN",
                    float(qty),
                    str(unit),
                    unit_cost,
                    total_cost,
                    int(order_id),
                    int(related_issue_movement_id) if related_issue_movement_id else None,
                    note or f"Return from order #{order_id}",
                    str(created_by),
                ),
            )
            return_movement_id = cursor.lastrowid

            vat_rate = 23.0
            amount_gross = round(total_cost * (1.0 + vat_rate / 100.0), 2)
            cursor.execute(
                """INSERT INTO order_cost_entries
                   (order_id, cost_type, source_type, source_id, amount_net,
                    vat_rate, amount_gross, qty, unit, description, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(order_id),
                    "MATERIAL",
                    "inventory_return",
                    return_movement_id,
                    -total_cost,
                    vat_rate,
                    -amount_gross,
                    -float(qty),
                    str(unit),
                    f"Return reversal #{return_movement_id}",
                    note,
                    str(created_by),
                ),
            )
            reversal_entry_id = cursor.lastrowid
            conn.commit()

        new_balance = self.rebuild_inventory_balance(material_id)
        return {
            "status": "returned",
            "return_movement_id": return_movement_id,
            "reversal_entry_id": reversal_entry_id,
            "material_id": material_id,
            "order_id": order_id,
            "qty_returned": qty,
            "cost_reversed_net": total_cost,
            "balance": new_balance,
        }

    def scrap_material(
        self,
        material_id: int,
        qty: float,
        unit: str = "pcs",
        order_id: Optional[int] = None,
        charge_to_order: bool = False,
        note: str = "",
        created_by: str = "",
    ) -> Dict:
        if qty <= 0:
            raise ValueError("Scrap qty must be positive")
        balance = self.rebuild_inventory_balance(material_id)
        if balance["qty_on_hand"] < qty:
            raise ValueError(
                f"Insufficient on-hand stock: {balance['qty_on_hand']} {unit} on hand, {qty} requested for scrap"
            )

        unit_cost = self.get_material_unit_cost(material_id)
        total_cost = round(qty * unit_cost, 2)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inventory_movements
                   (material_id, movement_type, qty, unit, unit_cost_net, total_cost_net,
                    order_id, note, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    int(material_id),
                    "SCRAP",
                    float(qty),
                    str(unit),
                    unit_cost,
                    total_cost,
                    int(order_id) if order_id else None,
                    note or "Scrap / waste",
                    str(created_by),
                ),
            )
            scrap_movement_id = cursor.lastrowid

            cost_entry_id = None
            if charge_to_order and order_id:
                vat_rate = 23.0
                amount_gross = round(total_cost * (1.0 + vat_rate / 100.0), 2)
                cursor.execute(
                    """INSERT INTO order_cost_entries
                       (order_id, cost_type, source_type, source_id, amount_net,
                        vat_rate, amount_gross, qty, unit, description, note, created_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        int(order_id),
                        "MATERIAL",
                        "scrap",
                        scrap_movement_id,
                        total_cost,
                        vat_rate,
                        amount_gross,
                        float(qty),
                        str(unit),
                        f"Scrap charged to order #{order_id}",
                        note,
                        str(created_by),
                    ),
                )
                cost_entry_id = cursor.lastrowid
            conn.commit()

        new_balance = self.rebuild_inventory_balance(material_id)
        return {
            "status": "scrapped",
            "scrap_movement_id": scrap_movement_id,
            "cost_entry_id": cost_entry_id,
            "material_id": material_id,
            "order_id": order_id,
            "qty_scrapped": qty,
            "scrap_cost_net": total_cost,
            "charged_to_order": bool(charge_to_order and order_id),
            "balance": new_balance,
        }

    def correct_inventory(
        self,
        material_id: int,
        qty_delta: float,
        unit: str = "pcs",
        note: str = "",
        created_by: str = "",
    ) -> Dict:
        if qty_delta == 0:
            raise ValueError("Correction qty_delta must not be zero")

        movement_id = self.create_inventory_movement(
            material_id=material_id,
            movement_type="CORRECTION",
            qty=qty_delta,
            unit=unit,
            note=note or "Manual inventory correction",
            created_by=created_by,
        )
        new_balance = self.rebuild_inventory_balance(material_id)
        return {
            "status": "corrected",
            "movement_id": movement_id,
            "material_id": material_id,
            "qty_delta": qty_delta,
            "balance": new_balance,
        }

    # --- Stage 2: Combined Purchase + Receipt Flow ---

    def receive_purchase_document(
        self, doc_id: int, payment_method: str = "", created_by: str = ""
    ) -> Dict:
        doc = self.get_purchase_document(doc_id)
        if not doc:
            raise ValueError(f"Purchase document {doc_id} not found")
        if str(doc.get("payment_status", "")).strip().lower() == "received":
            raise ValueError(f"Purchase document {doc_id} already received")

        lines = self.get_purchase_document_lines(doc_id)
        movements_created = 0
        materials_updated = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for line in lines:
                if not int(line.get("is_stock_item", 0)):
                    continue
                mat_id = line.get("material_id")
                if not mat_id:
                    continue

                qty = float(line.get("qty", 0) or 0)
                if qty <= 0:
                    continue

                unit_price = float(line.get("unit_price_net", 0) or 0)
                total_cost = float(line.get("line_total_net", 0) or 0)

                cursor.execute(
                    """INSERT INTO inventory_movements
                       (material_id, movement_type, qty, unit, unit_cost_net, total_cost_net,
                        purchase_document_id, purchase_document_line_id, note, created_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        int(mat_id),
                        "IN",
                        qty,
                        str(line.get("unit", "pcs")),
                        unit_price,
                        total_cost,
                        int(doc_id),
                        int(line.get("id")),
                        f"Receipt from purchase doc #{doc_id}",
                        str(created_by),
                    ),
                )
                movements_created += 1
                materials_updated.append(int(mat_id))

            effective_method = payment_method or str(doc.get("payment_method", "")).strip()
            total_gross = float(doc.get("total_gross", 0) or 0)
            if total_gross > 0:
                if effective_method.lower() in ("cash", "gotowka", "gotówka"):
                    fin_type = "CASH_OUT"
                elif effective_method.lower() in ("bank", "przelew", "transfer"):
                    fin_type = "BANK_OUT"
                else:
                    fin_type = "PAYABLE"

                cursor.execute(
                    """INSERT INTO cash_bank_movements
                       (movement_type, amount, currency, payment_method, supplier_name,
                        purchase_document_id, note, created_by)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        fin_type,
                        total_gross,
                        str(doc.get("currency", "PLN")),
                        effective_method,
                        str(doc.get("supplier_name", "")),
                        int(doc_id),
                        f"Payment for purchase doc #{doc_id}",
                        str(created_by),
                    ),
                )

            cursor.execute(
                "UPDATE purchase_documents SET payment_status = 'received', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (int(doc_id),),
            )
            conn.commit()
            self.log_action(
                user_name=created_by,
                action="PURCHASE_DOC_RECEIVE",
                target_type="purchase_document",
                target_id=str(doc_id),
                details=f"Received doc #{doc_id}",
                metadata={"movements_created": movements_created, "total_gross": total_gross}
            )

        for mat_id in set(materials_updated):
            self.rebuild_inventory_balance(mat_id)

        return {
            "status": "received",
            "purchase_document_id": int(doc_id),
            "movements_created": movements_created,
            "materials_updated": list(set(materials_updated)),
            "financial_movement_type": fin_type if total_gross > 0 else None,
        }


    def log_action(
        self,
        user_name: str,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Zapisuje zdarzenie do audit_log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO audit_log (user_name, action, target_type, target_id, details, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_name,
                    action,
                    target_type,
                    str(target_id) if target_id is not None else None,
                    details,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_audit_logs(self, limit: int = 500) -> List[Dict]:
        """Pobiera historię zdarzeń."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (int(limit),)
            )
            return [dict(row) for row in cursor.fetchall()]

    def soft_delete_project(self, project_id: int, user_name: str = "System"):
        """Oznacza projekt jako usuniÄ™ty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET is_deleted = 1 WHERE id = ?", (int(project_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="SOFT_DELETE_PROJECT",
                target_type="project",
                target_id=str(project_id),
                details=f"Project #{project_id} marked as deleted"
            )
        return True

    def soft_delete_material(self, material_id: int, user_name: str = "System"):
        """Oznacza materiaĹ‚ jako usuniÄ™ty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE materials SET is_deleted = 1 WHERE id = ?", (int(material_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="SOFT_DELETE_MATERIAL",
                target_type="material",
                target_id=str(material_id),
                details=f"Material #{material_id} marked as deleted"
            )
        return True

    def soft_delete_order(self, order_id: int, user_name: str = "System"):
        """Oznacza zamĂłwienie jako usuniÄ™te."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET is_deleted = 1 WHERE id = ?", (int(order_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="SOFT_DELETE_ORDER",
                target_type="order",
                target_id=str(order_id),
                details=f"Order #{order_id} marked as deleted"
            )
        return True

    def soft_delete_client(self, client_id: int, user_name: str = "System"):
        """Oznacza klienta jako usuniÄ™tego."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE clients SET is_deleted = 1 WHERE id = ?", (int(client_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="SOFT_DELETE_CLIENT",
                target_type="client",
                target_id=str(client_id),
                details=f"Client #{client_id} marked as deleted"
            )
        return True

    def restore_project(self, project_id: int, user_name: str = "System"):
        """Przywraca usuniÄ™ty projekt."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET is_deleted = 0 WHERE id = ?", (int(project_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="RESTORE_PROJECT",
                target_type="project",
                target_id=str(project_id),
                details=f"Project #{project_id} restored from recycle bin"
            )
        return True

    def restore_material(self, material_id: int, user_name: str = "System"):
        """Przywraca usuniÄ™ty materiaĹ‚."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE materials SET is_deleted = 0 WHERE id = ?", (int(material_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="RESTORE_MATERIAL",
                target_type="material",
                target_id=str(material_id),
                details=f"Material #{material_id} restored from recycle bin"
            )
        return True

    def restore_order(self, order_id: int, user_name: str = "System"):
        """Przywraca usuniÄ™te zamĂłwienie."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET is_deleted = 0 WHERE id = ?", (int(order_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="RESTORE_ORDER",
                target_type="order",
                target_id=str(order_id),
                details=f"Order #{order_id} restored from recycle bin"
            )
        return True

    def restore_client(self, client_id: int, user_name: str = "System"):
        """Przywraca usuniÄ™tego klienta."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE clients SET is_deleted = 0 WHERE id = ?", (int(client_id),))
            conn.commit()
            self.log_action(
                user_name=user_name,
                action="RESTORE_CLIENT",
                target_type="client",
                target_id=str(client_id),
                details=f"Client #{client_id} restored from recycle bin"
            )
        return True

        return True

    # --- PROCUREMENT EXECUTION (ETAP 6) ---

    def get_procurement_items(self, status: Optional[str] = None, material_id: Optional[int] = None) -> List[Dict]:
        """Lists procurement execution tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
                SELECT pi.*, m.name as material_name, m.unit as material_unit, m.category as material_category,
                       o.title as order_title, o.client_name as order_client_name,
                       pd.document_number as purchase_doc_number
                FROM procurement_items pi
                JOIN materials m ON pi.material_id = m.id
                LEFT JOIN orders o ON pi.order_id = o.id
                LEFT JOIN purchase_documents pd ON pi.purchase_document_id = pd.id
                WHERE pi.is_deleted = 0
            """
            params = []
            if status:
                query += " AND pi.status = ?"
                params.append(status)
            if material_id:
                query += " AND pi.material_id = ?"
                params.append(int(material_id))
            
            query += " ORDER BY CASE WHEN pi.priority = 'krytyczny' THEN 0 WHEN pi.priority = 'wysoki' THEN 1 ELSE 2 END, pi.due_date ASC, pi.id DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def create_procurement_item(self, material_id: int, qty_target: float, **kwargs) -> int:
        """Creates a new procurement execution item."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cols = ["material_id", "qty_target"]
            vals = [int(material_id), float(qty_target)]
            
            allowed = ["order_id", "status", "owner_name", "supplier_name", "due_date", "priority", "note", "purchase_document_id"]
            for k in allowed:
                if k in kwargs:
                    cols.append(k)
                    vals.append(kwargs[k])
            
            query = f"INSERT INTO procurement_items ({', '.join(cols)}) VALUES ({', '.join(['?' for _ in vals])})"
            cursor.execute(query, tuple(vals))
            item_id = cursor.lastrowid
            conn.commit()
            
            self.log_action(
                user_name=kwargs.get("created_by", "System"),
                action="PROC_CREATE",
                target_type="procurement_item",
                target_id=str(item_id),
                details=f"Created procurement task for {qty_target} of material #{material_id}. Status: {kwargs.get('status', 'missing')}"
            )
            return item_id

    def update_procurement_item(self, item_id: int, updates: Dict, user_name: str = "System") -> bool:
        """Updates a procurement execution item with audit logging."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM procurement_items WHERE id = ?", (int(item_id),))
            existing = cursor.fetchone()
            if not existing:
                return False
            
            set_parts = []
            params = []
            changes = []
            
            allowed = ["status", "owner_name", "supplier_name", "due_date", "priority", "note", "purchase_document_id", "qty_ordered", "qty_target"]
            for k in allowed:
                if k in updates:
                    new_val = updates[k]
                    old_val = existing[k]
                    if new_val != old_val:
                        set_parts.append(f"{k} = ?")
                        params.append(new_val)
                        changes.append(f"{k}: {old_val} -> {new_val}")
            
            if not set_parts:
                return False
            
            set_parts.append("updated_at = CURRENT_TIMESTAMP")
            params.append(int(item_id))
            cursor.execute(f"UPDATE procurement_items SET {', '.join(set_parts)} WHERE id = ?", tuple(params))
            conn.commit()
            
            if changes:
                self.log_action(
                    user_name=user_name,
                    action="PROC_UPDATE",
                    target_type="procurement_item",
                    target_id=str(item_id),
                    details=f"Updated procurement item #{item_id}: {', '.join(changes)}"
                )
            return True

    def get_order_readiness_summary(self) -> List[Dict]:
        """Calculates material readiness for all active orders."""
        # 1. Get active orders
        orders = self.get_orders()
        active_orders = [o for o in orders if o.get("status") != "zamkniete"]
        
        # 2. Get procurement data (shortages)
        proc_data = self.get_procurement_data()
        shortages_by_material = {p["material_id"]: p for p in proc_data}
        
        # 3. Get persistent procurement items (execution state)
        exec_items = self.get_procurement_items()
        exec_by_material = {}
        for item in exec_items:
            mid = item["material_id"]
            if mid not in exec_by_material: exec_by_material[mid] = []
            exec_by_material[mid].append(item)
            
        # 4. Map readiness
        results = []
        for order in active_orders:
            oid = order["id"]
            # Get materials reserved for this order
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT im.material_id, m.name as material_name, m.unit as material_unit, SUM(im.qty) as reserved_qty
                    FROM inventory_movements im
                    JOIN materials m ON im.material_id = m.id
                    WHERE im.order_id = ? AND im.movement_type = 'RESERVED'
                    GROUP BY im.material_id
                """, (oid,))
                reserved_rows = [dict(row) for row in cursor.fetchall()]
            
            order_materials = []
            ready_count = 0
            partial_count = 0
            blocked_count = 0
            
            for r in reserved_rows:
                mid = r["material_id"]
                shortage_info = shortages_by_material.get(mid)
                
                # If there is no global shortage for this material, it's ready for this order (mostly)
                # Note: this is a simplification. Real readiness depends on allocation priority.
                # But for this sprint, we use shortage detection as the primary signal.
                
                status = "READY"
                shortage_qty = 0
                if shortage_info and shortage_info["shortage"] > 0:
                    # There is a shortage. Is it being handled?
                    items = exec_by_material.get(mid, [])
                    ordered_sum = sum(i["qty_ordered"] for i in items if i["status"] in ("ordered", "partially_received"))
                    
                    if ordered_sum >= shortage_info["shortage"]:
                        status = "PARTIAL" # Covered by open orders
                    else:
                        status = "BLOCKED" # Not covered
                
                if status == "READY": ready_count += 1
                elif status == "PARTIAL": partial_count += 1
                else: blocked_count += 1
                
                order_materials.append({
                    "material_id": mid,
                    "name": r["material_name"],
                    "reserved_qty": r["reserved_qty"],
                    "unit": r["material_unit"],
                    "status": status
                })
            
            readiness = "READY"
            if blocked_count > 0: readiness = "BLOCKED"
            elif partial_count > 0: readiness = "PARTIAL"
            
            results.append({
                "order_id": oid,
                "order_title": order["title"],
                "client_name": order["client_name"],
                "readiness": readiness,
                "ready_count": ready_count,
                "partial_count": partial_count,
                "blocked_count": blocked_count,
                "total_count": len(reserved_rows),
                "materials": order_materials
            })
            
        return results

    def _get_station_keywords(self, station_type: str) -> List[str]:
        mapping = {
            "cnc": ["cnc", "produkcja", "wycin"],
            "oklejanie": ["oklejanie", "okleiniarka"],
            "lakiernia": ["lakiernia", "lakierowanie", "malowanie"],
            "montaz": ["montaz", "montaż", "skladanie", "zbiorka", "zborka", "poprawki"],
            "pakowanie": ["pakowanie", "wysylka", "magazyn_gotowy"]
        }
        return mapping.get(station_type.lower(), [station_type.lower()])

    def get_station_jobs(self, station_type: str) -> List[Dict]:
        """Fetches tasks for a specific station with dependency check."""
        from src.core.operations_store import OperationsStore
        store = OperationsStore()
        all_routes = store.list_routes()
        
        keywords = self._get_station_keywords(station_type)
        station_tasks = [t for t in all_routes if any(kw in t.task_type.lower() for kw in keywords)]
        
        # Dependency sequence
        SEQUENCE = ["cnc", "oklejanie", "lakiernia", "montaz", "pakowanie"]
        try:
            s_idx = SEQUENCE.index(station_type.lower())
        except ValueError:
            s_idx = -1
            
        results = []
        for t in station_tasks:
            d = t.to_dict()
            d["is_ready"] = True
            d["prerequisite_blocked"] = False
            d["prerequisite_name"] = ""
            d["prev_task_id"] = None
            d["prev_handoff_status"] = None
            
            # If the task itself is already marked as problem or needs rework, it's not ready to continue automatically
            if t.status == "problem" or t.quality_result == "needs_rework":
                d["is_ready"] = False
            
            if s_idx > 0:
                # Check previous stages in sequence
                project_tasks = [rt for rt in all_routes if rt.project_name == t.project_name]
                for j in range(s_idx - 1, -1, -1):
                    prev_s = SEQUENCE[j]
                    prev_kw = self._get_station_keywords(prev_s)
                    prev_tasks = [rt for rt in project_tasks if any(kw in rt.task_type.lower() for kw in prev_kw)]
                    if prev_tasks:
                        # Find the first previous task for simplicity (usually 1:1)
                        prev_task = prev_tasks[0]
                        d["prev_task_id"] = prev_task.id
                        d["prev_handoff_status"] = prev_task.handoff_status
                        
                        # Task is ready to start IF previous task is done AND handed off OR accepted
                        if prev_task.status != "wykonane" or prev_task.handoff_status not in ("ready_for_next", "accepted"):
                            d["is_ready"] = False
                            d["prerequisite_blocked"] = True
                            d["prerequisite_name"] = prev_s
                        break # Only check immediate predecessor that exists
            
            results.append(d)
        return results

    def get_production_workflow_readiness(self) -> List[Dict]:
        """Analyzes all active projects and their production stage readiness."""
        from src.core.operations_store import OperationsStore
        store = OperationsStore()
        all_routes = store.list_routes()
        
        SEQUENCE = ["cnc", "oklejanie", "lakiernia", "montaz", "pakowanie"]
        
        # Map project -> tasks
        project_tasks = {}
        for r in all_routes:
            pname = r.project_name
            if pname not in project_tasks: project_tasks[pname] = []
            project_tasks[pname].append(r)
            
        results = []
        for pname, tasks in project_tasks.items():
            if not tasks: continue
            
            stages_status = {}
            for s in SEQUENCE:
                keywords = self._get_station_keywords(s)
                s_tasks = [t for t in tasks if any(kw in t.task_type.lower() for kw in keywords)]
                if not s_tasks:
                    stages_status[s] = "skipped"
                    continue
                
                # Check for rework / blocked
                if any(t.status == "problem" for t in s_tasks):
                    stages_status[s] = "blocked"
                elif any(t.quality_result == "needs_rework" for t in s_tasks):
                    stages_status[s] = "rework"
                elif any(t.handoff_status == "rejected_back" for t in s_tasks):
                    stages_status[s] = "rejected"
                elif all(t.status == "wykonane" for t in s_tasks):
                    # Check handoff
                    if all(t.handoff_status == "accepted" for t in s_tasks):
                        stages_status[s] = "accepted"
                    elif all(t.handoff_status == "ready_for_next" for t in s_tasks):
                        stages_status[s] = "pending_handoff"
                    else:
                        stages_status[s] = "done"
                elif any(t.status in ("w_trasie", "w toku") for t in s_tasks):
                    stages_status[s] = "in_progress"
                else:
                    stages_status[s] = "waiting"
            
            current_stage = None
            next_stage = None
            is_blocked = False
            blocked_reason = ""
            
            for i, s in enumerate(SEQUENCE):
                status = stages_status.get(s)
                if status == "skipped": continue
                
                if status in ("blocked", "rework", "rejected"):
                    current_stage = s
                    is_blocked = True
                    b_task = next((t for t in tasks if any(kw in t.task_type.lower() for kw in self._get_station_keywords(s)) and (t.status == "problem" or t.quality_result == "needs_rework" or t.handoff_status == "rejected_back")), None)
                    blocked_reason = b_task.rework_reason or b_task.blocked_reason if b_task else "Problem na tym etapie"
                    # Look for next stage
                    for j in range(i+1, len(SEQUENCE)):
                        if stages_status.get(SEQUENCE[j]) != "skipped":
                            next_stage = SEQUENCE[j]
                            break
                    break
                
                if status in ("in_progress", "pending_handoff", "done"):
                    # We might be in progress or waiting for acceptance
                    current_stage = s
                    for j in range(i+1, len(SEQUENCE)):
                        if stages_status.get(SEQUENCE[j]) != "skipped":
                            next_stage = SEQUENCE[j]
                            break
                    if status != "pending_handoff" and status != "done":
                        break
                    # If pending handoff or done, keep checking next stages, maybe they are waiting
                
                if status == "waiting":
                    current_stage = s
                    # Check if actually ready
                    pre_stage = None
                    for j in range(i-1, -1, -1):
                        if stages_status.get(SEQUENCE[j]) != "skipped":
                            pre_stage = SEQUENCE[j]
                            break
                    
                    if pre_stage and stages_status.get(pre_stage) not in ("done", "pending_handoff", "accepted"):
                        is_blocked = True
                        blocked_reason = f"Oczekuje na: {pre_stage.upper()}"
                    
                    for j in range(i+1, len(SEQUENCE)):
                        if stages_status.get(SEQUENCE[j]) != "skipped":
                            next_stage = SEQUENCE[j]
                            break
                    break
            
            is_complete = False
            if all(stages_status.get(s) in ("done", "pending_handoff", "accepted", "skipped") for s in SEQUENCE):
                 # Find the last actual stage
                 last_s = None
                 for s in reversed(SEQUENCE):
                     if stages_status.get(s) != "skipped":
                         last_s = s
                         break
                 if last_s and stages_status.get(last_s) in ("done", "pending_handoff", "accepted"):
                     is_complete = True
                     current_stage = "production_complete"

            results.append({
                "project_name": pname,
                "client_name": tasks[0].client_name,
                "current_stage": current_stage,
                "next_stage": next_stage,
                "is_blocked": is_blocked,
                "blocked_reason": blocked_reason,
                "stages": stages_status,
                "last_update": max(t.updated_at for t in tasks) if tasks else None,
                "is_complete": is_complete
            })            
        # Sort by blocked first, then by last update
        results.sort(key=lambda x: (not x["is_blocked"], x["last_update"]), reverse=True)
        return results

    def get_fulfillment_queue(self) -> list[dict[str, Any]]:
        readiness = self.get_production_workflow_readiness()
        fulfillments = {f.project_name: f for f in self.operations.list_fulfillments()}
        
        queue = []
        for p in readiness:
            # Include if production is complete OR if a fulfillment record already exists
            if p.get("is_complete") or p["project_name"] in fulfillments:
                f_record = fulfillments.get(p["project_name"])
                if not f_record:
                    # Create a default if it doesn't exist yet
                    f_record = __import__("src.core.operations_models", fromlist=["FulfillmentRecord"]).FulfillmentRecord(project_name=p["project_name"])
                    
                queue.append({
                    "project_name": p["project_name"],
                    "client_name": p["client_name"],
                    "production_status": "Zakończona" if p.get("is_complete") else "W toku",
                    "fulfillment": f_record.to_dict()
                })
        
        # Sort by status and created at
        # Order of statuses: ready_for_shipping, packed, dispatched, delivered, installation_blocked, installation_in_progress, installed, closed
        status_order = {
            "ready_for_shipping": 0,
            "packed": 1,
            "dispatched": 2,
            "delivered": 3,
            "installation_blocked": 4,
            "installation_in_progress": 5,
            "installed": 6,
            "closed": 7
        }
        queue.sort(key=lambda x: (status_order.get(x["fulfillment"]["status"], 99), x["fulfillment"]["created_at"]), reverse=False)
        return queue


# Singleton do użycia w API
data_manager = TechModulDataManager()
# Phase 1 Safe Work Mode: skip module-level demo seeds in prod.
if not safe_mode.is_prod():
    data_manager.seed_demo_modules_if_empty()
    data_manager.seed_demo_materials_if_empty()
    data_manager.seed_demo_clients_if_empty()
