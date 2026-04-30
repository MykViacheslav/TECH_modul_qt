from __future__ import annotations

import asyncio
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager


def test_create_and_list_clients_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "db_clients.db"
    manager = TechModulDataManager(db_path=str(db_path))

    previous_manager = main_api.data_manager
    try:
        main_api.data_manager = manager
        created = asyncio.run(
            main_api.create_client(
                main_api.ClientCreate(
                    name="Klient Testowy",
                    location="Warszawa",
                    address="ul. Testowa 1",
                    email="klient@test.pl",
                    phone="+48 600 700 800",
                    type="b2b",
                    status="vip",
                )
            )
        )
        assert created["status"] == "success"
        assert int(created["id"]) > 0

        listed = asyncio.run(main_api.get_clients())
    finally:
        main_api.data_manager = previous_manager

    assert len(listed) >= 1
    first = listed[0]
    assert first["name"] == "Klient Testowy"
    assert first["address"] == "ul. Testowa 1"
    assert first["email"] == "klient@test.pl"
    assert first["phone"] == "+48 600 700 800"
    assert first["type"] == "b2b"
    assert first["status"] == "vip"
