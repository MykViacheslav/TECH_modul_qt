from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


def _default_data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)

    root = Path(__file__).resolve().parents[2]
    proj = root.parent
    return proj / "data"


class OrderDraftStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _default_data_dir() / "new_order_draft.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def load(self) -> Dict[str, str]:
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, payload: Dict[str, str]) -> None:
        data = payload if isinstance(payload, dict) else {}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self._path.write_text("{}", encoding="utf-8")
