from src.domain.order_models import OrderDef
import json


def test_order_calendar_sync_removes_orphaned_stage_events(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.services.order_calendar_sync import sync_single_order
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson

    order_store = OrderStoreJson()
    calendar_store = CalendarEventStoreJson()

    order = OrderDef(
        code="ORD-SYNC-1",
        client_name="Klient A",
        status="Wycena",
        date_wycena="2026-04-03",
    )
    result_new = order_store.save_new(order)
    assert result_new.ok is True

    touched_1 = sync_single_order("ORD-SYNC-1")
    assert touched_1 >= 1
    events_1 = [ev for ev in calendar_store.list_events() if str(ev.order_code or "") == "ORD-SYNC-1"]
    assert any(ev.date == "2026-04-03" and "Wycena" in str(ev.title or "") for ev in events_1)

    order_updated = order_store.get("ORD-SYNC-1")
    assert order_updated is not None
    order_updated.date_wycena = "2026-04-08"
    result_overwrite = order_store.overwrite(order_updated)
    assert result_overwrite.ok is True

    touched_2 = sync_single_order("ORD-SYNC-1")
    assert touched_2 >= 1
    events_2 = [ev for ev in calendar_store.list_events() if str(ev.order_code or "") == "ORD-SYNC-1"]
    assert any(ev.date == "2026-04-08" and "Wycena" in str(ev.title or "") for ev in events_2)
    assert not any(ev.date == "2026-04-03" and "Wycena" in str(ev.title or "") for ev in events_2)


def test_order_calendar_sync_all_cleans_events_for_deleted_orders(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.services.order_calendar_sync import sync_orders_to_calendar, sync_single_order
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson

    order_store = OrderStoreJson()
    calendar_store = CalendarEventStoreJson()

    order = OrderDef(
        code="ORD-SYNC-DEL-1",
        client_name="Klient A",
        status="Wycena",
        date_wycena="2026-04-03",
    )
    assert order_store.save_new(order).ok is True
    assert sync_single_order("ORD-SYNC-DEL-1") >= 1

    assert any(str(ev.order_code or "") == "ORD-SYNC-DEL-1" for ev in calendar_store.list_events())
    assert order_store.delete("ORD-SYNC-DEL-1").ok is True

    touched = sync_orders_to_calendar()
    assert touched >= 1
    assert not any(str(ev.order_code or "") == "ORD-SYNC-DEL-1" for ev in calendar_store.list_events())


def test_order_calendar_sync_marks_all_stage_events_as_cancelled_for_anulowane(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.services.order_calendar_sync import sync_single_order
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson

    order_store = OrderStoreJson()
    calendar_store = CalendarEventStoreJson()

    order = OrderDef(
        code="ORD-SYNC-CANCEL-1",
        client_name="Klient C",
        status="Anulowane",
        date_wycena="2026-04-03",
        date_produkcja="2026-04-06",
    )
    assert order_store.save_new(order).ok is True
    assert sync_single_order("ORD-SYNC-CANCEL-1") >= 1

    events = [ev for ev in calendar_store.list_events() if str(ev.order_code or "") == "ORD-SYNC-CANCEL-1"]
    assert len(events) >= 2
    for event in events:
        notes = str(getattr(event, "notes", "") or "").strip()
        payload = json.loads(notes) if notes else {}
        assert payload.get("source") == "order_sync"
        assert payload.get("status") == "anulowany"


def test_order_calendar_sync_marks_future_stage_events_as_on_hold_for_wstrzymane(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.services.order_calendar_sync import sync_single_order
    from src.storage.calendar_event_store_json import CalendarEventStoreJson
    from src.storage.order_store_json import OrderStoreJson

    order_store = OrderStoreJson()
    calendar_store = CalendarEventStoreJson()

    order = OrderDef(
        code="ORD-SYNC-HOLD-1",
        client_name="Klient H",
        status="Wstrzymane",
        date_wycena="2026-04-03",
        date_produkcja="2026-04-06",
    )
    assert order_store.save_new(order).ok is True
    assert sync_single_order("ORD-SYNC-HOLD-1") >= 1

    events = [ev for ev in calendar_store.list_events() if str(ev.order_code or "") == "ORD-SYNC-HOLD-1"]
    assert len(events) >= 2
    by_title = {str(ev.title or ""): ev for ev in events}

    ev_wycena = next((ev for title, ev in by_title.items() if "Wycena" in title), None)
    ev_produkcja = next((ev for title, ev in by_title.items() if "Produkcja" in title), None)
    assert ev_wycena is not None
    assert ev_produkcja is not None

    notes_wycena = json.loads(str(getattr(ev_wycena, "notes", "") or "{}"))
    notes_produkcja = json.loads(str(getattr(ev_produkcja, "notes", "") or "{}"))
    assert notes_wycena.get("status") == "zakonczony"
    assert notes_produkcja.get("status") == "wstrzymany"
