from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.app.app_settings import save_ui_string_list


def test_tab_modul_shortcuts_focus_name_and_save_strategy(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.show()
    app.processEvents()

    w._shortcut_focus_name.activated.emit()
    app.processEvents()
    assert w.dim.ed_name.hasFocus() is True

    calls = {"save": 0, "overwrite": 0}
    monkeypatch.setattr(w, "_on_save_new", lambda: calls.__setitem__("save", calls["save"] + 1))
    monkeypatch.setattr(w, "_on_overwrite", lambda: calls.__setitem__("overwrite", calls["overwrite"] + 1))

    w.dim.ed_name.setText("MOD-SHORT-1")
    monkeypatch.setattr(w, "_store_has", lambda _name: False)
    w._shortcut_save_module()
    assert calls["save"] == 1
    assert calls["overwrite"] == 0

    monkeypatch.setattr(w, "_store_has", lambda _name: True)
    w._shortcut_save_module()
    assert calls["save"] == 1
    assert calls["overwrite"] == 1

    w.close()


def test_tab_modul_shortcuts_can_be_loaded_from_settings_and_quick_bar_works(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    save_ui_string_list(
        "modul_shortcuts_v2",
        [
            "save=Ctrl+Alt+S",
            "overwrite=Ctrl+Alt+Shift+S",
            "load=Ctrl+Alt+L",
            "new=Ctrl+Alt+N",
            "focus_name=Ctrl+Alt+F",
            "toggle_front=Ctrl+Alt+H",
        ],
    )

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.show()
    app.processEvents()

    assert w._shortcut_focus_name.key().toString() == "Ctrl+Alt+F"

    calls = {"save": 0}
    monkeypatch.setattr(w, "_on_save_new", lambda: calls.__setitem__("save", calls["save"] + 1))
    monkeypatch.setattr(w, "_store_has", lambda _name: False)
    w.btn_q_save.click()
    assert calls["save"] == 1

    w.btn_q_drawers.click()
    assert str(w.fhw.cb_facade_mode.currentData() or "") == "drawers"

    before = bool(w.fhw.chk_temp_hide_front.isChecked())
    w._shortcut_toggle_front.activated.emit()
    app.processEvents()
    after = bool(w.fhw.chk_temp_hide_front.isChecked())
    assert after is (not before)

    w.close()
