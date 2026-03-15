from PyQt6.QtWidgets import QApplication

def test_visible_parts_block_set_get():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import VisiblePartsBlock

    b = VisiblePartsBlock()
    b.set_checked({"side_left", "front", "back"})
    got = b.get_visible_parts()
    assert "side_left" in got
    assert "front" in got
    assert "back" in got