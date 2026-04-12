from __future__ import annotations

from datetime import date
from typing import Any


def _priority_rank(value: str) -> int:
    mapping = {"krytyczny": 3, "wysoki": 2, "normalny": 1, "niski": 0}
    return mapping.get(str(value or "normalny").strip().lower(), 1)


def build_daily_report(rows: list[dict], today: date | None = None, top_limit: int = 10) -> dict[str, Any]:
    today_d = today or date.today()
    tomorrow = date.fromordinal(today_d.toordinal() + 1).isoformat()
    safe_rows = [dict(x) for x in rows if isinstance(x, dict)]
    active_rows = [
        x
        for x in safe_rows
        if not bool(x.get("financially_closed", False)) and str(x.get("office_status", "")) != "domkniete_finansowo"
    ]
    summary = {
        "today_count": sum(1 for x in safe_rows if bool(x.get("action_due_today", False))),
        "tomorrow_count": sum(1 for x in safe_rows if str(x.get("next_action_date", "") or "") == tomorrow),
        "overdue_count": sum(1 for x in safe_rows if bool(x.get("action_overdue", False))),
        "snoozed_count": sum(1 for x in safe_rows if bool(x.get("is_snoozed", False))),
        "high_priority_count": sum(1 for x in safe_rows if str(x.get("office_priority", "")) in {"krytyczny", "wysoki"}),
        "blocks_payment_count": sum(
            1
            for x in safe_rows
            if bool(x.get("blocks_payment", False)) or float(x.get("estimated_payment_unlock", 0.0) or 0.0) > 0
        ),
        "ready_to_invoice_count": sum(1 for x in safe_rows if bool(x.get("ready_to_invoice", False))),
        "requires_settlement_count": sum(1 for x in safe_rows if bool(x.get("requires_settlement", False))),
        "requires_confirmation_count": sum(1 for x in safe_rows if bool(x.get("requires_confirmation", False))),
        "active_amount_total": sum(float(x.get("estimated_payment_unlock", 0.0) or 0.0) for x in active_rows),
    }

    def _sort_key(x: dict) -> tuple:
        return (
            1 if bool(x.get("action_overdue", False)) else 0,
            1 if bool(x.get("action_due_today", False)) else 0,
            1 if bool(x.get("needs_attention_today", False)) else 0,
            _priority_rank(str(x.get("office_priority", "normalny"))),
            float(x.get("estimated_payment_unlock", 0.0) or 0.0),
        )

    sorted_rows = sorted(safe_rows, key=_sort_key, reverse=True)
    top_items = sorted_rows[: max(1, int(top_limit or 10))]
    contact_items = [x for x in sorted_rows if bool(x.get("needs_contact", False))]
    check_items = [x for x in sorted_rows if bool(x.get("needs_check", False))]

    return {
        "report_date": today_d.isoformat(),
        "summary": summary,
        "top_items": top_items,
        "contact_items": contact_items,
        "check_items": check_items,
    }


def build_daily_summary_text(report: dict[str, Any]) -> str:
    summary = dict(report.get("summary", {}) or {})
    return (
        f"Na dzis: {int(summary.get('today_count', 0) or 0)}\n"
        f"Na jutro: {int(summary.get('tomorrow_count', 0) or 0)}\n"
        f"Po terminie: {int(summary.get('overdue_count', 0) or 0)}\n"
        f"Odlozone: {int(summary.get('snoozed_count', 0) or 0)}\n"
        f"Wysoki priorytet: {int(summary.get('high_priority_count', 0) or 0)}\n"
        f"Odblokowuje platnosc: {int(summary.get('blocks_payment_count', 0) or 0)}\n"
        f"Gotowe do fakturowania: {int(summary.get('ready_to_invoice_count', 0) or 0)}\n"
        f"Wymaga rozliczenia: {int(summary.get('requires_settlement_count', 0) or 0)}\n"
        f"Czeka na potwierdzenie: {int(summary.get('requires_confirmation_count', 0) or 0)}\n"
        f"Laczna kwota aktywna: {float(summary.get('active_amount_total', 0.0) or 0.0):.2f} zl"
    )
