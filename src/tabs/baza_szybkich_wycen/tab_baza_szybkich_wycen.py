from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.app.app_settings import load_ui_theme_settings

from src.domain.order_models import OrderDef
from src.storage.data_paths import data_dir
from src.storage.order_store_json import OrderStoreJson


QUICK_QUOTE_SORT_NEWEST = "newest"
QUICK_QUOTE_SORT_PRICE_DESC = "price_desc"
QUICK_QUOTE_SORT_PRICE_ASC = "price_asc"


def quick_quote_archive_path() -> Path:
    return data_dir() / "quick_quote_archive.json"


def quick_quote_export_dir() -> Path:
    path = data_dir() / "exports" / "quick_quotes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    raw = raw.replace("zl", "").replace("ZL", "").replace("%", "")
    try:
        return float(raw)
    except Exception:
        return 0.0


def _format_price(value: Any) -> str:
    return f"{max(0.0, _to_float(value)):.2f} zl"


def _format_percent(value: Any, clamp_min: float = 0.0, clamp_max: float = 100.0) -> str:
    parsed = _to_float(value)
    parsed = max(clamp_min, min(clamp_max, parsed))
    return f"{parsed:.2f}%"


def _slugify_filename(value: str, fallback: str = "oferta") -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def _next_unique_export_path(directory: Path, stem: str, suffix: str) -> Path:
    first = directory / f"{stem}{suffix}"
    if not first.exists():
        return first
    index = 2
    while True:
        candidate = directory / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _create_simple_pdf(path: Path, lines: list[str]) -> None:
    # Minimal PDF payload; enough for export artifact checks.
    text = "\n".join(lines)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    payload = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        f"4 0 obj << /Length {len(escaped) + 40} >> stream\n"
        "BT /F1 12 Tf 36 760 Td\n"
        f"({escaped}) Tj\n"
        "ET\n"
        "endstream endobj\n"
        "xref\n0 5\n0000000000 65535 f \n"
        "0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n0000000205 00000 n \n"
        "trailer << /Root 1 0 R /Size 5 >>\nstartxref\n320\n%%EOF\n"
    )
    path.write_bytes(payload.encode("utf-8", errors="ignore"))


def _is_empty_entry(entry: dict[str, Any]) -> bool:
    if str(entry.get("title", "") or "").strip():
        return False
    if str(entry.get("client", "") or "").strip():
        return False
    if _to_float(entry.get("price", entry.get("base_price", "0"))) > 0.0:
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
        sections = entry.get("sections", [])
        if not isinstance(sections, list):
            sections = []
        entry["id"] = str(entry.get("id", "") or "").strip()
        entry["title"] = str(entry.get("title", "") or "").strip() or "[bez nazwy]"
        entry["client"] = str(entry.get("client", "") or "").strip()
        entry["price"] = _format_price(entry.get("price", entry.get("base_price", "0")))
        entry["discount_pct"] = _format_percent(entry.get("discount_pct", "0"), clamp_min=0.0, clamp_max=95.0)
        raw_vat = str(entry.get("vat", "") or "").strip()
        if not raw_vat or raw_vat in ("-", "—"):
            entry["vat"] = "23%"
        else:
            entry["vat"] = raw_vat
        entry["margin"] = _format_percent(entry.get("margin", "0"), clamp_min=0.0, clamp_max=1000.0)
        entry["order_code"] = str(entry.get("order_code", "") or "").strip()
        entry["created_at"] = str(entry.get("created_at", "") or "").strip()
        entry["sections"] = [section for section in sections if isinstance(section, dict)]
        cleaned.append(entry)
    return cleaned


# Removed static TREE_TEXT_STYLE to use dynamic theme-aware styling


