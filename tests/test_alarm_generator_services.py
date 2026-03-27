from datetime import date, timedelta

from src.domain.service_models import ServiceDef
from src.services.alarm_generator import AlarmGenerator
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.service_store_json import ServiceStoreJson


def test_alarm_generator_adds_service_alarms(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    service_store = ServiceStoreJson()
    service_store.save_service(
        ServiceDef(
            service_id="SVC0001",
            name="Lakierowanie premium",
            category="lakierowanie",
            price=0.0,
        )
    )
    service_store.save_service(
        ServiceDef(
            service_id="SVC0002",
            name="Oklejanie laser",
            category="wycinanie_oklejanie",
            price=250.0,
            deadline=(date.today() - timedelta(days=1)).isoformat(),
        )
    )
    service_store.save_service(
        ServiceDef(
            service_id="SVC0003",
            name="Fronty surowe",
            category="fronty_surowe",
            price=180.0,
            deadline=(date.today() + timedelta(days=2)).isoformat(),
        )
    )

    AlarmGenerator().generate_all()
    alarms = AlarmStoreJson().list_alarms()
    titles = [str(a.title or "") for a in alarms]

    assert any("brak ceny" in title for title in titles)
    assert any("termin zalegly" in title for title in titles)
    assert any("termin do 3 dni" in title for title in titles)

