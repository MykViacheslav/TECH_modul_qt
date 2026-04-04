from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.storage.receptura_store_json import RecepturaStoreJson
from src.storage.material_store_json import MaterialStoreJson


class TabReceptura(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = RecepturaStoreJson()
        self._material_store = MaterialStoreJson()
        self._material_by_id: dict[str, dict[str, Any]] = {}
        self._worker_name = ""
        self._role = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("RECEPTURA", self)
        title.setStyleSheet("font-size:26px; font-weight:900;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Baza pozycji materialowych pod wycene i modul. Kazdy wpis ma stale ID.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#56606d;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_new = QPushButton("Nowa pozycja", self)
        self.btn_save = QPushButton("Zapisz", self)
        self.btn_delete = QPushButton("Usun zaznaczona", self)
        self.btn_refresh = QPushButton("Odswiez", self)
        for btn in (self.btn_new, self.btn_save, self.btn_delete, self.btn_refresh):
            btn.setMinimumHeight(34)
            actions.addWidget(btn, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        self.lab_stats = QLabel("", self)
        self.lab_stats.setStyleSheet("font-weight:700;")
        root.addWidget(self.lab_stats, 0)

        self.tbl = QTableWidget(0, 11, self)
        self.tbl.setHorizontalHeaderLabels(
            [
                "ID",
                "Nazwa",
                "Material",
                "Jedn",
                "Ilosc",
                "Cena netto",
                "VAT %",
                "Cena brutto",
                "Do wyceny",
                "Do modulu",
                "Uwagi",
            ]
        )
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setColumnWidth(0, 90)
        self.tbl.setColumnWidth(1, 250)
        self.tbl.setColumnWidth(2, 240)
        self.tbl.setColumnWidth(3, 70)
        self.tbl.setColumnWidth(4, 75)
        self.tbl.setColumnWidth(5, 95)
        self.tbl.setColumnWidth(6, 70)
        self.tbl.setColumnWidth(7, 95)
        self.tbl.setColumnWidth(8, 90)
        self.tbl.setColumnWidth(9, 90)
        self.tbl.setColumnWidth(10, 260)
        root.addWidget(self.tbl, 1)

        form_box = QWidget(self)
        form = QFormLayout(form_box)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.ed_id = QLineEdit(self)
        self.ed_id.setReadOnly(True)
        self.ed_name = QLineEdit(self)
        self.cb_material = QComboBox(self)
        self.cb_material.setMinimumWidth(360)
        self.btn_refresh_materials = QPushButton("Odswiez baze", self)
        self.btn_refresh_materials.setMinimumHeight(30)
        material_row = QWidget(self)
        material_row_layout = QHBoxLayout(material_row)
        material_row_layout.setContentsMargins(0, 0, 0, 0)
        material_row_layout.setSpacing(6)
        material_row_layout.addWidget(self.cb_material, 1)
        material_row_layout.addWidget(self.btn_refresh_materials, 0)
        self.ed_unit = QLineEdit(self)
        self.sp_qty = QDoubleSpinBox(self)
        self.sp_qty.setDecimals(3)
        self.sp_qty.setRange(0.0, 999999.0)
        self.sp_qty.setSingleStep(1.0)
        self.chk_quote = QCheckBox("Pokazuj w wycenie", self)
        self.chk_quote.setChecked(True)
        self.chk_module = QCheckBox("Pokazuj w module", self)
        self.chk_module.setChecked(True)
        self.ed_notes = QLineEdit(self)

        form.addRow("ID", self.ed_id)
        form.addRow("Nazwa", self.ed_name)
        form.addRow("Material", material_row)
        form.addRow("Jednostka", self.ed_unit)
        form.addRow("Ilosc", self.sp_qty)
        form.addRow("", self.chk_quote)
        form.addRow("", self.chk_module)
        form.addRow("Uwagi", self.ed_notes)
        root.addWidget(form_box, 0)

        self.lab_status = QLabel("", self)
        self.lab_status.setStyleSheet("color:#166534;")
        root.addWidget(self.lab_status, 0)

        self.btn_new.clicked.connect(self._new_entry)
        self.btn_save.clicked.connect(self._save_entry)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.tbl.itemSelectionChanged.connect(self._load_selected)
        self.cb_material.currentIndexChanged.connect(self._on_material_changed)
        self.btn_refresh_materials.clicked.connect(self._reload_material_choices)

        self._reload_material_choices()
        self._new_entry()
        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()

    def refresh_data(self) -> None:
        self._reload_material_choices()
        rows = self._store.list_rows()
        self.tbl.setRowCount(0)
        for payload in rows:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)

            row_id = str(payload.get("id", "") or "").strip()
            id_item = QTableWidgetItem(row_id)
            id_item.setData(Qt.ItemDataRole.UserRole, payload)
            self.tbl.setItem(row, 0, id_item)

            self.tbl.setItem(row, 1, QTableWidgetItem(str(payload.get("name", "") or "")))
            material_label = str(payload.get("material_name", "") or "").strip() or str(payload.get("material_type", "") or "")
            self.tbl.setItem(row, 2, QTableWidgetItem(material_label))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(payload.get("unit", "") or "")))
            self.tbl.setItem(row, 4, QTableWidgetItem(f"{float(payload.get('quantity', 0.0) or 0.0):.3f}"))
            self.tbl.setItem(row, 5, QTableWidgetItem(f"{float(payload.get('price_net', 0.0) or 0.0):.2f}"))
            self.tbl.setItem(row, 6, QTableWidgetItem(f"{float(payload.get('vat_percent', 0.0) or 0.0):.2f}"))
            self.tbl.setItem(row, 7, QTableWidgetItem(f"{float(payload.get('price_gross', 0.0) or 0.0):.2f}"))
            self.tbl.setItem(row, 8, QTableWidgetItem("TAK" if bool(payload.get("for_quote", True)) else "NIE"))
            self.tbl.setItem(row, 9, QTableWidgetItem("TAK" if bool(payload.get("for_module", True)) else "NIE"))
            self.tbl.setItem(row, 10, QTableWidgetItem(str(payload.get("notes", "") or "")))

        self.lab_stats.setText(f"Pozycji receptury: {len(rows)}")

    @staticmethod
    def _parse_float(value: Any) -> float:
        raw = str(value or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except Exception:
            return 0.0

    def _reload_material_choices(self) -> None:
        current_id = str(self.cb_material.currentData() or "").strip()
        self._material_by_id = {}

        rows = self._material_store.list_materials()
        normalized = [row for row in rows if isinstance(row, dict)]
        normalized.sort(key=lambda row: str(row.get("nazwa", "") or "").strip().lower())

        self.cb_material.blockSignals(True)
        self.cb_material.clear()
        self.cb_material.addItem("[Wybierz material]", "")
        for row in normalized:
            material_id = str(row.get("id", "") or "").strip()
            material_name = str(row.get("nazwa", "") or "").strip()
            material_type = str(row.get("typ", "") or "").strip()
            if not material_id or not material_name:
                continue
            label = f"{material_id} | {material_name}"
            if material_type:
                label += f" ({material_type})"
            self.cb_material.addItem(label, material_id)
            self._material_by_id[material_id] = row

        idx = self.cb_material.findData(current_id)
        self.cb_material.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_material.blockSignals(False)

    def _selected_material_row(self) -> dict[str, Any]:
        material_id = str(self.cb_material.currentData() or "").strip()
        return dict(self._material_by_id.get(material_id, {}))

    def _on_material_changed(self) -> None:
        material = self._selected_material_row()
        if not material:
            return
        name = str(material.get("nazwa", "") or "").strip()
        if name:
            self.ed_name.setText(name)

    def _select_material_from_payload(self, payload: dict[str, Any]) -> None:
        material_id = str(payload.get("material_id", "") or "").strip()
        if material_id:
            idx = self.cb_material.findData(material_id)
            if idx >= 0:
                self.cb_material.setCurrentIndex(idx)
                return

        material_name = str(payload.get("material_name", "") or "").strip().lower()
        if not material_name:
            material_name = str(payload.get("material_type", "") or "").strip().lower()
        if not material_name:
            self.cb_material.setCurrentIndex(0)
            return

        for idx in range(1, self.cb_material.count()):
            row_id = str(self.cb_material.itemData(idx) or "").strip()
            row = self._material_by_id.get(row_id, {})
            row_name = str(row.get("nazwa", "") or "").strip().lower()
            if row_name == material_name:
                self.cb_material.setCurrentIndex(idx)
                return

        self.cb_material.setCurrentIndex(0)

    def _selected_payload(self) -> dict[str, Any]:
        row = self.tbl.currentRow()
        if row < 0:
            return {}
        item = self.tbl.item(row, 0)
        if item is None:
            return {}
        payload = item.data(Qt.ItemDataRole.UserRole)
        return payload if isinstance(payload, dict) else {}

    def _load_selected(self) -> None:
        payload = self._selected_payload()
        if not payload:
            return
        self.ed_id.setText(str(payload.get("id", "") or "").strip())
        self.ed_name.setText(str(payload.get("name", "") or ""))
        self._select_material_from_payload(payload)
        self.ed_unit.setText(str(payload.get("unit", "") or ""))
        self.sp_qty.setValue(float(payload.get("quantity", 0.0) or 0.0))
        self.chk_quote.setChecked(bool(payload.get("for_quote", True)))
        self.chk_module.setChecked(bool(payload.get("for_module", True)))
        self.ed_notes.setText(str(payload.get("notes", "") or ""))

    def _new_entry(self) -> None:
        self.tbl.clearSelection()
        self.ed_id.setText(self._store.next_id())
        self.ed_name.clear()
        if self.cb_material.count() > 0:
            self.cb_material.setCurrentIndex(0)
        self.ed_unit.setText("szt")
        self.sp_qty.setValue(1.0)
        self.chk_quote.setChecked(True)
        self.chk_module.setChecked(True)
        self.ed_notes.clear()
        self._set_status("Nowa pozycja receptury.", ok=True)

    def _build_payload_from_form(self) -> dict[str, Any]:
        material = self._selected_material_row()
        material_id = str(material.get("id", "") or "").strip()
        material_name = str(material.get("nazwa", "") or "").strip()
        material_type = str(material.get("typ", "") or "").strip()
        price_net = self._parse_float(material.get("cena_zl", 0.0))
        return {
            "id": str(self.ed_id.text().strip() or ""),
            "name": str(self.ed_name.text().strip() or material_name),
            "material_id": material_id,
            "material_name": material_name,
            "material_type": material_type,
            "unit": str(self.ed_unit.text().strip() or ""),
            "quantity": float(self.sp_qty.value()),
            "price_net": float(price_net),
            "vat_percent": 0.0,
            "for_quote": bool(self.chk_quote.isChecked()),
            "for_module": bool(self.chk_module.isChecked()),
            "notes": str(self.ed_notes.text().strip() or ""),
        }

    def _save_entry(self) -> None:
        payload = self._build_payload_from_form()
        if not payload.get("name"):
            QMessageBox.information(self, "Receptura", "Podaj nazwe materialu.")
            return
        if not payload.get("material_id"):
            QMessageBox.information(self, "Receptura", "Wybierz material z bazy materialow.")
            return
        if not payload.get("unit"):
            QMessageBox.information(self, "Receptura", "Podaj jednostke (np. szt, m2, mb).")
            return

        try:
            is_new, saved = self._store.upsert(payload)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Receptura",
                f"Nie udalo sie zapisac pozycji receptury.\n\nSzczegoly: {exc}",
            )
            return

        self.refresh_data()
        saved_id = str(saved.get("id", "") or "")
        if saved_id:
            for row in range(self.tbl.rowCount()):
                item = self.tbl.item(row, 0)
                if item is not None and item.text().strip() == saved_id:
                    self.tbl.selectRow(row)
                    break
        self._set_status("Dodano nowa pozycje receptury." if is_new else "Zapisano zmiany pozycji receptury.", ok=True)

    def _delete_selected(self) -> None:
        payload = self._selected_payload()
        row_id = str(payload.get("id", "") or "").strip()
        if not row_id:
            QMessageBox.information(self, "Receptura", "Wybierz pozycje do usuniecia.")
            return

        confirm = QMessageBox.question(
            self,
            "Receptura",
            (
                f"Czy na pewno usunac pozycje receptury?\n\n"
                f"ID: {row_id}\n"
                f"Nazwa: {str(payload.get('name', '') or '-')}"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self._store.delete(row_id)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Receptura",
                f"Nie udalo sie usunac pozycji receptury.\n\nSzczegoly: {exc}",
            )
            return
        if not deleted:
            QMessageBox.warning(self, "Receptura", "Nie znaleziono pozycji do usuniecia.")
            return

        self.refresh_data()
        self._new_entry()
        self._set_status("Usunieto pozycje receptury.", ok=True)

    def _set_status(self, text: str, ok: bool) -> None:
        self.lab_status.setText(str(text or ""))
        self.lab_status.setStyleSheet("color:#166534;" if ok else "color:#9f1239;")
