from __future__ import annotations

from dataclasses import dataclass

from src.domain.work_time_models import WorkerMonthSheetDef
from src.domain.worker_models import WorkerDef


@dataclass
class WorkTimeCostBreakdown:
    tracked_days: int = 0
    total_hours: float = 0.0
    overtime_hours: float = 0.0
    base_total: float = 0.0
    overtime_total: float = 0.0
    stage_extra_total: float = 0.0
    manual_extra_total: float = 0.0
    total_cost: float = 0.0


def compute_work_time_cost(
    sheets: list[WorkerMonthSheetDef],
    workers_by_name: dict[str, WorkerDef | None],
    project_codes: set[str] | None = None,
) -> WorkTimeCostBreakdown:
    normalized_codes = {str(code or "").strip() for code in (project_codes or set()) if str(code or "").strip()}
    filter_by_codes = bool(normalized_codes)

    breakdown = WorkTimeCostBreakdown()
    tracked_days: set[tuple[str, str]] = set()
    daily_costs: dict[tuple[str, str], float] = {}
    delegation_days: set[tuple[str, str]] = set()

    for sheet in sheets:
        worker_name = str(sheet.worker_name or "").strip()
        worker = workers_by_name.get(worker_name)
        pay_mode = str(getattr(worker, "pay_mode", "Godzinowa") or "Godzinowa").strip() or "Godzinowa"
        hourly_rate = float(getattr(worker, "hourly_rate", 0.0) or 0.0)
        daily_rate = float(getattr(worker, "daily_rate", 0.0) or 0.0)
        overtime_multiplier = max(float(getattr(worker, "overtime_multiplier", 1.0) or 1.0), 0.0)
        delegation_day_addon = float(getattr(worker, "delegation_day_addon_pln", 0.0) or 0.0)
        montage_hour_addon = float(getattr(worker, "montage_hour_addon_pln", 0.0) or 0.0)
        onsite_hour_addon = float(getattr(worker, "onsite_hour_addon_pln", 0.0) or 0.0)
        lacquer_hour_addon = float(getattr(worker, "lacquer_hour_addon_pln", 0.0) or 0.0)

        for entry in sheet.entries:
            project_code = str(getattr(entry, "project_code", "") or "").strip()
            if filter_by_codes and project_code not in normalized_codes:
                continue

            date_iso = str(getattr(entry, "date_iso", "") or "").strip() or f"{int(sheet.year):04d}-{int(sheet.month):02d}-{int(entry.day):02d}"
            day_key = (worker_name, date_iso)
            tracked_days.add(day_key)

            hours = float(getattr(entry, "hours", 0.0) or 0.0)
            overtime_hours = float(getattr(entry, "overtime_hours", 0.0) or 0.0)
            manual_extra = float(getattr(entry, "extra_pay", 0.0) or 0.0)
            work_type = str(getattr(entry, "work_type", "") or "").strip()

            breakdown.total_hours += hours
            breakdown.overtime_hours += overtime_hours
            breakdown.manual_extra_total += manual_extra

            if pay_mode == "Dniowka":
                daily_costs[day_key] = max(daily_costs.get(day_key, 0.0), daily_rate)
            else:
                breakdown.base_total += hours * hourly_rate

            breakdown.overtime_total += overtime_hours * hourly_rate * overtime_multiplier

            if work_type == "Delegacja / wyjazd":
                if delegation_day_addon > 0.0:
                    delegation_days.add(day_key)
            elif work_type == "Montaz":
                breakdown.stage_extra_total += hours * montage_hour_addon
            elif work_type == "Praca na miejscu":
                breakdown.stage_extra_total += hours * onsite_hour_addon
            elif work_type == "Lakiernia":
                breakdown.stage_extra_total += hours * lacquer_hour_addon

    breakdown.tracked_days = len(tracked_days)
    breakdown.base_total += sum(daily_costs.values())
    breakdown.stage_extra_total += float(len(delegation_days)) * sum(
        float(getattr(workers_by_name.get(worker_name), "delegation_day_addon_pln", 0.0) or 0.0)
        for worker_name, _date_iso in delegation_days
    )
    breakdown.total_hours = round(breakdown.total_hours, 2)
    breakdown.overtime_hours = round(breakdown.overtime_hours, 2)
    breakdown.base_total = round(breakdown.base_total, 2)
    breakdown.overtime_total = round(breakdown.overtime_total, 2)
    breakdown.stage_extra_total = round(breakdown.stage_extra_total, 2)
    breakdown.manual_extra_total = round(breakdown.manual_extra_total, 2)
    breakdown.total_cost = round(
        breakdown.base_total
        + breakdown.overtime_total
        + breakdown.stage_extra_total
        + breakdown.manual_extra_total,
        2,
    )
    return breakdown
