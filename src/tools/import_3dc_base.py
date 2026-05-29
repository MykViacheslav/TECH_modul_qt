from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.constructor3d_base import scan_constructor3d_base
from tools import module_db_cli


DEFAULT_3DC_BASE = r"C:\Elecran\3D-Constructor 7E\KM5\BASE"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_db() -> str:
    return str(_project_root() / "data" / "tech.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import 3D-Constructor BASE modules into TechModel DB.")
    parser.add_argument("--base-root", default=DEFAULT_3DC_BASE)
    parser.add_argument("--db", default=_default_db())
    parser.add_argument("--table", default="tab52.ls5", help="3D-Constructor table file to scan, default: tab52.ls5")
    parser.add_argument("--base-name", default="", help="Optional BASE_* folder filter, e.g. BASE_MY")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-history", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.base_root)
    modules = scan_constructor3d_base(root, table_name=args.table)
    if args.base_name:
        modules = [m for m in modules if m.base_name.lower() == args.base_name.lower()]
    modules.sort(key=lambda m: (m.base_name, m.category, m.code))
    if args.limit and args.limit > 0:
        modules = modules[: args.limit]

    if args.dry_run:
        print(json.dumps([m.to_payload() for m in modules[:20]], ensure_ascii=False, indent=2))
        print(json.dumps({"found": len(modules), "db": args.db, "dry_run": True}, ensure_ascii=False))
        return 0

    con = module_db_cli.connect(args.db)
    module_db_cli.ensure_schema(con)
    saved = 0
    for module in modules:
        module_db_cli.upsert(con, module.to_payload(), overwrite=True, history=not args.no_history)
        saved += 1

    print(json.dumps({"found": len(modules), "saved": saved, "db": args.db}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
