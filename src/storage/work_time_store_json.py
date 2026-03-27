from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from src.domain.work_time_models import WorkerMonthSheetDef, new_entry_id
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message_pl: str


class WorkTimeStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "work_time.json"
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

    def upsert_day_entry(self, worker_name: str, year: int, month: int, entry) -> StoreResult:
        """
        Insert or merge a single day entry into the monthly sheet.
        Used by kiosk clocking so the monthly view stays one row per day.
        """
        sheet = self.get_sheet(worker_name, year, month)
        day = int(getattr(entry, "day", 0) or 0)
        if day <= 0:
            return StoreResult(False, "Nieprawidłowy dzień wpisu czasu pracy.")

        entry_id = str(getattr(entry, "entry_id", "") or "").strip() or new_entry_id()

        entries = list(sheet.entries)
        merged = False
        for idx, existing in enumerate(entries):
            if int(getattr(existing, "day", 0) or 0) != day:
                continue
            existing_hours = float(getattr(existing, "hours", 0.0) or 0.0)
            existing_overtime = float(getattr(existing, "overtime_hours", 0.0) or 0.0)
            existing_extra = float(getattr(existing, "extra_pay", 0.0) or 0.0)
            new_hours = float(getattr(entry, "hours", 0.0) or 0.0)
            new_overtime = float(getattr(entry, "overtime_hours", 0.0) or 0.0)
            new_extra = float(getattr(entry, "extra_pay", 0.0) or 0.0)

            start_time = str(getattr(existing, "start_time", "") or "").strip() or str(getattr(entry, "start_time", "") or "").strip()
            end_time = str(getattr(entry, "end_time", "") or "").strip() or str(getattr(existing, "end_time", "") or "").strip()
            if not start_time:
                start_time = str(getattr(entry, "start_time", "") or "").strip()

            work_type = str(getattr(entry, "work_type", "") or "").strip() or str(getattr(existing, "work_type", "") or "").strip()
            project_code = str(getattr(entry, "project_code", "") or "").strip() or str(getattr(existing, "project_code", "") or "").strip()
            note_existing = str(getattr(existing, "note", "") or "").strip()
            note_new = str(getattr(entry, "note", "") or "").strip()
            note = " | ".join(part for part in (note_existing, note_new) if part)

            merged_entry = type(existing)(
                entry_id=str(getattr(existing, "entry_id", "") or entry_id or ""),
                day=day,
                date_iso=str(getattr(entry, "date_iso", "") or getattr(existing, "date_iso", "") or ""),
                work_type=work_type,
                start_time=start_time,
                end_time=end_time,
                hours=round(existing_hours + new_hours, 2),
                overtime_hours=round(existing_overtime + new_overtime, 2),
                extra_pay=round(existing_extra + new_extra, 2),
                project_code=project_code,
                note=note,
            )
            entries[idx] = merged_entry
            merged = True
            break

        if not merged:
            if not str(getattr(entry, "entry_id", "") or "").strip():
                entry = type(entry)(
                    entry_id=entry_id,
                    day=day,
                    date_iso=str(getattr(entry, "date_iso", "") or ""),
                    work_type=str(getattr(entry, "work_type", "") or ""),
                    start_time=str(getattr(entry, "start_time", "") or ""),
                    end_time=str(getattr(entry, "end_time", "") or ""),
                    hours=float(getattr(entry, "hours", 0.0) or 0.0),
                    overtime_hours=float(getattr(entry, "overtime_hours", 0.0) or 0.0),
                    extra_pay=float(getattr(entry, "extra_pay", 0.0) or 0.0),
                    project_code=str(getattr(entry, "project_code", "") or ""),
                    note=str(getattr(entry, "note", "") or ""),
                )
            entries.append(entry)

        entries.sort(key=lambda item: int(getattr(item, "day", 0) or 0))
        sheet.entries = entries
        self.save_sheet(sheet)
        return StoreResult(True, f'Zapisano wpis czasu pracy: "{worker_name}" {year:04d}-{month:02d}-{day:02d}.')

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
