import json
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.usefixtures("tmp_path")
def test_end_to_end_no_gui_add_to_shopping(tmp_path, monkeypatch):
    # Prepare temporary data dir for no-GUI end-to-end
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    data_dir = tmp_path
    # Create material with zero stock M0001
    baza = {"rows": [ {"id": "M0001", "typ": "korpus", "nazwa": "Korpus Dąb", "producent": "", "parametry": "", "grubosc": "18", "cena_zl": "120", "ostatnia_cena": "", "dostawca": "", "ilosc": "", "ilosc_magazyn": "0", "pracownik": "", "data_wpisu": "2026-03-29", "zakup": "", "numer_faktury": "", "data_zakupu": "", "suma_zam_kw": "", "suma_za_szt": ""} ] }
    (data_dir / "baza_materialu.json").write_text(json.dumps(baza), encoding="utf-8")
    # Shopping store: add item directly (no GUI path)
    from src.storage.shopping_list_store_json import ShoppingListStoreJson
    store = ShoppingListStoreJson()
    store.add_shopping_item(material_id="M0001", material_name="Korpus Dąb", quantity=1, unit="szt")
    items = store.list_items()
    assert any(it.material_id == "M0001" for it in items)
