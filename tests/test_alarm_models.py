import pytest
from pathlib import Path
from datetime import datetime

from src.domain.alarm_models import AlarmDef, new_alarm_id, ALARM_CATEGORIES, ALARM_SEVERITY


class TestAlarmDef:
    def test_new_alarm_id_format(self):
        aid = new_alarm_id()
        assert isinstance(aid, str)
        assert len(aid) == 8
        assert aid.isalnum()

    def test_alarm_def_from_dict_minimal(self):
        data = {"title": "Brak materiału", "category": "materialy", "severity": "krytyczny"}
        a = AlarmDef.from_dict(data)
        assert a.title == "Brak materiału"
        assert a.category == "materialy"
        assert a.severity == "krytyczny"

    def test_alarm_def_from_dict_full(self):
        data = {
            "alarm_id": "ALARM01",
            "category": "platnosci",
            "severity": "ostrzezenie",
            "title": "Brak wpłaty",
            "description": "Klient nie wpłacił",
            "related_order": "ORD-001",
            "related_client": "Kowalski",
            "created_at": "2026-03-26 10:00:00",
            "due_date": "2026-03-30",
            "is_resolved": False,
        }
        a = AlarmDef.from_dict(data)
        assert a.alarm_id == "ALARM01"
        assert a.category == "platnosci"
        assert a.severity == "ostrzezenie"
        assert a.title == "Brak wpłaty"
        assert a.related_order == "ORD-001"

    def test_alarm_def_to_dict_roundtrip(self):
        original = AlarmDef(
            alarm_id="TESTALRM",
            category="terminy",
            severity="info",
            title="Termin montage",
            description="Montaż za 3 dni",
            related_order="ORD-002",
            created_at="2026-03-26 12:00:00",
            is_resolved=False,
        )
        data = original.to_dict()
        restored = AlarmDef.from_dict(data)
        assert restored.alarm_id == original.alarm_id
        assert restored.category == original.category
        assert restored.severity == original.severity
        assert restored.title == original.title

    def test_alarm_categories(self):
        assert "materialy" in ALARM_CATEGORIES
        assert "platnosci" in ALARM_CATEGORIES
        assert "kasa" in ALARM_CATEGORIES
        assert "pracownicy" in ALARM_CATEGORIES
        assert "terminy" in ALARM_CATEGORIES
        assert "faktury" in ALARM_CATEGORIES
        assert "projekty" in ALARM_CATEGORIES
        assert "inne" in ALARM_CATEGORIES

    def test_alarm_severity(self):
        assert "krytyczny" in ALARM_SEVERITY
        assert "ostrzezenie" in ALARM_SEVERITY
        assert "info" in ALARM_SEVERITY


class TestAlarmStoreJson:
    def test_list_alarms_empty(self, tmp_path):
        from src.storage.alarm_store_json import AlarmStoreJson
        store = AlarmStoreJson(tmp_path / "alarms.json")
        assert store.list_alarms() == []

    def test_save_and_list_alarm(self, tmp_path):
        from src.storage.alarm_store_json import AlarmStoreJson
        store = AlarmStoreJson(tmp_path / "alarms.json")
        a = AlarmDef.from_dict({"title": "Test alarm", "category": "materialy", "severity": "krytyczny"})
        store.save_alarm(a)
        alarms = store.list_alarms()
        assert len(alarms) == 1
        assert alarms[0].title == "Test alarm"

    def test_resolve_alarm(self, tmp_path):
        from src.storage.alarm_store_json import AlarmStoreJson
        store = AlarmStoreJson(tmp_path / "alarms.json")
        a = AlarmDef.from_dict({"alarm_id": "RESOLVE1", "title": "Do rozwiązania", "category": "platnosci", "severity": "ostrzezenie"})
        store.save_alarm(a)
        store.resolve_alarm("RESOLVE1")
        alarms = store.list_alarms()
        assert len(alarms) == 1
        assert alarms[0].is_resolved is True
        assert alarms[0].resolved_at != ""

    def test_delete_alarm(self, tmp_path):
        from src.storage.alarm_store_json import AlarmStoreJson
        store = AlarmStoreJson(tmp_path / "alarms.json")
        a = AlarmDef.from_dict({"alarm_id": "DELALRM", "title": "Do usunięcia", "category": "kasa", "severity": "info"})
        store.save_alarm(a)
        store.delete_alarm("DELALRM")
        assert store.list_alarms() == []

    def test_clear_resolved(self, tmp_path):
        from src.storage.alarm_store_json import AlarmStoreJson
        store = AlarmStoreJson(tmp_path / "alarms.json")
        a1 = AlarmDef.from_dict({"alarm_id": "RES1", "title": "Rozwiązany", "category": "pracownicy", "severity": "info", "is_resolved": True})
        a2 = AlarmDef.from_dict({"alarm_id": "RES2", "title": "Aktywny", "category": "terminy", "severity": "krytyczny", "is_resolved": False})
        store.save_alarm(a1)
        store.save_alarm(a2)
        store.clear_resolved()
        alarms = store.list_alarms()
        assert len(alarms) == 1
        assert alarms[0].title == "Aktywny"


class TestAlarmGenerator:
    def test_alarm_generator_creates_alarms(self, tmp_path):
        from src.services.alarm_generator import AlarmGenerator
        gen = AlarmGenerator()
        gen.generate_all()
        alarms = gen._store.list_alarms()
        assert isinstance(alarms, list)
