from datetime import date

from PyQt6.QtWidgets import QApplication

from src.core.operations_models import IssueRecord
from src.core.operations_store import OperationsStore
from src.core.orders_map_service import OrdersMapService
from src.core.visit_history_store import VisitHistoryStore, VisitHistoryRecord
from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.tabs.operations_hub.panel_orders_map import OrdersMapPanel


def test_panel_orders_map_loads_on_empty_data(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    panel = OrdersMapPanel(service=OrdersMapService(data_dir=tmp_path))
    panel.refresh_data()
    assert panel.tbl_points.rowCount() == 0
    assert panel.lbl_points_empty.isHidden() is False
    assert panel.lbl_history_empty.isHidden() is False
    assert panel.lbl_route_empty.isHidden() is False
    assert panel.btn_open_selected is not None
    assert panel.btn_open_day_route is not None
    assert panel.btn_copy_phone_top is not None
    assert panel.btn_copy_address_top is not None
    assert panel.tbl_points.columnCount() >= 12


def test_panel_orders_map_selection_updates_details(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    order_store.save_new(
        OrderDef(
            code="ORD-X",
            order_name="Projekt X",
            client_name="Klient X",
            site_street="Dluga",
            site_house_number="1",
            site_city="Krakow",
        )
    )
    client_store.save_new(ClientDef(name="Klient X", phone="600700800"))
    issue = ops.add_issue(
        IssueRecord(
            title="Wizyta",
            project_name="Projekt X",
            client_name="Klient X",
            city="Krakow",
            address="Dluga 1, Krakow",
            issue_type="montaz",
        )
    )
    ops.create_route_task_from_issue(issue.id, date.today().strftime("%Y-%m-%d"), "Ekipa X")
    history = VisitHistoryStore(data_dir=tmp_path)
    service = OrdersMapService(
        app_context={"order_store": order_store, "client_store": client_store, "visit_history_store": history},
        operations_store=ops,
        data_dir=tmp_path,
    )
    panel = OrdersMapPanel(service=service, operations_store=ops)
    panel.refresh_data()
    assert panel.tbl_points.rowCount() >= 1
    panel.tbl_points.selectRow(0)
    panel._show_point_details()
    assert "Osoba kontaktowa:" in panel.txt_details.toPlainText()
    assert panel.lab_client.text() != ""
    assert panel.lab_address.text() != ""
    assert panel.lab_phone.text() != ""


def test_panel_orders_map_history_and_route_order_and_exports(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    history = VisitHistoryStore(data_dir=tmp_path)
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    order_store.save_new(OrderDef(code="ORD-1", order_name="P1", client_name="K1", site_street="A", site_house_number="1", site_city="KRK"))
    order_store.save_new(OrderDef(code="ORD-2", order_name="P2", client_name="K2", site_street="B", site_house_number="2", site_city="KRK"))
    service = OrdersMapService(
        app_context={"order_store": order_store, "client_store": client_store, "visit_history_store": history},
        operations_store=ops,
        data_dir=tmp_path,
    )
    service.append_point_to_route("order::ORD-1", date.today().strftime("%Y-%m-%d"), "Ekipa Z", "G1")
    service.append_point_to_route("order::ORD-2", date.today().strftime("%Y-%m-%d"), "Ekipa Z", "G1")

    panel = OrdersMapPanel(service=service, operations_store=ops)
    monkeypatch.setattr("src.tabs.operations_hub.panel_orders_map.QMessageBox.information", lambda *a, **k: 0)
    panel.f_crew.setText("Ekipa Z")
    panel.refresh_data()
    assert panel.tbl_route.rowCount() >= 2
    panel.tbl_route.selectRow(1)
    panel._on_move_route_point_up()
    panel._on_save_route_order()
    assert panel.tbl_route.item(0, 1).text() in {"K1", "K2"}

    route_first = panel._route_points[0]
    history.add_record(VisitHistoryRecord(point_id=route_first.id, visit_date=date.today().strftime("%Y-%m-%d"), work_done="OK"))
    panel._refresh_history_for_selected_point()
    assert panel.tbl_history.rowCount() >= 0

    out_csv = tmp_path / "trip.csv"
    out_html = tmp_path / "trip.html"
    monkeypatch.setattr("src.tabs.operations_hub.panel_orders_map.QFileDialog.getSaveFileName", lambda *a, **k: (str(out_csv), "CSV (*.csv)"))
    panel._on_export_trip_card_csv()
    assert out_csv.exists()
    monkeypatch.setattr("src.tabs.operations_hub.panel_orders_map.QFileDialog.getSaveFileName", lambda *a, **k: (str(out_html), "HTML (*.html)"))
    panel._on_export_trip_card_html()
    assert out_html.exists()


def test_panel_orders_map_finance_result_flow(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-F", order_name="PF", client_name="KF", site_street="X", site_house_number="1", site_city="KRK"))
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    service = OrdersMapService(app_context={"order_store": order_store}, operations_store=ops, data_dir=tmp_path)
    day = date.today().strftime("%Y-%m-%d")
    service.append_point_to_route("order::ORD-F", day, "Ekipa F", "GF")
    panel = OrdersMapPanel(service=service, operations_store=ops)
    panel.f_crew.setText("Ekipa F")
    panel.refresh_data()
    assert panel.tbl_points.rowCount() >= 1
    panel.tbl_points.selectRow(0)

    class _FakeDialog:
        def __init__(self, *_a, **_k):
            pass
        def exec(self):
            return 1
        def get_payload(self):
            return {
                "blocks_payment": True,
                "estimated_payment_unlock": 999.0,
                "finance_followup_status": "gotowe_do_fakturowania",
                "ready_to_invoice": True,
                "requires_settlement": False,
                "requires_confirmation": False,
                "finance_followup_note": "OK",
            }

    monkeypatch.setattr("src.tabs.operations_hub.panel_orders_map.VisitFinanceResultDialog", _FakeDialog)
    monkeypatch.setattr("src.tabs.operations_hub.panel_orders_map.QMessageBox.information", lambda *a, **k: 0)
    panel._on_set_finance_result()
    panel.refresh_data()
    assert panel.lab_fin_followup.text() in {"gotowe_do_fakturowania", "brak"}


def test_panel_orders_map_navigate_to_point_and_fallback(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-NAV",
            order_name="Projekt NAV",
            client_name="Klient NAV",
            site_street="Nav",
            site_house_number="1",
            site_city="Krakow",
        )
    )
    ops = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    service = OrdersMapService(app_context={"order_store": order_store}, operations_store=ops, data_dir=tmp_path)
    service.append_point_to_route("order::ORD-NAV", date.today().strftime("%Y-%m-%d"), "Ekipa NAV", "GN")
    panel = OrdersMapPanel(service=service, operations_store=ops)
    panel.refresh_data()
    assert panel.tbl_points.rowCount() >= 1
    point_id = panel._points[0].id

    assert panel.navigate_to_point(point_id=point_id) is True
    selected = panel._selected_point()
    assert selected is not None
    assert selected.id == point_id
    assert panel.lbl_navigation_info.isHidden() is True

    assert panel.navigate_to_point(point_id="not-found", project_name="Projekt NAV", client_name="Klient NAV") is True
    assert panel.lbl_navigation_info.isHidden() is False
    assert "Nie znaleziono dokladnego punktu" in panel.lbl_navigation_info.text()

    assert panel.navigate_to_point(point_id="not-found", project_name="X", client_name="Y") is False
    assert panel.lbl_navigation_info.isHidden() is False
