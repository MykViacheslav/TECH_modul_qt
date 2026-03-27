import json

from PyQt6.QtWidgets import QApplication


def test_wydatki_stale_defaults_and_sum(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.wydatki_stale.tab_wydatki_stale import TabWydatkiStale

    w = TabWydatkiStale()
    assert w.tbl.rowCount() >= 5

    first_amount = w.tbl.item(0, 2)
    second_amount = w.tbl.item(1, 2)
    assert first_amount is not None
    assert second_amount is not None
    first_amount.setText("1000")
    second_amount.setText("250.50")

    assert "1250.50" in w.lab_sum.text()

    payload = json.loads((tmp_path / "company_expenses.json").read_text(encoding="utf-8"))
    assert "fixed" in payload
    assert isinstance(payload["fixed"], list)
    assert len(payload["fixed"]) >= 2


def test_wydatki_zmienne_recalculates_real_hour(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
    from src.tabs.wydatki_zmienne.tab_wydatki_zmienne import TabWydatkiZmienne

    store = CompanyExpensesStoreJson()
    store.save_items("fixed", [{"name": "Wynajem", "amount": 1600.0}])
    store.save_items("variable", [{"name": "Paliwo", "amount": 3200.0}])
    store.save_workforce(workers_count=2, hours_per_worker=160.0)

    w = TabWydatkiZmienne()
    assert "1600.00" in w.lab_sum_fixed.text()
    assert "3200.00" in w.lab_sum_variable.text()
    assert "4800.00" in w.lab_sum_total.text()
    assert "320.00 h" in w.lab_hours_total.text()
    assert "15.00 zl/h" in w.lab_real_hour.text()
