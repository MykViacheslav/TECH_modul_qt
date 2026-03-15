from PyQt6.QtWidgets import QApplication


def test_visible_parts_block_has_height_limits():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import VisiblePartsBlock

    w = VisiblePartsBlock()

    assert w.minimumHeight() == 150
    assert w.maximumHeight() == 220