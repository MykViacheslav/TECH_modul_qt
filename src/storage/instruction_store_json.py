from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.instruction_models import InstructionCardDef
from src.storage.data_paths import data_dir
from src.storage.schema_versioning import read_versioned_map_file, write_versioned_map_file


@dataclass(frozen=True)
class InstructionStoreResult:
    ok: bool
    message_pl: str


class InstructionStoreJson:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (data_dir() / "instruction_cards.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all(self._default_cards_map())
        elif not self._read_all():
            self._write_all(self._default_cards_map())

    def list_cards(self, category: str = "") -> list[InstructionCardDef]:
        category_key = str(category or "").strip().lower()
        out: list[InstructionCardDef] = []
        for card_id, payload in self._read_all().items():
            card = InstructionCardDef.from_dict(payload)
            if not card.instruction_id:
                card.instruction_id = card_id
            if category_key and category_key not in ("all", "wszystkie") and card.category != category_key:
                continue
            out.append(card)
        out.sort(key=lambda item: (item.category, item.title.lower(), item.instruction_id))
        return out

    def get(self, instruction_id: str) -> InstructionCardDef | None:
        key = str(instruction_id or "").strip()
        if not key:
            return None
        raw = self._read_all().get(key)
        if not isinstance(raw, dict):
            return None
        card = InstructionCardDef.from_dict(raw)
        if not card.instruction_id:
            card.instruction_id = key
        return card

    def save_new(self, card: InstructionCardDef) -> InstructionStoreResult:
        payload = card.to_dict()
        key = str(payload.get("instruction_id", "") or "").strip() or self._next_id()
        data = self._read_all()
        if key in data:
            return InstructionStoreResult(False, f'Instrukcja "{key}" juz istnieje.')
        payload["instruction_id"] = key
        data[key] = dict(payload)
        self._write_all(data)
        return InstructionStoreResult(True, f'Zapisano instrukcje "{payload.get("title", key)}".')

    def overwrite(self, card: InstructionCardDef) -> InstructionStoreResult:
        payload = card.to_dict()
        key = str(payload.get("instruction_id", "") or "").strip() or self._next_id()
        payload["instruction_id"] = key
        data = self._read_all()
        data[key] = dict(payload)
        self._write_all(data)
        return InstructionStoreResult(True, f'Nadpisano instrukcje "{payload.get("title", key)}".')

    def delete(self, instruction_id: str) -> InstructionStoreResult:
        key = str(instruction_id or "").strip()
        if not key:
            return InstructionStoreResult(False, "Brak ID instrukcji.")
        data = self._read_all()
        if key not in data:
            return InstructionStoreResult(False, f'Instrukcja "{key}" nie istnieje.')
        data.pop(key, None)
        self._write_all(data)
        return InstructionStoreResult(True, f'Usunieto instrukcje "{key}".')

    def _next_id(self) -> str:
        now = datetime.now()
        return now.strftime("INS-%Y%m%d-%H%M%S-%f")

    def _read_all(self) -> dict[str, dict[str, Any]]:
        return read_versioned_map_file(
            self._path,
            current_version=self.SCHEMA_VERSION,
            migrate_record=self._migrate_record,
        )

    def _write_all(self, items: dict[str, dict[str, Any]]) -> None:
        write_versioned_map_file(self._path, items, current_version=self.SCHEMA_VERSION)

    @staticmethod
    def _migrate_record(record_id: str, raw: dict[str, Any], _source_version: int) -> dict[str, Any]:
        payload = dict(raw or {})
        if not str(payload.get("instruction_id", "") or "").strip():
            payload["instruction_id"] = str(record_id or "")
        payload["category"] = str(payload.get("category", "ogolne") or "ogolne").lower()
        payload["title"] = str(payload.get("title", "") or "")
        payload["when_to_use"] = str(payload.get("when_to_use", "") or "")
        payload["impact"] = str(payload.get("impact", "") or "")
        payload["steps"] = str(payload.get("steps", "") or "")
        payload["visualization_path"] = str(payload.get("visualization_path", "") or "")
        return payload

    def _default_cards_map(self) -> dict[str, dict[str, Any]]:
        defaults = [
            InstructionCardDef(
                instruction_id="INS-OKUCIA-001",
                category="okucia",
                title="Dobor zawiasow i prowadnic",
                when_to_use="Przed zatwierdzeniem finalnej listy elementow.",
                impact="Zmienia koszt, czas montazu i trwalosc zabudowy.",
                steps=(
                    "Sprawdz ciezar frontu.\n"
                    "Dobierz zawias/prowadnice do obciazenia.\n"
                    "Potwierdz rozstaw i ilosc punktow mocowania."
                ),
                visualization_path="",
            ),
            InstructionCardDef(
                instruction_id="INS-MONTAZ-001",
                category="montaz",
                title="Kolejnosc montazu na obiekcie",
                when_to_use="W dniu montazu i podczas odprawy zespolu.",
                impact="Redukuje poprawki i czas pracy ekipy na miejscu.",
                steps=(
                    "1. Weryfikacja wymiarow pomieszczenia.\n"
                    "2. Ustawienie i poziomowanie baz.\n"
                    "3. Montaz wysokich elementow i frontow.\n"
                    "4. Kontrola szczelin i finalny odbior."
                ),
                visualization_path="",
            ),
        ]
        return {card.instruction_id: card.to_dict() for card in defaults}
