GROUPS: list[tuple[str, list[str]]] = [
    (
        "Sprzedaż",
        [
            "Start",
            "Nowe zamowienie",
            "Uslugi",
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
        ],
    ),
]
