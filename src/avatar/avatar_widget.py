from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QInputDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.storage.avatar_store_json import AvatarStoreJson


class AvatarWidget(QWidget):
    """A minimal local avatar widget with start/stop listening and note saving.
    This is MVP-friendly and relies on a simple, manual transcription for MVP
    (in place of real STT during early iterations).
    """

    def __init__(self, data_dir: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._store = AvatarStoreJson(path=data_dir)
        self._init_ui()
        self._listening = False

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.lbl_title = QLabel("Avatar Assistant (Offline)")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)

        # Recording controls
        self.btn_record = QPushButton("Start Listening")
        self.lbl_status = QLabel("Idle")
        self.btn_record.clicked.connect(self._toggle_listening)
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.btn_record)
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Notes / transcripts pane
        self.notes_view = QTextEdit()
        self.notes_view.setReadOnly(True)
        layout.addWidget(self.notes_view)

        self._load_notes()

    def _load_notes(self) -> None:
        notes = self._store.get_notes()
        self.notes_view.clear()
        for idx, n in enumerate(notes, 1):
            self.notes_view.append(f"{idx}. {n}")

    def _toggle_listening(self) -> None:
        if not self._listening:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self) -> None:
        self._listening = True
        self.lbl_status.setText("Listening...")
        self.btn_record.setText("Stop Listening")
        # In MVP we do not perform real STT yet. We will prompt user to input transcription.
        # This keeps UI responsive without external dependencies.

    def _stop_listening(self) -> None:
        self._listening = False
        self.lbl_status.setText("Idle")
        self.btn_record.setText("Start Listening")
        self._simulate_transcription()

    def _simulate_transcription(self) -> None:
        text, ok = QInputDialog.getText(self, "Transcription (simulate)", "Enter transcribed text:")
        if ok and text:
            self._store_note(text)
            self._load_notes()

    def _store_note(self, text: str) -> None:
        self._store.add_note(text)
