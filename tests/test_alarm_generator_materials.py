import json

from src.domain.order_models import OrderDef
from src.services.alarm_generator import AlarmGenerator
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.order_store_json import OrderStoreJson


def test_alarm_generator_adds_material_shortage_alarm(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    (tmp_path / "baza_materialu.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "id": "M0001",
                        "nazwa": "MDF 18",
                        "ilosc_magazyn": "2",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (tmp_path / "usluga_quotes.json").write_text(
        json.dumps(
            [
                {
                    "quote_id": "UQ001",
                    "rows": [
                        {
                            "material_id": "M0001",
                            "material_name": "MDF 18",
                            "qty": 6,
                        }
                    ],
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    AlarmGenerator().generate_all()
    alarms = AlarmStoreJson().list_alarms()

    assert any("brak ilosci do uslug" in str(a.title or "") for a in alarms)
    assert any(str(a.category or "") == "materialy" for a in alarms)


def test_alarm_generator_adds_order_material_readiness_alarm(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    store = OrderStoreJson()
    result = store.save_new(
        OrderDef(
            code="ZAM001",
            order_id="ZAM001",
            client_name="Klient test",
            worker_name="Jan",
            status="W produkcji",
            material_choices=[],
        )
    )
    assert result.ok

    AlarmGenerator().generate_all()
    alarms = AlarmStoreJson().list_alarms()

    assert any("brak finalnych materialow" in str(a.title or "") for a in alarms)
