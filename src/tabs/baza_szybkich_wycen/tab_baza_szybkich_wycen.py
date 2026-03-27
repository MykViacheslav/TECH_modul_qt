from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


def quick_quote_archive_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "quick_quote_archive.json"


def _to_float(value: str) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    raw = raw.replace("zl", "").replace("ZL", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _is_empty_entry(entry: dict[str, Any]) -> bool:
    client = str(entry.get("client", "") or "").strip()
    if client:
        return False
    price = _to_float(str(entry.get("price", "") or ""))
    if price > 0.0:
        return False
    sections = entry.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            if any(str(section.get(key, "") or "").strip() for key in ("id", "title", "price")):
                return False
    return True


def sanitize_quick_quote_entries(entries: list[Any]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        entry = dict(row)
        if _is_empty_entry(entry):
            continue
        cleaned.append(entry)
    return cleaned


class TabBazaSzybkichWycen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._archive_path = quick_quote_archive_path()
        self._items: list[dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QLabel("BAZA SZYBKICH WYCEN", self)
        header.setStyleSheet("font-size:22px; font-weight:700;")
        root.addWidget(header)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("+ Dodaj wpis", self)
        self.btn_remove = QPushButton("- Usun wpis", self)
        self.btn_save = QPushButton("Zapisz do bazy", self)
        actions.addWidget(self.btn_add, 0)
        actions.addWidget(self.btn_remove, 0)
        actions.addWidget(self.btn_save, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        frame = QFrame(self)
        frame.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 10px; background:#ffffff; }")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["ID", "Klient", "Cena", "VAT", "Marza"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 200)
        frame_layout.addWidget(self.tree, 1)
        root.addWidget(frame, 1)

        self.btn_add.clicked.connect(self._add_entry)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_save.clicked.connect(self._save_archive)

        self._load_archive()
        self._refresh_tree()

    def _load_archive(self) -> None:
        try:
            if self._archive_path.exists():
                text = self._archive_path.read_text(encoding="utf-8")
                payload = json.loads(text)
                if isinstance(payload, list):
                    self._items = sanitize_quick_quote_entries(payload)
        except Exception:
            self._items = []

    def _save_archive(self) -> None:
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)
        self._archive_path.write_text(json.dumps(self._items, indent=2, ensure_ascii=False), encoding="utf-8")

    def _add_entry(self) -> None:
        entry = {
            "id": f"Q{len(self._items) + 1:03d}",
            "client": "",  # placeholder, user can edit tree
            "price": "0.00",
            "vat": "23%",
            "margin": "0.00",
            "sections": [],
        }
        self._items.append(entry)
        self._refresh_tree()

    def _remove_selected(self) -> None:
        for item in self.tree.selectedItems():
            idx = int(item.data(0, Qt.ItemDataRole.UserRole) or -1)
            if 0 <= idx < len(self._items):
                self._items.pop(idx)
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        self.tree.clear()
        for idx, entry in enumerate(self._items):
            top = QTreeWidgetItem(self.tree, [entry["id"], entry["client"], entry["price"], entry["vat"], entry["margin"]])
            top.setData(0, Qt.ItemDataRole.UserRole, idx)
            top.setExpanded(True)
            for section in entry.get("sections", []):
                child = QTreeWidgetItem(top, [section.get("id", ""), section.get("title", ""), section.get("price", "")])
                child.setDisabled(True)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._load_archive()
        self._refresh_tree()
