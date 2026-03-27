from datetime import date, timedelta

from PyQt6.QtWidgets import QApplication

from src.domain.service_models import ServiceDef
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.service_store_json import ServiceStoreJson
from src.tabs.dashboard.tab_dashboard import TabDashboard


def test_dashboard_counts_services_with_deadline(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    store = ServiceStoreJson()
    store.save_service(
        ServiceDef(
            service_id="SVC2001",
            name="Lakierowanie",
            category="lakierowanie",
            price=120.0,
            deadline=(date.today() - timedelta(days=1)).isoformat(),
        )
    )
    store.save_service(
        ServiceDef(
            service_id="SVC2002",
            name="Giete elementy",
            category="giete_elementy",
            price=200.0,
            deadline=(date.today() + timedelta(days=2)).isoformat(),
        )
    )
    store.save_service(
        ServiceDef(
            service_id="SVC2003",
            name="Front surowy",
            category="fronty_surowe",
            price=90.0,
            deadline="",
        )
    )

    app = QApplication.instance() or QApplication([])
    _ = app

    tab = TabDashboard()
    tab.refresh_data()

    assert tab._card_services._lab_value.text() == "2"
    assert "po terminie: 1" in tab._card_services._lab_sub.text()
    assert "wszystkie: 3" in tab._card_services._lab_sub.text()


def test_dashboard_shows_real_hour_from_company_expenses(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    expenses = CompanyExpensesStoreJson()
    expenses.save_items("fixed", [{"name": "Wynajem", "amount": 1600.0}])
    expenses.save_items("variable", [{"name": "Paliwo", "amount": 3200.0}])
    expenses.save_workforce(workers_count=2, hours_per_worker=160.0)  # 4800 / 320h = 15 zl/h

    app = QApplication.instance() or QApplication([])
    _ = app

    tab = TabDashboard()
    tab.refresh_data()

    assert tab._card_real_hour._lab_value.text() == "15.00 zl/h"
    assert "2 prac. x 160 h" in tab._card_real_hour._lab_sub.text()
