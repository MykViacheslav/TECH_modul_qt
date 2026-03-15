from PyQt6.QtWidgets import QApplication


def test_project_tree_block_has_height_limits():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ProjectTreeBlock

    w = ProjectTreeBlock()

    assert w.tree.minimumHeight() == 120
    assert w.tree.maximumHeight() == 180