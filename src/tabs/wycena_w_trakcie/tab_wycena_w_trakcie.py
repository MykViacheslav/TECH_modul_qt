from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.domain.order_models import OrderDef
from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import (
    TabBazaSzybkichWycen,
    quick_quote_archive_path,
    quick_quote_in_progress_archive_path,
    sanitize_quick_quote_entries,
)


class TabWycenaWTrakcie(TabBazaSzybkichWycen):
    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            archive_path=quick_quote_in_progress_archive_path(),
            title_text="WYCENA W TRAKCIE",
            save_button_text="ZAPISZ",
        )
        try:
            self.btn_save.clicked.disconnect()
        except Exception:
            pass
        self.btn_save.clicked.connect(self._save_selected_to_orders_base)

    def _selected_entry_indexes(self) -> list[int]:
        indexes: set[int] = set()
        for item in self.tree.selectedItems():
            top = item if item.parent() is None else item.parent()
            raw_idx = top.data(0, Qt.ItemDataRole.UserRole)
            idx = int(raw_idx) if raw_idx is not None else -1
            if 0 <= idx < len(self._items):
                indexes.add(idx)
        return sorted(indexes)

    @staticmethod
    def _load_quote_base_entries() -> list[dict[str, Any]]:
        path = quick_quote_archive_path()
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return sanitize_quick_quote_entries(payload)
        except Exception:
            pass
        return []

    @staticmethod
    def _save_quote_base_entries(entries: list[dict[str, Any]]) -> None:
        path = quick_quote_archive_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sanitize_quick_quote_entries(entries), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _upsert_quote_entry(entries: list[dict[str, Any]], entry: dict[str, Any]) -> None:
        order_code = str(entry.get("order_code", "") or "").strip()
        quote_id = str(entry.get("id", "") or "").strip()
        match_idx = -1
        for idx, row in enumerate(entries):
            row_order_code = str(row.get("order_code", "") or "").strip()
            row_quote_id = str(row.get("id", "") or "").strip()
            if order_code and row_order_code == order_code:
                match_idx = idx
                break
            if not order_code and quote_id and row_quote_id == quote_id:
                match_idx = idx
                break
        if match_idx >= 0:
            merged = dict(entries[match_idx])
            merged.update(entry)
            entries[match_idx] = merged
        else:
            entries.append(entry)

    def _ensure_order_in_base(self, entry: dict[str, Any]) -> tuple[OrderDef, bool]:
        linked_order = self._resolve_order_for_entry(entry)
        if linked_order is not None:
            return linked_order, False

        existing_codes = [str(getattr(row, "code", "") or "") for row in self._order_store.list_orders()]
        requested_code = str(entry.get("order_code", "") or "").strip()
        if requested_code and requested_code not in existing_codes:
            order_code = requested_code
        else:
            order_code = self._build_order_code(str(entry.get("id", "") or ""), existing_codes)

        sections = entry.get("sections", [])
        notes_lines = [
            f"Oferta: {entry.get('id', '')}",
            f"Tytul: {entry.get('title', '')}",
            f"Cena: {entry.get('price', '')}",
        ]
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue
                section_title = str(section.get("title", "") or "").strip()
                if section_title:
                    notes_lines.append(f"Sekcja: {section_title}")

        order = OrderDef(
            code=order_code,
            order_id=str(entry.get("id", "") or ""),
            order_name=str(entry.get("title", "") or ""),
            client_name=str(entry.get("client", "") or ""),
            status="Wycena gotowa",
            notes="\n".join(notes_lines).strip(),
        )
        self._order_store.save_new(order)
        return order, True

    def _save_selected_to_orders_base(self) -> None:
        selected_indexes = self._selected_entry_indexes()
        if not selected_indexes:
            QMessageBox.information(self, "Brak wyboru", "Zaznacz wycene do zapisania.")
            return

        quote_base_entries = self._load_quote_base_entries()
        moved_count = 0
        created_orders = 0

        for idx in selected_indexes:
            entry = self._normalize_entry(self._items[idx])
            if not str(entry.get("created_at", "") or "").strip():
                entry["created_at"] = datetime.now().isoformat(timespec="seconds")

            order, created = self._ensure_order_in_base(entry)
            entry["order_code"] = str(getattr(order, "code", "") or "").strip()
            self._upsert_quote_entry(quote_base_entries, entry)

            moved_count += 1
            if created:
                created_orders += 1

        self._save_quote_base_entries(quote_base_entries)

        for idx in sorted(selected_indexes, reverse=True):
            self._items.pop(idx)
        self._save_archive()
        self._refresh_tree()

        QMessageBox.information(
            self,
            "Zapisano",
            (
                f"Przeniesiono {moved_count} wycen(y) do bazy.\n"
                f"Utworzono {created_orders} nowe zamowienie(a) w bazie zamowien."
            ),
        )
