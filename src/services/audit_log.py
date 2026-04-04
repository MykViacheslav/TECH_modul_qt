"""
Audit log system for TECH_modul.
Tracks all changes to orders, clients, and other entities.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.storage.data_paths import data_dir
from src.storage.sqlite_db import get_database


class AuditAction(str, Enum):
    """Types of audit actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATUS_CHANGE = "status_change"
    PAYMENT_ADD = "payment_add"
    PAYMENT_UPDATE = "payment_update"
    PAYMENT_DELETE = "payment_delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    action: AuditAction
    entity_type: str # "order", "client", "worker", etc.
    entity_id: str
    user: str = ""
    changes: dict[str, Any] = field(default_factory=dict)
    old_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "user": self.user,
            "changes": self.changes,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "note": self.note,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            timestamp=data.get("timestamp", ""),
            action=AuditAction(data.get("action", "update")),
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            user=data.get("user", ""),
            changes=data.get("changes", {}),
            old_values=data.get("old_values", {}),
            new_values=data.get("new_values", {}),
            note=data.get("note", ""),
        )
    
    @property
    def action_label(self) -> str:
        labels = {
            AuditAction.CREATE: "Utworzono",
            AuditAction.UPDATE: "Zmodyfikowano",
            AuditAction.DELETE: "Usuni to",
            AuditAction.STATUS_CHANGE: "Zmiana statusu",
            AuditAction.PAYMENT_ADD: "Dodano p atno ",
            AuditAction.PAYMENT_UPDATE: "Zmieniono p atno ",
            AuditAction.PAYMENT_DELETE: "Usuni to p atno ",
            AuditAction.LOGIN: "Logowanie",
            AuditAction.LOGOUT: "Wylogowanie",
            AuditAction.EXPORT: "Eksport",
            AuditAction.IMPORT: "Import",
        }
        return labels.get(self.action, self.action.value)
    
    @property
    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.changes:
            parts = []
            for key, value in self.changes.items():
                if isinstance(value, dict) and "from" in value and "to" in value:
                    parts.append(f"{key}: {value['from']} -> {value['to']}")
                else:
                    parts.append(f"{key}: {value}")
            return "; ".join(parts)
        return self.note


