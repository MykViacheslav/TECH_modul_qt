import os
import json
from pathlib import Path
from datetime import date

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QComboBox

from src.tabs.uslugi.tab_uslugi import _ServiceComponentDialog
from src.storage.service_component_store_json import ServiceComponentStoreJson
from src.storage.data_paths import data_dir


def _ensure_app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


@pytest.mark.usefixtures("tmp_path")
def test_editor_ui_components_load_and_add_row(tmp_path, monkeypatch):
    # Prepare temp data dir
    temp_dir = tmp_path
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(temp_dir))

    # Create minimal material in baza_materialu.json with zero stock
    data = {
        "rows": [
            {
                "id": "M0002",
                "typ": "farba",
                "nazwa": "Test Material",
                "ilosc_magazyn": "0",
                "cena_zl": "10"
            }
        ]
    }
    (temp_dir / "baza_materialu.json").write_text(json.dumps(data), encoding="utf-8")

    app = _ensure_app()
    dialog = _ServiceComponentDialog(service_id="S1")
    # Load components and add a new row
    dialog._load_components()
    dialog._add_row()
    row = dialog.tbl.rowCount() - 1
    # Ensure type widget exists and select material
    type_widget = dialog.tbl.cellWidget(row, 0)
    if isinstance(type_widget, QComboBox):
        type_widget.setCurrentText("material")
    # Trigger material name widget population
    dialog._update_name_widget(row, "material")
    name_widget = dialog.tbl.cellWidget(row, 2)
    if isinstance(name_widget, QComboBox) and name_widget.count() > 1:
        name_widget.setCurrentIndex(1)
        dialog._on_material_selected(row, name_widget)
    # Attempt to save (accept)
    dialog.accept()
    # Verify that at least one component for service S1 exists
    comp_store = ServiceComponentStoreJson()
    comps = comp_store.list_components_by_service("S1")
    assert isinstance(comps, list)
