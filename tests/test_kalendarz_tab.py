from datetime import date

from PyQt6.QtWidgets import QApplication


def test_kalendarz_tab_creates_without_crash(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    w = TabKalendarz()
    w.show()
    app.processEvents()
    w.close()


def test_calendar_event_store_save_and_load(tmp_path):
    from src.domain.calendar_event import CalendarEvent
    from src.storage.calendar_event_store_json import CalendarEventStoreJson

    store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    ev = CalendarEvent.new("bhp", "Lakiernia", "Szkolenie BHP", "2026-04-01", worker_name="Jan")
    store.save(ev)

    loaded = store.list_events()
    assert len(loaded) == 1
    assert loaded[0].title == "Szkolenie BHP"
    assert loaded[0].station == "Lakiernia"
    assert loaded[0].event_type == "bhp"
    assert loaded[0].worker_name == "Jan"


def test_calendar_event_store_update(tmp_path):
    from dataclasses import replace

    from src.domain.calendar_event import CalendarEvent
    from src.storage.calendar_event_store_json import CalendarEventStoreJson

    store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    ev = CalendarEvent.new("zlecenie", "CNC", "Zlecenie #001", "2026-04-10")
    store.save(ev)

    updated = replace(ev, date="2026-04-15", station="Skladanie")
    store.save(updated)

    events = store.list_events()
    assert len(events) == 1
    assert events[0].date == "2026-04-15"
    assert events[0].station == "Skladanie"


def test_calendar_event_store_delete(tmp_path):
    from src.domain.calendar_event import CalendarEvent
    from src.storage.calendar_event_store_json import CalendarEventStoreJson

    store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    ev1 = CalendarEvent.new("montaz", "Biuro", "Montaz kuchni", "2026-04-05")
    ev2 = CalendarEvent.new("pomiary", "Biuro", "Pomiar mieszkania", "2026-04-06")
    store.save(ev1)
    store.save(ev2)
    assert len(store.list_events()) == 2

    store.delete(ev1.id)
    remaining = store.list_events()
    assert len(remaining) == 1
    assert remaining[0].id == ev2.id


def test_calendar_event_pomiar_migration(tmp_path):
    """Old events saved as 'pomiar' should be migrated to 'pomiary' on load."""
    import json

    from src.storage.calendar_event_store_json import CalendarEventStoreJson

    raw = [{"id": "abc", "event_type": "pomiar", "station": "Biuro",
            "title": "Stary pomiar", "date": "2026-01-01",
            "worker_name": "", "order_code": "", "notes": ""}]
    (tmp_path / "cal.json").write_text(json.dumps(raw), encoding="utf-8")

    store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    events = store.list_events()
    assert events[0].event_type == "pomiary"


def test_calendar_event_all_types_have_labels_and_colors():
    from src.domain.calendar_event import EVENT_COLORS, EVENT_TYPE_LABELS, EVENT_TYPES

    for et in EVENT_TYPES:
        assert et in EVENT_TYPE_LABELS, f"Brak etykiety dla: {et}"
        assert et in EVENT_COLORS, f"Brak koloru dla: {et}"


def test_calendar_event_stations_include_requested_categories():
    from src.domain.calendar_event import STATIONS

    for station in ("CNC", "LAKIERNIA", "OKLEJANIE", "ZBORKA"):
        assert station in STATIONS


def test_kalendarz_tab_rebuild_does_not_crash(tmp_path, monkeypatch):
    """_rebuild() can be called multiple times without crashing."""
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.calendar_event import CalendarEvent
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    store.save(CalendarEvent.new("bhp", "CNC", "BHP test", date.today().isoformat()))

    w = TabKalendarz(calendar_store=store)
    w.show()
    app.processEvents()

    # Navigate forward/back to trigger _rebuild
    w._navigate_next()
    app.processEvents()
    w._navigate_prev()
    app.processEvents()
    w._navigate_today()
    app.processEvents()

    # Switch views
    w._set_view("month")
    app.processEvents()
    w._navigate_next()
    app.processEvents()
    w._set_view("week")
    app.processEvents()

    w.close()


def test_kalendarz_tab_filters_events_and_shows_order_status_history(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.calendar_event import CalendarEvent
    from src.domain.order_models import OrderDef
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    calendar_store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    calendar_store.save(
        CalendarEvent.new("montaz", "Biuro", "Montaz A", date.today().isoformat(), worker_name="Jan")
    )
    calendar_store.save(
        CalendarEvent.new("bhp", "CNC", "BHP B", date.today().isoformat(), worker_name="Anna")
    )

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORDER-KAL-1",
            client_name="Klient K",
            worker_name="Jan",
            status="Wycena",
            progress_percent=40.0,
            calendar_stage="Wycena",
            status_history=[
                {
                    "changed_at": "2026-03-24T10:00:00",
                    "from_status": "Nowe",
                    "to_status": "Wycena",
                    "changed_by": "Jan",
                    "note": "postep 0% -> 40%",
                }
            ],
        )
    )

    w = TabKalendarz(order_store=order_store, calendar_store=calendar_store)
    w.show()
    app.processEvents()

    w._ed_filter_worker.setText("jan")
    w._on_event_filters_changed()
    app.processEvents()

    assert w._cb_filter_station.count() >= 2
    assert w._lst_order_status.count() >= 1
    first_order_item = w._lst_order_status.item(0)
    assert first_order_item is not None
    assert "ORDER-KAL-1" in first_order_item.text()
    assert w._lst_order_history.count() >= 1
    first_history_item = w._lst_order_history.item(0)
    assert first_history_item is not None
    assert "Nowe -> Wycena" in first_history_item.text()

    w.close()


