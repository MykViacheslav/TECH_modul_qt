from __future__ import annotations

from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_system_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "system_summary.db"
    manager = TechModulDataManager(db_path=str(db_path))
    manager.create_project("P_SYS", "Client SYS")

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        payload = main_api.get_system_summary()
    finally:
        main_api.data_manager = previous_manager

    assert payload["status"] == "online"
    assert isinstance(payload["api_version"], str)
    assert payload["engine"] == "TECH-V4"
    assert "db" in payload
    assert int(payload["db"]["projects_count"]) >= 1
