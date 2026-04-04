from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from src.storage.data_paths import data_dir


@dataclass
class InboxMessage:
    id: str
    source: str           # "email" | "whatsapp"
    sender: str
    subject: str
    snippet: str          # pierwsze ~300 znaków treści
    received_at: str      # ISO datetime string
    read: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "sender": self.sender,
            "subject": self.subject,
            "snippet": self.snippet,
            "received_at": self.received_at,
            "read": self.read,
        }

    @staticmethod
    def from_dict(d: dict) -> "InboxMessage":
        return InboxMessage(
            id=str(d.get("id") or uuid.uuid4()),
            source=str(d.get("source") or "email"),
            sender=str(d.get("sender") or ""),
            subject=str(d.get("subject") or ""),
            snippet=str(d.get("snippet") or ""),
            received_at=str(d.get("received_at") or ""),
            read=bool(d.get("read", False)),
        )


class InboxMessageStore:
    """Lokalny store wiadomości ze wszystkich źródeł (email, WhatsApp)."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "inbox_messages.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_all(self) -> List[InboxMessage]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [InboxMessage.from_dict(d) for d in raw if isinstance(d, dict)]
        except Exception:
            pass
        return []

    def list_unread(self) -> List[InboxMessage]:
        return [m for m in self.list_all() if not m.read]

    def upsert_many(self, messages: List[InboxMessage]) -> int:
        """Dodaje nowe wiadomości (po id). Zwraca liczbę faktycznie nowych."""
        existing = {m.id: m for m in self.list_all()}
        added = 0
        for msg in messages:
            if msg.id not in existing:
                existing[msg.id] = msg
                added += 1
        self._write(list(existing.values()))
        return added

    def mark_read(self, msg_id: str) -> None:
        msgs = self.list_all()
        for m in msgs:
            if m.id == msg_id:
                m.read = True
        self._write(msgs)

    def clear_source(self, source: str) -> None:
        msgs = [m for m in self.list_all() if m.source != source]
        self._write(msgs)

    def _write(self, messages: List[InboxMessage]) -> None:
        # Zachowaj tylko ostatnie 200 wiadomości
        messages = sorted(messages, key=lambda m: m.received_at, reverse=True)[:200]
        self._path.write_text(
            json.dumps([m.to_dict() for m in messages], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
