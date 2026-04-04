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
def test_ui_editor_regression_basic_flow(tmp_path, monkeypatch):
    # Prepare temporary data dir for materials
    tmp = tmp_path
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp))
    # Create a small baza_materialu.json with one material
    data = {
        "rows": [
            {"id": "M_MATX", "typ": "korpus", "nazwa": "Test Material X", "producent": "", "parametry": "", "grubosc": "18", "cena_zl": "120", "ostatnia_cena": "", "dostawca": "", "ilosc": "", "ilosc_magazyn": "0", "pracownik": "", "data_wpisu": "2026-03-29", "zakup": "", "numer_faktury": "", "data_zakupu": "", "suma_zam_kw": "", "suma_za_szt": ""}
        ]
    }
    (tmp / "baza_materialu.json").write_text(json.dumps(data), encoding="utf-8")
    app = _ensure_app()
    from src.tabs.uslugi.tab_uslugi import _ServiceComponentDialog
    dialog = _ServiceComponentDialog(service_id="S1")
    dialog._load_components()
    dialog._add_row()
    comps = dialog.components()
    assert isinstance(comps, list)
    # Try to accept dialog to exercise end-to-end path in a safe way
    dialog.accept()
