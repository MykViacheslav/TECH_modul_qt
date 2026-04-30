from __future__ import annotations

from pathlib import Path


def test_dashboard_v1_page_contains_confidence_and_drill_through_contract() -> None:
    page_path = Path("frontend/src/app/dashboard/page.tsx")
    source = page_path.read_text(encoding="utf-8")

    # Trust contract
    assert "READY" in source
    assert "PARTIAL" in source
    assert "Open source module" in source

    # Six required operational blocks
    assert "Order / Pipeline Health" in source
    assert "Pricing Quality" in source
    assert "Production Risk" in source
    assert "Time / Kiosk Activity" in source
    assert "Materials & Procurement" in source
    assert "Invoice Processing Control" in source

    # Explicit warning that PARTIAL data should be treated carefully.
    assert "READY metrics are normal KPI. PARTIAL metrics are shown as preview or warning." in source


def test_dashboard_v1_uses_backend_endpoint_not_frontend_formula_dashboard() -> None:
    api_path = Path("frontend/src/services/api.ts")
    api_source = api_path.read_text(encoding="utf-8")

    assert "/api/dashboard/v1" in api_source
    assert "getDashboardV1" in api_source
