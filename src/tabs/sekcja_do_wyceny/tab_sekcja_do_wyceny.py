from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.domain.project_model import ProjectModel
from src.tabs.wycena.dialog_import_3dc import DialogImport3dcWycena


class TabSekcjaDoWyceny(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Import 3D", self)
        title.setStyleSheet("font-size:20px; font-weight:800; color:#0f172a;")
        subtitle = QLabel("Import pliku .project (3DConstructor) i tabela rozliczeniowa.", self)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#64748b;")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.inner = DialogImport3dcWycena(self)
        self.inner.setWindowFlags(Qt.WindowType.Widget)
        self.inner.setWindowTitle("")
        layout.addWidget(self.inner, 1)

    def get_project_model(self) -> ProjectModel | None:
        getter = getattr(self.inner, "get_project_model", None)
        if callable(getter):
            return getter()
        return None
