from __future__ import annotations

import types

from PyQt6.QtWidgets import QApplication


def _build_loaded_module(tab_modul_module):
    return tab_modul_module.ModuleDef(
        name="LOADED_FROM_DIALOG",
        width_mm=910.0,
        depth_mm=520.0,
        height_mm=770.0,
        visible_parts={"side_left", "side_right", "top", "bottom", "front", "back"},
    )


def test_load_module_cancel_restores_previous_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.modul.tab_modul as tab_modul

    w = tab_modul.TabModul()
    w.dim.sp_w.setValue(801.0)
    w.dim.sp_d.setValue(501.0)
    w.dim.sp_h.setValue(701.0)
    w._on_any_change()

    class _DialogStub:
        DialogCode = types.SimpleNamespace(Accepted=1)

        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return 1

        def result_value(self):
            return types.SimpleNamespace(name="LOADED_FROM_DIALOG", module=_build_loaded_module(tab_modul))

    monkeypatch.setattr(tab_modul, "LoadModuleDialog", _DialogStub)
    monkeypatch.setattr(w, "_is_testing", lambda: False)
    monkeypatch.setattr(tab_modul.QMessageBox, "question", lambda *args, **kwargs: tab_modul.QMessageBox.StandardButton.No)
    monkeypatch.setattr(tab_modul.QMessageBox, "information", lambda *args, **kwargs: tab_modul.QMessageBox.StandardButton.Ok)

    w._on_load_from_base_preview()

    assert abs(w.dim.sp_w.value() - 801.0) < 0.001
    assert abs(w.dim.sp_d.value() - 501.0) < 0.001
    assert abs(w.dim.sp_h.value() - 701.0) < 0.001


def test_load_module_confirm_applies_new_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.modul.tab_modul as tab_modul

    w = tab_modul.TabModul()
    w.dim.sp_w.setValue(801.0)
    w.dim.sp_d.setValue(501.0)
    w.dim.sp_h.setValue(701.0)
    w._on_any_change()

    class _DialogStub:
        DialogCode = types.SimpleNamespace(Accepted=1)

        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return 1

        def result_value(self):
            return types.SimpleNamespace(name="LOADED_FROM_DIALOG", module=_build_loaded_module(tab_modul))

    monkeypatch.setattr(tab_modul, "LoadModuleDialog", _DialogStub)
    monkeypatch.setattr(w, "_is_testing", lambda: False)
    monkeypatch.setattr(tab_modul.QMessageBox, "question", lambda *args, **kwargs: tab_modul.QMessageBox.StandardButton.Yes)

    w._on_load_from_base_preview()

    assert abs(w.dim.sp_w.value() - 910.0) < 0.001
    assert abs(w.dim.sp_d.value() - 520.0) < 0.001
    assert abs(w.dim.sp_h.value() - 770.0) < 0.001

