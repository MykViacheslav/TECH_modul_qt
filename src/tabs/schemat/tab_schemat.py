from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _FlowBox(QFrame):
    def __init__(self, title: str, subtitle: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(92)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {accent}12;
                border: none;
                border-radius: 16px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #1f2937;")
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("font-size: 12px; color: #667085;")
        layout.addWidget(subtitle_label)


class _Arrow(QLabel):
    def __init__(self, text: str = ">", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-size: 18px; font-weight: 700; color: #b0895a;")


class _Section(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 18px;
            }
            """
        )
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(18, 18, 18, 18)
        self.layout_main.setSpacing(14)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #25334c;")
        self.layout_main.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("font-size: 13px; color: #667085;")
            self.layout_main.addWidget(subtitle_label)


class TabSchemat(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        title = QLabel("SCHEMAT DZIALANIA PROGRAMU")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #25334c;")
        root.addWidget(title)

        intro = QLabel(
            "Tu jest narysowane skad program bierze dane, gdzie one trafiaja i jak przechodza "
            "przez wycene, prowadzenie projektu, magazyn i finanse."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 14px; color: #556070;")
        root.addWidget(intro)

        section_sources = _Section(
            "1. Skad bierzemy dane",
            "To sa glowne wejscia do programu na starcie projektu.",
            self,
        )
        sources_grid = QGridLayout()
        sources_grid.setHorizontalSpacing(14)
        sources_grid.setVerticalSpacing(14)
        source_boxes = [
            ("Klient", "dane klienta, adres, kontakt", "#5271c4"),
            ("Architekt PDF", "rzuty, wizualizacje, notatki", "#5271c4"),
            ("WhatsApp / BAZA", "screeny, pliki, szybkie wrzutki", "#5271c4"),
            ("3D Constructor", "dokladny projekt po akceptacji", "#5271c4"),
            ("Dostawcy / faktury", "ceny, kody, dokumenty zakupu", "#5271c4"),
            ("Pracownicy", "role, stawki, czas pracy", "#5271c4"),
        ]
        for idx, (title_text, subtitle, color) in enumerate(source_boxes):
            sources_grid.addWidget(_FlowBox(title_text, subtitle, color, self), idx // 3, idx % 3)
        section_sources.layout_main.addLayout(sources_grid)
        root.addWidget(section_sources)

        section_flow = _Section(
            "2. Glowny przeplyw pracy",
            "To jest glowna droga projektu od pierwszego kontaktu do oferty.",
            self,
        )
        flow_row = QHBoxLayout()
        flow_row.setSpacing(10)
        for i, (title_text, subtitle, color) in enumerate(
            [
                ("Nowe zamowienie", "centrum projektu i zalacznikow", "#c58a2a"),
                ("Pozycje do wyceny", "podzial na kuchnia / szafa / RTV", "#c58a2a"),
                ("Sciana", "uklad miejsca i przeszkody", "#c58a2a"),
                ("Komplet", "moduly, materialy, szybka konfiguracja", "#c58a2a"),
                ("Wycena", "koszt, marza, oferta", "#c58a2a"),
                ("Oferta PDF", "dokument dla klienta", "#c58a2a"),
            ]
        ):
            flow_row.addWidget(_FlowBox(title_text, subtitle, color, self), 1)
            if i < 5:
                flow_row.addWidget(_Arrow(parent=self))
        section_flow.layout_main.addLayout(flow_row)
        root.addWidget(section_flow)

        section_company = _Section(
            "3. Prowadzenie firmy po drodze",
            "Te karty zbieraja realna prace firmy wokol projektu.",
            self,
        )
        company_grid = QGridLayout()
        company_grid.setHorizontalSpacing(14)
        company_grid.setVerticalSpacing(14)
        company_items = [
            ("Kalendarz", "statusy, terminy, etapy", "#2d8a5b"),
            ("Czas pracy", "godziny, dniowki, dodatki", "#2d8a5b"),
            ("Bazy", "klienci, materialy, pracownicy", "#2d8a5b"),
            ("Magazyn", "stany, rezerwacje, zakupy", "#2d8a5b"),
            ("Finanse", "kasa klienta, koszty i marza", "#2d8a5b"),
            ("Zakupy", "faktury, WZ, dostawcy", "#2d8a5b"),
        ]
        for idx, (title_text, subtitle, color) in enumerate(company_items):
            company_grid.addWidget(_FlowBox(title_text, subtitle, color, self), idx // 3, idx % 3)
        section_company.layout_main.addLayout(company_grid)
        root.addWidget(section_company)

        section_links = _Section(
            "4. Najwazniejsze powiazania",
            "Tu widac, co z czego korzysta i gdzie ida dane dalej.",
            self,
        )
        links_grid = QGridLayout()
        links_grid.setHorizontalSpacing(10)
        links_grid.setVerticalSpacing(10)

        links_grid.addWidget(_FlowBox("Architekt PDF", "zalaczniki i referencje", "#8b5e2b", self), 0, 0)
        links_grid.addWidget(_Arrow(parent=self), 0, 1)
        links_grid.addWidget(_FlowBox("Nowe zamowienie", "przypina pliki do projektu", "#8b5e2b", self), 0, 2)

        links_grid.addWidget(_FlowBox("Bazy / Materialy", "kody, ceny, jednostki", "#8b5e2b", self), 1, 0)
        links_grid.addWidget(_Arrow(parent=self), 1, 1)
        links_grid.addWidget(_FlowBox("Komplet + Wycena", "liczenie kosztu i oferty", "#8b5e2b", self), 1, 2)

        links_grid.addWidget(_FlowBox("Czas pracy", "realny koszt ludzi", "#8b5e2b", self), 2, 0)
        links_grid.addWidget(_Arrow(parent=self), 2, 1)
        links_grid.addWidget(_FlowBox("Wycena", "robocizna do projektu", "#8b5e2b", self), 2, 2)

        links_grid.addWidget(_FlowBox("Zakupy / faktury", "ceny zakupu i stany", "#8b5e2b", self), 3, 0)
        links_grid.addWidget(_Arrow(parent=self), 3, 1)
        links_grid.addWidget(_FlowBox("Magazyn / Bazy", "stany i historia zakupu", "#8b5e2b", self), 3, 2)

        links_grid.addWidget(_FlowBox("Kasa klienta", "zaliczki i platnosci", "#8b5e2b", self), 4, 0)
        links_grid.addWidget(_Arrow(parent=self), 4, 1)
        links_grid.addWidget(_FlowBox("Finanse", "co przyszlo i co zostalo", "#8b5e2b", self), 4, 2)

        section_links.layout_main.addLayout(links_grid)
        root.addWidget(section_links)

        root.addStretch(1)
