from PyQt6.QtWidgets import QApplication


def test_tab_modul_secondary_left_blocks_have_height_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    blk_vis = None
    blk_sess = None

    lay = w.zone_left.body_lay
    for i in range(lay.count()):
        item = lay.itemAt(i)
        widget = item.widget()
        if widget is None:
            continue

        if widget.objectName() == "blk_vis":
            blk_vis = widget
        elif widget.objectName() == "blk_sess":
            blk_sess = widget

    assert blk_vis is not None
    assert blk_sess is not None

    assert blk_vis.maximumHeight() == 280
    assert blk_sess.maximumHeight() == 260