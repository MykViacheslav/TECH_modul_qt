from __future__ import annotations

import asyncio
from pathlib import Path

from src.api import main_api


def test_fixed_company_expenses_endpoint_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    payload = main_api.CompanyExpensesUpdatePayload(
        fixed=[
            main_api.CompanyExpenseItemPayload(name="Wynajem", amount=2500.0),
            main_api.CompanyExpenseItemPayload(name="Internet", amount=150.0),
        ],
        workers_count=5,
        hours_per_worker=160.0,
    )

    saved = asyncio.run(main_api.update_fixed_company_expenses(payload))
    assert saved["workers_count"] == 5
    assert saved["hours_per_worker"] == 160.0
    assert saved["metrics"]["fixed_total"] == 2650.0
    assert saved["metrics"]["real_hour_rate"] == 3.31

    loaded = asyncio.run(main_api.get_fixed_company_expenses())
    assert len(loaded["fixed"]) >= 2
    assert any(str(item["name"]) == "Wynajem" for item in loaded["fixed"])
    assert loaded["metrics"]["fixed_total"] == 2650.0