class AuditLog:
    """
    Audit log service.
    Stores and retrieves audit entries using SQLite.
    """
    
    _instance: Optional["AuditLog"] = None
    
    def __new__(cls) -> "AuditLog":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._db = get_database()
        self._ensure_table()
    
    def _ensure_table(self) -> None:
        """Create audit_log table if not exists."""
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                user TEXT,
                changes TEXT,
                old_values TEXT,
                new_values TEXT,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for fast queries
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
    
    def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        user: str = "",
        changes: dict | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        note: str = "",
    ) -> int:
        """Log an audit entry. Returns entry ID."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            changes=changes or {},
            old_values=old_values or {},
            new_values=new_values or {},
            note=note,
        )
        
        cursor = self._db.execute(
            """INSERT INTO audit_log (timestamp, action, entity_type, entity_id, user, changes, old_values, new_values, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.timestamp,
                entry.action.value,
                entry.entity_type,
                entry.entity_id,
                entry.user,
                json.dumps(entry.changes, ensure_ascii=False),
                json.dumps(entry.old_values, ensure_ascii=False),
                json.dumps(entry.new_values, ensure_ascii=False),
                entry.note,
            )
        )
        
        return cursor.lastrowid if cursor else 0
    
    def log_change(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        user: str = "",
    ) -> int:
        """Log a field change."""
        return self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            changes={field_name: {"from": str(old_value), "to": str(new_value)}},
        )
    
    def log_status_change(
        self,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        user: str = "",
        note: str = "",
    ) -> int:
        """Log a status change."""
        return self.log(
            action=AuditAction.STATUS_CHANGE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            changes={"status": {"from": old_status, "to": new_status}},
            note=note,
        )
    
    def log_create(
        self,
        entity_type: str,
        entity_id: str,
        user: str = "",
        data: dict | None = None,
    ) -> int:
        """Log entity creation."""
        return self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            new_values=data or {},
            note=f"Utworzono {entity_type}: {entity_id}",
        )
    
    def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        user: str = "",
        data: dict | None = None,
    ) -> int:
        """Log entity deletion."""
        return self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            old_values=data or {},
            note=f"Usuni to {entity_type}: {entity_id}",
        )
    
    def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get audit history for a specific entity."""
        rows = self._db.execute(
            """SELECT timestamp, action, entity_type, entity_id, user, changes, old_values, new_values, note
               FROM audit_log
               WHERE entity_type = ? AND entity_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (entity_type, entity_id, limit)
        )
        
        return [
            AuditEntry(
                timestamp=row["timestamp"],
                action=AuditAction(row["action"]),
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                user=row["user"] or "",
                changes=json.loads(row["changes"] or "{}"),
                old_values=json.loads(row["old_values"] or "{}"),
                new_values=json.loads(row["new_values"] or "{}"),
                note=row["note"] or "",
            )
            for row in rows
        ]
    
    def get_recent_entries(
        self,
        entity_type: str | None = None,
        action: AuditAction | None = None,
        user: str | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Get recent audit entries with optional filters."""
        query = "SELECT timestamp, action, entity_type, entity_id, user, changes, old_values, new_values, note FROM audit_log WHERE 1=1"
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if action:
            query += " AND action = ?"
            params.append(action.value)
        if user:
            query += " AND user = ?"
            params.append(user)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self._db.execute(query, tuple(params))
        
        return [
            AuditEntry(
                timestamp=row["timestamp"],
                action=AuditAction(row["action"]),
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                user=row["user"] or "",
                changes=json.loads(row["changes"] or "{}"),
                old_values=json.loads(row["old_values"] or "{}"),
                new_values=json.loads(row["new_values"] or "{}"),
                note=row["note"] or "",
            )
            for row in rows
        ]
    
    def get_statistics(self) -> dict:
        """Get audit log statistics."""
        total = self._db.execute_one("SELECT COUNT(*) as cnt FROM audit_log")
        today = self._db.execute_one(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE date(timestamp) = date('now')"
        )
        by_action = self._db.execute(
            "SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action ORDER BY cnt DESC"
        )
        
        return {
            "total": total["cnt"] if total else 0,
            "today": today["cnt"] if today else 0,
            "by_action": {row["action"]: row["cnt"] for row in by_action},
        }
    
    def export_to_json(self, path: Path | None = None) -> Path:
        """Export audit log to JSON file."""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = data_dir() / "export" / f"audit_log_{timestamp}.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        rows = self._db.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC"
        )
        
        entries = [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "user": row["user"],
                "changes": json.loads(row["changes"] or "{}"),
                "old_values": json.loads(row["old_values"] or "{}"),
                "new_values": json.loads(row["new_values"] or "{}"),
                "note": row["note"],
            }
            for row in rows
        ]
        
        path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return path
    
    def cleanup(self, days_to_keep: int = 365) -> int:
        """Remove entries older than specified days."""
        result = self._db.execute(
            f"DELETE FROM audit_log WHERE julianday('now') - julianday(timestamp) > {days_to_keep}"
        )
        return len(result) if result else 0


# Singleton accessor
def get_audit_log() -> AuditLog:
    """Get global audit log instance."""
    return AuditLog()


# Convenience functions
def audit_log_change(entity_type: str, entity_id: str, field_name: str,
                     old_value: Any, new_value: Any, user: str = "") -> int:
    """Log a field change."""
    return get_audit_log().log_change(entity_type, entity_id, field_name, old_value, new_value, user)


def audit_log_status(entity_type: str, entity_id: str, old_status: str,
                     new_status: str, user: str = "", note: str = "") -> int:
    """Log a status change."""
    return get_audit_log().log_status_change(entity_type, entity_id, old_status, new_status, user, note)


def audit_log_create(entity_type: str, entity_id: str, user: str = "", data: dict | None = None) -> int:
    """Log entity creation."""
    return get_audit_log().log_create(entity_type, entity_id, user, data)


def audit_log_delete(entity_type: str, entity_id: str, user: str = "", data: dict | None = None) -> int:
    """Log entity deletion."""
    return get_audit_log().log_delete(entity_type, entity_id, user, data)
