from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class _BotCardSpec:
    title: str
    subtitle: str
    accent: str
    stage: str
    tasks: tuple[str, ...]


class _PreviewShell(QFrame):
    def __init__(self, title: str, subtitle: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewShell")
        self.setStyleSheet(
            """
            QFrame#previewShell {
                background: #f8fafc;
                border: 1px solid #dbe4f0;
                border-radius: 22px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QFrame()
        header.setStyleSheet(f"QFrame{{background:{accent};border-radius:18px;}}")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("color:#ffffff;font-size:22px;font-weight:800;")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color:#eaf2ff;font-size:12px;")
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header)

        self._body = QVBoxLayout()
        self._body.setSpacing(10)
        layout.addLayout(self._body)

    def body_layout(self) -> QVBoxLayout:
        return self._body


class _WorkstationPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        hero = _PreviewShell(
            "Ekran stanowiska",
            "Podglad dla hali i biura: statusy, kolejka projektow, blokady i co jest gotowe do dalszego etapu.",
            "#1f3c88",
            self,
        )
        hero.body_layout().addWidget(QLabel("Wersja pokazowa ukladu stanowiska i przeplywu projektu."))
        hero.body_layout().addWidget(QLabel("Na jednym ekranie: co gotowe, co blokuje i co przechodzi dalej."))
        root.addWidget(hero)

        board = QFrame()
        board.setStyleSheet(
            """
            QFrame {
                background: #ffffff;
                border: 1px solid #d9e2ec;
                border-radius: 18px;
            }
            """
        )
        board_layout = QGridLayout(board)
        board_layout.setContentsMargins(16, 16, 16, 16)
        board_layout.setHorizontalSpacing(12)
        board_layout.setVerticalSpacing(12)

        metrics = (
            ("Do odbioru", "06", "#10b981"),
            ("W toku", "03", "#f59e0b"),
            ("Blokady", "01", "#ef4444"),
            ("Planowane", "08", "#60a5fa"),
        )
        for idx, (label, value, color) in enumerate(metrics):
            card = QFrame()
            card.setStyleSheet("QFrame{background:#f8fafc;border:1px solid #dbe4f0;border-radius:16px;}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 14, 14, 14)
            card_layout.setSpacing(3)
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color:{color};font-size:28px;font-weight:800;")
            card_layout.addWidget(value_label)
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color:#334155;font-size:12px;font-weight:600;")
            card_layout.addWidget(label_widget)
            board_layout.addWidget(card, 0, idx)

        left = QFrame()
        left.setStyleSheet("QFrame{background:#f8fafc;border:1px solid #dbe4f0;border-radius:16px;}")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(8)
        left_title = QLabel("Kolejka stanowiska")
        left_title.setStyleSheet("font-size:14px;font-weight:800;color:#0f172a;")
        left_layout.addWidget(left_title)
        for title, status, color in (
            ("Projekt 24/031", "Gotowe do odbioru", "#10b981"),
            ("Projekt 24/032", "W toku", "#f59e0b"),
            ("Projekt 24/033", "Brak okuc", "#ef4444"),
        ):
            row = QLabel(f"- {title}  -  {status}")
            row.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")
            left_layout.addWidget(row)
        left_layout.addStretch(1)

        right = QFrame()
        right.setStyleSheet("QFrame{background:#0f172a;border-radius:16px;}")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)
        right_title = QLabel("Co widzi biuro")
        right_title.setStyleSheet("color:#ffffff;font-size:14px;font-weight:800;")
        right_layout.addWidget(right_title)
        for text in (
            "Zielone = gotowe dla nastepnego etapu",
            "Zolte = trwa praca na stanowisku",
            "Czerwone = blokada lub brak",
            "Jedno klikniecie pokazuje kto i kiedy odhaczyl",
        ):
            item = QLabel(f"- {text}")
            item.setStyleSheet("color:#cbd5e1;font-size:12px;")
            item.setWordWrap(True)
            right_layout.addWidget(item)
        right_layout.addStretch(1)

        board_layout.addWidget(left, 1, 0, 1, 2)
        board_layout.addWidget(right, 1, 2, 1, 2)
        root.addWidget(board, 1)

        footer = QLabel(
            "Ten ekran pokazuje tylko podglad. Wlasciwe odhaczanie moze zostac w bocie albo przy stanowisku."
        )
        footer.setStyleSheet("color:#475569;font-size:12px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)


class _BotPreview(QWidget):
    def __init__(self, spec: _BotCardSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        phone = QFrame()
        phone.setStyleSheet(
            """
            QFrame {
                background: #101828;
                border: 2px solid #334155;
                border-radius: 30px;
            }
            """
        )
        phone_layout = QVBoxLayout(phone)
        phone_layout.setContentsMargins(14, 14, 14, 14)
        phone_layout.setSpacing(10)

        top = QFrame()
        top.setStyleSheet("QFrame{background:#0f172a;border-radius:18px;}")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(3)
        title = QLabel(spec.title)
        title.setStyleSheet("color:#ffffff;font-size:18px;font-weight:800;")
        subtitle = QLabel(spec.subtitle)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#cbd5e1;font-size:11px;")
        top_layout.addWidget(title)
        top_layout.addWidget(subtitle)
        phone_layout.addWidget(top)

        banner = QLabel(spec.stage)
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setStyleSheet(
            f"QLabel{{background:{spec.accent};color:#ffffff;font-size:12px;font-weight:800;padding:8px 10px;border-radius:14px;}}"
        )
        phone_layout.addWidget(banner)

        list_shell = QFrame()
        list_shell.setStyleSheet("QFrame{background:#0b1220;border:1px solid #233044;border-radius:20px;}")
        list_layout = QVBoxLayout(list_shell)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(8)
        for task in spec.tasks:
            task_row = QLabel(f"- {task}")
            task_row.setWordWrap(True)
            task_row.setStyleSheet("color:#e2e8f0;font-size:12px;")
            list_layout.addWidget(task_row)
        phone_layout.addWidget(list_shell, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for label, color in (
            ("Zrobione", "#16a34a"),
            ("Brak", "#dc2626"),
            ("Do poprawy", "#f59e0b"),
        ):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton{{background:{color};color:#ffffff;font-weight:800;padding:9px 10px;border-radius:12px;}}"
            )
            buttons.addWidget(button)
        phone_layout.addLayout(buttons)

        note = QLabel("Bot tylko do szybkiego potwierdzenia. Reszta widoczna jest na ekranie stanowiska.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#94a3b8;font-size:11px;")
        phone_layout.addWidget(note)

        root.addWidget(phone, 1)


class _BotGridPage(QWidget):
    def __init__(self, specs: tuple[_BotCardSpec, ...], columns: int = 2, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        for idx, spec in enumerate(specs):
            card = _BotPreview(spec, self)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            grid.addWidget(card, idx // columns, idx % columns)

        root.addLayout(grid, 1)


class TabEkrany(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QWidget {
                background: #eef2f7;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        header = QLabel("Ekrany - podglad stanowiska i botow")
        header.setStyleSheet("font-size:20px;font-weight:800;color:#0f172a;")
        root.addWidget(header)

        sub = QLabel("Osobny podglad: stanowisko, boty dla stanowisk i widok wszystkich botow razem.")
        sub.setStyleSheet("font-size:12px;color:#475569;")
        root.addWidget(sub)

        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)

        workstation = QScrollArea(self)
        workstation.setWidgetResizable(True)
        workstation.setFrameShape(QFrame.Shape.NoFrame)
        workstation.setWidget(_WorkstationPreview(workstation))
        self._tabs.addTab(workstation, "Stanowisko")

        bot_specs = (
            _BotCardSpec(
                title="Bot Biuro glowne",
                subtitle="Koordynuje projekt, sprawdza braki i pcha zadanie do kolejnego stanowiska.",
                accent="#0f172a",
                stage="Koordynacja - decyzje / braki / dalej",
                tasks=("Projekt 24/031 - zatwierdzenie", "Projekt 24/032 - brak okuć", "Projekt 24/033 - priorytet"),
            ),
            _BotCardSpec(
                title="Bot CNC",
                subtitle="Szybkie odhaczanie ciecia i przekazanie do kolejnego etapu.",
                accent="#2563eb",
                stage="CNC - gotowe / brak / do poprawy",
                tasks=("Projekt 24/031 - fronty", "Projekt 24/032 - korpus", "Projekt 24/033 - polki"),
            ),
            _BotCardSpec(
                title="Bot Lakiernia",
                subtitle="Potwierdza lakier, suszenie i przekazanie na montaz.",
                accent="#7c3aed",
                stage="Lakiernia - odebrane / pomalowane",
                tasks=("Projekt 24/031 - fronty", "Projekt 24/034 - boki", "Projekt 24/035 - okleina"),
            ),
            _BotCardSpec(
                title="Bot Montaz",
                subtitle="Potwierdza montaz i zamkniecie zadania.",
                accent="#059669",
                stage="Montaz - gotowe do odbioru",
                tasks=("Projekt 24/031 - komplet", "Projekt 24/032 - brak okuc", "Projekt 24/036 - final"),
            ),
            _BotCardSpec(
                title="Bot Oklejanie",
                subtitle="Szybkie potwierdzenie obrobki i przekazanie dalej.",
                accent="#d97706",
                stage="Oklejanie - w toku / gotowe",
                tasks=("Projekt 24/031 - krawedzie", "Projekt 24/033 - wstawki", "Projekt 24/037 - panel"),
            ),
        )
        bot_page = QScrollArea(self)
        bot_page.setWidgetResizable(True)
        bot_page.setFrameShape(QFrame.Shape.NoFrame)
        bot_page.setWidget(_BotGridPage(bot_specs, columns=2, parent=bot_page))
        self._tabs.addTab(bot_page, "Boty")

        single_pages = (
            ("Bot Biuro glowne", bot_specs[0]),
            ("Bot CNC", bot_specs[1]),
            ("Bot Lakiernia", bot_specs[2]),
            ("Bot Montaz", bot_specs[3]),
            ("Bot Oklejanie", bot_specs[4]),
        )
        for label, spec in single_pages:
            page = QScrollArea(self)
            page.setWidgetResizable(True)
            page.setFrameShape(QFrame.Shape.NoFrame)
            page.setWidget(_BotPreview(spec, parent=page))
            self._tabs.addTab(page, label)

        all_scroll = QScrollArea(self)
        all_scroll.setWidgetResizable(True)
        all_scroll.setFrameShape(QFrame.Shape.NoFrame)
        all_scroll.setWidget(_BotGridPage(bot_specs, columns=2, parent=all_scroll))
        self._tabs.addTab(all_scroll, "Wszystkie")

        root.addWidget(self._tabs, 1)
