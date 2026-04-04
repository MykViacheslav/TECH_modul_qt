from datetime import datetime

from PyQt6.QtWidgets import QApplication


def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def test_tab_bazy_order_add_sets_stage_dates_for_wycena_gotowa(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])
    _ = app

    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    store = OrderStoreJson(path=tmp_path / "orders.json")
    w = TabBazy(order_store=store)
    w.ed_order_code.setText("ORD-DATE-ADD-1")
    w.cb_order_client.setCurrentText("Klient A")
    idx = w.cb_order_status.findText("Wycena gotowa")
    assert idx >= 0
    w.cb_order_status.setCurrentIndex(idx)
    w._on_order_add()

    saved = store.get("ORD-DATE-ADD-1")
    assert saved is not None
    assert saved.status == "Wycena gotowa"
    assert saved.date_wycena == _today_iso()
    assert saved.date_wycena_end == _today_iso()
    assert len(saved.status_history) >= 1
    assert saved.status_history[-1]["to_status"] == "Wycena gotowa"


def test_tab_bazy_order_overwrite_sets_stage_dates_and_preserves_existing_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])
    _ = app

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    store = OrderStoreJson(path=tmp_path / "orders.json")
    base = OrderDef(
        code="ORD-DATE-OVR-1",
        client_name="Klient B",
        status="Nowe",
        attachments=[{"path": "/tmp/a.pdf", "kind": "PDF"}],
        quote_items=[{"name": "Szafka", "quantity": "1"}],
    )
    assert store.save_new(base).ok is True

    w = TabBazy(order_store=store)
    w.ed_order_code.setText("ORD-DATE-OVR-1")
    w.cb_order_client.setCurrentText("Klient B")
    idx = w.cb_order_status.findText("W produkcji")
    assert idx >= 0
    w.cb_order_status.setCurrentIndex(idx)
    w._on_order_overwrite()

    saved = store.get("ORD-DATE-OVR-1")
    assert saved is not None
    assert saved.status == "W produkcji"
    assert saved.date_produkcja == _today_iso()
    assert len(saved.attachments) == 1
    assert len(saved.quote_items) == 1
    assert len(saved.status_history) >= 1
    assert saved.status_history[-1]["to_status"] == "W produkcji"


def test_tab_bazy_order_overwrite_sets_end_dates_for_anulowane(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])
    _ = app

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.bazy.tab_bazy import TabBazy

    store = OrderStoreJson(path=tmp_path / "orders.json")
    base = OrderDef(
        code="ORD-DATE-CANCEL-1",
        client_name="Klient C",
        status="W produkcji",
        date_wycena="2026-04-01",
        date_produkcja="2026-04-02",
    )
    assert store.save_new(base).ok is True

    w = TabBazy(order_store=store)
    w.ed_order_code.setText("ORD-DATE-CANCEL-1")
    w.cb_order_client.setCurrentText("Klient C")
    idx = w.cb_order_status.findText("Anulowane")
    assert idx >= 0
    w.cb_order_status.setCurrentIndex(idx)
    w._on_order_overwrite()

    saved = store.get("ORD-DATE-CANCEL-1")
    assert saved is not None
    assert saved.status == "Anulowane"
    assert saved.date_wycena_end == _today_iso()
    assert saved.date_produkcja_end == _today_iso()
