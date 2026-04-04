from PyQt6.QtWidgets import QApplication
from datetime import datetime


def test_tab_baza_szybkich_wycen_has_offer_and_discount_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    headers = [w.tree.headerItem().text(i) for i in range(w.tree.columnCount())]
    assert headers == ["ID", "Oferta", "Klient", "Cena", "Rabat", "VAT", "Marza", "Zamowienie", "Status zam."]


def test_tab_baza_szybkich_wycen_renders_offer_discount_and_fallbacks(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    w._items = [
        {
            "id": "Q1",
            "title": "Oferta testowa",
            "client": "Klient A",
            "price": "1200.00 zl",
            "discount_pct": "5.00%",
            "vat": "23%",
            "margin": "10.00%",
            "sections": [{"id": "SW001", "title": "Sekcja 1", "price": "700.00 zl"}],
        },
        {
            "id": "Q2",
            "client": "Klient B",
            "base_price": "900.00 zl",
            "sections": [],
        },
    ]
    w._refresh_tree()

    assert w.tree.topLevelItemCount() == 2

    first = w.tree.topLevelItem(0)
    assert first.text(1) == "Oferta testowa"
    assert first.text(4) == "5.00%"
    assert first.childCount() == 1
    assert first.child(0).text(0) == "SW001"
    assert first.child(0).text(1) == "Sekcja 1"
    assert first.child(0).text(3) == "700.00 zl"

    second = w.tree.topLevelItem(1)
    assert second.text(1) == "[bez nazwy]"
    assert second.text(3) == "900.00 zl"
    assert second.text(4) == "0.00%"


def test_sanitize_quick_quote_entries_keeps_title_only_rows():
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import sanitize_quick_quote_entries

    cleaned = sanitize_quick_quote_entries(
        [
            {"title": "Oferta bez ceny", "client": "", "price": "0.00", "sections": []},
            {"title": "", "client": "", "price": "0.00", "sections": []},
        ]
    )
    assert len(cleaned) == 1
    assert cleaned[0].get("title") == "Oferta bez ceny"


def test_tab_baza_szybkich_wycen_add_entry_sets_created_at(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    w._items = []
    w._add_entry()
    assert len(w._items) == 1
    created = str(w._items[0].get("created_at", "") or "").strip()
    assert created
    # ISO timestamp from datetime.now().isoformat(timespec="seconds")
    datetime.fromisoformat(created)


def test_tab_baza_szybkich_wycen_inline_edit_updates_item_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    w._items = [
        {
            "id": "Q1",
            "title": "Oferta A",
            "client": "Klient A",
            "price": "100.00 zl",
            "discount_pct": "0.00%",
            "vat": "23%",
            "margin": "0.00%",
            "sections": [],
        }
    ]
    w._refresh_tree()

    top = w.tree.topLevelItem(0)
    assert top is not None

    top.setText(3, "1234")
    w._on_tree_item_changed(top, 3)
    top.setText(4, "7,5")
    w._on_tree_item_changed(top, 4)
    top.setText(1, "")
    w._on_tree_item_changed(top, 1)
    top.setText(6, "-3")
    w._on_tree_item_changed(top, 6)
    top.setText(0, "Q999")
    w._on_tree_item_changed(top, 0)
    top.setText(7, "ORD-FAKE")
    w._on_tree_item_changed(top, 7)
    top.setText(8, "W produkcji")
    w._on_tree_item_changed(top, 8)

    entry = w._items[0]
    assert entry["price"] == "1234.00 zl"
    assert entry["discount_pct"] == "7.50%"
    assert entry["title"] == "[bez nazwy]"
    assert entry["margin"] == "0.00%"
    assert entry["id"] == "Q1"
    assert top.text(0) == "Q1"
    assert top.text(7) == ""
    assert top.text(8) == ""


def test_tab_baza_szybkich_wycen_filter_matches_offer_client_and_id(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    w._items = [
        {"id": "Q100", "title": "Kuchnia premium", "client": "Nowak", "price": "1000.00 zl", "sections": []},
        {"id": "Q200", "title": "Szafa", "client": "Kowalski", "price": "2000.00 zl", "sections": []},
    ]
    w._refresh_tree()
    assert w.tree.topLevelItemCount() == 2

    w.ed_filter.setText("kuchnia")
    assert w.tree.topLevelItemCount() == 1
    assert w.tree.topLevelItem(0).text(0) == "Q100"
    assert "1 / 2" in w.lab_filter_info.text()

    w.ed_filter.setText("kowalski")
    assert w.tree.topLevelItemCount() == 1
    assert w.tree.topLevelItem(0).text(0) == "Q200"

    w.ed_filter.setText("Q100")
    assert w.tree.topLevelItemCount() == 1
    assert w.tree.topLevelItem(0).text(1) == "Kuchnia premium"


def test_tab_baza_szybkich_wycen_filter_matches_order_status(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(OrderDef(code="ORD-Q111", order_id="Q111", client_name="Klient A", status="W produkcji"))
    order_store.save_new(OrderDef(code="ORD-Q222", order_id="Q222", client_name="Klient B", status="Nowe"))

    w = TabBazaSzybkichWycen()
    w._items = [
        {"id": "Q111", "title": "A", "client": "A", "price": "100.00 zl", "sections": []},
        {"id": "Q222", "title": "B", "client": "B", "price": "200.00 zl", "sections": []},
    ]
    w._refresh_tree()
    assert w.tree.topLevelItemCount() == 2

    w.ed_filter.setText("produkcji")
    assert w.tree.topLevelItemCount() == 1
    assert w.tree.topLevelItem(0).text(0) == "Q111"
    assert w.tree.topLevelItem(0).text(8) == "W produkcji"


def test_tab_baza_szybkich_wycen_remove_selected_handles_multiple_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    w = TabBazaSzybkichWycen()
    w._items = [
        {"id": "Q001", "title": "A", "client": "A", "price": "100.00 zl", "sections": []},
        {"id": "Q002", "title": "B", "client": "B", "price": "200.00 zl", "sections": []},
        {"id": "Q003", "title": "C", "client": "C", "price": "300.00 zl", "sections": []},
    ]
    w._refresh_tree()

    first = w.tree.topLevelItem(0)
    third = w.tree.topLevelItem(2)
    assert first is not None and third is not None
    first.setSelected(True)
    third.setSelected(True)

    w._remove_selected()

    ids = [row.get("id") for row in w._items]
    assert ids == ["Q002"]


def test_tab_baza_szybkich_wycen_sort_by_price_desc(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
        QUICK_QUOTE_SORT_PRICE_DESC,
        TabBazaSzybkichWycen,
    )

    w = TabBazaSzybkichWycen()
    w._items = [
        {"id": "Q001", "title": "A", "client": "A", "price": "100.00 zl", "sections": []},
        {"id": "Q002", "title": "B", "client": "B", "price": "250.00 zl", "sections": []},
        {"id": "Q003", "title": "C", "client": "C", "price": "180.00 zl", "sections": []},
    ]
    idx = w.cb_sort.findData(QUICK_QUOTE_SORT_PRICE_DESC)
    assert idx >= 0
    w.cb_sort.setCurrentIndex(idx)
    w._refresh_tree()

    ids = [w.tree.topLevelItem(row).text(0) for row in range(w.tree.topLevelItemCount())]
    assert ids == ["Q002", "Q003", "Q001"]


def test_tab_baza_szybkich_wycen_build_order_code_handles_duplicates():
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    code = TabBazaSzybkichWycen._build_order_code("Q20260403_101516", [])
    assert code == "ORD-Q20260403_101516"

    dup = TabBazaSzybkichWycen._build_order_code(
        "Q20260403_101516",
        ["ORD-Q20260403_101516", "ORD-Q20260403_101516-02"],
    )
    assert dup == "ORD-Q20260403_101516-03"


def test_tab_baza_szybkich_wycen_create_order_from_selected_quote(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen import tab_baza_szybkich_wycen as mod
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)

    w = TabBazaSzybkichWycen()
    opened_orders: list[str] = []
    w.sig_open_order_requested.connect(opened_orders.append)
    w._items = [
        {
            "id": "Q500",
            "title": "Oferta kuchnia A",
            "client": "Klient Test",
            "price": "3200.00 zl",
            "base_price": "3500.00 zl",
            "discount_pct": "8.57%",
            "sections": [{"id": "SW001", "title": "Sekcja 1", "price": "1500.00 zl"}],
        }
    ]
    w._refresh_tree()

    top = w.tree.topLevelItem(0)
    assert top is not None
    w.tree.setCurrentItem(top)
    top.setSelected(True)

    w._create_order_from_selected_quote()

    orders = w._order_store.list_orders()
    assert len(orders) == 1
    order = orders[0]
    assert order.code == "ORD-Q500"
    assert order.client_name == "Klient Test"
    assert order.status == "Wycena gotowa"
    assert "Q500" in order.notes
    assert "Sekcja 1" in order.notes
    assert w._items[0].get("order_code") == "ORD-Q500"
    assert opened_orders == ["ORD-Q500"]
    assert w.tree.topLevelItem(0).text(7) == "ORD-Q500"
    assert w.tree.topLevelItem(0).text(8) == "Wycena gotowa"

    # Drugie klikniecie nie duplikuje zamowienia dla tej samej wyceny.
    w._create_order_from_selected_quote()
    assert len(w._order_store.list_orders()) == 1
    assert opened_orders == ["ORD-Q500", "ORD-Q500"]


def test_tab_baza_szybkich_wycen_open_order_from_selected_quote(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen import tab_baza_szybkich_wycen as mod
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)

    w = TabBazaSzybkichWycen()
    opened_orders: list[str] = []
    w.sig_open_order_requested.connect(opened_orders.append)
    w._items = [
        {
            "id": "Q900",
            "title": "Oferta A",
            "client": "Klient A",
            "price": "1000.00 zl",
            "sections": [],
        }
    ]
    w._refresh_tree()

    top = w.tree.topLevelItem(0)
    assert top is not None
    w.tree.setCurrentItem(top)
    top.setSelected(True)

    w._create_order_from_selected_quote()
    assert opened_orders == ["ORD-Q900"]

    order = w._order_store.get("ORD-Q900")
    assert order is not None
    order.status = "W produkcji"
    w._order_store.overwrite(order)

    # Otwieranie powinno przejsc do istniejacego zamowienia bez duplikacji.
    w._open_order_from_selected_quote()
    assert opened_orders == ["ORD-Q900", "ORD-Q900"]
    assert len(w._order_store.list_orders()) == 1
    assert w.tree.topLevelItem(0).text(7) == "ORD-Q900"
    assert w.tree.topLevelItem(0).text(8) == "W produkcji"


def test_tab_baza_szybkich_wycen_open_order_without_link_shows_info(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.baza_szybkich_wycen import tab_baza_szybkich_wycen as mod
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen

    info_calls: list[tuple] = []
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: info_calls.append(args))

    w = TabBazaSzybkichWycen()
    opened_orders: list[str] = []
    w.sig_open_order_requested.connect(opened_orders.append)
    w._items = [
        {"id": "Q777", "title": "Oferta bez zamowienia", "client": "Klient X", "price": "0.00 zl", "sections": []}
    ]
    w._refresh_tree()

    top = w.tree.topLevelItem(0)
    assert top is not None
    w.tree.setCurrentItem(top)
    top.setSelected(True)
    w._open_order_from_selected_quote()

    assert opened_orders == []
    assert len(info_calls) == 1


def test_tab_baza_szybkich_wycen_export_selected_quote_txt_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.baza_szybkich_wycen import tab_baza_szybkich_wycen as mod
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
        TabBazaSzybkichWycen,
        quick_quote_export_dir,
    )

    info_calls: list[tuple] = []
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: info_calls.append(args))

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-Q321",
            order_id="Q321",
            client_name="Klient Export",
            status="W produkcji",
        )
    )

    w = TabBazaSzybkichWycen()
    w._items = [
        {
            "id": "Q321",
            "title": "Oferta test/export",
            "client": "Klient Export",
            "price": "3200.00 zl",
            "base_price": "3500.00 zl",
            "discount_pct": "8.57%",
            "sections": [{"id": "SW001", "title": "Sekcja 1", "price": "1500.00 zl"}],
        }
    ]
    w._refresh_tree()
    top = w.tree.topLevelItem(0)
    assert top is not None
    w.tree.setCurrentItem(top)
    top.setSelected(True)

    w._export_selected_quote_txt()
    w._export_selected_quote_txt()

    export_dir = quick_quote_export_dir()
    exported = sorted(export_dir.glob("Q321_Oferta_test_export*.txt"))
    assert [p.name for p in exported] == ["Q321_Oferta_test_export.txt", "Q321_Oferta_test_export_02.txt"]
    content = exported[0].read_text(encoding="utf-8")
    assert "ID oferty: Q321" in content
    assert "Klient: Klient Export" in content
    assert "Kod: ORD-Q321" in content
    assert "Status: W produkcji" in content
    assert "Sekcja 1" in content
    assert len(info_calls) == 2


