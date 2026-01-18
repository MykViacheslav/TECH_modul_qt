from __future__ import annotations
import sqlite3
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def table_cols(con: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]

def main(db_path: str) -> int:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # find newest legacy table
    legacy = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'modules_legacy_%' ORDER BY name DESC LIMIT 1"
    ).fetchone()

    if not legacy:
        print("OK: no modules_legacy_* table found. Nothing to copy.")
        return 0

    legacy_name = legacy[0]
    legacy_cols = table_cols(con, legacy_name)

    # pick anchor source column
    anchor_col = None
    for c in ("anchor", "name", "anhor", "key"):
        if c in legacy_cols:
            anchor_col = c
            break

    if anchor_col is None:
        raise SystemExit(f"ERROR: legacy table {legacy_name} has no anchor-like column. cols={legacy_cols}")

    if "payload_json" not in legacy_cols:
        raise SystemExit(f"ERROR: legacy table {legacy_name} has no payload_json. cols={legacy_cols}")

    now = utc_now_iso()
    has_created = "created_at" in legacy_cols
    has_updated = "updated_at" in legacy_cols

    created_expr = "COALESCE(created_at, ?)" if has_created else "?"
    updated_expr = "COALESCE(updated_at, ?)" if has_updated else "?"

    sql = f"""
    INSERT OR REPLACE INTO modules(anchor, payload_json, schema_version, created_at, updated_at)
    SELECT
        CAST({anchor_col} AS TEXT) AS anchor,
        payload_json,
        1 AS schema_version,
        {created_expr} AS created_at,
        {updated_expr} AS updated_at
    FROM {legacy_name}
    WHERE {anchor_col} IS NOT NULL
    """

    cur.execute("BEGIN")
    cur.execute(sql, (now, now))
    con.commit()

    cnt = cur.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    print(f"OK: copied from {legacy_name} into modules. modules count={cnt}")
    return 0

if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
