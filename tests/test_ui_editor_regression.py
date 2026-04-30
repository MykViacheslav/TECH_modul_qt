import os
import json

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.uslugi.tab_uslugi import _UslugaPanel


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

    # Create minimal material source data
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
    panel = _UslugaPanel()
    initial_rows = panel.tbl.rowCount()
    panel._add_row()
    assert panel.tbl.rowCount() == initial_rows + 1
