from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.storage.data_paths import data_dir


def _default_data_dir() -> Path:
    return data_dir()


def _to_float(value: Any) -> float:
    text = str(value or "").strip().replace(" ", "").replace(",", ".")
    text = text.replace("zl", "").replace("ZL", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def new_expense_id() -> str:
    return str(uuid.uuid4())[:8].upper()


class CompanyExpensesStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _default_data_dir() / "company_expenses.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def list_items(self, section: str, defaults: list[str]) -> list[dict[str, float | str]]:
        payload = self._read_payload()
        raw = payload.get(section, [])
        items: list[dict[str, float | str]] = []
        if isinstance(raw, list):
            for row in raw:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "") or "").strip()
                if not name:
                    continue
                expense_id = str(row.get("expense_id", "") or "").strip()
                if not expense_id:
                    expense_id = new_expense_id()
                items.append({"expense_id": expense_id, "name": name, "amount": float(_to_float(row.get("amount", 0.0)))})
        if items:
            return items
        return [{"expense_id": new_expense_id(), "name": name, "amount": 0.0} for name in defaults]

    def save_items(self, section: str, items: list[dict[str, float | str]]) -> None:
        payload = self._read_payload()
        cleaned: list[dict[str, float | str]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "") or "").strip()
            if not name:
                continue
            expense_id = str(row.get("expense_id", "") or "").strip()
            if not expense_id:
                expense_id = new_expense_id()
            cleaned.append({"expense_id": expense_id, "name": name, "amount": float(_to_float(row.get("amount", 0.0)))})
        payload[section] = cleaned
        self._write_payload(payload)

    def sum_items(self, section: str) -> float:
        payload = self._read_payload()
        raw = payload.get(section, [])
        total = 0.0
        if not isinstance(raw, list):
            return 0.0
        for row in raw:
            if not isinstance(row, dict):
                continue
            total += float(_to_float(row.get("amount", 0.0)))
        return total

    def get_workers_count(self, fallback: int = 1) -> int:
        payload = self._read_payload()
        value = payload.get("workers_count", fallback)
        try:
            count = int(value)
        except Exception:
            count = int(fallback)
        return max(1, count)

    def get_hours_per_worker(self, fallback: float = 160.0) -> float:
        payload = self._read_payload()
        value = payload.get("hours_per_worker", fallback)
        try:
            hours = float(value)
        except Exception:
            hours = float(fallback)
        return max(1.0, hours)

    def save_workforce(self, workers_count: int, hours_per_worker: float) -> None:
        payload = self._read_payload()
        payload["workers_count"] = max(1, int(workers_count))
        payload["hours_per_worker"] = max(1.0, float(hours_per_worker))
        self._write_payload(payload)

    def real_hour_metrics(self, workers_fallback: int = 1, hours_fallback: float = 160.0) -> dict[str, float]:
        payload = self._read_payload()
        fixed_total = 0.0
        variable_total = 0.0

        fixed_rows = payload.get("fixed", [])
        if isinstance(fixed_rows, list):
            for row in fixed_rows:
                if isinstance(row, dict):
                    fixed_total += float(_to_float(row.get("amount", 0.0)))

        variable_rows = payload.get("variable", [])
        if isinstance(variable_rows, list):
            for row in variable_rows:
                if isinstance(row, dict):
                    variable_total += float(_to_float(row.get("amount", 0.0)))

        try:
            workers_count = int(payload.get("workers_count", workers_fallback))
        except Exception:
            workers_count = int(workers_fallback)
        workers_count = max(1, workers_count)

        try:
            hours_per_worker = float(payload.get("hours_per_worker", hours_fallback))
        except Exception:
            hours_per_worker = float(hours_fallback)
        hours_per_worker = max(1.0, hours_per_worker)

        total_costs = fixed_total + variable_total
        total_hours = float(workers_count) * hours_per_worker
        real_hour_rate = total_costs / total_hours if total_hours > 0 else 0.0
        return {
            "fixed_total": fixed_total,
            "variable_total": variable_total,
            "total_costs": total_costs,
            "workers_count": float(workers_count),
            "hours_per_worker": hours_per_worker,
            "total_hours": total_hours,
            "real_hour_rate": real_hour_rate,
        }

    def _read_payload(self) -> dict[str, Any]:
        try:
            text = self._path.read_text(encoding="utf-8")
            payload = json.loads(text) if text.strip() else {}
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
