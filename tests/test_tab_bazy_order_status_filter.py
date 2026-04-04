from PyQt6.QtWidgets import QApplication


def test_tab_bazy_orders_status_filter_filters_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import ORDER_STATUS_FILTER_ALL, TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-A", client_name="Klient A", status="Nowe", site_address="A"))
    order_store.save_new(OrderDef(code="ORD-B", client_name="Klient B", status="W produkcji", site_address="B"))

    w = TabBazy(order_store=order_store)

    idx_all = w.cb_order_status_filter.findData(ORDER_STATUS_FILTER_ALL)
    assert idx_all >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_all)
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 2
    assert "2 / 2" in w.lab_order_filter_info.text()
    assert w.lab_order_filter_active.text() == "Filtry: brak"

    idx_prod = w.cb_order_status_filter.findData("W produkcji")
    assert idx_prod >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_prod)
    w._reload_orders_tab()

    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-B"
    assert w.tbl_orders.item(0, 2).text() == "W produkcji"
    assert "1 / 2" in w.lab_order_filter_info.text()
    assert "status: W produkcji" in w.lab_order_filter_active.text()


def test_tab_bazy_orders_status_filter_includes_custom_status_from_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(code="ORD-C", client_name="Klient C", status="Do odbioru CNC", site_address="C")
    )

    w = TabBazy(order_store=order_store)
    w._reload_orders_tab()

    idx_custom = w.cb_order_status_filter.findData("Do odbioru CNC")
    assert idx_custom >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_custom)
    w._reload_orders_tab()

    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-C"


def test_tab_bazy_orders_default_sort_puts_active_before_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import ORDER_STATUS_FILTER_ALL, TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-90", client_name="Klient C", status="Zakonczone", site_address="C"))
    order_store.save_new(OrderDef(code="ORD-10", client_name="Klient A", status="Nowe", site_address="A"))
    order_store.save_new(OrderDef(code="ORD-20", client_name="Klient B", status="W produkcji", site_address="B"))
    order_store.save_new(OrderDef(code="ORD-30", client_name="Klient D", status="Gotowe", site_address="D"))

    w = TabBazy(order_store=order_store)
    idx_all = w.cb_order_status_filter.findData(ORDER_STATUS_FILTER_ALL)
    assert idx_all >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_all)
    w._reload_orders_tab()

    codes = [w.tbl_orders.item(row, 0).text() for row in range(w.tbl_orders.rowCount())]
    assert codes == ["ORD-10", "ORD-20", "ORD-30", "ORD-90"]


def test_tab_bazy_orders_query_filter_matches_client_and_address(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-A", client_name="Klient Alfa", status="Nowe", site_address="Warszawa"))
    order_store.save_new(OrderDef(code="ORD-B", client_name="Klient Beta", status="Nowe", site_address="Gdansk"))

    w = TabBazy(order_store=order_store)
    w.ed_order_query_filter.setText("gdan")
    w._reload_orders_tab()

    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-B"
    assert "szukaj: gdan" in w.lab_order_filter_active.text()


def test_tab_bazy_open_orders_tab_focuses_requested_code(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-100", client_name="Klient A", status="Nowe", site_address="A"))
    order_store.save_new(OrderDef(code="ORD-200", client_name="Klient B", status="W produkcji", site_address="B"))

    w = TabBazy(order_store=order_store)
    idx_new = w.cb_order_status_filter.findData("Nowe")
    assert idx_new >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_new)
    w.ed_order_query_filter.setText("ORD-100")
    assert w.open_orders_tab(clear_form=False, focus_code="ORD-200") is True

    selected_rows = w.tbl_orders.selectionModel().selectedRows() if w.tbl_orders.selectionModel() is not None else []
    assert len(selected_rows) == 1
    row = int(selected_rows[0].row())
    assert w.tbl_orders.item(row, 0).text() == "ORD-200"
    assert w.ed_order_code.text() == "ORD-200"
    assert w.cb_order_client.currentText() == "Klient B"
    assert w.cb_order_status_filter.currentData() == "Wszystkie"
    assert w.ed_order_query_filter.text() == ""


def test_tab_bazy_orders_query_filter_matches_order_id_and_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-500",
            order_id="Q500",
            order_name="Oferta kuchnia premium",
            client_name="Klient A",
            status="Nowe",
            site_address="A",
        )
    )
    order_store.save_new(
        OrderDef(
            code="ORD-600",
            order_id="Q600",
            order_name="Oferta szafa",
            client_name="Klient B",
            status="Nowe",
            site_address="B",
        )
    )

    w = TabBazy(order_store=order_store)
    w.ed_order_query_filter.setText("q500")
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-500"

    w.ed_order_query_filter.setText("premium")
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-500"
