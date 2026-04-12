from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

# Reużywamy istniejący panel definicji usług z tab_uslugi.
# _CennikPanel obsługuje ServiceStoreJson (definicje: nazwa, typ, jednostka, cena domyślna).
from src.tabs.uslugi.tab_uslugi import _CennikPanel


class TabBazaUslug(QWidget):
    """
    Baza usług — definicje: cennik, typy, jednostki, ceny domyślne.

    Reużywa _CennikPanel z TabUslugi. Odczytuje i zapisuje przez ServiceStoreJson.
    Warstwa użycia usług (nowa usługa, klijenty, baza wycen) jest w Wycena → Usługi.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("Baza usług", self)
        title.setStyleSheet("font-size:20px; font-weight:800; color:#111827;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Definicje usług: cennik, typy, jednostki, ceny domyślne. "
            "Aby użyć usługi w ofercie — przejdź do Wycena → Usługi.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#64748b;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self._cennik = _CennikPanel(self)
        root.addWidget(self._cennik, 1)
