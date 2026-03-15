from PyQt6.QtWidgets import QApplication

def test_reference_point_block_values():
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ReferencePointBlock

    r = ReferencePointBlock()
    r.set_values("upper", "LBT")
    assert r.get_kind() == "upper"
    assert r.get_ref() == "LBT"

    r.set_values("lower", "LBB")
    assert r.get_kind() == "lower"
    assert r.get_ref() == "LBB"