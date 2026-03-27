from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import src.tabs.baza_materialu.tab_baza_materialu as module


class _FakeDialog:
    def __init__(self, _parent, _rows):
        self._entry = {
            "kod": "EG-U999-ST2-18",
            "typ": "plyta",
            "nazwa": "EGGER U999 ST2",
            "producent": "EGGER",
            "parametry": "U999 ST2",
            "grubosc": "18",
            "cena_zl": "289",
        }

    def exec(self):
        return module.QDialog.DialogCode.Accepted

    def selected_entry(self):
        return dict(self._entry)


def run() -> None:
    data_dir = Path(os.environ.get("TECH_MODUL_DATA_DIR", "").strip() or "")
    if not data_dir:
        data_dir = Path.cwd() / "tmp_mat_library_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TECH_MODUL_DATA_DIR"] = str(data_dir)
    os.environ["TECH_MODUL_TESTING"] = "1"

    app = QApplication.instance() or QApplication([])
    w = module.TabBazaMaterialu()

    w.btn_toggle_library.setChecked(True)
    w.ed_library_search.setText("SV-LOOX-16")
    rows = w._library_rows_filtered()
    print("rows for code SV-LOOX-16:", len(rows))
    assert len(rows) == 1
    assert rows[0]["producent"] == "SEVROLL"

    module.ProducerLibraryPickerDialog = _FakeDialog
    w._show_material_entry_bar()
    w._pick_material_from_library()
    print("picked name:", w.ed_mat_nazwa.text())
    assert w.ed_mat_nazwa.text() == "EGGER U999 ST2"
    assert w.cb_mat_typ.currentText() == "plyta"
    assert w.cb_mat_typ.isEnabled() is False
    assert w.ed_mat_nazwa.isReadOnly() is True
    assert w.ed_mat_cena.isReadOnly() is False
    print("Material library picker: OK")

    w.close()
    app.processEvents()


if __name__ == "__main__":
    run()
