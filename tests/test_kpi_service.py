from __future__ import annotations

from datetime import date, timedelta

from src.domain.order_models import OrderDef
from src.domain.shopping_models import ShoppingItemDef
from src.services.kpi_service import KPIService, SupplierKPI
from src.storage.order_store_json import OrderStoreJson
from src.storage.shopping_list_store_json import ShoppingListStoreJson


def _shopping_item(
    item_id: str,
    added_date: str,
    supplier: str,
    qty: float,
    price_actual: float,
) -> ShoppingItemDef:
    return ShoppingItemDef(
        item_id=item_id,
        material_id=f"M_{item_id}",
        material_name=f"Material {item_id}",
        quantity_needed=qty,
        unit="szt",
        added_date=added_date,
        status="zakupiono",
        supplier=supplier,
        price_actual=price_actual,
    )


def test_get_monthly_purchases_returns_data(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    shopping = ShoppingListStoreJson()
    today = date.today()
    previous = today - timedelta(days=31)
    shopping.save_item(_shopping_item("I001", today.isoformat(), "A", qty=2, price_actual=120.0))
    shopping.save_item(_shopping_item("I002", previous.isoformat(), "B", qty=1, price_actual=80.0))

    service = KPIService(cache_ttl_seconds=900)
    rows = service.get_monthly_purchases(months_back=12)

    assert len(rows) == 12
    assert any(row.total_spent > 0 for row in rows)
    assert sum(row.item_count for row in rows) >= 3


def test_kpi_caching_works(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    shopping = ShoppingListStoreJson()
    today = date.today().isoformat()
    shopping.save_item(_shopping_item("I010", today, "A", qty=1, price_actual=100.0))

    service = KPIService(cache_ttl_seconds=3600)
    first_rows = service.get_monthly_purchases(months_back=12)
    first_total = sum(row.total_spent for row in first_rows)

    shopping.save_item(_shopping_item("I011", today, "A", qty=1, price_actual=200.0))
    cached_rows = service.get_monthly_purchases(months_back=12)
    cached_total = sum(row.total_spent for row in cached_rows)
    assert cached_total == first_total

    service.refresh()
    refreshed_rows = service.get_monthly_purchases(months_back=12)
    refreshed_total = sum(row.total_spent for row in refreshed_rows)
    assert refreshed_total > first_total


def test_get_supplier_kpis_returns_expected_structure(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    shopping = ShoppingListStoreJson()
    today = date.today().isoformat()
    shopping.save_item(_shopping_item("I020", today, "Alpha", qty=2, price_actual=50.0))
    shopping.save_item(_shopping_item("I021", today, "Beta", qty=1, price_actual=200.0))

    orders = OrderStoreJson()
    orders.save_new(
        OrderDef(
            code="ZAM-1",
            client_name="Test",
            customer_payments=[{"date": today, "amount": 300.0, "paid": True}],
        )
    )

    service = KPIService(cache_ttl_seconds=900)
    rows = service.get_supplier_kpis()

    assert rows
    assert all(isinstance(row, SupplierKPI) for row in rows)
    assert all(row.total_spent >= 0 for row in rows)
    assert all(0.0 <= row.share_percent <= 100.0 for row in rows)


def test_dashboard_payload_contains_kpi_kri_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    today = date.today()
    closed_on_time = today - timedelta(days=2)
    closed_late = today - timedelta(days=1)

    orders = [
        OrderDef(
            code="KPI-1",
            status="Zakonczone",
            date_montaz_end=(today - timedelta(days=1)).isoformat(),
            status_history=[
                {"to_status": "Zakonczone", "changed_at": closed_on_time.isoformat()},
            ],
            customer_payments=[
                {"date": today.isoformat(), "amount": 1200.0, "paid": True},
                {"date": (today - timedelta(days=15)).isoformat(), "amount": 400.0, "paid": False},
            ],
        ),
        OrderDef(
            code="KPI-2",
            status="Zakonczone",
            date_montaz_end=(today - timedelta(days=6)).isoformat(),
            status_history=[
                {"to_status": "Zakonczone", "changed_at": closed_late.isoformat()},
            ],
            customer_payments=[
                {"date": (today - timedelta(days=20)).isoformat(), "amount": 700.0, "paid": False},
            ],
        ),
        OrderDef(
            code="KPI-3",
            status="Poprawki",
            date_poprawki=today.isoformat(),
            notes="Reklamacja klienta",
        ),
    ]

    class _OrderStoreStub:
        def __init__(self, rows):
            self._rows = list(rows)

        def list_orders(self):
            return list(self._rows)

    service = KPIService(
        data_store={
            "orders": _OrderStoreStub(orders),
        },
        cache_ttl_seconds=900,
    )
    payload = service.build_dashboard_payload()
    summary = dict(payload.get("kpi_kri", {}) or {})
    kpi = dict(summary.get("kpi", {}) or {})
    kri = dict(summary.get("kri", {}) or {})
    meta = dict(summary.get("meta", {}) or {})

    assert kpi
    assert kri
    assert str(meta.get("period", "")).startswith(f"{today.year:04d}-")
    assert float(kpi.get("revenue_month", 0.0)) >= 1200.0
    assert int(kpi.get("closed_orders_count", 0)) >= 1
    assert int(meta.get("on_time_sample_size", 0)) >= 1
    assert int(kri.get("rework_orders_count", 0)) >= 1
    assert float(kri.get("overdue_invoices_value", 0.0)) >= 1100.0
    assert int(kri.get("complaints_count", 0)) >= 1


def test_dashboard_payload_respects_range_days_for_payments(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    today = date.today()
    old_date = (today - timedelta(days=250)).isoformat()
    recent_date = (today - timedelta(days=10)).isoformat()

    orders = [
        OrderDef(
            code="RANGE-1",
            customer_payments=[
                {"date": old_date, "amount": 1000.0, "paid": True},
                {"date": recent_date, "amount": 500.0, "paid": True},
            ],
        )
    ]

    class _OrderStoreStub:
        def __init__(self, rows):
            self._rows = list(rows)

        def list_orders(self):
            return list(self._rows)

    service = KPIService(data_store={"orders": _OrderStoreStub(orders)}, cache_ttl_seconds=900)

    payload_all = service.build_dashboard_payload()
    payload_30 = service.build_dashboard_payload(range_days=30)
    summary_30 = dict(payload_30.get("kpi_kri", {}) or {})
    meta_30 = dict(summary_30.get("meta", {}) or {})

    assert float(payload_all.get("total_paid", 0.0)) >= 1500.0
    assert float(payload_30.get("total_paid", 0.0)) == 500.0
    assert int(meta_30.get("range_days", 0) or 0) == 30
    assert ".." in str(meta_30.get("period", "") or "")
