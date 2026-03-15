from PyQt6.QtWidgets import QApplication


def test_tab_modul_left_blocks_priority_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    names = []
    lay = w.zone_left.body_lay

    for i in range(lay.count()):
        item = lay.itemAt(i)
        widget = item.widget()
        if widget is not None:
            names.append(widget.objectName())

    assert names == [
        "blk_dims",
        "blk_mat",
        "blk_fhw",
        "blk_joint",
        "blk_shelves",
        "blk_div",
        "blk_ref",
        "blk_tree",
        "blk_vis",
        "blk_sess",
    ]