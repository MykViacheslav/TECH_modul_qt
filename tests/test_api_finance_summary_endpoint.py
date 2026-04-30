from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_finance_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "finance_summary.db"
    manager = TechModulDataManager(db_path=str(db_path))
    project_id = manager.create_project("P_FIN", "Client Fin")
    manager.update_project_margin(project_id, 40)

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client Fin", "Order A", "2026-06-11", 10000.0, "DRAFT"),
        )
        cursor.execute(
            "INSERT INTO orders (project_id, client_name, title, deadline, budget, status) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, "Client Fin", "Order B", "2026-06-21", 5000.0, "PENDING"),
        )
        conn.commit()

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = asyncio.run(main_api.get_project_finance_summary(project_id))
    finally:
        main_api.data_manager = previous_manager

    assert payload["project_id"] == project_id
    assert payload["project_title"] == "P_FIN"
    assert payload["client_name"] == "Client Fin"
    assert int(payload["margin"]) == 40
    assert int(payload["orders_count"]) == 2
    assert float(payload["base_cost"]) == 15000.0
    assert float(payload["total_net"]) == 21000.0
    assert float(payload["profit"]) == 6000.0
    assert float(payload["vat"]) == 4830.0
    assert float(payload["total_gross"]) == 25830.0
