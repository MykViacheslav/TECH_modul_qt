from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal


class DataDirSwitcherWidget(QWidget):
    """A lightweight widget to switch the local data directory (production vs sandbox).
    Emits sig_data_dir_changed when a new path is applied.
    """
    sig_data_dir_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        self.label = QLabel("Data directory:")
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton("Browse...")
        self.apply_btn = QPushButton("Apply")

        layout.addWidget(self.label)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.apply_btn)

        self.browse_btn.clicked.connect(self._on_browse)
        self.apply_btn.clicked.connect(self._on_apply)

    def _on_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Data Directory", self.path_edit.text())
        if directory:
            self.path_edit.setText(directory)

    def _on_apply(self) -> None:
        path = self.path_edit.text().strip()
        if path:
            # Update environment for current process and emit signal
            import os
            os.environ["TECH_MODUL_DATA_DIR"] = path
            self.sig_data_dir_changed.emit(path)
            print(f"[DataDirSwitcher] Data directory switched to: {path}")
