from __future__ import annotations

from src.core.orders_map_service import OrdersMapService


def list_operations_ready_for_finance(service: OrdersMapService | None = None) -> list[dict]:
    svc = service or OrdersMapService()
    rows = []
    for p in svc.list_map_points():
        if not (p.ready_to_invoice or p.requires_settlement or p.requires_confirmation or p.blocks_payment):
            continue
        rows.append(
            {
                "point_id": p.id,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "full_address": p.full_address,
                "visit_status": p.visit_status,
                "finance_followup_status": p.finance_followup_status,
                "estimated_payment_unlock": float(p.estimated_payment_unlock or 0.0),
                "ready_to_invoice": bool(p.ready_to_invoice),
                "requires_settlement": bool(p.requires_settlement),
                "requires_confirmation": bool(p.requires_confirmation),
                "blocks_payment": bool(p.blocks_payment),
                "last_visit_at": p.last_visit_at,
                "last_finance_result": p.last_finance_result,
                "finance_followup_note": p.finance_followup_note,
            }
        )
    return rows


def get_finance_kpis(rows: list[dict] | None = None, service: OrdersMapService | None = None) -> dict[str, float]:
    data = list(rows or list_operations_ready_for_finance(service=service))
    return {
        "ready_to_invoice_count": float(sum(1 for x in data if bool(x.get("ready_to_invoice", False)))),
        "requires_settlement_count": float(sum(1 for x in data if bool(x.get("requires_settlement", False)))),
        "requires_confirmation_count": float(sum(1 for x in data if bool(x.get("requires_confirmation", False)))),
        "blocks_payment_count": float(
            sum(
                1
                for x in data
                if bool(x.get("blocks_payment", False))
                or float(x.get("estimated_payment_unlock", 0.0) or 0.0) > 0.0
            )
        ),
        "estimated_payment_unlock_total": float(sum(float(x.get("estimated_payment_unlock", 0.0) or 0.0) for x in data)),
    }
