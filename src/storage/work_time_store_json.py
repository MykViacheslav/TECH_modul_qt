from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from src.domain.work_time_models import WorkerMonthSheetDef


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class WorkTimeStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            root = Path(__file__).resolve().parents[2]
            proj = root.parent
            path = proj / "data" / "work_time.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def get_sheet(self, worker_name: str, year: int, month: int) -> WorkerMonthSheetDef:
        key = self._key(worker_name, year, month)
        raw = self._read_all().get(key)
        if isinstance(raw, dict):
            return WorkerMonthSheetDef.from_dict(raw)
        return WorkerMonthSheetDef(worker_name=worker_name, year=int(year), month=int(month))

    def list_sheets(self) -> list[WorkerMonthSheetDef]:
        raw_all = self._read_all()
        result: list[WorkerMonthSheetDef] = []
        for key in sorted(raw_all.keys()):
            raw = raw_all.get(key)
            if isinstance(raw, dict):
                result.append(WorkerMonthSheetDef.from_dict(raw))
        return result

    def save_sheet(self, sheet: WorkerMonthSheetDef) -> StoreResult:
        data = self._read_all()
        data[self._key(sheet.worker_name, sheet.year, sheet.month)] = sheet.to_dict()
        self._write_all(data)
        return StoreResult(True, f'Zapisano godziny pracy: "{sheet.worker_name}" {sheet.year:04d}-{sheet.month:02d}.')

    def _key(self, worker_name: str, year: int, month: int) -> str:
        return f"{str(worker_name or '').strip()}|{int(year):04d}-{int(month):02d}"

    def _read_all(self) -> Dict[str, dict]:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
