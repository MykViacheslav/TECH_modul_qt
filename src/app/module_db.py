import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ModuleDB:
    """
    Simple SQLite storage for module states (JSON payload).
    File is stored in <project_root>/_data/modules.sqlite by default.
    """

    def __init__(self, path: Optional[str] = None):
        if path:
            db_path = Path(path)
        else:
            # module_db.py -> app -> src -> project root
            root = Path(__file__).resolve().parents[2]
            db_path = root / "_data" / "modules.sqlite"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = db_path
        self._init()

    def _conn(self):
        return sqlite3.connect(str(self.path))

    def _init(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS modules (
                    name TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def list_names(self) -> List[Tuple[str, str]]:
        with self._conn() as con:
            cur = con.execute("SELECT name, updated_at FROM modules ORDER BY updated_at DESC, name ASC")
            return list(cur.fetchall())

    def exists(self, name: str) -> bool:
        with self._conn() as con:
            cur = con.execute("SELECT 1 FROM modules WHERE name=? LIMIT 1", (name,))
            return cur.fetchone() is not None

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            cur = con.execute("SELECT payload_json FROM modules WHERE name=? LIMIT 1", (name,))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None

    def upsert(self, name: str, payload: Dict[str, Any], overwrite: bool = True) -> None:
        if not name or not str(name).strip():
            raise ValueError("Name is empty")

        s = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        with self._conn() as con:
            if overwrite:
                con.execute(
                    """
                    INSERT INTO modules(name, payload_json, updated_at)
                    VALUES(?, ?, datetime('now'))
                    ON CONFLICT(name) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        updated_at=datetime('now')
                    """,
                    (name, s),
                )
            else:
                # insert-only
                con.execute(
                    "INSERT INTO modules(name, payload_json, updated_at) VALUES(?, ?, datetime('now'))",
                    (name, s),
                )

    def delete(self, name: str) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM modules WHERE name=?", (name,))
