from PyQt6.QtWidgets import QApplication

from src.tabs.modul.tab_modul import DimensionsBlock, TabModul


def test_dimensions_block_hides_drawing_fields():
    app = QApplication.instance() or QApplication([])

    w = DimensionsBlock()

    assert hasattr(w, "sp_hinge_edge_offset")
    assert hasattr(w, "sp_auto_double_front_width")

    assert w.sp_hinge_edge_offset.isHidden() is True
    assert w.sp_auto_double_front_width.isHidden() is True


def test_tab_modul_keeps_hidden_drawing_fields_inside_dimensions_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = TabModul()

    assert hasattr(w, "dim")
    assert w.dim.sp_hinge_edge_offset.isHidden() is True
    assert w.dim.sp_auto_double_front_width.isHidden() is True