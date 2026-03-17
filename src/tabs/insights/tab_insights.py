from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class TabInsights(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("ANALIZA BAZA I 3D CONSTRUCTOR")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #25334c;")
        root.addWidget(title)

        summary = QLabel(
            "Przejrzany material: 90 screenshotow WhatsApp z 17 marca 2026 z folderu "
            "Screenshots oraz instrukcja 3D Constructor 7.0 ENG. To jest bardzo dobre "
            "zrodlo logiki pracy firmy, ale slabe zrodlo wygladu nowej aplikacji."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #4b5563; font-size: 14px; line-height: 1.4;")
        root.addWidget(summary)

        rating_title = QLabel("Ocena")
        rating_title.setStyleSheet("font-weight: 700; color: #1d2c3f;")
        root.addWidget(rating_title)

        rating = QLabel(
            "Funkcjonalnie: 8/10. Screeny pokazuja dobra baze procesow: materialy, "
            "magazyn, stany minimalne, kasa, pracownicy i statusy zlecen. Wizualnie: "
            "2/10. Nie warto kopiowac starego, ciezkiego wygladu i zasady 'wszystko na "
            "jednym ekranie'."
        )
        rating.setWordWrap(True)
        rating.setStyleSheet("color: #3b4755; font-size: 13px;")
        root.addWidget(rating)

        list_title = QLabel("Co warto przeniesc")
        list_title.setStyleSheet("font-weight: 700; color: #1d2c3f;")
        root.addWidget(list_title)

        self.list = QListWidget(self)
        self.list.setStyleSheet(
            "QListWidget { border: 1px solid #dbe0e6; border-radius: 12px; padding: 12px; font-size: 13px; }"
        )
        items = [
            "Baza materialow z kodem, jednostka, gruboscia, dekorem, cena i stanem minimalnym.",
            "Magazyn i raport stanow z rezerwacja materialu pod zamowienie.",
            "Kasa klienta: zaliczka, 60%, 20%, koncowka, dlug i historia platnosci.",
            "Rejestr pracownikow, ich rol, czasu pracy i kosztu robocizny.",
            "Statusy zamowienia: wycena, zakup materialow, produkcja, montaz, poprawki, koniec.",
            "Dokumenty zakupu: faktury, WZ, dostawy, z przypieciem do materialu i dostawcy.",
        ]
        for text in items:
            self.list.addItem(QListWidgetItem(f"- {text}"))
        root.addWidget(self.list)

        dont_title = QLabel("Czego nie kopiowac")
        dont_title.setStyleSheet("font-weight: 700; color: #1d2c3f;")
        root.addWidget(dont_title)

        dont = QLabel(
            "Nie kopiowac starego wygladu XP, przeciazonych formularzy i logiki, w ktorej "
            "wszystko miesza sie na jednym ekranie. AXIC jest dla nas lepsza inspiracja dla "
            "oferty i czytelnosci. Stary program jest inspiracja procesowa, nie wizualna."
        )
        dont.setWordWrap(True)
        dont.setStyleSheet("color: #3b4755; font-size: 13px;")
        root.addWidget(dont)

        steps_title = QLabel("Kolejnosc dalszych krokow")
        steps_title.setStyleSheet("font-weight: 700; color: #1d2c3f;")
        root.addWidget(steps_title)

        steps = QLabel(
            "1. Rozwinac Bazy -> Materialy do prawdziwego katalogu cen i stanow.\n"
            "2. Dodac Magazyn i dokumenty zakupu: faktury, WZ, paragony, dostawy.\n"
            "3. Spiac kase klienta z realnymi platnosciami i dlugiem.\n"
            "4. Spiac czas pracy i kase pracownikow z kosztami projektu.\n"
            "5. Dopiero potem dopiescic oferte klienta i wyglad calosci."
        )
        steps.setWordWrap(True)
        steps.setStyleSheet("color: #3b4755; font-size: 13px;")
        root.addWidget(steps)

        root.addStretch(1)
