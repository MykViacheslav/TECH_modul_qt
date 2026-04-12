from __future__ import annotations


# ── Główna mapa nawigacji bocznego paska ─────────────────────────────────────
#
# Każda krotka: (nazwa_grupy, [tytuły_zakładek])
# Tytuły MUSZĄ dokładnie zgadzać się z kluczami w src/tabs/registry.py.
#
# Historia zmian:
#   2026-04-10  Krok 1: reorganizacja grup.
#               - usunięto "Usługi" jako osobną grupę → przeniesiono do "Firma"
#               - ujawniono ukryte bazy: BAZA_modul, Baza materialu, Baza szybkich wycen
#               - usunięto osierocone wpisy "Plan" i "Schemat" (brak backing tab)
#               - "Inne" przemianowano na "Ustawienia"
#   2026-04-10  Krok 2: naprawa registry — dodano 5 brakujących zakładek.
#   2026-04-10  Krok 3: hub Wycena — "Sekcje do wyceny" i "Wycena (3DConstructor)"
#               scalono w TabWycenaHub (podzakładki wewnątrz "Wycena").
#   2026-04-11  Krok 4: hub Finanse — wydatki/zakupy scalono do lokalnych
#               podzakładek w jednej zakładce "Finanse".
#
GROUPS: list[tuple[str, list[str]]] = [
    (
        "Sprzedaż",
        [
            "Start",
            "Nowe zamowienie",
            "Wycena",           # hub: Wycena projektu / Szybka wycena / Import 3D / Rozkrój / Podsumowanie
        ],
    ),
    (
        "Projekt",
        [
            "Modul",
            "Komplet",
            "Sciana",
        ],
    ),
    (
        "Firma",
        [
            "Dashboard",
            "ALARMY",
            "Kalendarz",
            "Czas pracy",
            "Pracownik",
            # "Uslugi" przeniesione do hub Wycena → Usługi (Faza 4)
        ],
    ),
    (
        "Finanse",
        [
            "Finanse",  # hub: Podsumowanie / Sprzedaż / Zakupy i koszty / Kasa / Wynagrodzenia / Podatki / Raporty
        ],
    ),
    (
        "Operacje",
        [
            "OPERACJE",  # hub: Problemy i alarmy / Priorytety i trasy
        ],
    ),
    (
        "Bazy",
        [
            "Bazy",
            "BAZA_modul",           # był ukryty — teraz widoczny
            "Baza materialu",       # był ukryty — teraz widoczny
            "Baza szybkich wycen",  # był ukryty — teraz widoczny
            "Baza uslug",           # definicje usług (cennik)
        ],
    ),
    (
        "Ustawienia",           # dawniej "Inne"
        [
            "Ustawienia",
            "Ekrany",
            "Stanowiska",
            "QR TELEFON",
            "STRUKTURA",
            # usunięte: "Plan", "Schemat" — brak backing widget w registry.py
        ],
    ),
]
