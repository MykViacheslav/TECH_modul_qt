from datetime import date

from src.core.mymaps_export import export_map_points_to_csv
from src.core.operations_models import IssueRecord
from src.core.operations_store import OperationsStore
from src.core.orders_map_service import OrdersMapService
from src.core.visit_history_store import VisitHistoryStore, VisitHistoryRecord
from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_store_json import OrderStoreJson


def test_orders_map_service_points_filter_and_route_url(tmp_path):
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    order_store.save_new(
        OrderDef(
            code="ORD-1",
            order_name="Projekt 1",
            client_name="Klient A",
            worker_name="Ekipa A",
            site_street="Kwiatowa",
            site_house_number="10",
            site_city="Krakow",
            site_postal_code="30-001",
            notes="Zakres robot",
        )
    )
    client_store.save_new(ClientDef(name="Klient A", phone="123456789", city="Krakow"))

    issue = ops.add_issue(
        IssueRecord(
            title="Montaż",
            project_name="Projekt 1",
            client_name="Klient A",
            city="Krakow",
            address="Kwiatowa 10, Krakow",
            issue_type="montaz",
            status="nowe",
        )
    )
    ops.create_route_task_from_issue(issue.id, date.today().strftime("%Y-%m-%d"), "Ekipa A", "KRK-A")

    service = OrdersMapService(
        app_context={"order_store": order_store, "client_store": client_store},
        operations_store=ops,
        data_dir=tmp_path,
    )
    points = service.list_map_points()
    assert len(points) >= 2

    filtered = service.filter_map_points(city="krakow", crew="ekipa a")
    assert len(filtered) >= 1

    route_url = service.build_google_maps_route_for_day(date.today().strftime("%Y-%m-%d"), crew="Ekipa A")
    assert "google.com/maps/dir" in route_url


def test_export_mymaps_csv(tmp_path):
    service = OrdersMapService(data_dir=tmp_path)
    points = service.list_map_points()
    out = tmp_path / "mymaps.csv"
    export_map_points_to_csv(points, str(out))
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Name,Description,Address,City,Phone" in text


def test_append_reorder_and_mark_done(tmp_path):
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    history = VisitHistoryStore(data_dir=tmp_path)
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    order_store.save_new(
        OrderDef(code="ORD-A", order_name="Projekt A", client_name="Klient A", site_street="A", site_house_number="1", site_city="Krakow")
    )
    order_store.save_new(
        OrderDef(code="ORD-B", order_name="Projekt B", client_name="Klient B", site_street="B", site_house_number="2", site_city="Krakow")
    )
    client_store.save_new(ClientDef(name="Klient A", phone="111"))
    client_store.save_new(ClientDef(name="Klient B", phone="222"))

    service = OrdersMapService(
        app_context={"order_store": order_store, "client_store": client_store, "visit_history_store": history},
        operations_store=ops,
        data_dir=tmp_path,
    )
    day = date.today().strftime("%Y-%m-%d")
    service.append_point_to_route("order::ORD-A", day, "Ekipa X", "G1")
    service.append_point_to_route("order::ORD-B", day, "Ekipa X", "G1")
    points = service.build_route_points_for_day(day, "Ekipa X")
    assert len(points) == 2

    ordered_ids = [points[1].id, points[0].id]
    service.reorder_route_points("G1", ordered_ids)
    points2 = service.build_route_points_for_day(day, "Ekipa X")
    assert points2[0].id == ordered_ids[0]

    service.mark_point_done(points2[0].id, day, "Ekipa X")
    points3 = service.build_route_points_for_day(day, "Ekipa X")
    done = [p for p in points3 if p.id == points2[0].id][0]
    assert done.visit_status == "wykonane"

    history.add_record(
        VisitHistoryRecord(
            point_id=points3[0].id,
            visit_date=day,
            status_after="wykonane",
            notes="Wykonane poprawnie",
        )
    )
    points4 = service.list_map_points()
    target = [p for p in points4 if p.id == points3[0].id][0]
    assert target.has_history is True

    service.mark_point_finance_result(
        point_id=target.id,
        finance_followup_status="gotowe_do_fakturowania",
        estimated_payment_unlock=1500.0,
        ready_to_invoice=True,
        requires_settlement=False,
        requires_confirmation=False,
        finance_followup_note="Mozna wystawic",
    )
    updated = [p for p in service.list_map_points() if p.id == target.id][0]
    assert updated.ready_to_invoice is True
    assert updated.blocks_payment is True
    assert updated.finance_followup_status == "gotowe_do_fakturowania"
    assert len(service.get_points_ready_to_invoice()) >= 1
    assert len(service.get_points_blocking_payment()) >= 1

    filtered = service.filter_map_points(only_ready_to_invoice=True)
    assert any(p.id == target.id for p in filtered)
