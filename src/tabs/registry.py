from __future__ import annotations

from typing import List, Tuple

from PyQt6.QtWidgets import QWidget

from src.tabs.bazy.tab_bazy import TabBazy
from src.tabs.kalendarz.tab_kalendarz import TabKalendarz
from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy
from src.tabs.insights.tab_insights import TabInsights
from src.tabs.modul.tab_modul import TabModul
from src.tabs.rysunek.tab_rysunek import TabRysunek
from src.tabs.schemat.tab_schemat import TabSchemat
from src.tabs.sciana.tab_sciana import TabSciana
from src.tabs.sciana.tab_sciana_layout import TabScianaLayout
from src.tabs.start.tab_start import TabStart
from src.tabs.wycena.tab_wycena import TabWycena
from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie


def build_tabs() -> List[Tuple[str, QWidget]]:
    return [
        ("Start", TabStart()),
        ("Nowe zamowienie", TabNoweZamowienie()),
        ("Wycena", TabWycena()),
        ("Plan", TabInsights()),
        ("Schemat", TabSchemat()),
        ("Kalendarz", TabKalendarz()),
        ("Czas pracy", TabCzasPracy()),
        ("Modul", TabModul()),
        ("Komplet", TabSciana()),
        ("Sciana", TabScianaLayout()),
        ("Bazy", TabBazy()),
        ("Ustawienia", TabRysunek()),
    ]
