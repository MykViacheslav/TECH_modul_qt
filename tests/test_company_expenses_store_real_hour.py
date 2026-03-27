from src.storage.company_expenses_store_json import CompanyExpensesStoreJson


def test_company_expenses_store_real_hour_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    store = CompanyExpensesStoreJson()
    store.save_items("fixed", [{"name": "Wynajem", "amount": 3000.0}])
    store.save_items("variable", [{"name": "Paliwo", "amount": 1500.0}])
    store.save_workforce(workers_count=5, hours_per_worker=160.0)

    metrics = store.real_hour_metrics(workers_fallback=1, hours_fallback=1.0)

    assert metrics["fixed_total"] == 3000.0
    assert metrics["variable_total"] == 1500.0
    assert metrics["total_costs"] == 4500.0
    assert metrics["workers_count"] == 5.0
    assert metrics["hours_per_worker"] == 160.0
    assert metrics["total_hours"] == 800.0
    assert metrics["real_hour_rate"] == 5.625
