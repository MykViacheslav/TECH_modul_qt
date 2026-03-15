from PyQt6.QtWidgets import QApplication


def test_tab_modul_expands_group_edgebands_into_module_map(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.mat.set_edgebands({"carcass": "ABS 2.0", "front": "ABS 0.8", "back": "Brak"})
    w._on_any_change()

    assert w._draft.edgebands["carcass"] == "ABS 2.0"
    assert w._draft.edgebands["side"] == "ABS 2.0"
    assert w._draft.edgebands["top"] == "ABS 2.0"
    assert w._draft.edgebands["bottom"] == "ABS 2.0"
    assert w._draft.edgebands["shelf"] == "ABS 2.0"
    assert w._draft.edgebands["divider"] == "ABS 2.0"
    assert w._draft.edgebands["front"] == "ABS 0.8"
    assert w._draft.edgebands["back"] == "Brak"


def test_selected_part_uses_group_default_edgeband(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.vis.set_checked({"side_left", "side_right", "top", "bottom", "front", "back"})
    w.mat.set_edgebands({"carcass": "ABS 2.0", "front": "ABS 0.8", "back": "Brak"})
    w._on_any_change()

    w._selected_part_key = "side_left"
    w.tree.select_part("side_left")
    w._render_right()

    assert w.edge.get_default_edgeband_key() == "ABS 2.0"

    cb_left, combo_left = w.edge._rows["left"]
    cb_left.setChecked(True)
    w._on_edge_changed()

    assert str(combo_left.currentData() or "") == "ABS 2.0"
    assert w._draft.parts["side_left"].edge_banding["left"] == "ABS 2.0"

    w._selected_part_key = "front"
    w.tree.select_part("front")
    w._render_right()

    assert w.edge.get_default_edgeband_key() == "ABS 0.8"
