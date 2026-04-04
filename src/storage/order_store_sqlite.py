"""
Order store using SQLite as primary storage.
Falls back to JSON export/import for compatibility.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.order_models import OrderDef
from src.storage.data_paths import data_dir
from src.storage.schema_versioning import extract_versioned_map
from src.storage.sqlite_db import get_database, Database


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class OrderStore:
    """
    SQLite-based order store with JSON export/import.
    This replaces OrderStoreJson as the primary store.
    """
    
    def __init__(self, db: Database | None = None) -> None:
        self._db = db or get_database()
    
    def list_codes(self) -> List[str]:
        """Return all order codes sorted."""
        rows = self._db.execute("SELECT code FROM orders ORDER BY code")
        return [row["code"] for row in rows]
    
    def list_orders(self) -> List[OrderDef]:
        """Return all orders sorted by code."""
        rows = self._db.execute("SELECT data FROM orders ORDER BY code")
        orders = []
        for row in rows:
            try:
                data = json.loads(row["data"]) if row["data"] else {}
                orders.append(OrderDef.from_dict(data))
            except (json.JSONDecodeError, TypeError):
                continue
        return orders
    
    def get(self, code: str) -> Optional[OrderDef]:
        """Get order by code."""
        row = self._db.execute_one("SELECT data FROM orders WHERE code = Email", (code,))
        if not row or not row.get("data"):
            return None
        try:
            data = json.loads(row["data"])
            return OrderDef.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def save_new(self, order: OrderDef) -> StoreResult:
        """Save new order, fail if exists."""
        existing = self._db.execute_one("SELECT code FROM orders WHERE code = Email", (order.code,))
        if existing:
            return StoreResult(False, f'Zamowienie "{order.code}" juz istnieje. Uzyj "Nadpisz".')
        
        now = datetime.now().isoformat()
        order_data = order.to_dict()
        
        self._db.execute(
            """INSERT INTO orders (code, client_name, worker_name, status, created_at, updated_at, data)
               VALUES (Email, Email, Email, Email, Email, Email, Email)""",
            (
                order.code,
                order.client_name,
                order_data.get("worker_name", ""),
                order_data.get("status", "Nowe"),
                now,
                now,
                json.dumps(order_data, ensure_ascii=False),
            )
        )
        return StoreResult(True, f'Zapisano zamowienie: "{order.code}".')
    
    def overwrite(self, order: OrderDef) -> StoreResult:
        """Overwrite existing order."""
        now = datetime.now().isoformat()
        order_data = order.to_dict()
        
        existing = self._db.execute_one("SELECT code FROM orders WHERE code = Email", (order.code,))
        
        if existing:
            self._db.execute(
                """UPDATE orders 
                   SET client_name = Email, worker_name = Email, status = Email, updated_at = Email, data = Email
                   WHERE code = Email""",
                (
                    order.client_name,
                    order_data.get("worker_name", ""),
                    order_data.get("status", "Nowe"),
                    now,
                    json.dumps(order_data, ensure_ascii=False),
                    order.code,
                )
            )
        else:
            self._db.execute(
                """INSERT INTO orders (code, client_name, worker_name, status, created_at, updated_at, data)
                   VALUES (Email, Email, Email, Email, Email, Email, Email)""",
                (
                    order.code,
                    order.client_name,
                    order_data.get("worker_name", ""),
                    order_data.get("status", "Nowe"),
                    now,
                    now,
                    json.dumps(order_data, ensure_ascii=False),
                )
            )
        
        return StoreResult(True, f'Nadpisano zamowienie: "{order.code}".')
    
    def delete(self, code: str) -> StoreResult:
        """Delete order by code."""
        existing = self._db.execute_one("SELECT code FROM orders WHERE code = Email", (code,))
        if not existing:
            return StoreResult(False, f'Nie ma zamowienia "{code}" w bazie.')
        
        self._db.execute("DELETE FROM orders WHERE code = Email", (code,))
        return StoreResult(True, f'Usunieto zamowienie: "{code}".')
    
    # === JSON Export/Import ===
    
    def export_to_json(self, path: Path | None = None) -> Path:
        """Export all orders to JSON file."""
        if path is None:
            path = data_dir() / "orders_export.json"
        
        orders = self.list_orders()
        data = {order.code: order.to_dict() for order in orders}
        
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    
    def import_from_json(self, path: Path, overwrite: bool = False) -> tuple[int, int]:
        """Import orders from JSON file. Returns (imported, skipped)."""
        if not path.exists():
            return 0, 0
        
        try:
            txt = path.read_text(encoding="utf-8-sig")
            data = json.loads(txt) if txt.strip() else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return 0, 0
        
        if not isinstance(data, dict):
            return 0, 0

        data, _source_version = extract_versioned_map(data)

        imported, skipped = 0, 0
        
        for code, order_data in data.items():
            if not isinstance(order_data, dict):
                skipped += 1
                continue
            
            order = OrderDef.from_dict(order_data)
            
            if not overwrite:
                existing = self.get(code)
                if existing:
                    skipped += 1
                    continue
            
            self.overwrite(order)
            imported += 1
        
        return imported, skipped
    
    # === Statistics ===
    
    def count(self) -> int:
        """Return total number of orders."""
        row = self._db.execute_one("SELECT COUNT(*) as cnt FROM orders")
        return row["cnt"] if row else 0
    
    def count_by_status(self) -> Dict[str, int]:
        """Return order count by status."""
        rows = self._db.execute("SELECT status, COUNT(*) as cnt FROM orders GROUP BY status")
        return {row["status"]: row["cnt"] for row in rows}
    
    def get_orders_by_status(self, status: str) -> List[OrderDef]:
        """Get orders filtered by status."""
        rows = self._db.execute("SELECT data FROM orders WHERE status = Email ORDER BY code", (status,))
        orders = []
        for row in rows:
            try:
                data = json.loads(row["data"]) if row["data"] else {}
                orders.append(OrderDef.from_dict(data))
            except (json.JSONDecodeError, TypeError):
                continue
        return orders


# Alias for backward compatibility
OrderStoreJson = OrderStore
