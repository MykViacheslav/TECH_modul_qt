from PyQt6.QtWidgets import QApplication

from src.tabs.bazy.tab_bazy import TabBazy
from src.tabs.kalendarz.tab_kalendarz import TabKalendarz
from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy
from src.tabs.modul.tab_modul import TabModul
from src.tabs.rysunek.tab_rysunek import TabRysunek
from src.tabs.schemat.tab_schemat import TabSchemat
from src.tabs.registry import build_tabs
from src.tabs.sciana.tab_sciana import TabSciana
from src.tabs.sciana.tab_sciana_layout import TabScianaLayout
from src.tabs.start.tab_start import TabStart
from src.tabs.wycena.tab_wycena import TabWycena
from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


def test_build_tabs_contains_start_order_quote_calendar_worktime_modul_komplet_sciana_bazy_and_ustawienia(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    tabs = build_tabs()

    assert isinstance(tabs, list)
    assert len(tabs) >= 10

    titles = [title for title, _widget in tabs]
    for expected in [
        "Start", "Nowe zamowienie", "Wycena",
        "Plan", "Schemat", "Kalendarz", "Czas pracy",
        "Modul", "Komplet", "Sciana",
        "Bazy", "Ustawienia",
    ]:
        assert expected in titles, f'Brak zakładki: "{expected}"'

    by_title = {title: widget for title, widget in tabs}

    assert isinstance(by_title["Start"], TabStart)
    assert isinstance(by_title["Nowe zamowienie"], TabNoweZamowienie)
    assert isinstance(by_title["Wycena"], TabWycena)
    assert isinstance(by_title["Schemat"], TabSchemat)
    assert isinstance(by_title["Kalendarz"], TabKalendarz)
    assert isinstance(by_title["Czas pracy"], TabCzasPracy)
    assert isinstance(by_title["Modul"], TabModul)
    assert isinstance(by_title["Komplet"], TabSciana)
    assert isinstance(by_title["Sciana"], TabScianaLayout)
    assert isinstance(by_title["Bazy"], TabBazy)
    assert isinstance(by_title["Ustawienia"], TabRysunek)
