import pytest
import json
import tempfile
from pathlib import Path

from src.domain.service_models import ServiceDef, new_service_id


class TestServiceDef:
    def test_new_service_id_format(self):
        sid = new_service_id()
        assert isinstance(sid, str)
        assert len(sid) == 8
        assert sid.isalnum()

    def test_service_def_from_dict_minimal(self):
        data = {"name": "Wycinanie", "price": 100.0, "duration_min": 60}
        s = ServiceDef.from_dict(data)
        assert s.name == "Wycinanie"
        assert s.price == 100.0
        assert s.duration_min == 60
        assert s.service_id != ""

    def test_service_def_from_dict_full(self):
        data = {
            "service_id": "TEST1234",
            "name": "Oklejanie",
            "price": 80.0,
            "duration_min": 45,
            "category": "uslugi",
            "description": "Oklejanie krawędzi",
            "deadline": "2026-05-10",
            "note": "Uwagi testowe"
        }
        s = ServiceDef.from_dict(data)
        assert s.service_id == "TEST1234"
        assert s.name == "Oklejanie"
        assert s.price == 80.0
        assert s.duration_min == 45
        assert s.category == "uslugi"
        assert s.description == "Oklejanie krawędzi"
        assert s.deadline == "2026-05-10"
        assert s.note == "Uwagi testowe"

    def test_service_def_to_dict_roundtrip(self):
        original = ServiceDef(
            service_id="ABC12345",
            name="Lakierowanie",
            price=150.0,
            duration_min=120,
            category="uslugi",
            description="Lakierowanie frontów",
            deadline="2026-05-11",
            note="Test"
        )
        data = original.to_dict()
        restored = ServiceDef.from_dict(data)
        assert restored.service_id == original.service_id
        assert restored.name == original.name
        assert restored.price == original.price
        assert restored.duration_min == original.duration_min
        assert restored.category == original.category
        assert restored.deadline == original.deadline

    def test_service_def_default_values(self):
        s = ServiceDef.from_dict({})
        assert s.name == ""
        assert s.price == 0.0
        assert s.duration_min == 0
        assert s.category == ""
        assert s.service_id != ""


class TestServiceStoreJson:
    def test_list_services_empty(self, tmp_path):
        from src.storage.service_store_json import ServiceStoreJson
        store = ServiceStoreJson(tmp_path / "services.json")
        assert store.list_services() == []

    def test_save_and_list_service(self, tmp_path):
        from src.storage.service_store_json import ServiceStoreJson
        store = ServiceStoreJson(tmp_path / "services.json")
        s = ServiceDef.from_dict({"name": "Gięcie", "price": 200.0, "duration_min": 90})
        store.save_service(s)
        services = store.list_services()
        assert len(services) == 1
        assert services[0].name == "Gięcie"

    def test_save_overwrites_existing(self, tmp_path):
        from src.storage.service_store_json import ServiceStoreJson
        store = ServiceStoreJson(tmp_path / "services.json")
        s1 = ServiceDef.from_dict({"service_id": "SAMEID", "name": "A", "price": 10.0, "duration_min": 10})
        store.save_service(s1)
        s2 = ServiceDef.from_dict({"service_id": "SAMEID", "name": "B", "price": 20.0, "duration_min": 20})
        store.save_service(s2)
        services = store.list_services()
        assert len(services) == 1
        assert services[0].name == "B"
        assert services[0].price == 20.0

    def test_delete_service(self, tmp_path):
        from src.storage.service_store_json import ServiceStoreJson
        store = ServiceStoreJson(tmp_path / "services.json")
        s = ServiceDef.from_dict({"service_id": "DEL123", "name": "Do usunięcia", "price": 50.0, "duration_min": 30})
        store.save_service(s)
        store.delete_service("DEL123")
        assert store.list_services() == []

    def test_import_export_csv(self, tmp_path):
        from src.storage.service_store_json import ServiceStoreJson
        store = ServiceStoreJson(tmp_path / "services.csv")
        csv_content = """service_id,name,price,duration_min,category,description
SVC001,Wycinanie,100.0,60,uslugi,Wycinanie elementów
SVC002,Oklejanie,80.0,45,uslugi,Oklejanie krawędzi
"""
        csv_path = tmp_path / "import.csv"
        csv_path.write_text(csv_content, encoding="utf-8")
        imported = store.import_from_csv(str(csv_path))
        assert len(imported) == 2
        assert imported[0].name == "Wycinanie"
        assert imported[1].name == "Oklejanie"
        export_path = tmp_path / "export.csv"
        store.export_to_csv(str(export_path))
        content = export_path.read_text(encoding="utf-8")
        assert "Wycinanie" in content
        assert "Oklejanie" in content
