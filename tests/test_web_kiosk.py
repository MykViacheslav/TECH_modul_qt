from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen


def _request_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_web_kiosk_http_routes_and_clocking(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    from src.domain.worker_models import WorkerDef
    from src.server.data_server import DataServer
    from src.server.kiosk_service import KioskService
    from src.storage.work_time_session_store_json import WorkTimeSessionStoreJson
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.widgets.qr_utils import worker_qr_payload

    class FixedClock:
        current = datetime(2026, 3, 27, 8, 0, 0)

        @classmethod
        def now(cls):
            return cls.current

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    session_store = WorkTimeSessionStoreJson(path=tmp_path / "work_time_sessions.json")
    worker_store.save_new(WorkerDef(name="Jan Kowalski", worker_id="W001", pin_code="246810", role="Produkcja"))

    service = KioskService(
        worker_store=worker_store,
        work_time_store=work_time_store,
        session_store=session_store,
        now_func=FixedClock.now,
    )
    server = DataServer(host="127.0.0.1", port=0, kiosk_service=service)
    server.start(background=True)
    try:
        assert server._server is not None
        port = server._server.server_port

        for _ in range(30):
            try:
                health = _request_json(f"http://127.0.0.1:{port}/api/health")
                if health.get("status") == "ok":
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise AssertionError("server did not become ready")

        kiosk_html = urlopen(f"http://127.0.0.1:{port}/kiosk", timeout=5).read().decode("utf-8")
        assert "TECH_modul" in kiosk_html
        assert "kiosk czasu pracy" in kiosk_html.lower()

        scan = _request_json(
            f"http://127.0.0.1:{port}/api/kiosk/scan",
            method="POST",
            body={"qr_text": worker_qr_payload("W001", "Jan Kowalski")},
        )
        assert scan["ok"] is True
        assert scan["worker"]["worker_id"] == "W001"

        pin_scan = _request_json(
            f"http://127.0.0.1:{port}/api/kiosk/scan",
            method="POST",
            body={"qr_text": "246810"},
        )
        assert pin_scan["ok"] is True
        assert pin_scan["worker"]["pin_code"] == "246810"

        start = _request_json(
            f"http://127.0.0.1:{port}/api/kiosk/action",
            method="POST",
            body={"worker_id": "W001", "action": "start", "work_type": "Produkcja"},
        )
        assert start["ok"] is True
        assert session_store.get("W001") is not None

        FixedClock.current = FixedClock.current + timedelta(minutes=90)
        finish = _request_json(
            f"http://127.0.0.1:{port}/api/kiosk/action",
            method="POST",
            body={"worker_id": "W001", "action": "finish", "work_type": "Produkcja"},
        )
        assert finish["ok"] is True
        assert session_store.get("W001") is None

        sheet = work_time_store.get_sheet("Jan Kowalski", 2026, 3)
        assert len(sheet.entries) == 1
        assert sheet.entries[0].hours == 1.5
        assert sheet.entries[0].start_time == "08:00"
        assert sheet.entries[0].end_time == "09:30"
    finally:
        server.stop()
