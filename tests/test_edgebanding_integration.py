from PyQt6.QtWidgets import QApplication


def test_edgebanding_updates_draft_part(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # upewnij sie, ze sa czesci
    w.vis.set_checked({"side_left", "side_right", "top", "bottom", "front", "back", "shelf"})
    w.shelves.set_value(1)
    w._on_any_change()

    assert "side_left" in w._draft.parts

    # wybor elementu
    w._selected_part_key = "side_left"
    w.tree.select_part("side_left")

    # Podstawiamy zrodlo okleiny (nie znamy UI w tescie) - sprawdzamy integracje TabModul.
    w.edge.get_edge_banding = lambda: {"left": "ABS 0,8", "top": "ABS 2,0"}

    w._on_edge_changed()

    assert w._draft.parts["side_left"].edge_banding == {"left": "ABS 0,8", "top": "ABS 2,0"}


def test_render_right_loads_edgebanding_into_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    w.vis.set_checked({"side_left", "side_right", "top", "bottom", "front", "back"})
    w._on_any_change()

    w._selected_part_key = "side_left"
    w.tree.select_part("side_left")

    w._draft.parts["side_left"].edge_banding = {"right": "ABS 0,8"}

    captured = {}

    def cap(d):
        captured["d"] = dict(d or {})

    # przechwytujemy to co TabModul wysyla do bloku okleiny
    if hasattr(w.edge, "load_edge_banding"):
        w.edge.load_edge_banding = cap
    elif hasattr(w.edge, "set_edge_banding"):
        w.edge.set_edge_banding = cap
    else:
        # jesli nie ma metody, test ma jasno powiedziec
        assert False, "EdgeBandingBlock nie ma load_edge_banding/set_edge_banding"

    w._render_right()

    assert captured.get("d") == {"right": "ABS 0,8"}


def test_edge_banding_block_assigns_default_band_when_side_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import EdgeBandingBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    expected_key = next(eb.key for eb in catalog.list_edgebands() if eb.key != "Brak")

    w = EdgeBandingBlock(catalog)
    cb, combo = w._rows["left"]

    assert str(combo.currentData() or "Brak") == "Brak"
    assert combo.isEnabled() is False

    cb.setChecked(True)

    assert combo.isEnabled() is True
    assert str(combo.currentData() or "") == expected_key
    assert w.get_edge_banding()["left"] == expected_key
