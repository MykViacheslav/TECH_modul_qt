from __future__ import annotations

import traceback
from PyQt6.QtWidgets import QLabel, QWidget


def _safe_build(title: str, factory) -> tuple[str, QWidget]:
    """Buduje zakładkę, a w razie błędu zwraca placeholder zamiast crashować."""
    try:
        return (title, factory())
    except Exception as exc:
        traceback.print_exc()
        placeholder = QLabel(
            f"[{title}]\n\nNie udało się załadować zakładki.\n\n{type(exc).__name__}: {exc}"
        )
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color:#b91c1c; padding:24px; font-size:12px;")
        return (title, placeholder)


def build_tabs() -> list[tuple[str, QWidget]]:
    tabs: list[tuple[str, QWidget]] = []

    def add(title: str, factory):
        tabs.append(_safe_build(title, factory))

    # --- Sprzedaż ---
    add("Start",           lambda: __import__("src.tabs.start.tab_start", fromlist=["TabStart"]).TabStart())
    add("Nowe zamowienie", lambda: __import__("src.tabs.zamowienie.tab_nowe_zamowienie", fromlist=["TabNoweZamowienie"]).TabNoweZamowienie())
    # "Wycena" = hub z sześcioma podzakładkami (Wycena projektu / Szybka wycena / Import 3D / Usługi / Rozkrój / Podsumowanie)
    add("Wycena",          lambda: __import__("src.tabs.wycena_hub.tab_wycena_hub", fromlist=["TabWycenaHub"]).TabWycenaHub())

    # --- Projekt ---
    add("Modul",   lambda: __import__("src.tabs.modul.tab_modul", fromlist=["TabModul"]).TabModul())
    add("Komplet", lambda: __import__("src.tabs.sciana.tab_sciana", fromlist=["TabSciana"]).TabSciana())

    def _build_sciana():
        try:
            return __import__("src.tabs.sciana.tab_sciana_layout", fromlist=["TabScianaLayout"]).TabScianaLayout()
        except Exception:
            return __import__("src.tabs.sciana.tab_sciana", fromlist=["TabSciana"]).TabSciana()

    add("Sciana", _build_sciana)

    # --- Firma ---
    add("Dashboard",           lambda: __import__("src.tabs.dashboard.tab_dashboard", fromlist=["TabDashboard"]).TabDashboard())
    add("ALARMY",              lambda: __import__("src.tabs.alarmy.tab_alarmy", fromlist=["TabAlarmy"]).TabAlarmy())
    add("Kalendarz",           lambda: __import__("src.tabs.kalendarz.tab_kalendarz", fromlist=["TabKalendarz"]).TabKalendarz())
    add("Czas pracy",          lambda: __import__("src.tabs.czas_pracy.tab_czas_pracy", fromlist=["TabCzasPracy"]).TabCzasPracy())
    add("Pracownik",           lambda: __import__("src.tabs.pracownicy.tab_pracownicy", fromlist=["TabPracownicy"]).TabPracownicy())

    # --- Finanse ---
    add("Finanse",             lambda: __import__("src.tabs.finanse_hub.tab_finanse_hub", fromlist=["TabFinanseHub"]).TabFinanseHub())
    add("OPERACJE",            lambda: __import__("src.tabs.operations_hub.tab_operations_hub", fromlist=["TabOperationsHub"]).TabOperationsHub())

    # --- Bazy ---
    add("Bazy",               lambda: __import__("src.tabs.bazy.tab_bazy", fromlist=["TabBazy"]).TabBazy())
    add("BAZA_modul",         lambda: __import__("src.tabs.baza_modul.tab_baza_modul", fromlist=["TabBazaModul"]).TabBazaModul())
    add("Baza materialu",     lambda: __import__("src.tabs.baza_materialu.tab_baza_materialu", fromlist=["TabBazaMaterialu"]).TabBazaMaterialu())
    add("Baza szybkich wycen",lambda: __import__("src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen", fromlist=["TabBazaSzybkichWycen"]).TabBazaSzybkichWycen())
    add("Baza uslug",         lambda: __import__("src.tabs.baza_uslug.tab_baza_uslug", fromlist=["TabBazaUslug"]).TabBazaUslug())

    # --- Ustawienia ---
    add("Ustawienia", lambda: __import__("src.tabs.rysunek.tab_rysunek", fromlist=["TabRysunek"]).TabRysunek())
    add("Ekrany",     lambda: __import__("src.tabs.ekrany.tab_ekrany", fromlist=["TabEkrany"]).TabEkrany())
    add("Stanowiska", lambda: __import__("src.tabs.stanowiska.tab_stanowiska", fromlist=["TabStanowiska"]).TabStanowiska())
    add("QR TELEFON", lambda: __import__("src.tabs.qr_telefon.tab_qr_telefon", fromlist=["TabQrTelefon"]).TabQrTelefon())
    add("STRUKTURA",  lambda: __import__("src.tabs.struktura.tab_struktura", fromlist=["TabStruktura"]).TabStruktura())

    return tabs
