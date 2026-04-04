from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.storage.codex_notes_store import CodexNotesStore


class TabCodex(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = CodexNotesStore()
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("CODEX_")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        subtitle = QLabel(
            "Wk adka do notatek technicznych, review, decyzji i kr tkich plan w. "
            "Tre zapisuje si do pliku w katalogu danych."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        self.editor = QTextEdit(self)
        self.editor.setPlaceholderText("Wpisz tutaj notatki CODEX_...")
        self.editor.setAcceptRichText(False)
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.editor.setStyleSheet(
            "QTextEdit {"
            " background: #fffdf8;"
            " border: 1px solid #d9c7b2;"
            " border-radius: 10px;"
            " padding: 10px;"
            " font-family: Consolas, 'Courier New', monospace;"
            " font-size: 12px;"
            "}"
        )
        root.addWidget(self.editor, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_reload = QPushButton("Wczytaj")
        self.btn_save = QPushButton("Zapisz")
        self.btn_reset = QPushButton("Przywroc domyslne")
        self.btn_clear = QPushButton("Wyczysc")

        for button in (self.btn_reload, self.btn_save, self.btn_reset, self.btn_clear):
            button.setMinimumWidth(130)

        btn_row.addWidget(self.btn_reload)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #666;")
        root.addWidget(self.lbl_status)

        self.btn_reload.clicked.connect(self._load_text)
        self.btn_save.clicked.connect(self._save_text)
        self.btn_reset.clicked.connect(self._reset_text)
        self.btn_clear.clicked.connect(self._clear_text)
        self.editor.textChanged.connect(self._on_text_changed)

        self._load_text()

    def _set_status(self, text: str, ok: bool = True) -> None:
        color = "#2b7a2b" if ok else "#a33"
        self.lbl_status.setStyleSheet(f"color: {color};")
        self.lbl_status.setText(text)

    def _load_text(self) -> None:
        self._loading = True
        try:
            self.editor.setPlainText(self._store.load_text())
            self._set_status("Wczytano notatk CODEX_.", ok=True)
        finally:
            self._loading = False

    def _save_text(self) -> None:
        text = self.editor.toPlainText()
        self._store.save_text(text)
        self._set_status("Zapisano notatk CODEX_.", ok=True)

    def _reset_text(self) -> None:
        answer = QMessageBox.question(
            self,
            "Przywr ci domy lneEmail",
            "Przywr ci domy ln tre review w zak adce CODEX_Email",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._loading = True
        try:
            self.editor.setPlainText(self._store.reset_to_default())
            self._set_status("Przywr cono domy ln tre CODEX_.", ok=True)
        finally:
            self._loading = False

    def _clear_text(self) -> None:
        answer = QMessageBox.question(
            self,
            "Wyczy ci notatk Email",
            "Wyczy ci zawarto zak adki CODEX_Email",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._loading = True
        try:
            self.editor.clear()
            self._set_status("Wyczyszczono zawarto . Zapisz, eby nadpisa plik.", ok=True)
        finally:
            self._loading = False

    def _on_text_changed(self) -> None:
        if self._loading:
            return
        self._set_status("Masz niezapisane zmiany.", ok=False)
