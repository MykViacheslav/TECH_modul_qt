from __future__ import annotations
import os, json, sqlite3
from pathlib import Path
from datetime import datetime

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def project_root() -> Path:
    # src/app/storage.py -> src/app -> src -> project root
    return Path(__file__).resolve().parents[2]

def default_db_path() -> str:
    # allow override by env TECH_DB
    env = os.environ.get("TECH_DB", "").strip()
    if env:
        return env
    return str(project_root() / "data" / "tech.db")

def connect(db_path: str | None = None) -> sqlite3.Connection:
    db = db_path or default_db_path()
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con

def table_exists(con, name: str) -> bool:
    r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(r)

def table_cols(con, name: str):
    if not table_exists(con, name):
        return []
    return [r["name"] for r in con.execute(f"PRAGMA table_info({name})").fetchall()]

def ensure_modules_schema(con: sqlite3.Connection):
    con.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        anchor TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS modules_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anchor TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        saved_at TEXT NOT NULL
    )
    """)
    con.commit()

    # fix legacy history schema
    cols = table_cols(con, "modules_history")
    if "saved_at" not in cols:
        con.execute("ALTER TABLE modules_history ADD COLUMN saved_at TEXT NOT NULL DEFAULT ''")
        con.commit()
    cols = table_cols(con, "modules_history")
    if "schema_version" not in cols:
        con.execute("ALTER TABLE modules_history ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")
        con.commit()

def ensure_materials_schema(con: sqlite3.Connection):
    con.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        thickness_mm REAL,
        payload_json TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    con.commit()

def upsert_module(con: sqlite3.Connection, payload: dict, overwrite: bool = True, history: bool = True):
    ensure_modules_schema(con)
    anchor = str(payload.get("anchor") or "").strip()
    if not anchor:
        raise ValueError("anchor is required")

    row = con.execute("SELECT created_at FROM modules WHERE anchor=?", (anchor,)).fetchone()
    created_at = (row["created_at"] if row and row["created_at"] else now_iso())
    updated_at = now_iso()

    payload = dict(payload)
    payload["anchor"] = anchor
    payload.setdefault("schema_version", 1)

    pj = json.dumps(payload, ensure_ascii=False)

    if row and not overwrite:
        return False

    con.execute("""
      INSERT INTO modules(anchor, payload_json, schema_version, created_at, updated_at)
      VALUES(?,?,?,?,?)
      ON CONFLICT(anchor) DO UPDATE SET
        payload_json=excluded.payload_json,
        schema_version=excluded.schema_version,
        updated_at=excluded.updated_at
    """, (anchor, pj, int(payload.get("schema_version", 1)), created_at, updated_at))

    if history:
        con.execute("""
          INSERT INTO modules_history(anchor, payload_json, schema_version, saved_at)
          VALUES(?,?,?,?)
        """, (anchor, pj, int(payload.get("schema_version", 1)), updated_at))

    con.commit()
    return True

def get_module(con: sqlite3.Connection, anchor: str) -> dict | None:
    ensure_modules_schema(con)
    r = con.execute("SELECT payload_json FROM modules WHERE anchor=?", (anchor,)).fetchone()
    if not r:
        return None
    return json.loads(r["payload_json"])

def list_modules(con: sqlite3.Connection, limit: int = 200) -> list[dict]:
    ensure_modules_schema(con)
    rows = con.execute("SELECT payload_json FROM modules ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]

def query_materials(con: sqlite3.Connection, q: str, limit: int = 20) -> list[dict]:
    ensure_materials_schema(con)
    q = (q or "").strip()
    limit = int(limit) if limit else 20
    if not q:
        rows = con.execute("SELECT payload_json FROM materials ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    else:
        like = f"%{q}%"
        rows = con.execute("""
          SELECT payload_json FROM materials
          WHERE code LIKE ? OR name LIKE ?
          ORDER BY updated_at DESC
          LIMIT ?
        """, (like, like, limit)).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]
