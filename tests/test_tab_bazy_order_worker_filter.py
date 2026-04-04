from PyQt6.QtWidgets import QApplication


def test_tab_bazy_orders_worker_filter_filters_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import ORDER_STATUS_FILTER_ALL, ORDER_WORKER_FILTER_ALL, TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-A", client_name="Klient A", worker_name="Jan", status="Nowe", site_address="A"))
    order_store.save_new(
        OrderDef(code="ORD-B", client_name="Klient B", worker_name="Anna", status="W produkcji", site_address="B")
    )

    w = TabBazy(order_store=order_store)

    idx_all_status = w.cb_order_status_filter.findData(ORDER_STATUS_FILTER_ALL)
    idx_all_worker = w.cb_order_worker_filter.findData(ORDER_WORKER_FILTER_ALL)
    assert idx_all_status >= 0
    assert idx_all_worker >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_all_status)
    w.cb_order_worker_filter.setCurrentIndex(idx_all_worker)
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 2

    idx_jan = w.cb_order_worker_filter.findData("Jan")
    assert idx_jan >= 0
    w.cb_order_worker_filter.setCurrentIndex(idx_jan)
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-A"
    assert "pracownik: Jan" in w.lab_order_filter_active.text()

    idx_prod = w.cb_order_status_filter.findData("W produkcji")
    assert idx_prod >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_prod)
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 0
    assert "status: W produkcji" in w.lab_order_filter_active.text()
    assert "pracownik: Jan" in w.lab_order_filter_active.text()


def test_tab_bazy_orders_worker_filter_includes_worker_from_existing_order_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-C",
            client_name="Klient C",
            worker_name="Monter Zmiana B",
            status="Nowe",
            site_address="C",
        )
    )

    w = TabBazy(order_store=order_store)
    w._reload_orders_tab()

    idx_worker = w.cb_order_worker_filter.findData("Monter Zmiana B")
    assert idx_worker >= 0
    w.cb_order_worker_filter.setCurrentIndex(idx_worker)
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 1
    assert w.tbl_orders.item(0, 0).text() == "ORD-C"


def test_tab_bazy_clear_order_filters_restores_full_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import ORDER_STATUS_FILTER_ALL, ORDER_WORKER_FILTER_ALL, TabBazy

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-A", client_name="Klient A", worker_name="Jan", status="Nowe", site_address="A"))
    order_store.save_new(
        OrderDef(code="ORD-B", client_name="Klient B", worker_name="Anna", status="W produkcji", site_address="B")
    )

    w = TabBazy(order_store=order_store)

    idx_status = w.cb_order_status_filter.findData("W produkcji")
    idx_worker = w.cb_order_worker_filter.findData("Anna")
    assert idx_status >= 0
    assert idx_worker >= 0
    w.cb_order_status_filter.setCurrentIndex(idx_status)
    w.cb_order_worker_filter.setCurrentIndex(idx_worker)
    w.ed_order_query_filter.setText("anna")
    w._reload_orders_tab()
    assert w.tbl_orders.rowCount() == 1

    w._clear_order_filters()
    assert w.tbl_orders.rowCount() == 2
    assert w.cb_order_status_filter.currentData() == ORDER_STATUS_FILTER_ALL
    assert w.cb_order_worker_filter.currentData() == ORDER_WORKER_FILTER_ALL
    assert w.ed_order_query_filter.text() == ""
    assert w.lab_order_filter_active.text() == "Filtry: brak"
