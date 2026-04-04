import json
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QComboBox


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.usefixtures("tmp_path")
def test_end_to_end_full_flow_with_material_to_shopping(tmp_path, monkeypatch):
    # Setup temporary data dir
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    data_dir = tmp_path
    # 1) Add material with stock 0 to baza_materialu.json
    baza = {"rows": [ {"id": "M0002", "typ": "front", "nazwa": "Front lakierowany", "producent": "", "parametry": "", "grubosc": "12", "cena_zl": "90", "ostatnia_cena": "", "dostawca": "", "ilosc": "", "ilosc_magazyn": "0", "pracownik": "", "data_wpisu": "2026-03-29", "zakup": "", "numer_faktury": "", "data_zakupu": "", "suma_zam_kw": "", "suma_za_szt": ""} ] }
    (data_dir / "baza_materialu.json").write_text(json.dumps(baza), encoding="utf-8")
    # 2) Create a service component for S1 referencing M0002
    comps = {"rows": [ {"component_id": "C0001", "service_id": "S1", "component_type": "material", "ref_id": "M0002", "name": "Front lakierowany", "quantity": 2, "unit": "kg", "estimated_cost": 90.0, "note": ""} ]}
    (data_dir / "service_components.json").write_text(json.dumps(comps), encoding="utf-8")
    # 3) Initialize an empty shopping list
    (data_dir / "shopping_list.json").write_text("[]", encoding="utf-8")

    app = _ensure_app()
    from src.tabs.uslugi.tab_uslugi import _ServiceComponentDialog
    dialog = _ServiceComponentDialog(service_id="S1")
    dialog._load_components()
    dialog._add_row()
    row = dialog.tbl.rowCount() - 1
    # Ensure material type and select the first material in list
    type_widget = dialog.tbl.cellWidget(row, 0)
    if isinstance(type_widget, QComboBox):
        type_widget.setCurrentText("material")
    dialog._update_name_widget(row, "material")
    name_widget = dialog.tbl.cellWidget(row, 2)
    if isinstance(name_widget, QComboBox) and name_widget.count() > 1:
        name_widget.setCurrentIndex(1)
        dialog._on_material_selected(row, name_widget)
    # Accept edits to trigger end-to-end flow
    dialog.accept()

    # Verify shopping item added for M0002
    from src.storage.shopping_list_store_json import ShoppingListStoreJson
    store = ShoppingListStoreJson()
    items = store.list_items()
    assert any(it.material_id == "M0002" for it in items)
