from PyQt6.QtWidgets import QApplication

from src.tabs.registry import build_tabs
from src.tabs.uslugi.tab_uslugi import TabUslugi


def test_build_tabs_contains_unified_uslugi_tab(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])
    _ = app

    by_title = {title: widget for title, widget in build_tabs()}
    assert isinstance(by_title["Uslugi"], TabUslugi)

    widget = by_title["Uslugi"]
    labels = [widget.tabs.tabText(i) for i in range(widget.tabs.count())]
    assert labels == ["Cenik", "Klijenty", "Nowa USLUGA", "BAZA USLUG"]