def test_kalendarz_tab_shows_filter_chips_and_can_clear_all_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.domain.calendar_event import CalendarEvent
    from src.domain.order_models import OrderDef
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.kalendarz.tab_kalendarz import TabKalendarz

    calendar_store = CalendarEventStoreJson(path=tmp_path / "cal.json")
    calendar_store.save(CalendarEvent.new("bhp", "CNC", "BHP", date.today().isoformat(), worker_name="Jan"))

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORDER-KAL-2",
            client_name="Klient Q",
            worker_name="Jan",
            status="Produkcja",
            progress_percent=50.0,
            calendar_stage="Produkcja",
            status_history=[
                {
                    "changed_at": "2026-03-24T11:30:00",
                    "from_status": "Wycena",
                    "to_status": "Produkcja",
                    "changed_by": "Jan",
                    "note": "start produkcji",
                }
            ],
        )
    )

    w = TabKalendarz(order_store=order_store, calendar_store=calendar_store)
    w.show()
    app.processEvents()

    idx_station = w._cb_filter_station.findData("CNC")
    if idx_station >= 0:
        w._cb_filter_station.setCurrentIndex(idx_station)
    w._ed_filter_worker.setText("Jan")
    idx_status = w._cb_order_status.findData("Produkcja")
    if idx_status >= 0:
        w._cb_order_status.setCurrentIndex(idx_status)
    app.processEvents()

    assert "Aktywne filtry wydarzen:" in w._lab_event_filter_chips.text()
    assert "CNC" in w._lab_event_filter_chips.text()
    assert "Aktywne filtry zamowien:" in w._lab_order_filter_chips.text()
    assert "Produkcja" in w._lab_order_filter_chips.text()
    first_history_item = w._lst_order_history.item(0)
    assert first_history_item is not None
    assert "24.03.2026 11:30" in first_history_item.text()

    w._clear_all_filters()
    app.processEvents()

    assert "brak" in w._lab_event_filter_chips.text().lower()
    assert "brak" in w._lab_order_filter_chips.text().lower()

    w.close()
