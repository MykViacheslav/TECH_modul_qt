from __future__ import annotations

from pathlib import Path

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class AvatarStoreJson:
    def __init__(self, path: str | Path | None = None) -> None:
        self.base_path = Path(path) if path else data_dir()
        self.avatar_path = Path(self.base_path) / "avatar_store.json"
        self._ensure_store()

    def _ensure_store(self) -> None:
        self.avatar_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.avatar_path.exists():
            write_json_atomic(
                self.avatar_path,
                {"notes": [], "reminders": []},
                ensure_ascii=False,
                indent=2,
            )

    def _read(self) -> dict:
        data = read_json_file(self.avatar_path, default={"notes": [], "reminders": []}, expected_type=dict)
        notes = data.get("notes", [])
        reminders = data.get("reminders", [])
        return {
            "notes": notes if isinstance(notes, list) else [],
            "reminders": reminders if isinstance(reminders, list) else [],
        }

    def _write(self, data: dict) -> None:
        write_json_atomic(self.avatar_path, data, ensure_ascii=False, indent=2)

    # Public API
    def get_notes(self) -> list[str]:
        data = self._read()
        return data.get("notes", [])

    def add_note(self, text: str) -> None:
        data = self._read()
        notes = data.get("notes", [])
        notes.append(text)
        data["notes"] = notes
        self._write(data)

    def get_reminders(self) -> list[str]:
        data = self._read()
        return data.get("reminders", [])

    def add_reminder(self, text: str) -> None:
        data = self._read()
        reminders = data.get("reminders", [])
        reminders.append(text)
        data["reminders"] = reminders
        self._write(data)
