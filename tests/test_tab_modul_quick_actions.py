from PyQt6.QtWidgets import QApplication


def _build_tab_modul(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])
    from src.tabs.modul.tab_modul import TabModul

    return app, TabModul()


def test_tab_modul_quick_actions_block_exists(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    assert hasattr(w, "blk_quick_actions")
    assert w.blk_quick_actions.objectName() == "blk_quick_actions"
    assert hasattr(w, "btn_left_add_shelf")
    assert hasattr(w, "btn_left_add_divider")
    assert hasattr(w, "btn_left_add_front")
    assert hasattr(w, "btn_left_add_drawer")
    assert hasattr(w, "btn_left_recalc")
    assert hasattr(w, "btn_left_duplicate_selected")
    assert hasattr(w, "btn_left_remove_selected")


def test_quick_action_add_shelf_updates_count_and_visibility(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    w.shelves.set_value(0)
    w.vis.set_part_checked("shelf", False)

    w._quick_action_add_shelf()

    assert w.shelves.get_value() == 1
    assert w.vis.is_part_checked("shelf") is True


def test_quick_action_add_divider_updates_count_and_visibility(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    w.dividers.set_values(0, "right")
    w.vis.set_part_checked("divider", False)

    w._quick_action_add_divider()

    assert w.dividers.get_count() == 1
    assert w.vis.is_part_checked("divider") is True


def test_quick_action_add_front_switches_facade_to_doors(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    idx_drawers = w.fhw.cb_facade_mode.findData("drawers")
    if idx_drawers >= 0:
        w.fhw.cb_facade_mode.setCurrentIndex(idx_drawers)
    w.vis.set_part_checked("front", False)

    w._quick_action_add_front()

    assert str(w.fhw.cb_facade_mode.currentData() or "") == "doors"
    assert w.vis.is_part_checked("front") is True


def test_quick_action_add_drawer_sets_drawers_mode_and_increments_count(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    idx_doors = w.fhw.cb_facade_mode.findData("doors")
    if idx_doors >= 0:
        w.fhw.cb_facade_mode.setCurrentIndex(idx_doors)
    w.fhw.sp_drawer_count.setValue(1)
    w.vis.set_part_checked("front", False)

    w._quick_action_add_drawer()

    assert str(w.fhw.cb_facade_mode.currentData() or "") == "drawers"
    assert w.fhw.sp_drawer_count.value() == 2
    assert w.vis.is_part_checked("front") is True


def test_quick_action_duplicate_selected_shelf_increments_count(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    w.shelves.set_value(1)
    w._selected_part_key = "shelf_1"

    w._quick_action_duplicate_selected()

    assert w.shelves.get_value() == 2


def test_quick_action_remove_selected_shelf_decrements_count(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    w.shelves.set_value(1)
    w.vis.set_part_checked("shelf", True)
    w._selected_part_key = "shelf_1"

    w._quick_action_remove_selected()

    assert w.shelves.get_value() == 0
    assert w.vis.is_part_checked("shelf") is False


def test_quick_action_remove_selected_divider_decrements_count(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    w.dividers.set_values(1, "right")
    w.vis.set_part_checked("divider", True)
    w._selected_part_key = "divider_1"

    w._quick_action_remove_selected()

    assert w.dividers.get_count() == 0
    assert w.vis.is_part_checked("divider") is False


def test_quick_action_duplicate_selected_front_moves_to_drawers(tmp_path, monkeypatch):
    _app, w = _build_tab_modul(tmp_path, monkeypatch)
    idx_doors = w.fhw.cb_facade_mode.findData("doors")
    if idx_doors >= 0:
        w.fhw.cb_facade_mode.setCurrentIndex(idx_doors)
    w.fhw.sp_drawer_count.setValue(1)
    w._selected_part_key = "front"

    w._quick_action_duplicate_selected()

    assert str(w.fhw.cb_facade_mode.currentData() or "") == "drawers"
    assert w.fhw.sp_drawer_count.value() == 2