def test_tab_baza_szybkich_wycen_export_selected_quote_pdf_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.baza_szybkich_wycen import tab_baza_szybkich_wycen as mod
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
        TabBazaSzybkichWycen,
        quick_quote_export_dir,
    )

    info_calls: list[tuple] = []
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: info_calls.append(args))

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORD-Q654",
            order_id="Q654",
            client_name="Klient PDF",
            status="Nowe",
        )
    )

    w = TabBazaSzybkichWycen()
    w._items = [
        {
            "id": "Q654",
            "title": "Oferta pdf test",
            "client": "Klient PDF",
            "price": "2500.00 zl",
            "base_price": "2800.00 zl",
            "discount_pct": "10.71%",
            "sections": [{"id": "SW010", "title": "Sekcja PDF", "price": "900.00 zl"}],
        }
    ]
    w._refresh_tree()
    top = w.tree.topLevelItem(0)
    assert top is not None
    w.tree.setCurrentItem(top)
    top.setSelected(True)

    w._export_selected_quote_pdf()
    w._export_selected_quote_pdf()

    export_dir = quick_quote_export_dir()
    exported = sorted(export_dir.glob("Q654_Oferta_pdf_test*.pdf"))
    assert [p.name for p in exported] == ["Q654_Oferta_pdf_test.pdf", "Q654_Oferta_pdf_test_02.pdf"]
    assert exported[0].stat().st_size > 0
    assert len(info_calls) == 2
