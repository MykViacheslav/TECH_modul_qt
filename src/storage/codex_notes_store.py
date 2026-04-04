from __future__ import annotations

from pathlib import Path

from src.storage.data_paths import data_dir


DEFAULT_CODEX_NOTE = """# CODEX_

## Cel wkładki
Ta zakładka służy jako notatnik roboczy dla review, uwag i decyzji technicznych.

## Ostatni review programu
### Najważniejsze uwagi
1. Wkładki są grupowane poprawnie, ale część z nich jest tylko wyłączana, nie ukrywana.
2. Nazwy i treść części wkładek nie zawsze odpowiadają temu, co robi widget.
3. Kiosk na Androidzie działa, ale ma wyraźny próg wejścia: HTTPS, certyfikat i kamera.
4. Moduł czasu pracy działa, ale logika edycji i zapisu jest jeszcze mocno w jednym widoku.
5. Brakuje jeszcze testów na nowe ścieżki, szczególnie dla kiosku i edycji czasu pracy.

## Wnioski
- Układ zakładek jest czytelny i praktyczny.
- Największe ryzyko to spójność nazw i utrzymanie logiki przy dalszym rozwoju.
- `kiosk-lite` jest rozsądniejszym domyślnym trybem na tablet.

## Następne kroki
1. Ukryć nieaktywne wkładki zamiast tylko je wyłączać.
2. Doprecyzować `Ustawienia`, żeby nazwa odpowiadała funkcji.
3. Ustawić `kiosk-lite` jako domyślny tryb na Androidzie.
4. Dodać testy do edycji czasu pracy i kiosku.
5. Rozdzielić logikę czasu pracy od UI.
"""


class CodexNotesStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "codex_notes.md"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(DEFAULT_CODEX_NOTE, encoding="utf-8")

    def load_text(self) -> str:
        try:
            text = self._path.read_text(encoding="utf-8")
            return text if text.strip() else DEFAULT_CODEX_NOTE
        except Exception:
            return DEFAULT_CODEX_NOTE

    def save_text(self, text: str) -> None:
        payload = str(text or "").rstrip()
        if not payload:
            payload = DEFAULT_CODEX_NOTE
        self._path.write_text(payload + "\n", encoding="utf-8")

    def reset_to_default(self) -> str:
        self.save_text(DEFAULT_CODEX_NOTE)
        return DEFAULT_CODEX_NOTE

