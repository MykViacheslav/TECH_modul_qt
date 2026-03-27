from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.baza_materialu import tab_baza_materialu as module


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


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


@pytest.mark.gui
def test_material_entry_pick_from_library_autofills_and_locks(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()
    monkeypatch.setattr(module, "ProducerLibraryPickerDialog", _FakeDialog)

    w = module.TabBazaMaterialu()
    w._show_material_entry_bar()
    w._pick_material_from_library()

    assert w.cb_mat_typ.currentText() == "plyta"
    assert w.ed_mat_nazwa.text() == "EGGER U999 ST2"
    assert w.ed_mat_grub.text() == "18"
    assert w.ed_mat_param.text() == "U999 ST2"
    assert w.ed_mat_cena.text() == "289"
    assert w.cb_mat_typ.isEnabled() is False
    assert w.ed_mat_nazwa.isReadOnly() is True
    assert w.ed_mat_cena.isReadOnly() is False
    w.close()


@pytest.mark.gui
def test_library_search_matches_code_and_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    _app()

    w = module.TabBazaMaterialu()
    w.btn_toggle_library.setChecked(True)
    w.ed_library_search.setText("SV-LOOX-16")
    rows = w._library_rows_filtered()
    assert len(rows) == 1
    assert rows[0]["producent"] == "SEVROLL"

    w.ed_library_search.setText("Antiscratch")
    rows = w._library_rows_filtered()
    assert len(rows) == 1
    assert rows[0]["producent"] == "ADLER"
    w.close()
