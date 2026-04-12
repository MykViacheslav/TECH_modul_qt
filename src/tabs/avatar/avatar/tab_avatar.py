from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from src.avatar.avatar_widget import AvatarWidget
from src.storage.data_paths import data_dir


class AvatarTab(QWidget):
    def __init__(self, data_dir_path: str | None = None, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.avatar = AvatarWidget(data_dir=data_dir_path or str(data_dir()), parent=self)
        layout.addWidget(self.avatar)
        self.setLayout(layout)
