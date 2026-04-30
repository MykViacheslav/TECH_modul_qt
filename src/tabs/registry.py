from __future__ import annotations

import traceback
from typing import Callable

from PyQt6.QtWidgets import QLabel, QWidget


TabFactory = Callable[[], QWidget]


def _safe_build(title: str, factory: TabFactory) -> tuple[str, QWidget]:
    """Build a tab, and return an error placeholder instead of crashing."""
    try:
        return (title, factory())
    except Exception as exc:
        traceback.print_exc()
        placeholder = QLabel(
            f"[{title}]\n\nNie udalo sie zaladowac zakladki.\n\n{type(exc).__name__}: {exc}"
        )
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color:#b91c1c; padding:24px; font-size:12px;")
        return (title, placeholder)


def build_tab_factories() -> list[tuple[str, TabFactory]]:
    def _build_sciana() -> QWidget:
        try:
            return __import__(
                "src.tabs.sciana.tab_sciana_layout",
                fromlist=["TabScianaLayout"],
            ).TabScianaLayout()
        except Exception:
            return __import__(
                "src.tabs.sciana.tab_sciana",
                fromlist=["TabSciana"],
            ).TabSciana()

    return [
        # --- Sprzedaz ---
        ("Start", lambda: __import__("src.tabs.start.tab_start", fromlist=["TabStart"]).TabStart()),
        ("Nowe zamowienie", lambda: __import__("src.tabs.zamowienie.tab_nowe_zamowienie", fromlist=["TabNoweZamowienie"]).TabNoweZamowienie()),
        ("Uslugi", lambda: __import__("src.tabs.uslugi.tab_uslugi", fromlist=["TabUslugi"]).TabUslugi()),
        ("Wycena", lambda: __import__("src.tabs.wycena_hub.tab_wycena_hub", fromlist=["TabWycenaHub"]).TabWycenaHub()),
        # --- Projekt ---
        ("Modul", lambda: __import__("src.tabs.modul.tab_modul", fromlist=["TabModul"]).TabModul()),
        ("Komplet", lambda: __import__("src.tabs.sciana.tab_sciana", fromlist=["TabSciana"]).TabSciana()),
        ("Sciana", _build_sciana),
        # --- Firma ---
        ("Dashboard", lambda: __import__("src.tabs.dashboard.tab_dashboard", fromlist=["TabDashboard"]).TabDashboard()),
        ("ALARMY", lambda: __import__("src.tabs.alarmy.tab_alarmy", fromlist=["TabAlarmy"]).TabAlarmy()),
        ("Kalendarz", lambda: __import__("src.tabs.kalendarz.tab_kalendarz", fromlist=["TabKalendarz"]).TabKalendarz()),
        ("Czas pracy", lambda: __import__("src.tabs.czas_pracy.tab_czas_pracy", fromlist=["TabCzasPracy"]).TabCzasPracy()),
        ("Pracownik", lambda: __import__("src.tabs.pracownicy.tab_pracownicy", fromlist=["TabPracownicy"]).TabPracownicy()),
        # --- Finanse ---
        ("Finanse", lambda: __import__("src.tabs.finanse_hub.tab_finanse_hub", fromlist=["TabFinanseHub"]).TabFinanseHub()),
        ("OPERACJE", lambda: __import__("src.tabs.operations_hub.tab_operations_hub", fromlist=["TabOperationsHub"]).TabOperationsHub()),
        # --- Bazy ---
        ("Bazy", lambda: __import__("src.tabs.bazy.tab_bazy", fromlist=["TabBazy"]).TabBazy()),
        ("BAZA_modul", lambda: __import__("src.tabs.baza_modul.tab_baza_modul", fromlist=["TabBazaModul"]).TabBazaModul()),
        ("Baza materialu", lambda: __import__("src.tabs.baza_materialu.tab_baza_materialu", fromlist=["TabBazaMaterialu"]).TabBazaMaterialu()),
        ("Baza szybkich wycen", lambda: __import__("src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen", fromlist=["TabBazaSzybkichWycen"]).TabBazaSzybkichWycen()),
        ("Baza uslug", lambda: __import__("src.tabs.baza_uslug.tab_baza_uslug", fromlist=["TabBazaUslug"]).TabBazaUslug()),
        # --- Plan / Schemat ---
        ("Plan", lambda: __import__("src.tabs.plan.tab_plan", fromlist=["TabPlan"]).TabPlan()),
        ("Schemat", lambda: __import__("src.tabs.schemat.tab_schemat", fromlist=["TabSchemat"]).TabSchemat()),
        # --- Ustawienia ---
        ("Ustawienia", lambda: __import__("src.tabs.rysunek.tab_rysunek", fromlist=["TabRysunek"]).TabRysunek()),
        ("Ekrany", lambda: __import__("src.tabs.ekrany.tab_ekrany", fromlist=["TabEkrany"]).TabEkrany()),
        ("Stanowiska", lambda: __import__("src.tabs.stanowiska.tab_stanowiska", fromlist=["TabStanowiska"]).TabStanowiska()),
        ("QR TELEFON", lambda: __import__("src.tabs.qr_telefon.tab_qr_telefon", fromlist=["TabQrTelefon"]).TabQrTelefon()),
        ("STRUKTURA", lambda: __import__("src.tabs.struktura.tab_struktura", fromlist=["TabStruktura"]).TabStruktura()),
    ]


def build_tabs() -> list[tuple[str, QWidget]]:
    tabs: list[tuple[str, QWidget]] = []
    for title, factory in build_tab_factories():
        tabs.append(_safe_build(title, factory))
    return tabs
