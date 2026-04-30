from pathlib import Path
import inspect
from datetime import datetime

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _selected_station_title(tab_stanowiska) -> str:
    tabs = getattr(tab_stanowiska, "_tabs", None)
    if tabs is None:
        return ""
    idx = int(tabs.currentIndex())
    if idx < 0:
        return ""
    return str(tabs.tabText(idx) or "")


def test_tab_stanowiska_open_station_exists(qapp):
    from src.tabs.stanowiska.tab_stanowiska import TabStanowiska

    tab = TabStanowiska()
    assert hasattr(tab, "open_station")
    assert callable(getattr(tab, "open_station"))
    params = inspect.signature(tab.open_station).parameters
    assert "station_key" in params
    assert "reference_date" in params


def test_main_window_has_open_stanowiska_for_order(monkeypatch, tmp_path, qapp):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow

    win = MainWindow()
    assert hasattr(win, "_open_stanowiska_for_order")
    assert callable(getattr(win, "_open_stanowiska_for_order"))
    params = inspect.signature(win._open_stanowiska_for_order).parameters
    assert "calendar_stage" in params
    assert "reference_date" in params


def test_handoff_stage_mapping_known_values(monkeypatch, tmp_path, qapp):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow

    win = MainWindow()
    tab = win._tabs_by_title.get("Stanowiska")
    assert tab is not None

    expected = {
        "produkcja": "CNC",
        "lakiernia": "Lakiernia",
        "montaz": "Montaz",
        "poprawki": "Montaz",
        "wycena": "BIURO",
        "projekt": "BIURO",
        "zakup materialow": "BIURO",
        "probki": "BIURO",
    }
    for stage, station_title in expected.items():
        win._open_stanowiska_for_order(stage)
        QApplication.processEvents()
        assert _selected_station_title(tab) == station_title


def test_handoff_montaz_lands_on_montaz(monkeypatch, tmp_path, qapp):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow

    win = MainWindow()
    tab = win._tabs_by_title.get("Stanowiska")
    assert tab is not None

    win._open_stanowiska_for_order("montaz")
    QApplication.processEvents()
    assert _selected_station_title(tab) == "Montaz"


def test_handoff_fallback_lands_on_biuro(monkeypatch, tmp_path, qapp):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow

    win = MainWindow()
    tab = win._tabs_by_title.get("Stanowiska")
    assert tab is not None

    win._open_stanowiska_for_order("cos_nieznanego")
    QApplication.processEvents()
    assert _selected_station_title(tab) == "BIURO"


def test_wall_calendar_has_reference_date_api(qapp):
    from src.widgets.wall_calendar_view import WallCalendarView

    assert hasattr(WallCalendarView, "set_reference_date")
    assert callable(getattr(WallCalendarView, "set_reference_date"))
    assert hasattr(WallCalendarView, "_normalize_date_iso")


def test_handoff_valid_date_becomes_runtime_reference(monkeypatch, tmp_path, qapp):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow

    win = MainWindow()
    tab = win._tabs_by_title.get("Stanowiska")
    assert tab is not None

    ref_date = "2031-01-05"
    win._open_stanowiska_for_order("montaz", reference_date=ref_date)
    QApplication.processEvents()
    assert _selected_station_title(tab) == "Montaz"

    tabs = getattr(tab, "_tabs", None)
    panes = getattr(tab, "_panes", None)
    assert tabs is not None and panes is not None
    idx = int(tabs.currentIndex())
    assert idx >= 0
    pane = panes[idx]
    assert getattr(pane, "_reference_date_iso", "") == ref_date
    view = getattr(pane, "_view", None)
    assert view is not None
    assert getattr(view, "_reference_date_iso", "") == ref_date


def test_wall_calendar_invalid_or_missing_date_falls_back_to_current_date(qapp):
    from src.widgets.wall_calendar_view import WallCalendarView

    view = WallCalendarView()
    today_label = datetime.now().strftime("%d %B %Y")

    view.set_reference_date("invalid-date")
    assert getattr(view, "_reference_date_iso", "") == ""
    assert str(view._date_label.text() or "").strip() == today_label

    view.set_reference_date("")
    assert getattr(view, "_reference_date_iso", "") == ""
    assert str(view._date_label.text() or "").strip() == today_label


def test_nowe_zamowienie_trigger_exists_in_source():
    src = Path("src/tabs/zamowienie/tab_nowe_zamowienie.py").read_text(encoding="utf-8")
    assert "Otworz stanowiska dla etapu" in src
    assert "_on_open_stanowiska_for_stage" in src
    assert "w._open_stanowiska_for_order(stage, reference_date=ref_date)" in src
