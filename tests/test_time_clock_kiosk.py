from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QApplication


def test_worker_qr_payload_roundtrip_and_pixmap(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.domain.worker_qr import extract_worker_identifier
    from src.storage.worker_store_json import WorkerStoreJson
    from src.widgets.qr_utils import qr_pixmap_from_text, worker_qr_payload

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.save_new(WorkerDef(name="Jan Kowalski", worker_id="W001", role="Produkcja"))

    payload = worker_qr_payload("W001", "Jan Kowalski")
    assert extract_worker_identifier(payload) == ("W001", "Jan Kowalski")
    assert worker_store.resolve_identifier(payload).name == "Jan Kowalski"
    assert not qr_pixmap_from_text(payload, size=180).isNull()


def test_work_time_store_upsert_day_entry_merges_existing_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.work_time_models import WorkTimeEntryDef
    from src.storage.work_time_store_json import WorkTimeStoreJson

    store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    store.upsert_day_entry(
        "Jan Kowalski",
        2026,
        3,
        WorkTimeEntryDef(day=27, date_iso="2026-03-27", work_type="Produkcja", start_time="08:00", end_time="12:00", hours=4.0),
    )
    store.upsert_day_entry(
        "Jan Kowalski",
        2026,
        3,
        WorkTimeEntryDef(day=27, date_iso="2026-03-27", work_type="Produkcja", start_time="13:00", end_time="17:00", hours=4.0),
    )

    sheet = store.get_sheet("Jan Kowalski", 2026, 3)
    assert len(sheet.entries) == 1
    assert sheet.entries[0].hours == 8.0
    assert sheet.entries[0].start_time == "08:00"
    assert sheet.entries[0].end_time == "17:00"


def test_time_clock_kiosk_start_break_and_finish_writes_monthly_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.storage.work_time_session_store_json import WorkTimeSessionStoreJson
    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.widgets.time_clock_kiosk import TimeClockKioskWindow

    class FixedDateTime(datetime):
        current = datetime(2026, 3, 27, 8, 0, 0)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr("src.widgets.time_clock_kiosk.datetime", FixedDateTime)

    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    work_time_store = WorkTimeStoreJson(path=tmp_path / "work_time.json")
    session_store = WorkTimeSessionStoreJson(path=tmp_path / "work_time_sessions.json")
    worker_store.save_new(WorkerDef(name="Jan Kowalski", worker_id="W001", role="Produkcja"))

    kiosk = TimeClockKioskWindow(
        worker_store=worker_store,
        work_time_store=work_time_store,
        session_store=session_store,
    )

    kiosk.ed_scan.setText("TECH_MODUL_WORKER|ID=W001|NAME=Jan Kowalski")
    kiosk._on_scan_entered()
    assert kiosk._current_worker is not None

    kiosk._start_session()
    assert session_store.get("W001") is not None

    FixedDateTime.current = datetime(2026, 3, 27, 12, 0, 0)
    kiosk._start_break()
    assert session_store.get("W001").break_started_at_iso

    FixedDateTime.current = datetime(2026, 3, 27, 12, 30, 0)
    kiosk._end_break()
    assert session_store.get("W001").break_started_at_iso == ""

    FixedDateTime.current = datetime(2026, 3, 27, 16, 0, 0)
    kiosk._finish_session()

    sheet = work_time_store.get_sheet("Jan Kowalski", 2026, 3)
    assert len(sheet.entries) == 1
    assert sheet.entries[0].hours == 7.5
    assert sheet.entries[0].start_time == "08:00"
    assert sheet.entries[0].end_time == "16:00"
