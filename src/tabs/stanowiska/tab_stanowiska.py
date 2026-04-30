from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from src.widgets.wall_calendar_view import WallCalendarView


class _StationPane(QWidget):
    def __init__(self, station_filter: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._station_filter = station_filter
        self._view: WallCalendarView | None = None
        self._reference_date_iso: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self._hint = QLabel(
            "Kliknij 'Wczytaj ekran', aby uruchomic podglad stanowiska. "
            "To jest ekran tylko do podgladu pracy i statusow."
        )
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("font-size:13px;color:#334155;")
        root.addWidget(self._hint, 1)

        self._btn_load = QPushButton("Wczytaj ekran")
        self._btn_load.setStyleSheet(
            "QPushButton{background:#1d4ed8;color:#ffffff;font-weight:700;padding:8px 14px;border-radius:8px;}"
            "QPushButton:hover{background:#1e40af;}"
        )
        self._btn_load.clicked.connect(self.ensure_loaded)
        root.addWidget(self._btn_load, 0, Qt.AlignmentFlag.AlignCenter)

    def ensure_loaded(self) -> None:
        if self._view is not None:
            if self._reference_date_iso and hasattr(self._view, "set_reference_date"):
                self._view.set_reference_date(self._reference_date_iso)
            return
        layout = self.layout()
        if layout is None:
            return
        self._hint.hide()
        self._btn_load.hide()
        self._view = WallCalendarView(
            parent=self,
            station_filter=self._station_filter,
        )
        if self._reference_date_iso and hasattr(self._view, "set_reference_date"):
            self._view.set_reference_date(self._reference_date_iso)
        layout.addWidget(self._view, 1)

    def set_reference_date(self, date_iso: str) -> None:
        self._reference_date_iso = str(date_iso or "").strip()
        if self._view is not None and hasattr(self._view, "set_reference_date"):
            self._view.set_reference_date(self._reference_date_iso)


class TabStanowiska(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        header = QLabel("Stanowiska - podglad ekranow kiosku")
        header.setStyleSheet("font-size:20px;font-weight:800;color:#0f172a;")
        root.addWidget(header)

        sub = QLabel("CNC / Oklejanie / Lakiernia / Montaz / Biuro")
        sub.setStyleSheet("font-size:12px;color:#94a3b8;")
        root.addWidget(sub)

        plan_hint = QLabel(
            "Warstwa planowania (dawny Plan) jest obecnie prowadzona przez Stanowiska i Ekrany. "
            "Dane robocze pochodza glownie z kalendarza zsynchronizowanego z zamowieniami."
        )
        plan_hint.setWordWrap(True)
        plan_hint.setStyleSheet(
            "QLabel{background:transparent;border:1px solid #d7e1ef;border-radius:8px;"
            "padding:7px 10px;color:#334155;font-size:11px;font-weight:600;}"
        )
        root.addWidget(plan_hint)

        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)

        self._panes: list[_StationPane] = []
        for title, station_filter in (
            ("CNC", "cnc"),
            ("Oklejanie", "oklejanie"),
            ("Lakiernia", "lakiernia"),
            ("Montaz", "montaz"),
            ("BIURO", "biuro"),
        ):
            pane = _StationPane(station_filter=station_filter, parent=self._tabs)
            self._panes.append(pane)
            self._tabs.addTab(pane, title)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, 1)

        # Load first station immediately so user sees real view right away.
        self._on_tab_changed(0)

    @staticmethod
    def _normalize_station_key(value: str) -> str:
        token = str(value or "").strip().lower()
        repl = {
            "ą": "a",
            "ć": "c",
            "ę": "e",
            "ł": "l",
            "ń": "n",
            "ó": "o",
            "ś": "s",
            "ż": "z",
            "ź": "z",
        }
        for src, dst in repl.items():
            token = token.replace(src, dst)
        return " ".join(token.split())

    def open_station(self, station_key: str, reference_date: str | None = None) -> None:
        """Publiczny minimalny handoff: wybiera stanowisko i dociąga pane."""
        normalized = self._normalize_station_key(station_key)
        station_to_tab = {
            "cnc": "CNC",
            "oklejanie": "Oklejanie",
            "lakiernia": "Lakiernia",
            "montaz": "Montaz",
            "zborka": "Montaz",
            "skladanie": "Montaz",
            "biuro": "BIURO",
            "produkcja": "CNC",
            "wycena": "BIURO",
            "projekt": "BIURO",
            "zakup materialow": "BIURO",
            "poprawki": "Montaz",
            "probki": "BIURO",
            "": "BIURO",
        }
        target_title = station_to_tab.get(normalized, "BIURO")
        target_index = -1
        for idx in range(self._tabs.count()):
            if self._tabs.tabText(idx) == target_title:
                target_index = idx
                break
        if target_index < 0:
            target_index = 0
        self._tabs.setCurrentIndex(target_index)
        if reference_date is not None and 0 <= target_index < len(self._panes):
            self._panes[target_index].set_reference_date(str(reference_date or "").strip())
        self._on_tab_changed(target_index)

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._panes):
            return
        self._panes[index].ensure_loaded()
