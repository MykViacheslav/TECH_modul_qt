from PyQt6.QtWidgets import QApplication


def test_tab_modul_tree_block_has_limited_height(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    blk_tree = None
    lay = w.zone_left.body_lay

    for i in range(lay.count()):
        item = lay.itemAt(i)
        widget = item.widget()
        if widget is not None and widget.objectName() == "blk_tree":
            blk_tree = widget
            break

    assert blk_tree is not None
    assert blk_tree.maximumHeight() == 240