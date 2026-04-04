import json
import os
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.usefixtures("tmp_path")
def test_end_to_end_dialog_adds_material_to_shopping(tmp_path, monkeypatch):
    # Prepare temp data dir
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    data_dir = tmp_path / 'data'
    # 1) Materials: M0002 with zero stock
    baza = {
        "rows": [
            {"id": "M0002", "typ": "front", "nazwa": "Front lakierowany", "producent": "", "parametry": "", "grubosc": "12", "cena_zl": "90", "ostatnia_cena": "", "dostawca": "", "ilosc": "", "ilosc_magazyn": "0", "pracownik": "", "data_wpisu": "2026-03-29", "zakup": "", "numer_faktury": "", "data_zakupu": "", "suma_zam_kw": "", "suma_za_szt": ""}
        ]
    }
    (data_dir / "baza_materialu.json").write_text(json.dumps(baza), encoding="utf-8")
    # 2) Service components: one material for service S1
    comps = {
        "rows": [
            {
                "component_id": "C0001",
                "service_id": "S1",
                "component_type": "material",
                "ref_id": "M0002",
                "name": "Front lakierowany",
                "quantity": 2,
                "unit": "kg",
                "estimated_cost": 90.0,
                "note": "",
            }
        ]
    }
    (data_dir / "service_components.json").write_text(json.dumps(comps), encoding="utf-8")
    # 3) Prepare environment for shopping_list.json (empty initial state)
    (data_dir / "shopping_list.json").write_text("[]", encoding="utf-8")

    app = _ensure_app()
    # Import after app ready to avoid import-time PyQt issues
    from src.tabs.uslugi.tab_uslugi import _ServiceComponentDialog
    dialog = _ServiceComponentDialog(service_id="S1")
    dialog._load_components()
    # Accept to trigger end-to-end logic (add to shopping if stock <= 0)
    dialog.accept()

    # Verify shopping list has an entry for M0002
    from src.storage.shopping_list_store_json import ShoppingListStoreJson
    store = ShoppingListStoreJson()
    items = store.list_items()
    found = any(it.material_id == "M0002" for it in items)
    assert found, f"Expected a shopping item for M0002, got: {[(i.material_id, i.quantity_needed) for i in items]}"
