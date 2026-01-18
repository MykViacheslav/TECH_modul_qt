from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ISO = "%Y-%m-%dT%H:%M:%S"

def _now_iso() -> str:
    return datetime.now().strftime(ISO)

def _db_path() -> Path:
    proj = Path(__file__).resolve().parents[2]
    data_dir = proj / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "tech.db"

def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path()))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def init_db() -> None:
    con = _connect()
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        con.commit()
    finally:
        con.close()

def list_modules() -> list[str]:
    con = _connect()
    try:
        cur = con.execute("SELECT name FROM modules ORDER BY updated_at DESC")
        return [r[0] for r in cur.fetchall()]
    finally:
        con.close()

def get_module(name: str) -> Optional[dict[str, Any]]:
    con = _connect()
    try:
        cur = con.execute("SELECT payload_json FROM modules WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])
    finally:
        con.close()

def save_module(name: str, payload: dict[str, Any], overwrite: bool = False) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    con = _connect()
    try:
        now = _now_iso()
        if overwrite:
            con.execute("""
            INSERT INTO modules(name, payload_json, created_at, updated_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              payload_json=excluded.payload_json,
              updated_at=excluded.updated_at
            """, (name, payload_json, now, now))
        else:
            con.execute("""
            INSERT INTO modules(name, payload_json, created_at, updated_at)
            VALUES(?, ?, ?, ?)
            """, (name, payload_json, now, now))
        con.commit()
    finally:
        con.close()

def delete_module(name: str) -> bool:
    con = _connect()
    try:
        cur = con.execute("DELETE FROM modules WHERE name=?", (name,))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()
