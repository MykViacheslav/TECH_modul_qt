from datetime import date

from src.core.operations_finance_adapter import get_finance_kpis, list_operations_ready_for_finance
from src.core.operations_store import OperationsStore
from src.core.orders_map_service import OrdersMapService
from src.domain.order_models import OrderDef
from src.storage.order_store_json import OrderStoreJson


def test_operations_finance_adapter_returns_relevant_rows(tmp_path):
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-FA", order_name="PFA", client_name="KFA", site_street="A", site_house_number="1", site_city="KRK"))
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    svc = OrdersMapService(app_context={"order_store": order_store}, operations_store=ops, data_dir=tmp_path)
    day = date.today().strftime("%Y-%m-%d")
    svc.append_point_to_route("order::ORD-FA", day, "Ekipa F", "GF")
    p = svc.build_route_points_for_day(day, "Ekipa F")[0]
    svc.mark_point_finance_result(
        point_id=p.id,
        finance_followup_status="gotowe_do_fakturowania",
        estimated_payment_unlock=500.0,
        ready_to_invoice=True,
        requires_settlement=False,
        requires_confirmation=False,
        finance_followup_note="OK",
    )
    rows = list_operations_ready_for_finance(svc)
    assert len(rows) >= 1
    assert rows[0]["ready_to_invoice"] is True


def test_operations_finance_adapter_kpis(tmp_path):
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-KPI",
            order_name="PKPI",
            client_name="KPI Client",
            site_street="A",
            site_house_number="1",
            site_city="KRK",
        )
    )
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    svc = OrdersMapService(app_context={"order_store": order_store}, operations_store=ops, data_dir=tmp_path)
    day = date.today().strftime("%Y-%m-%d")
    svc.append_point_to_route("order::ORD-KPI", day, "Ekipa KPI", "GK")
    p = svc.build_route_points_for_day(day, "Ekipa KPI")[0]
    svc.mark_point_finance_result(
        point_id=p.id,
        finance_followup_status="wymaga_rozliczenia",
        estimated_payment_unlock=250.0,
        ready_to_invoice=False,
        requires_settlement=True,
        requires_confirmation=False,
        finance_followup_note="KPI",
    )
    rows = list_operations_ready_for_finance(svc)
    kpi = get_finance_kpis(rows=rows)
    assert int(kpi["ready_to_invoice_count"]) == 0
    assert int(kpi["requires_settlement_count"]) == 1
    assert int(kpi["blocks_payment_count"]) == 1
    assert float(kpi["estimated_payment_unlock_total"]) == 250.0
