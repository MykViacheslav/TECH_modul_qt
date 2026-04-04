import json
from pathlib import Path
import os

import pytest

from src.storage.shopping_list_store_json import ShoppingListStoreJson


def _prepare_data_dir(tmp_path: Path):
    os.environ["TECH_MODUL_DATA_DIR"] = str(tmp_path)
    # Minimal materials entry to ensure exists (stock = 0)
    baza = {
        "rows": [
            {
                "id": "M0002",
                "typ": "farba",
                "nazwa": "Test Material",
                "cena_zl": "0",
                "ilosc_magazyn": "0",
            }
        ]
    }
    (tmp_path / "baza_materialu.json").write_text(json.dumps(baza), encoding="utf-8")


def test_add_to_shopping_when_zero_stock(tmp_path, monkeypatch):
    _prepare_data_dir(tmp_path)
    store = ShoppingListStoreJson()
    # Ensure clean state
    path = (tmp_path / "shopping_list.json").as_posix()
    if Path(path).exists():
        Path(path).unlink()
    # Add a shopping item for material with id M0002 (stock is 0)
    store.add_shopping_item(material_id="M0002", material_name="Test Material", quantity=2, unit="kg")
    items = store.list_items()
    assert any(it.material_id == "M0002" for it in items)
