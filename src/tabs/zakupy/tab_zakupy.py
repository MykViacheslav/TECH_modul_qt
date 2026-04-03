from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_telegram_settings
from src.domain.shopping_models import ShoppingItemDef, new_shopping_id
from src.integrations.telegram_checklist import (
    collect_latest_item_states,
    send_shopping_checklist_message,
    sync_shopping_checklist_callbacks,
)
from src.integrations.telegram_sender import send_pdf_document
from src.services.shopping_price_compare_service import ShoppingPriceCompareService
from src.storage.shopping_list_store_json import ShoppingListStoreJson
from src.storage.supplier_price_store_json import SupplierPriceStoreJson
from src.tabs.zakupy.telegram_settings_dialog import TelegramSettingsDialog
from src.widgets.shopping_list_report import export_shopping_list_pdf


def _to_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


class TabZakupy(QWidget):
    _HEADERS = [
        "#",
        "ID",
        "Material ID",
        "Nazwa materialu",
        "Ilosc",
        "Jednostka",
        "Data dodania",
        "Status",
        "Dostawca",
        "Cena szac.",
        "Uwagi",
        "Projekt",
    ]

    _STATUSES = ["do kupienia", "zamowiono", "zakupiono", "anulowano"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = ShoppingListStoreJson()
        self._supplier_price_store = SupplierPriceStoreJson()
        self._price_compare_service = ShoppingPriceCompareService(
            supplier_store=self._supplier_price_store
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.btn_reload = QPushButton("Odswiez", self)
        self.btn_add = QPushButton("+ Dodaj", self)
        self.btn_remove = QPushButton("- Usun", self)
        self.btn_save = QPushButton("Zapisz", self)
        self.btn_offer = QPushButton("Oferta dostawcy", self)
        self.btn_compare = QPushButton("Porownaj ceny", self)
        self.btn_advice = QPushButton("Doradz zakup", self)
        self.btn_advice_all = QPushButton("Doradz wszystkie", self)
        self.btn_pdf = QPushButton("PDF", self)
        self.btn_tg_send = QPushButton("Telegram PDF", self)
        self.btn_tg_checklist = QPushButton("Telegram Lista", self)
        self.btn_tg_sync = QPushButton("Telegram Sync", self)
        self.btn_tg_settings = QPushButton("Ustaw Telegram", self)
        for btn in (
            self.btn_reload,
            self.btn_add,
            self.btn_remove,
            self.btn_save,
            self.btn_offer,
            self.btn_compare,
            self.btn_advice,
            self.btn_advice_all,
            self.btn_pdf,
            self.btn_tg_send,
            self.btn_tg_checklist,
            self.btn_tg_sync,
            self.btn_tg_settings,
        ):
            top.addWidget(btn, 0)
        top.addStretch(1)
        root.addLayout(top)

        # --- Filtr po projekcie ---
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        lbl_filter = QLabel("Projekt:", self)
        lbl_filter.setStyleSheet("color:#555;font-size:11px;")
        self.cmb_project_filter = QComboBox(self)
        self.cmb_project_filter.setMinimumWidth(200)
        self.cmb_project_filter.setMaximumWidth(360)
        self.cmb_project_filter.addItem("(wszystkie)")
        self.cmb_project_filter.currentIndexChanged.connect(self._apply_project_filter)
        filter_row.addWidget(lbl_filter, 0)
        filter_row.addWidget(self.cmb_project_filter, 0)
        filter_row.addStretch(1)
        root.addLayout(filter_row)

        self.tbl = QTableWidget(0, len(self._HEADERS), self)
        self.tbl.setHorizontalHeaderLabels(self._HEADERS)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(30)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(10, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(11, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.tbl, 1)

        self.lab = QLabel("", self)
        self.lab.setStyleSheet("color:#1f5130;")
        root.addWidget(self.lab, 0, Qt.AlignmentFlag.AlignLeft)

        self.btn_reload.clicked.connect(self.reload_data)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_save.clicked.connect(self._save)
        self.btn_offer.clicked.connect(self._add_supplier_offer_for_selected)
        self.btn_compare.clicked.connect(self._compare_selected_row_prices)
        self.btn_advice.clicked.connect(self._apply_advice_for_selected)
        self.btn_advice_all.clicked.connect(self._apply_advice_for_all)
        self.btn_pdf.clicked.connect(self._export_pdf_clicked)
        self.btn_tg_send.clicked.connect(self._send_pdf_to_telegram)
        self.btn_tg_checklist.clicked.connect(self._send_checklist_to_telegram)
        self.btn_tg_sync.clicked.connect(self._sync_telegram_checklists)
        self.btn_tg_settings.clicked.connect(self._open_telegram_settings)

        # Light auto-sync so checkbox clicks from Telegram are reflected in app.
        self._tg_sync_timer = QTimer(self)
        self._tg_sync_timer.setInterval(12000)
        self._tg_sync_timer.timeout.connect(self._sync_telegram_checklists_silent)
        self._tg_sync_timer.start()

        self._all_items: list = []
        self.reload_data()

    def reload_data(self) -> None:
        self._all_items = self._store.list_items()
        self._all_items.sort(key=lambda it: str(it.added_date or ""), reverse=True)
        self._refresh_project_filter()
        self._apply_project_filter()

    def _refresh_project_filter(self) -> None:
        """Odswiezenie listy projektow w filtrze."""
        current = self.cmb_project_filter.currentText()
        self.cmb_project_filter.blockSignals(True)
        self.cmb_project_filter.clear()
        self.cmb_project_filter.addItem("(wszystkie)")
        projects = sorted({str(it.project_name or "").strip() for it in self._all_items if str(it.project_name or "").strip()})
        for p in projects:
            self.cmb_project_filter.addItem(p)
        idx = self.cmb_project_filter.findText(current)
        self.cmb_project_filter.setCurrentIndex(max(0, idx))
        self.cmb_project_filter.blockSignals(False)

    def _apply_project_filter(self) -> None:
        """Filtruje tabele po wybranym projekcie."""
        selected = self.cmb_project_filter.currentText().strip()
        show_all = not selected or selected == "(wszystkie)"
        items = self._all_items if show_all else [
            it for it in self._all_items if str(it.project_name or "").strip() == selected
        ]
        self.tbl.setRowCount(0)
        for idx, item in enumerate(items, start=1):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self._set_row_values(row=row, order_no=idx, item=item)

    def _set_row_values(self, row: int, order_no: int, item: ShoppingItemDef) -> None:
        self.tbl.setItem(row, 0, QTableWidgetItem(str(order_no)))
        self.tbl.setItem(row, 1, QTableWidgetItem(str(item.item_id or "")))
        self.tbl.setItem(row, 2, QTableWidgetItem(str(item.material_id or "")))
        self.tbl.setItem(row, 3, QTableWidgetItem(str(item.material_name or "")))
        self.tbl.setItem(row, 4, QTableWidgetItem(f"{float(item.quantity_needed or 0.0):.2f}"))
        self.tbl.setItem(row, 5, QTableWidgetItem(str(item.unit or "")))
        self.tbl.setItem(row, 6, QTableWidgetItem(str(item.added_date or "")))

        status_combo = QComboBox(self.tbl)
        status_combo.addItems(self._STATUSES)
        status_combo.setMinimumHeight(22)
        status_combo.setMaximumHeight(24)
        status_combo.setStyleSheet(
            "QComboBox {"
            " margin: 0px;"
            " padding: 1px 6px;"
            " border: 1px solid #cfc7b8;"
            " border-radius: 6px;"
            " background: #fbfaf7;"
            "}"
            "QComboBox::drop-down { border: 0; width: 16px; }"
        )
        idx_status = status_combo.findText(str(item.status or "").strip())
        if idx_status >= 0:
            status_combo.setCurrentIndex(idx_status)
        self.tbl.setCellWidget(row, 7, status_combo)
        self.tbl.setRowHeight(row, max(self.tbl.rowHeight(row), status_combo.sizeHint().height() + 6))

        self.tbl.setItem(row, 8, QTableWidgetItem(str(item.supplier or "")))
        self.tbl.setItem(row, 9, QTableWidgetItem(f"{float(item.price_estimate or 0.0):.2f}"))
        self.tbl.setItem(row, 10, QTableWidgetItem(str(item.notes or "")))
        self.tbl.setItem(row, 11, QTableWidgetItem(str(item.project_name or "")))

    def _add_row(self) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        item = ShoppingItemDef(
            item_id="",
            material_id="",
            material_name="Nowy material",
            quantity_needed=1.0,
            unit="szt",
            added_date=datetime.now().strftime("%Y-%m-%d"),
            status="do kupienia",
        )
        self._set_row_values(row=row, order_no=row + 1, item=item)

    def _remove_row(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not rows:
            if self.tbl.currentRow() >= 0:
                self.tbl.removeRow(self.tbl.currentRow())
            return
        for idx in sorted(rows, key=lambda x: x.row(), reverse=True):
            self.tbl.removeRow(int(idx.row()))
        self._refresh_row_numbers()

    def _refresh_row_numbers(self) -> None:
        for row in range(self.tbl.rowCount()):
            self.tbl.setItem(row, 0, QTableWidgetItem(str(row + 1)))

    def _collect_table_items(self, assign_missing_ids: bool) -> list[ShoppingItemDef]:
        out: list[ShoppingItemDef] = []
        for row in range(self.tbl.rowCount()):
            item_id = self.tbl.item(row, 1).text().strip() if self.tbl.item(row, 1) else ""
            material_id = self.tbl.item(row, 2).text().strip() if self.tbl.item(row, 2) else ""
            material_name = self.tbl.item(row, 3).text().strip() if self.tbl.item(row, 3) else ""
            quantity = _to_float(self.tbl.item(row, 4).text().strip() if self.tbl.item(row, 4) else "")
            unit = self.tbl.item(row, 5).text().strip() if self.tbl.item(row, 5) else ""
            added_date = self.tbl.item(row, 6).text().strip() if self.tbl.item(row, 6) else ""
            status_combo = self.tbl.cellWidget(row, 7)
            status = status_combo.currentText().strip() if isinstance(status_combo, QComboBox) else "do kupienia"
            supplier = self.tbl.item(row, 8).text().strip() if self.tbl.item(row, 8) else ""
            price_estimate = _to_float(self.tbl.item(row, 9).text().strip() if self.tbl.item(row, 9) else "")
            notes = self.tbl.item(row, 10).text().strip() if self.tbl.item(row, 10) else ""
            project_name = self.tbl.item(row, 11).text().strip() if self.tbl.item(row, 11) else ""

            # Skip empty technical rows.
            if not any([item_id, material_id, material_name, quantity > 0, unit, supplier, notes]):
                continue

            if assign_missing_ids and not item_id:
                item_id = new_shopping_id()
                self.tbl.setItem(row, 1, QTableWidgetItem(item_id))

            if not added_date:
                added_date = datetime.now().strftime("%Y-%m-%d")
                self.tbl.setItem(row, 6, QTableWidgetItem(added_date))

            out.append(
                ShoppingItemDef(
                    item_id=item_id,
                    material_id=material_id,
                    material_name=material_name,
                    quantity_needed=quantity,
                    unit=unit,
                    added_date=added_date,
                    status=status,
                    supplier=supplier,
                    price_estimate=price_estimate,
                    notes=notes,
                    last_updated=datetime.now().isoformat(timespec="seconds"),
                    project_name=project_name,
                )
            )
        return out

    def _save(self) -> None:
        items = self._collect_table_items(assign_missing_ids=True)
        existing_ids = {str(item.item_id) for item in self._store.list_items()}
        current_ids = {str(item.item_id) for item in items if str(item.item_id).strip()}

        for removed_id in sorted(existing_ids - current_ids):
            self._store.delete_item(removed_id)

        for item in items:
            self._store.save_item(item)

        self.lab.setText("Zapisano liste zakupow.")
        self.reload_data()

    def _selected_row(self) -> int:
        model = self.tbl.selectionModel()
        if model is not None:
            rows = model.selectedRows()
            if rows:
                return int(rows[0].row())
        return int(self.tbl.currentRow())

    def _cell_text(self, row: int, column: int) -> str:
        item = self.tbl.item(row, column)
        return item.text().strip() if item is not None else ""

    def _set_cell_text(self, row: int, column: int, value: str) -> None:
        self.tbl.setItem(row, column, QTableWidgetItem(str(value or "")))

    def _material_context_for_row(self, row: int) -> tuple[str, str, float, str, float]:
        material_id = self._cell_text(row, 2)
        material_name = self._cell_text(row, 3)
        quantity = _to_float(self._cell_text(row, 4))
        unit = self._cell_text(row, 5)
        current_price = _to_float(self._cell_text(row, 9))
        return material_id, material_name, quantity, unit, current_price

    def _add_supplier_offer_for_selected(self) -> None:
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Zakupy", "Najpierw zaznacz pozycje na liscie zakupow.")
            return

        material_id, material_name, _, unit, current_price = self._material_context_for_row(row)
        if not material_id and not material_name:
            QMessageBox.information(
                self,
                "Zakupy",
                "Wybrana pozycja nie ma Material ID ani nazwy materialu.",
            )
            return

        supplier_default = self._cell_text(row, 8)
        supplier, ok = QInputDialog.getText(
            self,
            "Oferta dostawcy",
            "Dostawca / hurtownia:",
            text=supplier_default,
        )
        if not ok or not str(supplier or "").strip():
            return

        price, ok = QInputDialog.getDouble(
            self,
            "Oferta dostawcy",
            "Cena za jednostke:",
            value=max(0.0, current_price),
            min=0.0,
            max=10_000_000.0,
            decimals=4,
        )
        if not ok or price <= 0:
            return

        basis, ok = QInputDialog.getItem(
            self,
            "Oferta dostawcy",
            "Typ ceny:",
            ["brutto", "netto", "unknown"],
            0,
            False,
        )
        if not ok:
            return

        note, ok = QInputDialog.getText(
            self,
            "Oferta dostawcy",
            "Notatka (opcjonalnie):",
            text="",
        )
        if not ok:
            return

        payload = self._supplier_price_store.upsert_row(
            {
                "material_id": material_id,
                "material_name": material_name,
                "supplier": str(supplier or "").strip(),
                "unit": unit,
                "unit_price": float(price),
                "price_basis": str(basis or "unknown").strip().lower(),
                "source": "manual",
                "note": str(note or "").strip(),
            }
        )
        self.lab.setText(
            f"Zapisano oferte: {payload.get('supplier', '-')}, {float(payload.get('unit_price', 0.0)):.2f} zl."
        )

    def _compare_selected_row_prices(self) -> None:
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Zakupy", "Najpierw zaznacz pozycje na liscie zakupow.")
            return

        material_id, material_name, quantity, unit, current_price = self._material_context_for_row(row)
        recommendation = self._price_compare_service.recommend_for_item(
            material_id=material_id,
            material_name=material_name,
            quantity=quantity,
            unit=unit,
            preferred_basis="brutto",
            current_unit_price=current_price,
        )
        if recommendation is None:
            QMessageBox.information(
                self,
                "Porownanie cen",
                "Brak ofert dla wybranego materialu.\nDodaj recznie oferte przyciskiem 'Oferta dostawcy'.",
            )
            return

        lines: list[str] = []
        title_name = material_name or material_id or "-"
        lines.append(f"Material: {title_name}")
        lines.append(f"Ilosc: {quantity:.3f} {unit or ''}".strip())
        lines.append(f"Porownanie po: {recommendation.compare_basis}")
        lines.append("")
        lines.append("Ranking ofert:")
        for idx, offer in enumerate(recommendation.ranked_offers[:10], start=1):
            total = offer.estimated_total(quantity)
            unit_label = offer.unit or unit or "jedn"
            src_label = offer.source or "zrodlo"
            lines.append(
                f"{idx}. {offer.supplier} | {offer.unit_price:.2f} zl/{unit_label} | razem: {total:.2f} zl | {offer.price_basis} | {src_label}"
            )

        lines.append("")
        lines.append(
            f"Najlepsza oferta: {recommendation.best_offer.supplier} ({recommendation.best_offer.unit_price:.2f} zl)."
        )
        if recommendation.current_total > 0:
            lines.append(
                f"Oszczednosc szacowana: {recommendation.potential_saving:.2f} zl (dla tej pozycji)."
            )
        if recommendation.warning:
            lines.append(f"Uwaga: {recommendation.warning}")

        QMessageBox.information(self, "Porownanie cen", "\n".join(lines))
        self.lab.setText(
            f"Najtaniej: {recommendation.best_offer.supplier} ({recommendation.best_offer.unit_price:.2f} zl)."
        )

    def _apply_advice_for_selected(self) -> None:
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Zakupy", "Najpierw zaznacz pozycje na liscie zakupow.")
            return

        changed = self._apply_recommendation_to_row(row)
        if not changed:
            QMessageBox.information(
                self,
                "Doradz zakup",
                "Brak dostepnej rekomendacji dla wybranej pozycji.",
            )
            return
        self.lab.setText("Wpisano rekomendacje dostawcy i ceny dla wybranej pozycji.")

    def _apply_advice_for_all(self) -> None:
        changed = 0
        missing = 0
        for row in range(self.tbl.rowCount()):
            if self._apply_recommendation_to_row(row):
                changed += 1
            else:
                missing += 1

        if changed <= 0:
            QMessageBox.information(
                self,
                "Doradz wszystkie",
                "Brak pozycji z dostepna rekomendacja cenowa.",
            )
            return

        QMessageBox.information(
            self,
            "Doradz wszystkie",
            f"Zaktualizowano pozycji: {changed}\nBez rekomendacji: {missing}",
        )
        self.lab.setText(f"Doradzono zakupy dla {changed} pozycji.")

    def _apply_recommendation_to_row(self, row: int) -> bool:
        material_id, material_name, quantity, unit, current_price = self._material_context_for_row(row)
        if not material_id and not material_name:
            return False

        recommendation = self._price_compare_service.recommend_for_item(
            material_id=material_id,
            material_name=material_name,
            quantity=quantity,
            unit=unit,
            preferred_basis="brutto",
            current_unit_price=current_price,
        )
        if recommendation is None:
            return False

        best = recommendation.best_offer
        changed = False
        if best.supplier and best.supplier != self._cell_text(row, 8):
            self._set_cell_text(row, 8, best.supplier)
            changed = True

        best_price_text = f"{best.unit_price:.2f}"
        if best.unit_price > 0 and best_price_text != self._cell_text(row, 9):
            self._set_cell_text(row, 9, best_price_text)
            changed = True

        note = self._cell_text(row, 10)
        parts: list[str] = [part for part in [best.source, best.price_basis] if part]
        note_suffix = f"Rekomendacja: {best.unit_price:.2f} zl"
        if parts:
            note_suffix += f" ({' / '.join(parts)})"
        if note_suffix and note_suffix not in note:
            merged = f"{note} | {note_suffix}".strip(" |") if note else note_suffix
            self._set_cell_text(row, 10, merged)
            changed = True
        return changed

    def _export_pdf_clicked(self) -> None:
        path = self._export_pdf(open_after=True)
        if path is not None:
            self.lab.setText(f"PDF gotowy: {path}")

    def _export_pdf(self, open_after: bool) -> str | None:
        items = self._collect_table_items(assign_missing_ids=False)
        if not items:
            QMessageBox.information(self, "Lista zakupow", "Brak pozycji do eksportu.")
            return None
        try:
            target = export_shopping_list_pdf(items)
            if open_after:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            return str(target)
        except Exception as exc:
            QMessageBox.critical(self, "PDF", f"Nie udalo sie wygenerowac PDF:\n{exc}")
            return None

    def _send_pdf_to_telegram(self) -> None:
        pdf_path = self._export_pdf(open_after=False)
        if not pdf_path:
            return

        settings = load_telegram_settings()
        if not (settings.enabled and settings.bot_token and settings.chat_id):
            answer = QMessageBox.question(
                self,
                "Telegram",
                "Telegram nie jest skonfigurowany.\nOtworzyc ustawienia teraz?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._open_telegram_settings()
            settings = load_telegram_settings()
            if not (settings.enabled and settings.bot_token and settings.chat_id):
                return

        try:
            items = self._collect_table_items(assign_missing_ids=False)
            caption = (
                f"TECH_modul - lista zakupow ({len(items)} poz.) "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            send_pdf_document(
                bot_token=settings.bot_token,
                chat_id=settings.chat_id,
                pdf_path=pdf_path,
                caption=caption,
            )
            self.lab.setText("PDF wyslany na Telegram.")
        except Exception as exc:
            QMessageBox.critical(self, "Telegram", f"Wysylka nie udala sie:\n{exc}")

    def _send_checklist_to_telegram(self) -> None:
        items = self._collect_table_items(assign_missing_ids=True)
        if not items:
            QMessageBox.information(self, "Telegram", "Brak pozycji na liscie zakupow.")
            return

        # Keep IDs/state consistent before sending checklist.
        self._save()
        items = self._store.list_items()
        items.sort(key=lambda it: str(it.added_date or ""), reverse=True)

        settings = load_telegram_settings()
        if not (settings.enabled and settings.bot_token and settings.chat_id):
            answer = QMessageBox.question(
                self,
                "Telegram",
                "Telegram nie jest skonfigurowany.\nOtworzyc ustawienia teraz?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._open_telegram_settings()
            settings = load_telegram_settings()
            if not (settings.enabled and settings.bot_token and settings.chat_id):
                return

        try:
            payload = send_shopping_checklist_message(
                bot_token=settings.bot_token,
                chat_id=settings.chat_id,
                items=items,
                title=f"TECH_modul - lista zakupow ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            )
            self.lab.setText(
                f"Wyslano checkliste Telegram (ID: {payload.get('list_id', '-')}, poz.: {len(items)})."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Telegram", f"Wysylka checklisty nie udala sie:\n{exc}")

    def _sync_telegram_checklists(self) -> None:
        self._sync_telegram_checklists_impl(silent=False)

    def _sync_telegram_checklists_silent(self) -> None:
        self._sync_telegram_checklists_impl(silent=True)

    def _sync_telegram_checklists_impl(self, silent: bool) -> None:
        settings = load_telegram_settings()
        if not (settings.enabled and settings.bot_token and settings.chat_id):
            return

        try:
            summary = sync_shopping_checklist_callbacks(bot_token=settings.bot_token)
        except Exception as exc:
            if not silent:
                QMessageBox.critical(self, "Telegram", f"Sync checklisty nie udal sie:\n{exc}")
            return

        applied = summary.get("applied")
        if not isinstance(applied, list):
            applied = []

        now_iso = datetime.now().isoformat(timespec="seconds")
        changed = 0
        changed_ids: set[str] = set()

        def _state_to_status(state_value: object, checked_value: object) -> str:
            state = str(state_value or "").strip().lower()
            if state in {"partial", "zamowiono", "ordered"}:
                return "zamowiono"
            if state in {"done", "zakupiono"}:
                return "zakupiono"
            return "zakupiono" if bool(checked_value) else "do kupienia"

        for row in applied:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("item_id", "") or "").strip()
            if not item_id:
                continue
            new_status = _state_to_status(row.get("state"), row.get("checked", False))
            item = self._store.get_item(item_id)
            if item is None:
                # Allow Telegram-only test/demo checklists to materialize in local list.
                item = ShoppingItemDef(
                    item_id=item_id,
                    material_id="",
                    material_name=str(row.get("label", "") or f"Pozycja {item_id}").strip() or f"Pozycja {item_id}",
                    quantity_needed=1.0,
                    unit="szt",
                    added_date=datetime.now().strftime("%Y-%m-%d"),
                    status=new_status,
                    supplier="",
                    price_estimate=0.0,
                    notes="Dodano z Telegram checklist",
                    last_updated=now_iso,
                )
            if item is None:
                continue
            if str(item.status or "").strip() == new_status:
                continue
            item.status = new_status
            item.last_updated = now_iso
            self._store.save_item(item)
            changed += 1
            changed_ids.add(item_id)

        # Reconcile with latest persisted checklist state to avoid missing changes
        # when callbacks were already consumed by another sync process.
        latest_states = collect_latest_item_states()
        for item_id, tri_state in latest_states.items():
            if not item_id:
                continue
            item = self._store.get_item(item_id)
            if item is None:
                continue
            new_status = _state_to_status(tri_state, False)
            if str(item.status or "").strip() == new_status:
                continue
            item.status = new_status
            item.last_updated = now_iso
            self._store.save_item(item)
            if item_id not in changed_ids:
                changed += 1
                changed_ids.add(item_id)

        if changed > 0:
            self.reload_data()
            self.lab.setText(f"Telegram Sync: zaktualizowano {changed} pozycji.")
        elif not silent:
            self.lab.setText("Telegram Sync: brak zmian do zapisania.")

    def _open_telegram_settings(self) -> None:
        dlg = TelegramSettingsDialog(self)
        if dlg.exec():
            self.lab.setText("Ustawienia Telegram zapisane.")
