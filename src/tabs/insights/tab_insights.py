from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _plan_path() -> Path:
    return _repo_root() / "PLAN_ETAPOW.txt"


def _load_plan_counts() -> tuple[str, int, int, int]:
    updated = "brak"
    done_count = 0
    progress_count = 0
    todo_count = 0
    plan_file = _plan_path()
    if not plan_file.exists():
        return updated, done_count, progress_count, todo_count

    for raw_line in plan_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("Aktualizacja:"):
            updated = line.split(":", 1)[1].strip()
        done_count += line.count("[DONE]")
        progress_count += line.count("[IN PROGRESS]")
        todo_count += line.count("[TODO]")
    return updated, done_count, progress_count, todo_count


class _InfoCard(QFrame):
    def __init__(self, title: str, value: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: #ffffff;
                border: 1px solid #d7dee8;
                border-top: 4px solid {accent};
                border-radius: 14px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #6b7280;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #1f2937;")
        layout.addWidget(value_label)


class _SectionBox(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 16px;
            }
            """
        )
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(18, 18, 18, 18)
        self.layout_main.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #1f2937;")
        self.layout_main.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("font-size: 13px; color: #667085;")
            self.layout_main.addWidget(subtitle_label)


class TabInsights(QWidget):
    DONE_ITEMS = [
        "Nowe zamowienie dziala jako centrum projektu: klient, pracownik, zalaczniki, pozycje, probki i kasa klienta.",
        "Szybka oferta klienta jest juz gotowa: HTML, PDF i referencje obrazowe z PDF architekta.",
        "Komplet ma biblioteke gotowych modulow, presety materialow, dekorow i szybka edycje grupowa.",
        "Kalendarz ma statusy, procent zaawansowania, historie zmian i szybkie filtry etapow.",
        "Czas pracy ma juz tabele miesieczne, tryby rozliczenia i podstawy kosztu robocizny.",
    ]

    IN_PROGRESS_ITEMS = [
        "Etap 1: dalej upraszczamy wyglad i prace w Komplet i Sciana.",
        "Etap 1A: dalej wzmacniamy szybka wycene zamiast pelnego projektu technicznego.",
        "Etap 3: rozwijamy prowadzenie firmy: statusy, kalendarz, pracownicy i obciazenie pracy.",
    ]

    NEXT_ITEMS = [
        "Bazy -> Materialy trzeba przerobic na prawdziwy katalog z cenami, kodami i stanowymi minimum.",
        "Magazyn i dokumenty zakupu: faktury, WZ, paragony, dostawy oraz zejscie materialu ze stanu.",
        "Kasa pracownikow i stale koszty firmy: zaliczki, wyplaty, auta, paliwo, czynsz, serwis.",
        "Dopiero potem mocniejsze dopieszczenie oferty klienta i bardziej premium wygladu aplikacji.",
    ]

    WHAT_WE_KEEP = [
        "Logika materialow, magazynu, stanów minimalnych i dokumentow zakupu.",
        "Kase klienta i realne etapy platnosci powiazane z projektem.",
        "Statusy zamowienia i prowadzenie pracy firmy na etapach.",
        "Pracownikow, ich czas pracy i koszty robocizny.",
    ]

    WHAT_WE_SKIP = [
        "Starego wygladu typu XP i ciezkich, dlugich formularzy.",
        "Zasady 'wszystko na jednym ekranie'.",
        "Chaotycznego mieszania logiki technicznej, finansowej i magazynowej w jednej karcie.",
    ]

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

        updated, done_count, progress_count, todo_count = _load_plan_counts()

        title = QLabel("PLAN I ANALIZA PROJEKTU")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #25334c;")
        root.addWidget(title)

        intro = QLabel(
            "Tu trzymamy w aplikacji dwie rzeczy naraz: co juz zrobilismy w projekcie "
            "oraz jakie wnioski wyciagnelismy ze screenow BAZA i instrukcji 3D Constructor."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 14px; color: #556070;")
        root.addWidget(intro)

        flow_box = _SectionBox(
            "Przeplyw pracy",
            "To jest glowny kierunek pracy firmy i naszej aplikacji. Najpierw szybka wycena, pozniej prowadzenie projektu i rozliczenie.",
            self,
        )
        flow_row = QHBoxLayout()
        flow_row.setSpacing(10)
        for label in ["Nowe zamowienie", "Wycena", "Kalendarz", "Czas pracy", "Bazy / Magazyn", "Finanse"]:
            card = QLabel(label)
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setMinimumHeight(44)
            card.setStyleSheet(
                """
                QLabel {
                    background: #f9fbfd;
                    border: 1px solid #d7dee8;
                    border-radius: 12px;
                    padding: 8px 14px;
                    font-weight: 700;
                    color: #1f2937;
                }
                """
            )
            flow_row.addWidget(card, 1)
        flow_box.layout_main.addLayout(flow_row)
        root.addWidget(flow_box)

        stats = QGridLayout()
        stats.setHorizontalSpacing(14)
        stats.setVerticalSpacing(14)
        stats.addWidget(_InfoCard("Plan aktualizacja", updated, "#c58a2a"), 0, 0)
        stats.addWidget(_InfoCard("Zrobione", str(done_count), "#2d8a5b"), 0, 1)
        stats.addWidget(_InfoCard("W toku", str(progress_count), "#d97706"), 0, 2)
        stats.addWidget(_InfoCard("Do zrobienia", str(todo_count), "#c2410c"), 0, 3)
        root.addLayout(stats)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(16)

        done_box = _SectionBox("Zrobione", "Najwazniejsze rzeczy, ktore juz realnie dzialaja.", self)
        done_list = QListWidget(self)
        self._style_list(done_list)
        for item in self.DONE_ITEMS:
            done_list.addItem(QListWidgetItem(f"- {item}"))
        done_box.layout_main.addWidget(done_list)
        progress_row.addWidget(done_box, 1)

        work_box = _SectionBox("W toku", "To sa obszary, nad ktorymi teraz najbardziej warto pracowac.", self)
        work_list = QListWidget(self)
        self._style_list(work_list)
        for item in self.IN_PROGRESS_ITEMS:
            work_list.addItem(QListWidgetItem(f"- {item}"))
        work_box.layout_main.addWidget(work_list)
        progress_row.addWidget(work_box, 1)

        next_box = _SectionBox("Do zrobienia", "Nastepne duze kroki, z ktorych bedzie najwieksza korzysc dla firmy.", self)
        next_list = QListWidget(self)
        self._style_list(next_list)
        for item in self.NEXT_ITEMS:
            next_list.addItem(QListWidgetItem(f"- {item}"))
        next_box.layout_main.addWidget(next_list)
        progress_row.addWidget(next_box, 1)

        root.addLayout(progress_row)

        analysis_row = QHBoxLayout()
        analysis_row.setSpacing(16)

        keep_box = _SectionBox("Co bierzemy z BAZA i starego programu", "", self)
        keep_list = QListWidget(self)
        self._style_list(keep_list)
        for item in self.WHAT_WE_KEEP:
            keep_list.addItem(QListWidgetItem(f"- {item}"))
        keep_box.layout_main.addWidget(keep_list)
        analysis_row.addWidget(keep_box, 1)

        skip_box = _SectionBox("Czego nie kopiujemy", "", self)
        skip_list = QListWidget(self)
        self._style_list(skip_list)
        for item in self.WHAT_WE_SKIP:
            skip_list.addItem(QListWidgetItem(f"- {item}"))
        skip_box.layout_main.addWidget(skip_list)
        analysis_row.addWidget(skip_box, 1)

        root.addLayout(analysis_row)
        root.addStretch(1)

    @staticmethod
    def _style_list(widget: QListWidget) -> None:
        widget.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #e5eaf0;
                border-radius: 12px;
                background: #fbfcfe;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 4px;
            }
            """
        )
