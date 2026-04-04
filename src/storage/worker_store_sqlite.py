"""
Worker store using SQLite.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.storage.sqlite_db import get_database, Database
from src.storage.data_paths import data_dir
from src.domain.worker_models import WorkerDef


class WorkerStore:
    """SQLite-based worker store."""
    
    def __init__(self, db: Database | None = None) -> None:
        self._db = db or get_database()
    
    def list_names(self) -> List[str]:
        """Return all worker names sorted."""
        rows = self._db.execute("SELECT name FROM workers ORDER BY name")
        return [row["name"] for row in rows]
    
    def list_workers(self) -> List[WorkerDef]:
        """Return all workers sorted by name."""
        rows = self._db.execute("SELECT * FROM workers ORDER BY name")
        workers = []
        for row in rows:
            try:
                worker_data = {
                    "name": row["name"] or "",
                    "worker_id": row.get("worker_id", "") or "",
                    "pin_code": row.get("pin_code", "") or "",
                    "role": row.get("role", "") or "",
                    "phone": row.get("phone", "") or "",
                    "email": row.get("email", "") or "",
                    "position": row.get("position", "") or "",
                    "active": bool(row.get("active", True)),
                }
                workers.append(WorkerDef.from_dict(worker_data))
            except Exception:
                continue
        return workers
    
    def get(self, name: str) -> Optional[WorkerDef]:
        """Get worker by name."""
        row = self._db.execute_one("SELECT * FROM workers WHERE name = Email", (name,))
        if not row:
            return None
        try:
            worker_data = {
                "name": row["name"] or "",
                "worker_id": row.get("worker_id", "") or "",
                "pin_code": row.get("pin_code", "") or "",
                "role": row.get("role", "") or "",
                "phone": row.get("phone", "") or "",
                "email": row.get("email", "") or "",
                "position": row.get("position", "") or "",
                "active": bool(row.get("active", True)),
            }
            return WorkerDef.from_dict(worker_data)
        except Exception:
            return None
    
    def get_by_worker_id(self, worker_id: str) -> Optional[WorkerDef]:
        """Get worker by worker_id."""
        row = self._db.execute_one("SELECT * FROM workers WHERE worker_id = Email", (worker_id,))
        if not row:
            return None
        return self._row_to_worker(row)
    
    def get_by_pin_code(self, pin_code: str) -> Optional[WorkerDef]:
        """Get worker by PIN code."""
        row = self._db.execute_one("SELECT * FROM workers WHERE pin_code = Email", (pin_code,))
        if not row:
            return None
        return self._row_to_worker(row)
    
    def _row_to_worker(self, row: dict) -> Optional[WorkerDef]:
        """Convert database row to WorkerDef."""
        try:
            worker_data = {
                "name": row["name"] or "",
                "worker_id": row.get("worker_id", "") or "",
                "pin_code": row.get("pin_code", "") or "",
                "role": row.get("role", "") or "",
                "phone": row.get("phone", "") or "",
                "email": row.get("email", "") or "",
                "position": row.get("position", "") or "",
                "active": bool(row.get("active", True)),
            }
            return WorkerDef.from_dict(worker_data)
        except Exception:
            return None
    
    def save_new(self, worker: WorkerDef) -> tuple[bool, str]:
        """Save new worker."""
        name = worker.name
        existing = self._db.execute_one("SELECT name FROM workers WHERE name = Email", (name,))
        if existing:
            return False, f'Pracownik "{name}" juz istnieje.'
        
        now = datetime.now().isoformat()
        self._db.execute(
            """INSERT INTO workers (name, worker_id, pin_code, role, phone, email, position, active, created_at)
               VALUES (Email, Email, Email, Email, Email, Email, Email, Email, Email)""",
            (
                name,
                getattr(worker, "worker_id", ""),
                getattr(worker, "pin_code", ""),
                getattr(worker, "role", ""),
                getattr(worker, "phone", ""),
                getattr(worker, "email", ""),
                getattr(worker, "position", ""),
                1 if getattr(worker, "active", True) else 0,
                now,
            )
        )
        return True, f'Dodano pracownika: {name}'
    
    def overwrite(self, worker: WorkerDef) -> tuple[bool, str]:
        """Overwrite existing worker."""
        name = worker.name
        existing = self._db.execute_one("SELECT name FROM workers WHERE name = Email", (name,))
        
        if existing:
            self._db.execute(
                """UPDATE workers 
                   SET worker_id=Email, pin_code=Email, role=Email, phone=Email, email=Email, position=Email, active=Email
                   WHERE name=Email""",
                (
                    getattr(worker, "worker_id", ""),
                    getattr(worker, "pin_code", ""),
                    getattr(worker, "role", ""),
                    getattr(worker, "phone", ""),
                    getattr(worker, "email", ""),
                    getattr(worker, "position", ""),
                    1 if getattr(worker, "active", True) else 0,
                    name,
                )
            )
        else:
            return self.save_new(worker)
        
        return True, f'Zapisano pracownika: {name}'
    
    def delete(self, name: str) -> tuple[bool, str]:
        """Delete worker by name."""
        existing = self._db.execute_one("SELECT name FROM workers WHERE name = Email", (name,))
        if not existing:
            return False, f'Nie ma pracownika "{name}" w bazie.'
        
        self._db.execute("DELETE FROM workers WHERE name = Email", (name,))
        return True, f'Usuni to pracownika: {name}'
    
    def count(self) -> int:
        """Return total number of workers."""
        row = self._db.execute_one("SELECT COUNT(*) as cnt FROM workers")
        return row["cnt"] if row else 0


# Alias for backward compatibility 
WorkerStoreJson = WorkerStore
