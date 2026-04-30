from PyQt6.QtWidgets import QApplication, QFormLayout, QLabel


def _has_form_label(form: QFormLayout, text: str) -> bool:
    for row in range(form.rowCount()):
        label_item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        if label_item is None:
            continue
        widget = label_item.widget()
        if isinstance(widget, QLabel) and widget.text() == text:
            return True
    return False


def test_front_hardware_uses_sectioned_rows_without_duplicate_gaps(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.front_hardware_block import FrontHardwareBlock

    w = FrontHardwareBlock()
    form = w.layout()
    assert isinstance(form, QFormLayout)

    assert _has_form_label(form, "Luzy")
    assert _has_form_label(form, "Tryb i okucia")

    # Step 47: gap controls should live in grouped section, not duplicated as top-level rows.
    assert not _has_form_label(form, "Luz lewy")
    assert not _has_form_label(form, "Luz prawy")
    assert not _has_form_label(form, "Luz gorny")
    assert not _has_form_label(form, "Luz dolny")
    assert not _has_form_label(form, "Luz miedzy frontami")



def test_tab_modul_default_splitter_balance_is_frozen(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    assert w._default_zone_splitter_sizes() == [210, 1080, 210]


def test_tab_modul_vertical_tab_bars_readable_width_is_frozen(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()
    left_w = int(w.left_tabs.tabBar().width())
    right_w = int(w.right_tabs.tabBar().width())

    # Step NEXT freeze: accepted readable runtime width.
    assert left_w == 96
    assert right_w == 96
