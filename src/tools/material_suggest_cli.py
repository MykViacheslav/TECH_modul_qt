import argparse, json, os, sqlite3, re
from datetime import datetime

def connect(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def has_table(con, name: str) -> bool:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return bool(row)

def table_cols(con, table: str):
    try:
        return [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.Error:
        return []

def norm(s: str) -> str:
    return (s or "").strip().lower()

def tokens(q: str):
    q = norm(q)
    # split on whitespace and punctuation
    parts = re.split(r"[\s,;|/\\\t]+", q)
    return [p for p in parts if p]

def safe_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

def pick_name(row, payload):
    # prefer explicit columns
    for k in ("name", "title", "label"):
        if k in row.keys() and row[k]:
            return str(row[k])
    if isinstance(payload, dict):
        for k in ("name", "title", "label"):
            if payload.get(k):
                return str(payload.get(k))
    return ""

def extract_kind(payload: dict):
    if not isinstance(payload, dict):
        return ""
    for k in ("kind", "type", "group"):
        if payload.get(k):
            return str(payload.get(k))
    return ""

def extract_thickness(payload: dict):
    if not isinstance(payload, dict):
        return None
    for k in ("thickness_mm", "thickness", "t_mm", "t"):
        v = payload.get(k)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except Exception:
            pass
    # layered: maybe "layers": [{"thickness_mm":...}, ...]
    layers = payload.get("layers")
    if isinstance(layers, list):
        total = 0.0
        ok = False
        for it in layers:
            if isinstance(it, dict):
                for kk in ("thickness_mm","thickness","t_mm","t"):
                    if kk in it:
                        try:
                            total += float(it[kk])
                            ok = True
                            break
                        except Exception:
                            pass
        if ok:
            return total
    return None

def score_item(q_tokens, hay: str):
    hay = norm(hay)
    if not q_tokens:
        return 0
    sc = 0
    for t in q_tokens:
        if t in hay:
            sc += 10
    # bonus if whole query substring
    return sc

def suggest(db: str, q: str, limit: int):
    con = connect(db)

    if not has_table(con, "materials"):
        raise SystemExit("ERROR: materials table not found. Run: .\\tools\\mat_init.ps1")

    cols = table_cols(con, "materials")
    # common layouts:
    # 1) materials(anchor TEXT PRIMARY KEY, payload_json TEXT, ...)
    # 2) materials(id..., anchor, name, payload_json...)
    anchor_col = "anchor" if "anchor" in cols else ("name" if "name" in cols else None)
    payload_col = "payload_json" if "payload_json" in cols else None

    if not anchor_col:
        raise SystemExit(f"ERROR: materials table has no 'anchor' column. Columns: {cols}")

    qn = norm(q)
    qtok = tokens(q)

    # Candidate query (best effort)
    where = []
    params = []

    where.append(f"lower({anchor_col}) LIKE ?")
    params.append(f"%{qn}%")

    if "name" in cols:
        where.append("lower(name) LIKE ?")
        params.append(f"%{qn}%")

    if payload_col:
        where.append(f"lower({payload_col}) LIKE ?")
        params.append(f"%{qn}%")

    sql = f"SELECT * FROM materials WHERE ({' OR '.join(where)})"
    # get more candidates than limit to score them in python
    rows = con.execute(sql, params).fetchall()

    items = []
    for r in rows:
        payload = safe_json(r[payload_col]) if payload_col and r[payload_col] else None
        anc = str(r[anchor_col])
        nm  = pick_name(r, payload)
        kind = extract_kind(payload) if isinstance(payload, dict) else ""
        th = extract_thickness(payload) if isinstance(payload, dict) else None

        hay = " ".join([anc, nm, json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else ""])
        sc = score_item(qtok, hay)

        items.append({
            "anchor": anc,
            "name": nm,
            "kind": kind,
            "thickness_mm": th,
            "score": sc
        })

    # sort: score desc, anchor asc
    items.sort(key=lambda x: (-int(x.get("score") or 0), str(x.get("anchor") or "")))

    out = items[: max(0, int(limit))]

    # add idx for nicer display
    for i, it in enumerate(out, 1):
        it["idx"] = i

    print(json.dumps(out, ensure_ascii=False, indent=2))

def build_parser():
    p = argparse.ArgumentParser(prog="material_suggest_cli")
    p.add_argument("--db", required=True)

    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suggest")
    s.add_argument("--q", required=True)
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=lambda a: suggest(a.db, a.q, a.limit))

    return p

def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    a.fn(a)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
