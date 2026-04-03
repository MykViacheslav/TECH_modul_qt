from src.tabs.start.tab_start import TabStart
from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie
from src.tabs.wycena.tab_wycena import TabWycena
from src.tabs.szybka_wycena.tab_szybka_wycena import TabSzybkaWycena
from src.tabs.baza_modul.tab_baza_modul import TabBazaModul
from src.tabs.baza_materialu.tab_baza_materialu import TabBazaMaterialu
from src.tabs.kalendarz.tab_kalendarz import TabKalendarz
from src.tabs.czas_pracy.tab_czas_pracy import TabCzasPracy
from src.tabs.modul.tab_modul import TabModul
from src.tabs.sciana.tab_sciana import TabSciana
from src.tabs.sciana.tab_sciana_layout import TabScianaLayout
from src.tabs.bazy.tab_bazy import TabBazy
from src.tabs.rysunek.tab_rysunek import TabRysunek
from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import TabBazaSzybkichWycen
from src.tabs.pracownicy.tab_pracownicy import TabPracownicy
from src.tabs.wydatki_stale.tab_wydatki_stale import TabWydatkiStale
from src.tabs.wydatki_zmienne.tab_wydatki_zmienne import TabWydatkiZmienne
from src.tabs.dashboard.tab_dashboard import TabDashboard
from src.tabs.alarmy.tab_alarmy import TabAlarmy
from src.tabs.uslugi.tab_uslugi import TabUslugi
from src.tabs.zakupy.tab_zakupy import TabZakupy


def build_tabs():
    return [
        ("Start", TabStart()),
        ("Nowe zamowienie", TabNoweZamowienie()),
        ("Wycena", TabWycena()),
        ("Uslugi", TabUslugi()),
        ("Sekcje do wyceny", TabSzybkaWycena()),
        ("BAZA_modul", TabBazaModul()),
        ("Baza materialu", TabBazaMaterialu()),
        ("Baza szybkich wycen", TabBazaSzybkichWycen()),
        ("Wydatki stale firmy", TabWydatkiStale()),
        ("Wydatki zmienne", TabWydatkiZmienne()),
        ("Dashboard", TabDashboard()),
        ("Kalendarz", TabKalendarz()),
        ("Czas pracy", TabCzasPracy()),
        ("Modul", TabModul()),
        ("Komplet", TabSciana()),
        ("Sciana", TabScianaLayout()),
        ("Bazy", TabBazy()),
        ("Pracownik", TabPracownicy()),
        ("Zakupy", TabZakupy()),
        ("Ustawienia", TabRysunek()),
        ("ALARMY", TabAlarmy()),
    ]
