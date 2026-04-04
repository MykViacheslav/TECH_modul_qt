from __future__ import annotations

import json
from pathlib import Path

from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson


def test_order_store_migrates_legacy_map_and_writes_schema_wrapper(tmp_path):
    path = tmp_path / "orders.json"
    path.write_text(
        json.dumps(
            {
                "ORD-001": {
                    "client_name": "Klient A",
                    "status": "Nowe",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    store = OrderStoreJson(path=path)
    order = store.get("ORD-001")
    assert order is not None
    assert order.code == "ORD-001"

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("schema_version") == 2
    assert isinstance(raw.get("items"), dict)
    assert raw["items"]["ORD-001"]["code"] == "ORD-001"


def test_worker_store_migrates_missing_name_from_key(tmp_path):
    path = tmp_path / "workers.json"
    path.write_text(
        json.dumps(
            {
                "Andrii Borshch": {
                    "role": "produkcja",
                    "phone": "123",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    store = WorkerStoreJson(path=path)
    worker = store.get("Andrii Borshch")
    assert worker is not None
    assert worker.name == "Andrii Borshch"

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("schema_version") == 2
    assert raw["items"]["Andrii Borshch"]["name"] == "Andrii Borshch"


def test_work_time_store_migrates_key_based_sheet_metadata(tmp_path):
    path = tmp_path / "work_time.json"
    path.write_text(
        json.dumps(
            {
                "Emilia Kmita|2026-03": {
                    "entries": [],
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    store = WorkTimeStoreJson(path=path)
    sheet = store.get_sheet("Emilia Kmita", 2026, 3)
    assert sheet.worker_name == "Emilia Kmita"
    assert sheet.year == 2026
    assert sheet.month == 3

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("schema_version") == 2
    assert raw["items"]["Emilia Kmita|2026-03"]["worker_name"] == "Emilia Kmita"
    assert int(raw["items"]["Emilia Kmita|2026-03"]["year"]) == 2026
    assert int(raw["items"]["Emilia Kmita|2026-03"]["month"]) == 3

