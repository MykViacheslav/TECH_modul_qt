from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.service_store_json import ServiceStoreJson
from src.storage.shopping_list_store_json import ShoppingListStoreJson
from src.storage.worker_store_json import WorkerStoreJson


@dataclass(frozen=True)
class MonthlyKPI:
    period: str
    total_spent: float
    item_count: int
    average_price: float


@dataclass(frozen=True)
class SupplierKPI:
    supplier: str
    total_spent: float
    item_count: int
    average_unit_price: float
    share_percent: float


@dataclass(frozen=True)
class TrendPoint:
    period: str
    value: float


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _month_keys(months_back: int) -> list[str]:
    months = max(1, int(months_back))
    today = date.today()
    y, m = today.year, today.month
    keys_desc: list[str] = []
    for _ in range(months):
        keys_desc.append(f"{y:04d}-{m:02d}")
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
    return list(reversed(keys_desc))


def _parse_month_key(raw_date: str) -> str:
    text = str(raw_date or "").strip()
    if len(text) < 7:
        return ""
    try:
        year, month = text[:7].split("-", 1)
        return f"{int(year):04d}-{int(month):02d}"
    except Exception:
        return ""


def _parse_iso_date(raw_value: Any) -> date | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def _is_closed_status(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return status in {"zakonczone", "zakończone", "closed", "done"}


def _is_rework_status(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return "poprawk" in status or "rework" in status


class KPIService:
    def __init__(self, data_store: Any = None, cache_ttl_seconds: int = 900) -> None:
        self._cache_ttl_seconds = max(1, int(cache_ttl_seconds or 900))
        self._cache: dict[str, tuple[float, Any]] = {}
        self._data_store = data_store

        self._order_store = self._resolve_store(
            data_store,
            ("orders", "order_store", "_order_store"),
            OrderStoreJson,
        )
        self._expenses_store = self._resolve_store(
            data_store,
            ("expenses", "expenses_store", "_expenses_store"),
            CompanyExpensesStoreJson,
        )
        self._worker_store = self._resolve_store(
            data_store,
            ("workers", "worker_store", "_worker_store"),
            WorkerStoreJson,
        )
        self._service_store = self._resolve_store(
            data_store,
            ("services", "service_store", "_service_store"),
            ServiceStoreJson,
        )
        self._shopping_store = self._resolve_store(
            data_store,
            ("shopping", "shopping_store", "_shopping_store"),
            ShoppingListStoreJson,
        )
        self._alarm_store = self._resolve_store(
            data_store,
            ("alarms", "alarm_store", "_alarm_store"),
            AlarmStoreJson,
        )

    def refresh(self) -> None:
        self._cache.clear()

    def get_monthly_purchases(self, months_back: int = 12) -> list[MonthlyKPI]:
        months = max(1, int(months_back or 12))
        key = f"monthly_purchases:{months}"
        return self._cached(key, lambda: self._compute_monthly_purchases(months))

    def get_supplier_kpis(self) -> list[SupplierKPI]:
        return self._cached("supplier_kpis", self._compute_supplier_kpis)

    def get_trend(self, metric: str, period: str = "monthly") -> list[TrendPoint]:
        metric_key = str(metric or "").strip().lower()
        period_key = str(period or "monthly").strip().lower()
        key = f"trend:{metric_key}:{period_key}"
        return self._cached(key, lambda: self._compute_trend(metric_key, period_key))

    def build_dashboard_payload(self, range_days: int | None = None) -> dict[str, Any]:
        days = int(range_days or 0)
        if days <= 0:
            return self._cached("dashboard_payload", lambda: self._compute_dashboard_payload(None))
        key = f"dashboard_payload:{days}"
        return self._cached(key, lambda: self._compute_dashboard_payload(days))

    def _cached(self, key: str, producer: Callable[[], Any]) -> Any:
        now = time.time()
        cached = self._cache.get(key)
        if cached is not None:
            ts, value = cached
            if (now - ts) <= self._cache_ttl_seconds:
                return value
        value = producer()
        self._cache[key] = (now, value)
        return value

    @staticmethod
    def _resolve_store(data_store: Any, keys: tuple[str, ...], default_factory: Callable[[], Any]) -> Any:
        if isinstance(data_store, dict):
            for key in keys:
                if key in data_store and data_store[key] is not None:
                    return data_store[key]
        if data_store is not None:
            for key in keys:
                if hasattr(data_store, key):
                    value = getattr(data_store, key)
                    if callable(value):
                        try:
                            value = value()
                        except Exception:
                            continue
                    if value is not None:
                        return value
        return default_factory()

    def _compute_monthly_purchases(self, months_back: int) -> list[MonthlyKPI]:
        keys = _month_keys(months_back)
        sums = {k: 0.0 for k in keys}
        counts = {k: 0 for k in keys}
        items = list(getattr(self._shopping_store, "list_items", lambda: [])() or [])
        for item in items:
            if str(getattr(item, "status", "") or "").strip().lower() != "zakupiono":
                continue
            month_key = _parse_month_key(str(getattr(item, "added_date", "") or ""))
            if month_key not in sums:
                continue
            qty = max(0.0, _to_float(getattr(item, "quantity_needed", 0.0)))
            amount = max(0.0, _to_float(getattr(item, "price_actual", 0.0))) * qty
            sums[month_key] += amount
            counts[month_key] += int(round(qty))
        return [
            MonthlyKPI(
                period=key,
                total_spent=sums[key],
                item_count=counts[key],
                average_price=(sums[key] / counts[key]) if counts[key] > 0 else 0.0,
            )
            for key in keys
        ]

    def _compute_supplier_kpis(self) -> list[SupplierKPI]:
        cutoff = date.today() - timedelta(days=365)
        totals: dict[str, tuple[float, int]] = {}
        items = list(getattr(self._shopping_store, "list_items", lambda: [])() or [])
        for item in items:
            if str(getattr(item, "status", "") or "").strip().lower() != "zakupiono":
                continue
            try:
                added = date.fromisoformat(str(getattr(item, "added_date", "") or "").strip())
            except Exception:
                continue
            if added < cutoff:
                continue
            supplier = str(getattr(item, "supplier", "") or "").strip() or "<nieznany>"
            qty = max(0, int(round(_to_float(getattr(item, "quantity_needed", 0.0)))))
            amount = max(0.0, _to_float(getattr(item, "price_actual", 0.0))) * max(0.0, _to_float(getattr(item, "quantity_needed", 0.0)))
            prev_total, prev_count = totals.get(supplier, (0.0, 0))
            totals[supplier] = (prev_total + amount, prev_count + qty)

        overall = sum(total for total, _ in totals.values())
        rows = sorted(totals.items(), key=lambda pair: pair[1][0], reverse=True)
        result: list[SupplierKPI] = []
        for supplier, (total_spent, item_count) in rows:
            avg = (total_spent / item_count) if item_count > 0 else 0.0
            share = (100.0 * total_spent / overall) if overall > 0 else 0.0
            result.append(
                SupplierKPI(
                    supplier=supplier,
                    total_spent=total_spent,
                    item_count=item_count,
                    average_unit_price=avg,
                    share_percent=share,
                )
            )
        return result

    def _compute_trend(self, metric: str, period: str) -> list[TrendPoint]:
        if period != "monthly":
            period = "monthly"
        if metric in {"shopping_spend", "monthly_purchases"}:
            monthly = self.get_monthly_purchases(12)
            return [TrendPoint(period=row.period, value=row.total_spent) for row in monthly]

        if metric in {"payments_paid", "payments_pending"}:
            keys = _month_keys(12)
            values = {k: 0.0 for k in keys}
            is_paid_metric = metric == "payments_paid"
            orders = list(getattr(self._order_store, "list_orders", lambda: [])() or [])
            for order in orders:
                payments = list(getattr(order, "customer_payments", []) or [])
                for payment in payments:
                    if not isinstance(payment, dict):
                        continue
                    month_key = _parse_month_key(str(payment.get("date", "") or ""))
                    if month_key not in values:
                        continue
                    paid = bool(payment.get("paid", False))
                    if paid != is_paid_metric:
                        continue
                    values[month_key] += _to_float(payment.get("amount", 0.0))
            return [TrendPoint(period=key, value=values[key]) for key in keys]

        return []

    @staticmethod
    def _closed_date_from_history(order: Any) -> date | None:
        history = list(getattr(order, "status_history", []) or [])
        closed_dates: list[date] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            to_status = str(entry.get("to_status", "") or "").strip()
            if not _is_closed_status(to_status):
                continue
            changed_at = _parse_iso_date(entry.get("changed_at", ""))
            if changed_at is not None:
                closed_dates.append(changed_at)
        if not closed_dates:
            return None
        return max(closed_dates)

    @staticmethod
    def _order_deadline_date(order: Any) -> date | None:
        date_end = _parse_iso_date(getattr(order, "date_montaz_end", ""))
        if date_end is not None:
            return date_end
        return _parse_iso_date(getattr(order, "date_montaz", ""))

    @staticmethod
    def _order_has_complaint(order: Any) -> bool:
        notes = str(getattr(order, "notes", "") or "").strip().lower()
        if "reklam" in notes or "complaint" in notes:
            return True
        history = list(getattr(order, "status_history", []) or [])
        for entry in history:
            if not isinstance(entry, dict):
                continue
            note = str(entry.get("note", "") or "").strip().lower()
            to_status = str(entry.get("to_status", "") or "").strip().lower()
            if "reklam" in note or "complaint" in note or "reklam" in to_status:
                return True
        return False

    @staticmethod
    def _resolve_window(range_days: int | None) -> tuple[date | None, date | None]:
        days = int(range_days or 0)
        if days <= 0:
            return None, None
        end_date = date.today()
        start_date = end_date - timedelta(days=max(1, days) - 1)
        return start_date, end_date

    @staticmethod
    def _in_window(value: date | None, start_date: date | None, end_date: date | None) -> bool:
        if value is None:
            return False
        if start_date is None or end_date is None:
            return True
        return start_date <= value <= end_date

    @staticmethod
    def _order_window_anchor(order: Any) -> date | None:
        fields = (
            "date_montaz_end",
            "date_montaz",
            "date_produkcja_end",
            "date_produkcja",
            "date_wycena_end",
            "date_wycena",
            "date_poprawki_end",
            "date_poprawki",
            "date_zakup_mat_end",
            "date_zakup_mat",
        )
        anchors: list[date] = []
        for field in fields:
            parsed = _parse_iso_date(getattr(order, field, ""))
            if parsed is not None:
                anchors.append(parsed)
        if anchors:
            return max(anchors)
        return None

    def _compute_kpi_kri_summary(
        self,
        orders: list[Any],
        total_paid: float,
        total_pending: float,
        range_days: int | None = None,
    ) -> dict[str, Any]:
        today = date.today()
        current_month = (today.year, today.month)
        start_date, end_date = self._resolve_window(range_days)

        revenue_month = 0.0
        has_payment_dates = False
        margins: list[float] = []
        on_time_num = 0
        on_time_den = 0
        closed_orders_count = 0
        rework_orders_count = 0
        complaints_count = 0
        overdue_invoices_value = 0.0

        for order in orders:
            status = str(getattr(order, "status", "") or "").strip()
            is_closed = _is_closed_status(status)
            if is_closed:
                closed_date = self._closed_date_from_history(order) or _parse_iso_date(getattr(order, "date_montaz", ""))
                if start_date is not None and end_date is not None:
                    if self._in_window(closed_date, start_date, end_date):
                        closed_orders_count += 1
                elif closed_date is not None and (closed_date.year, closed_date.month) == current_month:
                    closed_orders_count += 1
                deadline = self._order_deadline_date(order)
                if deadline is not None and closed_date is not None:
                    if start_date is None or end_date is None or self._in_window(closed_date, start_date, end_date):
                        on_time_den += 1
                        if closed_date <= deadline:
                            on_time_num += 1

            if _is_rework_status(status):
                if start_date is not None and end_date is not None:
                    rework_anchor = _parse_iso_date(getattr(order, "date_poprawki", "")) or self._order_window_anchor(order)
                    if self._in_window(rework_anchor, start_date, end_date):
                        rework_orders_count += 1
                else:
                    rework_orders_count += 1
            else:
                rework_date = _parse_iso_date(getattr(order, "date_poprawki", ""))
                if start_date is not None and end_date is not None:
                    if self._in_window(rework_date, start_date, end_date):
                        rework_orders_count += 1
                elif rework_date is not None and (rework_date.year, rework_date.month) == current_month:
                    rework_orders_count += 1

            if self._order_has_complaint(order):
                if start_date is not None and end_date is not None:
                    complaint_in_range = False
                    history = list(getattr(order, "status_history", []) or [])
                    for entry in history:
                        if not isinstance(entry, dict):
                            continue
                        note = str(entry.get("note", "") or "").strip().lower()
                        to_status = str(entry.get("to_status", "") or "").strip().lower()
                        if ("reklam" in note or "complaint" in note or "reklam" in to_status):
                            changed_at = _parse_iso_date(entry.get("changed_at", ""))
                            if self._in_window(changed_at, start_date, end_date):
                                complaint_in_range = True
                                break
                    if not complaint_in_range:
                        complaint_in_range = self._in_window(self._order_window_anchor(order), start_date, end_date)
                    if complaint_in_range:
                        complaints_count += 1
                else:
                    complaints_count += 1

            margin_percent = _to_float(getattr(order, "margin_percent", 0.0))
            if abs(margin_percent) > 0.0001:
                margins.append(margin_percent)
            else:
                price_final = _to_float(getattr(order, "price_final", 0.0))
                price_cost = _to_float(getattr(order, "price_total", 0.0))
                if price_final > 0 and price_cost >= 0:
                    margins.append(max(-100.0, min(100.0, 100.0 * (price_final - price_cost) / price_final)))

            payments = list(getattr(order, "customer_payments", []) or [])
            for payment in payments:
                if not isinstance(payment, dict):
                    continue
                amount = max(0.0, _to_float(payment.get("amount", 0.0)))
                if amount <= 0:
                    continue
                paid = bool(payment.get("paid", False))
                payment_date = _parse_iso_date(payment.get("date", ""))
                if payment_date is not None:
                    has_payment_dates = True
                if paid:
                    if start_date is not None and end_date is not None:
                        if payment_date is None or self._in_window(payment_date, start_date, end_date):
                            revenue_month += amount
                    elif payment_date is not None and (payment_date.year, payment_date.month) == current_month:
                        revenue_month += amount
                else:
                    if payment_date is not None and payment_date < today:
                        if start_date is None or end_date is None or self._in_window(payment_date, start_date, end_date):
                            overdue_invoices_value += amount

        if not has_payment_dates:
            # Fallback for legacy rows without payment dates.
            revenue_month = total_paid
            overdue_invoices_value = total_pending

        avg_margin_percent = (sum(margins) / len(margins)) if margins else 0.0
        on_time_rate_percent = (100.0 * on_time_num / on_time_den) if on_time_den > 0 else 0.0
        if start_date is not None and end_date is not None:
            period = f"{start_date.isoformat()}..{end_date.isoformat()}"
        else:
            period = f"{today.year:04d}-{today.month:02d}"

        return {
            "kpi": {
                "revenue_month": revenue_month,
                "avg_margin_percent": avg_margin_percent,
                "on_time_rate_percent": on_time_rate_percent,
                "closed_orders_count": closed_orders_count,
            },
            "kri": {
                "rework_orders_count": rework_orders_count,
                "overdue_invoices_value": overdue_invoices_value,
                "complaints_count": complaints_count,
            },
            "meta": {
                "period": period,
                "on_time_sample_size": on_time_den,
                "range_days": int(range_days or 0),
            },
        }

    def _compute_dashboard_payload(self, range_days: int | None = None) -> dict[str, Any]:
        orders = list(getattr(self._order_store, "list_orders", lambda: [])() or [])
        active_orders = [o for o in orders if str(getattr(o, "status", "") or "").strip().lower() != "zakonczone"]
        start_date, end_date = self._resolve_window(range_days)

        total_paid = 0.0
        total_pending = 0.0
        order_payments: list[tuple[str, float, float]] = []
        for order in orders:
            payments = list(getattr(order, "customer_payments", []) or [])
            paid = 0.0
            pending = 0.0
            for payment in payments:
                if not isinstance(payment, dict):
                    continue
                amount = _to_float(payment.get("amount", 0.0))
                if amount <= 0:
                    continue
                payment_date = _parse_iso_date(payment.get("date", ""))
                if start_date is not None and end_date is not None and payment_date is not None:
                    if not self._in_window(payment_date, start_date, end_date):
                        continue
                if bool(payment.get("paid", False)):
                    paid += amount
                else:
                    pending += amount
            total_paid += paid
            total_pending += pending
            if (paid + pending) > 0:
                label = str(getattr(order, "client_name", "") or getattr(order, "code", "") or "-")
                order_payments.append((label, paid, pending))
        order_payments.sort(key=lambda row: (row[1] + row[2]), reverse=True)

        fixed_items = list(getattr(self._expenses_store, "list_items", lambda _s, _d: [])("fixed", []) or [])
        variable_items = list(getattr(self._expenses_store, "list_items", lambda _s, _d: [])("variable", []) or [])
        fixed_total = sum(_to_float(row.get("amount", 0.0)) for row in fixed_items if isinstance(row, dict))
        variable_total = sum(_to_float(row.get("amount", 0.0)) for row in variable_items if isinstance(row, dict))
        monthly_costs = fixed_total + variable_total
        workers_count = len(list(getattr(self._worker_store, "list_workers", lambda: [])() or []))
        real_hour = dict(getattr(self._expenses_store, "real_hour_metrics", lambda **_k: {})(
            workers_fallback=max(1, workers_count),
            hours_fallback=160.0,
        ) or {})

        services = list(getattr(self._service_store, "list_services", lambda: [])() or [])
        total_services = len(services)
        with_deadline = 0
        overdue_services = 0
        today = date.today()
        for svc in services:
            deadline = str(getattr(svc, "deadline", "") or "").strip()
            if not deadline:
                continue
            try:
                due = date.fromisoformat(deadline)
            except ValueError:
                continue
            with_deadline += 1
            if due < today:
                overdue_services += 1

        alarms = list(getattr(self._alarm_store, "list_alarms", lambda: [])() or [])
        active_alarms = [alarm for alarm in alarms if not bool(getattr(alarm, "is_resolved", False))]
        critical_count = len([alarm for alarm in active_alarms if str(getattr(alarm, "severity", "") or "") == "krytyczny"])
        warning_count = len([alarm for alarm in active_alarms if str(getattr(alarm, "severity", "") or "") == "ostrzezenie"])

        monthly_purchases = self.get_monthly_purchases(12)
        monthly_totals = [row.total_spent for row in monthly_purchases]
        payments_paid_monthly = [row.value for row in self.get_trend("payments_paid", period="monthly")]
        payments_pending_monthly = [row.value for row in self.get_trend("payments_pending", period="monthly")]
        if start_date is not None and end_date is not None:
            shopping_current_month = 0.0
            items = list(getattr(self._shopping_store, "list_items", lambda: [])() or [])
            for item in items:
                if str(getattr(item, "status", "") or "").strip().lower() != "zakupiono":
                    continue
                added_date = _parse_iso_date(getattr(item, "added_date", ""))
                if not self._in_window(added_date, start_date, end_date):
                    continue
                qty = max(0.0, _to_float(getattr(item, "quantity_needed", 0.0)))
                shopping_current_month += max(0.0, _to_float(getattr(item, "price_actual", 0.0))) * qty
        else:
            shopping_current_month = monthly_totals[-1] if monthly_totals else 0.0

        supplier_kpis = self.get_supplier_kpis()
        supplier_trends: dict[str, list[float]] = {}
        if hasattr(self._shopping_store, "monthly_supplier_trends"):
            try:
                raw = self._shopping_store.monthly_supplier_trends(months=12)
                if isinstance(raw, dict):
                    for supplier, values in raw.items():
                        if isinstance(values, list):
                            supplier_trends[str(supplier or "").strip() or "<nieznany>"] = [
                                _to_float(v) for v in values
                            ]
            except Exception:
                supplier_trends = {}

        status_counts: dict[str, int] = {}
        worker_counts: dict[str, int] = {}
        for order in active_orders:
            status = str(getattr(order, "status", "") or "Nowe").strip()
            status_counts[status] = status_counts.get(status, 0) + 1
            worker = str(getattr(order, "worker_name", "") or "- brak -").strip() or "- brak -"
            worker_counts[worker] = worker_counts.get(worker, 0) + 1

        donut_data: list[tuple[str, float]] = []
        for item in fixed_items + variable_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            amount = _to_float(item.get("amount", 0.0))
            if name and amount > 0:
                donut_data.append((name, amount))
        donut_data.sort(key=lambda row: row[1], reverse=True)

        kpi_kri = self._compute_kpi_kri_summary(
            orders=orders,
            total_paid=total_paid,
            total_pending=total_pending,
            range_days=range_days,
        )

        return {
            "total_paid": total_paid,
            "total_pending": total_pending,
            "orders_total": len(orders),
            "orders_active": len(active_orders),
            "orders_with_paid": len([o for o in orders if any(bool(p.get("paid")) for p in (getattr(o, "customer_payments", []) or []) if isinstance(p, dict))]),
            "order_payments": order_payments,
            "fixed_total": fixed_total,
            "variable_total": variable_total,
            "monthly_costs": monthly_costs,
            "real_hour": real_hour,
            "services_total": total_services,
            "services_with_deadline": with_deadline,
            "services_overdue": overdue_services,
            "alarms_active": len(active_alarms),
            "alarms_critical": critical_count,
            "alarms_warning": warning_count,
            "shopping_current_month": shopping_current_month,
            "shopping_monthly_totals": monthly_totals,
            "payments_paid_monthly": payments_paid_monthly,
            "payments_pending_monthly": payments_pending_monthly,
            "supplier_kpis": supplier_kpis,
            "supplier_trends": supplier_trends,
            "status_counts": status_counts,
            "worker_counts": worker_counts,
            "donut_data": donut_data,
            "kpi_kri": kpi_kri,
            "meta": {
                "range_days": int(range_days or 0),
                "range_from": start_date.isoformat() if start_date else "",
                "range_to": end_date.isoformat() if end_date else "",
            },
        }
