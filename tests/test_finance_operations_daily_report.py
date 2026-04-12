from datetime import date

from src.core.finance_operations_daily_report import build_daily_report, build_daily_summary_text


def test_build_daily_report_summary_and_top_items():
    rows = [
        {
            "point_id": "r1",
            "project_name": "P1",
            "client_name": "C1",
            "action_due_today": True,
            "action_overdue": False,
            "is_snoozed": False,
            "office_priority": "wysoki",
            "blocks_payment": True,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "estimated_payment_unlock": 1000.0,
            "financially_closed": False,
            "next_action_date": date.today().isoformat(),
        },
        {
            "point_id": "r2",
            "project_name": "P2",
            "client_name": "C2",
            "action_due_today": False,
            "action_overdue": True,
            "is_snoozed": False,
            "office_priority": "krytyczny",
            "blocks_payment": True,
            "ready_to_invoice": False,
            "requires_settlement": True,
            "requires_confirmation": True,
            "estimated_payment_unlock": 2500.0,
            "financially_closed": False,
            "next_action_date": date.fromordinal(date.today().toordinal() - 1).isoformat(),
        },
    ]
    report = build_daily_report(rows)
    summary = report["summary"]
    assert int(summary["today_count"]) >= 1
    assert int(summary["overdue_count"]) >= 1
    assert int(summary["high_priority_count"]) == 2
    assert int(summary["blocks_payment_count"]) == 2
    assert float(summary["active_amount_total"]) == 3500.0
    assert len(report["top_items"]) >= 2
    text = build_daily_summary_text(report)
    assert "Na dzis:" in text
    assert "Po terminie:" in text