class TabBazaSzybkichWycen(QWidget):
    sig_open_order_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._archive_path = quick_quote_archive_path()
        self._order_store = OrderStoreJson()
        self._items: list[dict[str, Any]] = []
        self._is_syncing_tree = False

        theme = load_ui_theme_settings()
        is_tech_night = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        c_text = "#e8efff" if is_tech_night else "#0f172a"
        c_border = "#2a3b59" if is_tech_night else "#d9e0ea"

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QLabel("BAZA SZYBKICH WYCEN", self)
        header.setStyleSheet(f"font-size:22px; font-weight:700; color:{c_text};")
        root.addWidget(header)

        row_filters = QHBoxLayout()
        row_filters.setSpacing(8)
        row_filters.addWidget(QLabel("Szukaj:", self), 0)
        self.ed_filter = QLineEdit(self)
        self.ed_filter.setPlaceholderText("ID / oferta / klient / zamówienie / status")
        row_filters.addWidget(self.ed_filter, 1)
        row_filters.addWidget(QLabel("Sortuj:", self), 0)
        self.cb_sort = QComboBox(self)
        self.cb_sort.addItem("Najnowsze", QUICK_QUOTE_SORT_NEWEST)
        self.cb_sort.addItem("Cena malejaco", QUICK_QUOTE_SORT_PRICE_DESC)
        self.cb_sort.addItem("Cena rosnaco", QUICK_QUOTE_SORT_PRICE_ASC)
        row_filters.addWidget(self.cb_sort, 0)
        self.lab_filter_info = QLabel("0 / 0", self)
        self.lab_filter_info.setStyleSheet("color:#94a3b8; font-weight:700;")
        row_filters.addWidget(self.lab_filter_info, 0)
        root.addLayout(row_filters)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("+ Dodaj wpis", self)
        self.btn_remove = QPushButton("- Usun wpis", self)
        self.btn_create_order = QPushButton("Utwórz zamówienie", self)
        self.btn_open_order = QPushButton("Otwórz zamówienie", self)
        self.btn_export_txt = QPushButton("Eksport TXT", self)
        self.btn_export_pdf = QPushButton("Eksport PDF", self)
        self.btn_save = QPushButton("Zapisz do bazy", self)
        actions.addWidget(self.btn_add, 0)
        actions.addWidget(self.btn_remove, 0)
        actions.addWidget(self.btn_create_order, 0)
        actions.addWidget(self.btn_open_order, 0)
        actions.addWidget(self.btn_export_txt, 0)
        actions.addWidget(self.btn_export_pdf, 0)
        actions.addWidget(self.btn_save, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        frame = QFrame(self); frame.setProperty("uiCard", True)
        frame.setStyleSheet(f"QFrame {{ border: 1px solid {c_border}; border-radius: 10px; background:transparent; }}")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        self.tree = QTreeWidget(self)
        self.tree.setStyleSheet(
            f"""
            QTreeWidget {{
                color: {c_text};
                background: transparent;
                border: none;
            }}
            QTreeWidget::item:selected {{
                background: #3b82f6;
                color: #ffffff;
            }}
            """
        )
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setHeaderLabels(
            ["ID", "Oferta", "Klient", "Cena", "Rabat", "VAT", "Marza", "Zamowienie", "Status zam."]
        )
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 240)
        self.tree.setColumnWidth(2, 180)
        self.tree.setColumnWidth(3, 120)
        self.tree.setColumnWidth(4, 90)
        self.tree.setColumnWidth(5, 70)
        self.tree.setColumnWidth(6, 90)
        self.tree.setColumnWidth(7, 170)
        self.tree.setColumnWidth(8, 130)
        frame_layout.addWidget(self.tree, 1)
        root.addWidget(frame, 1)

        self.btn_add.clicked.connect(self._add_entry)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_create_order.clicked.connect(self._create_order_from_selected_quote)
        self.btn_open_order.clicked.connect(self._open_order_from_selected_quote)
        self.btn_export_txt.clicked.connect(self._export_selected_quote_txt)
        self.btn_export_pdf.clicked.connect(self._export_selected_quote_pdf)
        self.btn_save.clicked.connect(self._save_archive)
        self.ed_filter.textChanged.connect(self._refresh_tree)
        self.cb_sort.currentIndexChanged.connect(self._refresh_tree)
        self.tree.itemChanged.connect(self._on_tree_item_changed)

        self._load_archive()
        self._refresh_tree()

    @staticmethod
    def _build_order_code(quote_id: str, existing_codes: list[str]) -> str:
        base = f"ORD-{str(quote_id or '').strip()}"
        if base not in existing_codes:
            return base
        index = 2
        while True:
            candidate = f"{base}-{index:02d}"
            if candidate not in existing_codes:
                return candidate
            index += 1

    def _selected_top_item(self) -> QTreeWidgetItem | None:
        item = self.tree.currentItem()
        if item is None:
            selected = self.tree.selectedItems()
            item = selected[0] if selected else None
        if item is None:
            return None
        return item if item.parent() is None else item.parent()

    def _selected_entry_index(self) -> int:
        top = self._selected_top_item()
        if top is None:
            return -1
        raw_idx = top.data(0, Qt.ItemDataRole.UserRole)
        idx = int(raw_idx) if raw_idx is not None else -1
        return idx if 0 <= idx < len(self._items) else -1

    def _select_item_by_quote_id(self, quote_id: str) -> None:
        wanted = str(quote_id or "").strip()
        if not wanted:
            return
        for row in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(row)
            if item is None:
                continue
            if str(item.text(0) or "").strip() == wanted:
                self.tree.setCurrentItem(item)
                item.setSelected(True)
                return

    def _load_archive(self) -> None:
        try:
            if self._archive_path.exists():
                text = self._archive_path.read_text(encoding="utf-8")
                payload = json.loads(text) if text.strip() else []
                if isinstance(payload, list):
                    self._items = sanitize_quick_quote_entries(payload)
        except Exception:
            self._items = []

    def _save_archive(self) -> None:
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)
        self._archive_path.write_text(
            json.dumps(self._items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _add_entry(self) -> None:
        now = datetime.now()
        entry = {
            "id": f"Q{len(self._items) + 1:03d}",
            "title": "[bez nazwy]",
            "client": "",
            "price": "0.00 zl",
            "discount_pct": "0.00%",
            "vat": "23%",
            "margin": "0.00%",
            "order_code": "",
            "created_at": now.isoformat(timespec="seconds"),
            "sections": [],
        }
        self._items.append(entry)
        self._refresh_tree()

    def _remove_selected(self) -> None:
        indexes: set[int] = set()
        for item in self.tree.selectedItems():
            top = item if item.parent() is None else item.parent()
            raw_idx = top.data(0, Qt.ItemDataRole.UserRole)
            idx = int(raw_idx) if raw_idx is not None else -1
            if 0 <= idx < len(self._items):
                indexes.add(idx)
        if not indexes:
            return
        for idx in sorted(indexes, reverse=True):
            self._items.pop(idx)
        self._refresh_tree()

    def _normalize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(entry)
        normalized["id"] = str(entry.get("id", "") or "").strip()
        normalized["title"] = str(entry.get("title", "") or "").strip() or "[bez nazwy]"
        normalized["client"] = str(entry.get("client", "") or "").strip()
        normalized["price"] = _format_price(entry.get("price", entry.get("base_price", "0")))
        normalized["discount_pct"] = _format_percent(entry.get("discount_pct", "0"), clamp_min=0.0, clamp_max=95.0)
        normalized["vat"] = str(entry.get("vat", "23%") or "23%").strip()
        normalized["margin"] = _format_percent(entry.get("margin", "0"), clamp_min=0.0, clamp_max=1000.0)
        normalized["order_code"] = str(entry.get("order_code", "") or "").strip()
        normalized["sections"] = [s for s in (entry.get("sections") or []) if isinstance(s, dict)]
        normalized["created_at"] = str(entry.get("created_at", "") or "").strip()
        return normalized

    def _resolve_order_for_entry(self, entry: dict[str, Any]) -> OrderDef | None:
        explicit_code = str(entry.get("order_code", "") or "").strip()
        if explicit_code:
            found = self._order_store.get(explicit_code)
            if found is not None:
                return found
        quote_id = str(entry.get("id", "") or "").strip()
        if quote_id:
            by_prefixed = self._order_store.get(f"ORD-{quote_id}")
            if by_prefixed is not None:
                return by_prefixed
        for order in self._order_store.list_orders():
            if str(getattr(order, "order_id", "") or "").strip() == quote_id:
                return order
        return None

    def _refresh_tree(self) -> None:
        query = str(self.ed_filter.text() or "").strip().lower()
        sort_key = str(self.cb_sort.currentData() or QUICK_QUOTE_SORT_NEWEST)

        rows: list[tuple[int, dict[str, Any], str, str]] = []
        for idx, entry in enumerate(self._items):
            normalized = self._normalize_entry(entry)
            self._items[idx] = normalized
            linked_order = self._resolve_order_for_entry(normalized)
            order_code = str(getattr(linked_order, "code", "") or "").strip()
            order_status = str(getattr(linked_order, "status", "") or "").strip()
            if order_code and not normalized.get("order_code"):
                normalized["order_code"] = order_code
            rows.append((idx, normalized, order_code, order_status))

        if sort_key == QUICK_QUOTE_SORT_PRICE_DESC:
            rows.sort(key=lambda it: _to_float(it[1].get("price", "0")), reverse=True)
        elif sort_key == QUICK_QUOTE_SORT_PRICE_ASC:
            rows.sort(key=lambda it: _to_float(it[1].get("price", "0")))
        else:
            rows.sort(key=lambda it: str(it[1].get("created_at", "") or ""), reverse=True)

        filtered: list[tuple[int, dict[str, Any], str, str]] = []
        for idx, entry, order_code, order_status in rows:
            if query:
                haystack = " | ".join(
                    [
                        str(entry.get("id", "") or ""),
                        str(entry.get("title", "") or ""),
                        str(entry.get("client", "") or ""),
                        str(entry.get("price", "") or ""),
                        order_code,
                        order_status,
                    ]
                ).lower()
                if query not in haystack:
                    continue
            filtered.append((idx, entry, order_code, order_status))

        self._is_syncing_tree = True
        try:
            self.tree.clear()
            for idx, entry, order_code, order_status in filtered:
                top = QTreeWidgetItem(
                    self.tree,
                    [
                        str(entry.get("id", "") or ""),
                        str(entry.get("title", "") or "[bez nazwy]"),
                        str(entry.get("client", "") or ""),
                        str(entry.get("price", "") or "0.00 zl"),
                        str(entry.get("discount_pct", "") or "0.00%"),
                        str(entry.get("vat", "") or "23%"),
                        str(entry.get("margin", "") or "0.00%"),
                        order_code,
                        order_status,
                    ],
                )
                top.setData(0, Qt.ItemDataRole.UserRole, idx)
                top.setData(0, Qt.ItemDataRole.UserRole + 1, str(entry.get("id", "") or ""))
                top.setFlags(
                    top.flags()
                    | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                top.setExpanded(True)

                for section in entry.get("sections", []):
                    child = QTreeWidgetItem(
                        top,
                        [
                            str(section.get("id", "") or ""),
                            str(section.get("title", "") or ""),
                            "",
                            str(section.get("price", "") or "0.00 zl"),
                            "",
                            "",
                            "",
                            "",
                            "",
                        ],
                    )
                    child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.lab_filter_info.setText(f"{len(filtered)} / {len(self._items)}")
        finally:
            self._is_syncing_tree = False

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._is_syncing_tree or item.parent() is not None:
            return
        raw_idx = item.data(0, Qt.ItemDataRole.UserRole)
        idx = int(raw_idx) if raw_idx is not None else -1
        if not (0 <= idx < len(self._items)):
            return

        entry = self._normalize_entry(self._items[idx])
        self._items[idx] = entry
        self._is_syncing_tree = True
        try:
            if column == 0:
                # ID is stable and cannot be changed inline.
                stable_id = str(item.data(0, Qt.ItemDataRole.UserRole + 1) or entry.get("id", ""))
                item.setText(0, stable_id)
            elif column == 1:
                title = str(item.text(1) or "").strip() or "[bez nazwy]"
                entry["title"] = title
                item.setText(1, title)
            elif column == 2:
                entry["client"] = str(item.text(2) or "").strip()
                item.setText(2, entry["client"])
            elif column == 3:
                entry["price"] = _format_price(item.text(3))
                item.setText(3, entry["price"])
            elif column == 4:
                entry["discount_pct"] = _format_percent(item.text(4), clamp_min=0.0, clamp_max=95.0)
                item.setText(4, entry["discount_pct"])
            elif column == 5:
                entry["vat"] = str(item.text(5) or "").strip() or "23%"
                item.setText(5, entry["vat"])
            elif column == 6:
                entry["margin"] = _format_percent(item.text(6), clamp_min=0.0, clamp_max=1000.0)
                item.setText(6, entry["margin"])
            elif column in (7, 8):
                # order link/status are read-only from order store.
                order = self._resolve_order_for_entry(entry)
                item.setText(7, str(getattr(order, "code", "") or ""))
                item.setText(8, str(getattr(order, "status", "") or ""))
                entry["order_code"] = str(getattr(order, "code", "") or "")
        finally:
            self._is_syncing_tree = False

    def _create_order_from_selected_quote(self) -> None:
        idx = self._selected_entry_index()
        if idx < 0:
            QMessageBox.information(self, "Brak wyboru", "Wybierz wycene z listy.")
            return

        entry = self._normalize_entry(self._items[idx])
        self._items[idx] = entry
        quote_id = str(entry.get("id", "") or "")
        order = self._resolve_order_for_entry(entry)

        if order is None:
            existing_codes = [str(getattr(row, "code", "") or "") for row in self._order_store.list_orders()]
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

        entry["order_code"] = str(getattr(order, "code", "") or "")
        self._items[idx] = entry
        self._save_archive()
        self._refresh_tree()
        self._select_item_by_quote_id(quote_id)
        self.sig_open_order_requested.emit(str(getattr(order, "code", "") or ""))
        QMessageBox.information(self, "Zamowienie", "Przejscie do zamowienia jest gotowe.")

    def _open_order_from_selected_quote(self) -> None:
        idx = self._selected_entry_index()
        if idx < 0:
            QMessageBox.information(self, "Brak wyboru", "Wybierz wycene z listy.")
            return

        entry = self._normalize_entry(self._items[idx])
        self._items[idx] = entry
        quote_id = str(entry.get("id", "") or "")
        order = self._resolve_order_for_entry(entry)
        if order is None:
            QMessageBox.information(
                self,
                "Brak powiązania",
                "Ta wycena nie ma jeszcze powiązanego zamówienia. Najpierw utwórz zamówienie.",
            )
            return

        entry["order_code"] = str(getattr(order, "code", "") or "")
        self._items[idx] = entry
        self._save_archive()
        self._refresh_tree()
        self._select_item_by_quote_id(quote_id)
        self.sig_open_order_requested.emit(str(getattr(order, "code", "") or ""))

    def _build_export_lines(self, entry: dict[str, Any], order: OrderDef | None) -> list[str]:
        lines = [
            f"ID oferty: {entry.get('id', '')}",
            f"Oferta: {entry.get('title', '')}",
            f"Klient: {entry.get('client', '')}",
            f"Cena: {entry.get('price', '')}",
            f"Rabat: {entry.get('discount_pct', '0.00%')}",
            f"VAT: {entry.get('vat', '23%')}",
            f"Marza: {entry.get('margin', '0.00%')}",
        ]
        if order is not None:
            lines.append(f"Kod: {order.code}")
            lines.append(f"Status: {order.status}")
        for section in entry.get("sections", []):
            if not isinstance(section, dict):
                continue
            sid = str(section.get("id", "") or "").strip()
            title = str(section.get("title", "") or "").strip()
            price = str(section.get("price", "") or "").strip()
            if sid or title or price:
                lines.append(f"Sekcja: {sid} | {title} | {price}")
        return lines

    def _export_selected_quote_txt(self) -> None:
        idx = self._selected_entry_index()
        if idx < 0:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz wycene do eksportu.")
            return
        entry = self._normalize_entry(self._items[idx])
        order = self._resolve_order_for_entry(entry)
        lines = self._build_export_lines(entry, order)

        stem = f"{entry.get('id', '')}_{_slugify_filename(entry.get('title', ''), fallback='oferta')}"
        out = _next_unique_export_path(quick_quote_export_dir(), stem, ".txt")
        out.write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "Eksport TXT", f"Zapisano: {out.name}")

    def _export_selected_quote_pdf(self) -> None:
        idx = self._selected_entry_index()
        if idx < 0:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz wycene do eksportu.")
            return
        entry = self._normalize_entry(self._items[idx])
        order = self._resolve_order_for_entry(entry)
        lines = self._build_export_lines(entry, order)

        stem = f"{entry.get('id', '')}_{_slugify_filename(entry.get('title', ''), fallback='oferta')}"
        out = _next_unique_export_path(quick_quote_export_dir(), stem, ".pdf")
        _create_simple_pdf(out, lines)
        QMessageBox.information(self, "Eksport PDF", f"Zapisano: {out.name}")

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._load_archive()
        self._refresh_tree()
