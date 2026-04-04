from PyQt6.QtWidgets import QApplication


def test_dimensions_block_has_new_and_clear_buttons():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.dimensions_block import DimensionsBlock

    w = DimensionsBlock()
    assert hasattr(w, "btn_new")
    assert hasattr(w, "btn_clear")
    assert w.btn_new.text() == "Nowy"
    assert w.btn_clear.text() == "Wyczysc"


def test_tab_modul_crud_buttons_enabled_only_for_existing_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    monkeypatch.setattr(w, "_store_has", lambda _name: False)
    w.dim.ed_name.setText("MOD_UI_STATE")
    w._refresh_crud_action_state()
    assert w.btn_q_overwrite.isEnabled() is False
    assert w.btn_q_delete.isEnabled() is False
    assert w.dim.btn_over.isEnabled() is False
    assert w.dim.btn_del.isEnabled() is False

    monkeypatch.setattr(w, "_store_has", lambda _name: True)
    w._refresh_crud_action_state()
    assert w.btn_q_overwrite.isEnabled() is True
    assert w.btn_q_delete.isEnabled() is True
    assert w.dim.btn_over.isEnabled() is True
    assert w.dim.btn_del.isEnabled() is True


def test_tab_modul_load_shortcut_points_to_preview_dialog(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    handler = w._shortcut_actions["load"][1]
    assert getattr(handler, "__name__", "") == "_on_load_from_base_preview"


def test_tab_modul_mini_preview_info_updates_from_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.dim.ed_name.setText("TEST_PREVIEW_INFO")
    w.dim.sp_w.setValue(812.0)
    w.dim.sp_h.setValue(745.0)
    w.dim.sp_d.setValue(503.0)
    w._on_any_change()

    info = str(w.preview_info.text() or "")
    assert "TEST_PREVIEW_INFO" in info
    assert "812 x 745 x 503 mm" in info


def test_tab_modul_delete_skips_when_name_not_in_store(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.dim.ed_name.setText("NIE_MA_W_BAZIE")

    calls = {"delete": 0}

    monkeypatch.setattr(w, "_store_has", lambda _name: False)

    def _fake_delete(_name: str) -> None:
        calls["delete"] += 1

    monkeypatch.setattr(w, "_store_delete", _fake_delete)

    w._on_dim_delete_clicked()

    assert calls["delete"] == 0
    assert w.btn_q_delete.isEnabled() is False
