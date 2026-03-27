from src.domain.service_models import ServiceDef
from src.storage.service_store_json import ServiceStoreJson
from src.tabs.kalendarz.tab_kalendarz import _build_service_calendar_events


def test_build_service_calendar_events_uses_deadlines(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    store = ServiceStoreJson()
    store.save_service(
        ServiceDef(
            service_id="SVC1001",
            name="Blat kerrock",
            category="blaty_kerrock",
            price=400.0,
            deadline="2026-05-15",
        )
    )
    store.save_service(
        ServiceDef(
            service_id="SVC1002",
            name="Bez terminu",
            category="inne",
            price=50.0,
            deadline="",
        )
    )

    events = _build_service_calendar_events()
    assert len(events) == 1
    event = events[0]
    assert event.id == "svc_SVC1001"
    assert event.date == "2026-05-15"
    assert "Usluga: Blat kerrock" in event.title

