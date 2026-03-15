from PyQt6.QtWidgets import QApplication


def _body_widget(block):
    lay = block.content_layout()
    assert lay is not None
    body = lay.parentWidget()
    assert body is not None
    return body


def test_tab_modul_secondary_left_blocks_are_collapsed_on_start(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "blk_shelves")
    assert hasattr(w, "blk_div")

    assert _body_widget(w.blk_shelves).isHidden() is True
    assert _body_widget(w.blk_div).isHidden() is True


def test_tab_modul_main_left_blocks_stay_open_on_start(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    assert hasattr(w, "blk_dims")
    assert hasattr(w, "blk_mat")
    assert hasattr(w, "blk_fhw")
    assert hasattr(w, "blk_joint")

    assert _body_widget(w.blk_dims).isHidden() is False
    assert _body_widget(w.blk_mat).isHidden() is False
    assert _body_widget(w.blk_fhw).isHidden() is False
    assert _body_widget(w.blk_joint).isHidden() is False