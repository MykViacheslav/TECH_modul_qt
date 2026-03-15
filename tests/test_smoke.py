from PyQt6.QtWidgets import QApplication
from src.tabs.modul.tab_modul import TabModul


def test_tab_modul_instantiates():
    app = QApplication.instance() or QApplication([])
    w = TabModul()
    assert w is not None