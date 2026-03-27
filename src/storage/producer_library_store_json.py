from __future__ import annotations

import json
from pathlib import Path

from src.storage.data_paths import data_dir


class ProducerLibraryStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else data_dir() / "producer_library.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self.path.exists():
            return {"rows": [], "import_headers": [], "import_mapping": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"rows": [], "import_headers": [], "import_mapping": {}}
        if not isinstance(payload, dict):
            return {"rows": [], "import_headers": [], "import_mapping": {}}
        rows = payload.get("rows", [])
        headers = payload.get("import_headers", [])
        mapping = payload.get("import_mapping", {})
        return {
            "rows": rows if isinstance(rows, list) else [],
            "import_headers": headers if isinstance(headers, list) else [],
            "import_mapping": mapping if isinstance(mapping, dict) else {},
        }

    def save(self, rows: list[dict[str, str]], import_headers: list[str], import_mapping: dict[str, str]) -> None:
        payload = {
            "rows": [dict(entry) for entry in rows],
            "import_headers": [str(item or "") for item in import_headers],
            "import_mapping": {str(k or ""): str(v or "") for k, v in import_mapping.items()},
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
