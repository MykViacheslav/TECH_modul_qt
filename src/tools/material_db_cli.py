import argparse, json, os, re, sqlite3
from datetime import datetime

SCHEMA_VERSION = 1

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def connect(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def table_exists(con, name: str) -> bool:
    r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(r)

def table_cols(con, name: str):
    if not table_exists(con, name):
        return []
    return [r["name"] for r in con.execute(f"PRAGMA table_info({name})").fetchall()]

def create_materials_table(con):
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

def slug_code(s: str) -> str:
    s = (s or "").strip().upper()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Z0-9_]+", "", s)
    return s[:40] if s else ""

def migrate_from_legacy(con, legacy: str):
    lcols = table_cols(con, legacy)
    if "payload_json" not in lcols:
        return 0

    rows = con.execute(f"SELECT * FROM {legacy}").fetchall()
    copied = 0

    for r in rows:
        pj = r["payload_json"]
        try:
            obj = json.loads(pj) if pj else {}
        except Exception:
            obj = {}

        # IMPORTANT: treat legacy anchor as code first (prevents MDF_18MM duplicates)
        code = (obj.get("code") or obj.get("Code") or obj.get("CODE") or
                obj.get("anchor") or obj.get("Anchor") or obj.get("ANCHOR") or "").strip()

        if not code:
            nm = (obj.get("name") or obj.get("Name") or obj.get("NAME") or "")
            code = slug_code(nm)

        if not code:
            if "id" in lcols:
                code = f"MAT{int(r['id'])}"
            else:
                code = f"MAT{copied+1}"

        name = (obj.get("name") or obj.get("Name") or "").strip()
        if not name:
            if "name" in lcols and r["name"]:
                name = str(r["name"])
            else:
                name = code

        kind = (obj.get("kind") or obj.get("Kind") or "board").strip() or "board"

        th = obj.get("thickness_mm", None)
        if th is None:
            th = obj.get("thickness", None)
        try:
            thickness_mm = float(th) if th is not None else None
        except Exception:
            thickness_mm = None

        created_at = r["created_at"] if "created_at" in lcols and r["created_at"] else now_iso()
        updated_at = now_iso()

        obj = dict(obj)
        # normalize payload
        obj.pop("anchor", None); obj.pop("Anchor", None); obj.pop("ANCHOR", None)
        obj["code"] = code
        obj["name"] = name
        obj["kind"] = kind
        if thickness_mm is not None:
            obj["thickness_mm"] = thickness_mm
        obj["schema_version"] = SCHEMA_VERSION

        payload_json = json.dumps(obj, ensure_ascii=False)

        con.execute("""
            INSERT OR IGNORE INTO materials(code, name, kind, thickness_mm, payload_json, schema_version, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, (code, name, kind, thickness_mm, payload_json, SCHEMA_VERSION, created_at, updated_at))

        copied += 1

    con.commit()
    return copied

def ensure_schema(con: sqlite3.Connection):
    if not table_exists(con, "materials"):
        create_materials_table(con)
        con.commit()
        return

    cols = table_cols(con, "materials")

    if "code" not in cols or "payload_json" not in cols:
        legacy = "materials_legacy_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        con.execute(f"ALTER TABLE materials RENAME TO {legacy}")
        create_materials_table(con)
        con.commit()
        copied = migrate_from_legacy(con, legacy)
        print(f"OK: migrated legacy materials -> new schema. Copied: {copied}. Legacy table: {legacy}")
        return

    # ensure expected cols exist
    def add_col(col, ddl):
        nonlocal cols
        if col in cols:
            return
        con.execute(f"ALTER TABLE materials ADD COLUMN {ddl}")
        cols = table_cols(con, "materials")

    add_col("kind", "kind TEXT NOT NULL DEFAULT 'board'")
    add_col("thickness_mm", "thickness_mm REAL")
    add_col("schema_version", "schema_version INTEGER NOT NULL DEFAULT 1")
    add_col("created_at", "created_at TEXT NOT NULL DEFAULT ''")
    add_col("updated_at", "updated_at TEXT NOT NULL DEFAULT ''")
    con.commit()

def upsert(con: sqlite3.Connection, payload: dict, overwrite: bool):
    ensure_schema(con)
    code = str(payload.get("code") or "").strip()
    if not code:
        raise SystemExit("ERROR: code is required")

    row = con.execute("SELECT code, created_at FROM materials WHERE code = ?", (code,)).fetchone()
    created_at = row["created_at"] if row and row["created_at"] else now_iso()
    updated_at = now_iso()

    if row and not overwrite:
        return code, False, True

    payload = dict(payload)
    payload["code"] = code
    payload["schema_version"] = SCHEMA_VERSION
    payload_json = json.dumps(payload, ensure_ascii=False)

    con.execute("""
        INSERT INTO materials(code, name, kind, thickness_mm, payload_json, schema_version, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(code) DO UPDATE SET
            name=excluded.name,
            kind=excluded.kind,
            thickness_mm=excluded.thickness_mm,
            payload_json=excluded.payload_json,
            schema_version=excluded.schema_version,
            updated_at=excluded.updated_at
    """, (
        code,
        payload.get("name",""),
        payload.get("kind","board"),
        payload.get("thickness_mm", None),
        payload_json,
        SCHEMA_VERSION,
        created_at,
        updated_at
    ))
    con.commit()
    return code, True, False

def cmd_init(args):
    con = connect(args.db)
    ensure_schema(con)
    print(f"OK: materials schema ready: {args.db}")
    return 0

def cmd_save(args):
    con = connect(args.db)
    payload = {
        "code": args.code,
        "name": args.name,
        "kind": args.kind,
        "thickness_mm": args.thickness,
        "note": args.note or "",
    }
    payload = {k:v for k,v in payload.items() if v is not None and v != ""}

    code, saved, existed_no_overwrite = upsert(con, payload, overwrite=bool(args.overwrite))
    if existed_no_overwrite:
        print(f"ERROR: '{code}' already exists. Use --overwrite.")
        return 2
    print(f"OK: saved material '{code}'" + (" (overwritten)" if args.overwrite else ""))
    return 0

def cmd_query(args):
    con = connect(args.db)
    ensure_schema(con)
    q = (args.q or "").strip()
    limit = int(args.limit) if args.limit else 20
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
    out = [json.loads(r["payload_json"]) for r in rows]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

def cmd_clean(args):
    con = connect(args.db)
    ensure_schema(con)

    rows = con.execute("SELECT code, payload_json FROM materials").fetchall()
    codes = set([r["code"] for r in rows])

    candidates = []
    for r in rows:
        code = r["code"]
        try:
            obj = json.loads(r["payload_json"]) if r["payload_json"] else {}
        except Exception:
            obj = {}
        anchor = (obj.get("anchor") or obj.get("Anchor") or obj.get("ANCHOR") or "")
        anchor = str(anchor).strip()
        if anchor and anchor != code and anchor in codes:
            candidates.append({"delete_code": code, "keep_code": anchor})

    if not candidates:
        print("OK: nothing to clean")
        return 0

    print(json.dumps({"candidates": candidates, "apply": bool(args.apply)}, ensure_ascii=False, indent=2))

    if args.apply:
        for c in candidates:
            con.execute("DELETE FROM materials WHERE code = ?", (c["delete_code"],))
        con.commit()
        print(f"OK: deleted {len(candidates)} duplicate legacy rows")
    return 0

def build_parser():
    p = argparse.ArgumentParser(prog="material_db_cli")
    p.add_argument("--db", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.set_defaults(fn=cmd_init)

    s = sub.add_parser("save")
    s.add_argument("--code", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--kind", default="board")
    s.add_argument("--thickness", type=float, default=None)
    s.add_argument("--note", default="")
    s.add_argument("--overwrite", action="store_true")
    s.set_defaults(fn=cmd_save)

    s = sub.add_parser("query")
    s.add_argument("--q", default="")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("clean")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(fn=cmd_clean)

    return p

def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    raise SystemExit(main())
