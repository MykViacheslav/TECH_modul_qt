from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api import main_api
from src.api.data_manager import TechModulDataManager
from src.core.operations_models import RouteTaskRecord
from src.core.operations_store import OperationsStore
from src.domain.worker_models import WorkerDef
from src.server.kiosk_service import KioskService
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.work_time_session_store_json import WorkTimeSessionStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson


def _make_kiosk_service(tmp_path: Path) -> KioskService:
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.overwrite(
        WorkerDef(
            name="Jan Kowalski",
            worker_id="W001",
            pin_code="1234",
            role="Operator",
        )
    )
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    session_store = WorkTimeSessionStoreJson(path=tmp_path / "work_time_sessions.json")
    return KioskService(
        worker_store=worker_store,
        work_time_store=work_time_store,
        session_store=session_store,
        now_func=lambda: datetime(2026, 4, 23, 12, 0, 0),
    )


def test_kiosk_state_endpoint_and_linkage_persistence(tmp_path: Path) -> None:
    service = _make_kiosk_service(tmp_path)
    previous = main_api.kiosk_service
    try:
        main_api.kiosk_service = service

        state = asyncio.run(main_api.get_kiosk_state("W001"))
        assert state["ok"] is True
        assert state["worker"]["worker_id"] == "W001"

        action_req = main_api.KioskActionRequest(
            worker_id="W001",
            action="start",
            work_type="Produkcja",
            project_code="PRJ-77",
            order_id="77",
            workstation="CNC",
            note="test-note",
        )
        started = asyncio.run(main_api.kiosk_action(action_req))
        assert started["ok"] is True
        assert started["session"]["project_code"] == "PRJ-77"
        assert started["session"]["order_id"] == "77"
        assert started["session"]["workstation"] == "CNC"

        finished = asyncio.run(
            main_api.kiosk_action(
                main_api.KioskActionRequest(
                    worker_id="W001",
                    action="finish",
                    project_code="PRJ-77",
                    order_id="77",
                    workstation="CNC",
                    note="test-note",
                )
            )
        )
        assert finished["ok"] is True
        assert finished["entry"]["project_code"] == "PRJ-77"
        assert "order_id=77" in str(finished["entry"]["note"])
        assert "workstation=CNC" in str(finished["entry"]["note"])
    finally:
        main_api.kiosk_service = previous


def test_production_task_action_requires_worker_id_and_persists_actor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = OperationsStore()
    saved = store.add_route_task(
        RouteTaskRecord(
            task_type="CNC",
            project_name="Projekt A",
            client_name="Klient A",
            status="planowane",
            planned_date="2026-04-23",
        )
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            main_api.production_task_action(
                {"task_id": saved.id, "worker_name": "Jan", "action": "start"}
            )
        )
    assert exc.value.status_code == 400

    res = asyncio.run(
        main_api.production_task_action(
            {
                "task_id": saved.id,
                "worker_id": "W001",
                "worker_name": "Jan Kowalski",
                "action": "start",
                "note": "start test",
            }
        )
    )
    assert res["status"] == "success"
    assert res["actor"]["worker_id"] == "W001"

    refreshed = OperationsStore().get_route_task(saved.id)
    assert refreshed is not None
    assert refreshed.crew == "W001"
    assert "W001 (Jan Kowalski): start" in str(refreshed.notes or "")


def test_production_status_uses_real_progress_formula(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = OperationsStore()
    store.add_route_task(
        RouteTaskRecord(task_type="CNC", status="planowane", project_name="P1", client_name="C1", planned_date="2026-04-23")
    )
    store.add_route_task(
        RouteTaskRecord(task_type="CNC", status="w_trakcie", project_name="P2", client_name="C2", planned_date="2026-04-23")
    )
    store.add_route_task(
        RouteTaskRecord(task_type="CNC", status="zakończone", project_name="P3", client_name="C3", planned_date="2026-04-23")
    )

    status = asyncio.run(main_api.get_production_status())
    cnc = next((w for w in status["workstations"] if str(w.get("id")) == "CNC"), None)
    assert cnc is not None
    # Formula: (done + 0.5 * in_progress) / total = (1 + 0.5) / 3 = 50%
    assert int(cnc["progress"]) == 50


def test_order_status_update_endpoint_for_handoff(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "orders_handoff.db"))
    previous = main_api.data_manager
    try:
        main_api.data_manager = manager
        project_id = manager.create_project("P_HANDOFF", "Client H")
        created = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Client H",
                title="Order H",
                status="Rysunek",
            )
        )
        order_id = int(created["id"])
        updated = asyncio.run(
            main_api.update_order_status_api(
                order_id,
                main_api.OrderStatusUpdate(status="Produkcja", worker="W001"),
            )
        )
        assert updated["status"] == "success"
    finally:
        main_api.data_manager = previous
