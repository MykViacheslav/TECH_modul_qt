import argparse, json, os
from datetime import datetime

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def save_json(path: str, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def export_all(db_path: str, out_path: str, limit_modules: int = 5000, limit_materials: int = 5000):
    from tools import module_db_cli
    from tools import material_db_cli

    con_m = module_db_cli.connect(db_path)
    module_db_cli.ensure_schema(con_m)
    rows = con_m.execute(
        "SELECT payload_json FROM modules ORDER BY updated_at DESC LIMIT ?",
        (int(limit_modules),)
    ).fetchall()
    modules = []
    for r in rows:
        try:
            modules.append(json.loads(r["payload_json"]))
        except Exception:
            pass

    con_t = material_db_cli.connect(db_path)
    material_db_cli.ensure_schema(con_t)
    rows = con_t.execute(
        "SELECT payload_json FROM materials ORDER BY updated_at DESC LIMIT ?",
        (int(limit_materials),)
    ).fetchall()
    materials = []
    for r in rows:
        try:
            materials.append(json.loads(r["payload_json"]))
        except Exception:
            pass

    pack = {
        "type": "TECH_EXPORT",
        "created_at": now_iso(),
        "db_path_hint": db_path,
        "modules": modules,
        "materials": materials,
    }
    save_json(out_path, pack)
    return pack

def import_all(db_path: str, in_path: str, overwrite: bool = False, no_history: bool = False):
    from tools import module_db_cli
    from tools import material_db_cli

    pack = load_json(in_path)
    if not isinstance(pack, dict) or pack.get("type") != "TECH_EXPORT":
        raise SystemExit("ERROR: invalid import file (expected type=TECH_EXPORT)")

    modules = pack.get("modules") or []
    materials = pack.get("materials") or []

    con_mod = module_db_cli.connect(db_path)
    module_db_cli.ensure_schema(con_mod)

    con_mat = material_db_cli.connect(db_path)
    material_db_cli.ensure_schema(con_mat)

    mat_ok = mat_skip = 0
    for m in materials:
        if not isinstance(m, dict):
            continue
        code = str(m.get("code") or "").strip()
        if not code:
            continue
        payload = dict(m)
        payload["code"] = code
        payload.setdefault("name", code)
        payload.setdefault("kind", "board")
        code2, saved, existed_no_overwrite = material_db_cli.upsert(con_mat, payload, overwrite=overwrite)
        if existed_no_overwrite:
            mat_skip += 1
        else:
            mat_ok += 1

    mod_ok = mod_skip = 0
    for m in modules:
        if not isinstance(m, dict):
            continue
        anchor = str(m.get("anchor") or "").strip()
        if not anchor:
            continue
        payload = dict(m)
        payload["anchor"] = anchor
        anchor2, saved, existed_no_overwrite = module_db_cli.upsert(
            con_mod, payload,
            overwrite=overwrite,
            history=(not no_history)
        )
        if existed_no_overwrite:
            mod_skip += 1
        else:
            mod_ok += 1

    return {"materials_saved": mat_ok, "materials_skipped": mat_skip, "modules_saved": mod_ok, "modules_skipped": mod_skip}

def build_parser():
    p = argparse.ArgumentParser(prog="tech_sync_cli")
    p.add_argument("--db", required=True)

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("export")
    s.add_argument("--out", required=True)
    s.add_argument("--limit-modules", type=int, default=5000)
    s.add_argument("--limit-materials", type=int, default=5000)

    s = sub.add_parser("import")
    s.add_argument("--in", dest="inp", required=True)
    s.add_argument("--overwrite", action="store_true")
    s.add_argument("--no-history", action="store_true")

    return p

def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.cmd == "export":
        pack = export_all(args.db, args.out, args.limit_modules, args.limit_materials)
        print(f"OK: exported modules={len(pack['modules'])} materials={len(pack['materials'])} -> {args.out}")
        return 0

    if args.cmd == "import":
        res = import_all(args.db, args.inp, overwrite=bool(args.overwrite), no_history=bool(args.no_history))
        print("OK: import done:", json.dumps(res, ensure_ascii=False))
        return 0

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
