from PyQt6.QtWidgets import QApplication

from src.tabs.finanse_hub.tab_finanse_hub import TabFinanseHub


def _find_tab_index(tabs, label: str) -> int:
    for i in range(tabs.count()):
        if tabs.tabText(i) == label:
            return i
    return -1


def test_finanse_hub_has_operations_ready_tab():
    app = QApplication.instance() or QApplication([])
    _ = app
    hub = TabFinanseHub()
    idx = _find_tab_index(hub._tabs, "Do rozliczenia z OPERACJE")
    assert idx >= 0


def test_finanse_hub_operations_ready_tab_role_visibility():
    app = QApplication.instance() or QApplication([])
    _ = app
    hub = TabFinanseHub()
    idx = _find_tab_index(hub._tabs, "Do rozliczenia z OPERACJE")
    assert idx >= 0

    hub.set_current_user("User A", "biuro")
    assert hub._tabs.isTabVisible(idx) is True

    hub.set_current_user("User B", "produkcja")
    assert hub._tabs.isTabVisible(idx) is False

