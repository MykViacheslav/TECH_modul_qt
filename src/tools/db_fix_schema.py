from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def cols(con: sqlite3.Connection, table: str) -> list[str]:
    try:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] for r in rows]
    except Exception:
        return []

def table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None

def create_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS modules (
            anchor         TEXT PRIMARY KEY,
            payload_json   TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS modules_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            anchor         TEXT NOT NULL,
            payload_json   TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            archived_at    TEXT NOT NULL
        );
        """
    )
    con.commit()

def best_effort_copy(con: sqlite3.Connection, legacy: str) -> int:
    legacy_cols = cols(con, legacy)
    now = utc_now_iso()

    # pick "anchor" column name from legacy
    anchor_col = None
    for c in ("anchor", "anhor", "name", "key"):
        if c in legacy_cols:
            anchor_col = c
            break

    if anchor_col is None:
        return 0

    if "payload_json" in legacy_cols:
        con.execute(
            f"""
            INSERT OR REPLACE INTO modules(anchor, payload_json, schema_version, created_at, updated_at)
            SELECT
                CAST({anchor_col} AS TEXT),
                payload_json,
                COALESCE(schema_version, 1),
                COALESCE(created_at, ?),
                COALESCE(updated_at, ?)
            FROM {legacy}
            WHERE {anchor_col} IS NOT NULL
            """,
            (now, now),
        )
        con.commit()
        return con.execute("SELECT changes()").fetchone()[0]

    # if legacy has separate columns (width/height/etc) we can't safely reconstruct payload_json
    return 0

def main(db_path: str) -> int:
    db = Path(db_path)
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row

    # if no modules table -> just create schema
    if not table_exists(con, "modules"):
        create_schema(con)
        print("OK: created schema (fresh DB).")
        return 0

    c = cols(con, "modules")
    if "anchor" in c and "payload_json" in c:
        create_schema(con)
        print("OK: schema already correct.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    legacy_name = f"modules_legacy_{stamp}"

    print("WARN: modules table has wrong schema:", c)
    print("Renaming modules ->", legacy_name)
    con.execute(f"ALTER TABLE modules RENAME TO {legacy_name}")
    con.commit()

    # history table also might be wrong; leave it as-is unless broken badly
    # ensure new schema
    create_schema(con)

    copied = best_effort_copy(con, legacy_name)
    print(f"OK: recreated modules table. Copied rows (best-effort): {copied}")
    return 0

if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
