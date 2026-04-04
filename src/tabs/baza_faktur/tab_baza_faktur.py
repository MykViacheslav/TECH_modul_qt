from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.services.invoice_workflow_service import (
    collect_invoice_unit_stats,
    export_invoice_to_material_store,
    export_pending_invoices_to_material_store,
    import_invoice_pdf_file_multi,
    sync_invoices_from_local_dirs,
    sync_invoices_from_mail,
)
from src.storage.invoice_store_json import InvoiceStoreJson

TABLE_TEXT_STYLE = """
QTableWidget {
    color: #1f2937;
    selection-color: #0f172a;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
"""


class TabBazaFaktur(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = InvoiceStoreJson()
        self._worker_name = ""
        self._role = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("BAZA FAKTUR", self)
        title.setStyleSheet("font-size:26px; font-weight:900;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Najpierw zapisujesz faktury z maila/PDF tutaj, a dopiero potem eksportujesz pozycje do magazynu.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#56606d;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_check_mail = QPushButton("Sprawdz mail", self)
        self.btn_check_downloads = QPushButton("Sprawdz pobrane", self)
        self.btn_import_pdf = QPushButton("Import PDF", self)
        self.btn_delete_selected = QPushButton("Usun zaznaczone", self)
        self.btn_export_selected = QPushButton("Eksportuj zaznaczone", self)
        self.btn_export_pending = QPushButton("Eksportuj wszystkie oczekujace", self)
        self.btn_only_review = QPushButton("Tylko do weryfikacji", self)
        self.btn_only_review.setCheckable(True)
        self.btn_units_report = QPushButton("Jednostki", self)
        self.btn_refresh = QPushButton("Odswiez", self)
        for btn in (
            self.btn_check_mail,
            self.btn_check_downloads,
            self.btn_import_pdf,
            self.btn_delete_selected,
            self.btn_export_selected,
            self.btn_export_pending,
            self.btn_only_review,
            self.btn_units_report,
            self.btn_refresh,
        ):
            btn.setMinimumHeight(34)
            actions.addWidget(btn, 0)
        self.lab_filter_nip = QLabel("Filtr MSI NIP:", self)
        self.cb_filter_nip = QComboBox(self)
        self.cb_filter_nip.setMinimumWidth(210)
        self.cb_filter_nip.addItem("Wszystkie", "all")
        self.cb_filter_nip.addItem("Tylko NIE/Brak NIP", "bad")
        self.cb_filter_nip.addItem("Tylko NIE", "mismatch")
        self.cb_filter_nip.addItem("Tylko Brak NIP", "missing")
        self.cb_filter_nip.addItem("Tylko OK", "ok")
        actions.addWidget(self.lab_filter_nip, 0)
        actions.addWidget(self.cb_filter_nip, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        self.lab_stats = QLabel("", self)
        self.lab_stats.setStyleSheet("font-weight:700;")
        root.addWidget(self.lab_stats, 0)

        self.tbl_invoices = QTableWidget(0, 17, self)
        self.tbl_invoices.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_invoices.setHorizontalHeaderLabels(
            [
                "ID",
                "Data odbioru",
                "Dostawca",
                "Nr faktury",
                "Data faktury",
                "Pozycji",
                "Netto",
                "VAT",
                "Brutto",
                "Do zaplaty",
                "Waluta",
                "Cena typ",
                "MSI NIP",
                "Status eksportu",
                "Duplikat",
                "OCR",
                "Powiazanie",
            ]
        )
        self.tbl_invoices.setAlternatingRowColors(True)
        self.tbl_invoices.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_invoices.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_invoices.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_invoices.verticalHeader().setVisible(False)
        self.tbl_invoices.setColumnWidth(0, 220)
        self.tbl_invoices.setColumnWidth(1, 120)
        self.tbl_invoices.setColumnWidth(2, 180)
        self.tbl_invoices.setColumnWidth(3, 140)
        self.tbl_invoices.setColumnWidth(4, 110)
        self.tbl_invoices.setColumnWidth(5, 70)
        self.tbl_invoices.setColumnWidth(6, 90)
        self.tbl_invoices.setColumnWidth(7, 90)
        self.tbl_invoices.setColumnWidth(8, 90)
        self.tbl_invoices.setColumnWidth(9, 95)
        self.tbl_invoices.setColumnWidth(10, 75)
        self.tbl_invoices.setColumnWidth(11, 90)
        self.tbl_invoices.setColumnWidth(12, 125)
        self.tbl_invoices.setColumnWidth(13, 120)
        self.tbl_invoices.setColumnWidth(14, 130)
        self.tbl_invoices.setColumnWidth(15, 120)
        self.tbl_invoices.setColumnWidth(16, 140)
        root.addWidget(self.tbl_invoices, 1)

        details_bar = QHBoxLayout()
        details_bar.setSpacing(8)
        details_title = QLabel("Pozycje zaznaczonych faktur", self)
        details_title.setStyleSheet("font-weight:700;")
        details_bar.addWidget(details_title, 0, Qt.AlignmentFlag.AlignLeft)
        details_bar.addSpacing(8)
        details_filter_label = QLabel("Filtr parsera:", self)
        self.cb_item_parser_filter = QComboBox(self)
        self.cb_item_parser_filter.setMinimumWidth(180)
        self.cb_item_parser_filter.addItem("Wszystkie", "all")
        self.cb_item_parser_filter.addItem("Template [T]", "template")
        self.cb_item_parser_filter.addItem("Fallback [F]", "fallback")
        self.cb_item_parser_filter.addItem("Generic [G]", "generic")
        self.cb_item_parser_filter.addItem("Niepewne [F+G]", "uncertain")
        details_bar.addWidget(details_filter_label, 0)
        details_bar.addWidget(self.cb_item_parser_filter, 0)
        legend_label = QLabel("Legenda:", self)
        legend_t = QLabel("[T] template", self)
        legend_f = QLabel("[F] fallback", self)
        legend_g = QLabel("[G] generic", self)
        legend_t.setStyleSheet("color:#166534; font-weight:700;")
        legend_f.setStyleSheet("color:#b45309; font-weight:700;")
        legend_g.setStyleSheet("color:#475569; font-weight:700;")
        legend_t.setToolTip("Pozycja rozpoznana regułą dostawcy.")
        legend_f.setToolTip("Pozycja rozpoznana fallbackiem po regule dostawcy.")
        legend_g.setToolTip("Pozycja rozpoznana parserem ogólnym.")
        details_bar.addWidget(legend_label, 0)
        details_bar.addWidget(legend_t, 0)
        details_bar.addWidget(legend_f, 0)
        details_bar.addWidget(legend_g, 0)
        details_bar.addStretch(1)
        root.addLayout(details_bar)

        self.lab_invoice_details = QLabel("Wybierz fakture z tabeli powyzej.", self)
        self.lab_invoice_details.setWordWrap(True)
        self.lab_invoice_details.setStyleSheet("color:#4f5b66;")
        root.addWidget(self.lab_invoice_details, 0)

        self.tbl_items = QTableWidget(0, 10, self)
        self.tbl_items.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl_items.setHorizontalHeaderLabels(
            [
                "Nazwa",
                "Ilosc",
                "Jedn",
                "Cena netto",
                "Cena brutto",
                "Wartosc netto",
                "Kwota VAT",
                "Wartosc brutto",
                "VAT %",
                "Typ",
            ]
        )
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setColumnWidth(0, 360)
        self.tbl_items.setColumnWidth(1, 90)
        self.tbl_items.setColumnWidth(2, 70)
        self.tbl_items.setColumnWidth(3, 100)
        self.tbl_items.setColumnWidth(4, 105)
        self.tbl_items.setColumnWidth(5, 110)
        self.tbl_items.setColumnWidth(6, 100)
        self.tbl_items.setColumnWidth(7, 115)
        self.tbl_items.setColumnWidth(8, 75)
        self.tbl_items.setColumnWidth(9, 120)
        root.addWidget(self.tbl_items, 1)

        self.lab_status = QLabel("", self)
        self.lab_status.setStyleSheet("color:#166534;")
        root.addWidget(self.lab_status, 0)

        self.btn_check_mail.clicked.connect(self._check_mail)
        self.btn_check_downloads.clicked.connect(self._check_downloads)
        self.btn_import_pdf.clicked.connect(self._import_pdf)
        self.btn_delete_selected.clicked.connect(self._delete_selected)
        self.btn_export_selected.clicked.connect(self._export_selected)
        self.btn_export_pending.clicked.connect(self._export_pending)
        self.btn_only_review.toggled.connect(self.refresh_data)
        self.btn_units_report.clicked.connect(self._show_units_report)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.cb_filter_nip.currentIndexChanged.connect(self.refresh_data)
        self.cb_item_parser_filter.currentIndexChanged.connect(self._on_invoice_selection_changed)
        self.tbl_invoices.itemSelectionChanged.connect(self._on_invoice_selection_changed)

        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()

    def refresh_data(self) -> None:
        all_invoices = self._store.list_invoices()
        filter_key = str(self.cb_filter_nip.currentData() or "all").strip().lower()
        only_review = bool(self.btn_only_review.isChecked())
        invoices = [
            row
            for row in all_invoices
            if self._invoice_matches_msi_filter(row, filter_key)
            and self._invoice_matches_review_filter(row, only_review)
        ]
        self.tbl_invoices.setRowCount(0)
        self.btn_only_review.setStyleSheet("font-weight:700;" if only_review else "")

        pending = 0
        exported = 0
        due_pending = 0.0
        msi_ok = 0
        msi_mismatch = 0
        msi_missing = 0
        review_count = 0
        for invoice in invoices:
            if bool(invoice.get("needs_review", False)):
                review_count += 1
            is_exported = bool(invoice.get("exported_to_material", False))
            if is_exported:
                exported += 1
            else:
                pending += 1
                try:
                    due_pending += float(invoice.get("amount_due", 0.0) or 0.0)
                except Exception:
                    pass

            row = self.tbl_invoices.rowCount()
            self.tbl_invoices.insertRow(row)

            invoice_id = str(invoice.get("invoice_id", "") or "").strip()
            id_item = QTableWidgetItem(invoice_id)
            id_item.setData(Qt.ItemDataRole.UserRole, invoice)
            self.tbl_invoices.setItem(row, 0, id_item)

            received = str(invoice.get("received_at", "") or invoice.get("imported_at", "") or "").strip()
            self.tbl_invoices.setItem(row, 1, QTableWidgetItem(received[:19]))

            supplier = str(invoice.get("supplier", "") or invoice.get("sender", "") or "").strip()
            self.tbl_invoices.setItem(row, 2, QTableWidgetItem(supplier))

            inv_no = str(invoice.get("invoice_number", "") or "").strip()
            if not inv_no:
                inv_no = str(invoice.get("attachment_name", "") or "").strip()
            self.tbl_invoices.setItem(row, 3, QTableWidgetItem(inv_no))

            self.tbl_invoices.setItem(row, 4, QTableWidgetItem(str(invoice.get("invoice_date", "") or "").strip()))
            self.tbl_invoices.setItem(row, 5, QTableWidgetItem(str(int(invoice.get("items_count", 0) or 0))))
            try:
                total_net = float(invoice.get("total_net", 0.0) or 0.0)
            except Exception:
                total_net = 0.0
            try:
                total_gross = float(invoice.get("total_gross", 0.0) or 0.0)
            except Exception:
                total_gross = 0.0
            try:
                total_vat = float(invoice.get("total_vat", 0.0) or 0.0)
            except Exception:
                total_vat = max(0.0, total_gross - total_net)
            try:
                amount_due = float(invoice.get("amount_due", 0.0) or 0.0)
            except Exception:
                amount_due = 0.0
            currency = str(invoice.get("currency", "PLN") or "PLN").strip().upper() or "PLN"
            price_basis = str(invoice.get("price_basis", "") or "").strip().lower() or "unknown"
            buyer_nip = str(invoice.get("buyer_nip", "") or "").strip()
            is_msi_invoice = bool(invoice.get("is_msi_project_invoice", False))
            if is_msi_invoice:
                msi_ok += 1
                msi_label = "OK"
            elif buyer_nip:
                msi_mismatch += 1
                msi_label = f"NIE ({buyer_nip})"
            else:
                msi_missing += 1
                msi_label = "Brak NIP"

            self.tbl_invoices.setItem(row, 6, QTableWidgetItem(f"{total_net:.2f}"))
            self.tbl_invoices.setItem(row, 7, QTableWidgetItem(f"{total_vat:.2f}"))
            self.tbl_invoices.setItem(row, 8, QTableWidgetItem(f"{total_gross:.2f}"))
            self.tbl_invoices.setItem(row, 9, QTableWidgetItem(f"{amount_due:.2f}"))
            self.tbl_invoices.setItem(row, 10, QTableWidgetItem(currency))
            self.tbl_invoices.setItem(row, 11, QTableWidgetItem(price_basis))
            self.tbl_invoices.setItem(row, 12, QTableWidgetItem(msi_label))

            export_label = "Wyeksportowana" if is_exported else "Do eksportu"
            self.tbl_invoices.setItem(row, 13, QTableWidgetItem(export_label))

            duplicate_reason = str(invoice.get("duplicate_reason", "") or "").strip()
            duplicate_of = str(invoice.get("duplicate_of_invoice_id", "") or "").strip()
            if duplicate_reason == "invoice_signature" and duplicate_of:
                duplicate_label = f"Tak ({duplicate_of[:8]})"
            elif duplicate_reason:
                duplicate_label = "Tak"
            else:
                duplicate_label = "-"
            self.tbl_invoices.setItem(row, 14, QTableWidgetItem(duplicate_label))

            parse_error = str(invoice.get("parse_error", "") or "").strip()
            extraction_method = str(invoice.get("extraction_method", "") or "").strip().lower()
            ocr_conf = float(invoice.get("ocr_confidence", 0.0) or 0.0)
            ai_used = bool(invoice.get("ai_fallback_used", False))
            try:
                ai_conf = float(invoice.get("ai_confidence", 0.0) or 0.0)
            except Exception:
                ai_conf = 0.0
            ai_model = str(invoice.get("ai_model", "") or "").strip()
            has_text = bool(invoice.get("has_text", False))
            needs_review = bool(invoice.get("needs_review", False))
            if parse_error:
                ocr_label = "Blad odczytu"
            elif ai_used:
                model_short = ai_model[:14] if ai_model else "AI"
                ocr_label = f"{model_short} {ai_conf:.2f}"
            elif extraction_method == "text":
                ocr_label = "TEXT"
            elif extraction_method == "ocr":
                ocr_label = f"OCR {ocr_conf:.2f}"
            elif extraction_method == "mixed":
                ocr_label = f"TEXT+OCR {ocr_conf:.2f}"
            elif has_text:
                ocr_label = "TEXT"
            else:
                ocr_label = "Brak tekstu"
            if needs_review and "Blad" not in ocr_label:
                ocr_label = f"{ocr_label} !"
            self.tbl_invoices.setItem(row, 15, QTableWidgetItem(ocr_label))

            try:
                exported_material_count = int(invoice.get("exported_material_count", 0) or 0)
            except Exception:
                exported_material_count = 0
            if exported_material_count <= 0:
                exported_material_ids = invoice.get("exported_material_ids", [])
                if isinstance(exported_material_ids, list):
                    exported_material_count = len(
                        [str(value or "").strip() for value in exported_material_ids if str(value or "").strip()]
                    )
            try:
                imported_last = int(invoice.get("last_export_imported_lines", 0) or 0)
            except Exception:
                imported_last = 0
            try:
                skipped_last = int(invoice.get("last_export_skipped_lines", 0) or 0)
            except Exception:
                skipped_last = 0
            if bool(invoice.get("exported_to_material", False)):
                link_label = f"MAT:{exported_material_count} | +{imported_last}/-{skipped_last}"
            else:
                link_label = "-"
            self.tbl_invoices.setItem(row, 16, QTableWidgetItem(link_label))

        self.lab_stats.setText(
            (
                f"Faktur (widok): {len(invoices)} / {len(all_invoices)} | Oczekuje eksportu: {pending} | "
                f"Kwota do zaplaty (oczekujace): {due_pending:.2f} | Wyeksportowane: {exported} | Do weryfikacji: {review_count} | "
                f"MSI NIP OK: {msi_ok} | NIP niezgodny: {msi_mismatch} | Brak NIP: {msi_missing}"
            )
        )

        if self.tbl_invoices.rowCount() > 0:
            self.tbl_invoices.selectRow(0)
        else:
            self.tbl_items.setRowCount(0)
            self.lab_invoice_details.setText("Brak faktur. Uzyj: Sprawdz mail lub Import PDF.")

    def _selected_invoices(self) -> list[dict]:
        selected_rows: list[int] = []
        model = self.tbl_invoices.selectionModel()
        if model is not None:
            selected_rows = sorted({idx.row() for idx in model.selectedRows()})

        if not selected_rows:
            current = self.tbl_invoices.currentRow()
            if current >= 0:
                selected_rows = [current]

        invoices: list[dict] = []
        for row in selected_rows:
            item = self.tbl_invoices.item(row, 0)
            if item is None:
                continue
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, dict):
                invoices.append(payload)
        return invoices

    def _selected_invoice(self) -> dict:
        selected = self._selected_invoices()
        return selected[0] if selected else {}

    def _on_invoice_selection_changed(self) -> None:
        selected = self._selected_invoices()
        can_export_new = any(not bool(inv.get("exported_to_material", False)) for inv in selected)
        self.btn_export_selected.setEnabled(can_export_new)
        self.btn_export_selected.setToolTip(
            "Eksport tylko dla faktur oczekujacych."
            if can_export_new
            else "Zaznaczone faktury sa juz wyeksportowane."
        )
        if not selected:
            self.tbl_items.setRowCount(0)
            self.lab_invoice_details.setText("Wybierz fakture z tabeli powyzej.")
            return

        all_items_full: list[dict] = []
        for invoice in selected:
            inv_label = str(invoice.get("invoice_number", "") or invoice.get("attachment_name", "") or "").strip()
            if not inv_label:
                inv_label = str(invoice.get("invoice_id", "") or "-").strip()[:8] or "-"
            for raw_item in invoice.get("items", []):
                if not isinstance(raw_item, dict):
                    continue
                row_copy = dict(raw_item)
                row_copy["__invoice_label"] = inv_label
                all_items_full.append(row_copy)

        parser_filter_key = str(self.cb_item_parser_filter.currentData() or "all").strip().lower()
        all_items = [
            row
            for row in all_items_full
            if self._item_matches_parser_filter(row, parser_filter_key)
        ]

        multi = len(selected) > 1
        self.tbl_items.setRowCount(0)
        for row_data in all_items:
            row = self.tbl_items.rowCount()
            self.tbl_items.insertRow(row)
            base_name = str(row_data.get("name", "") or "")
            parse_source = str(row_data.get("parse_source", "") or "generic").strip().lower()
            parse_badge = ""
            if parse_source.startswith("template:"):
                parse_badge = "[T] "
                color = "#166534"
            elif parse_source.startswith("fallback:"):
                parse_badge = "[F] "
                color = "#b45309"
            else:
                parse_badge = "[G] "
                color = "#475569"
            invoice_label = str(row_data.get("__invoice_label", "") or "").strip()
            display_base = f"{parse_badge}{base_name}"
            display_name = f"[{invoice_label}] {display_base}" if multi and invoice_label else display_base
            name_item = QTableWidgetItem(display_name)
            name_item.setForeground(QBrush(QColor(color)))
            name_item.setToolTip(f"Parser source: {parse_source or 'generic'}")
            self.tbl_items.setItem(row, 0, name_item)
            try:
                qty = float(row_data.get("quantity", 0.0) or 0.0)
            except Exception:
                qty = 0.0
            try:
                unit_net = float(row_data.get("unit_price_net", 0.0) or 0.0)
            except Exception:
                unit_net = 0.0
            try:
                unit_gross = float(row_data.get("unit_price_gross", 0.0) or 0.0)
            except Exception:
                unit_gross = 0.0
            try:
                total_net = float(row_data.get("total_price_net", 0.0) or 0.0)
            except Exception:
                total_net = 0.0
            try:
                total_gross = float(row_data.get("total_price_gross", 0.0) or 0.0)
            except Exception:
                total_gross = 0.0
            try:
                vat_amount = float(row_data.get("vat_amount", 0.0) or 0.0)
            except Exception:
                vat_amount = max(0.0, total_gross - total_net)
            vat_rate = str(row_data.get("vat_rate", "") or "").strip()
            self.tbl_items.setItem(row, 1, QTableWidgetItem(f"{qty:.3f}"))
            self.tbl_items.setItem(row, 2, QTableWidgetItem(str(row_data.get("unit", "") or "")))
            self.tbl_items.setItem(row, 3, QTableWidgetItem(f"{unit_net:.2f}"))
            self.tbl_items.setItem(row, 4, QTableWidgetItem(f"{unit_gross:.2f}"))
            self.tbl_items.setItem(row, 5, QTableWidgetItem(f"{total_net:.2f}"))
            self.tbl_items.setItem(row, 6, QTableWidgetItem(f"{vat_amount:.2f}"))
            self.tbl_items.setItem(row, 7, QTableWidgetItem(f"{total_gross:.2f}"))
            self.tbl_items.setItem(row, 8, QTableWidgetItem(vat_rate))
            material_label = str(row_data.get("material_type", "") or "").strip()
            thickness = str(row_data.get("thickness_mm", "") or "").strip()
            if thickness:
                material_label = f"{material_label} ({thickness} mm)" if material_label else f"{thickness} mm"
            self.tbl_items.setItem(row, 9, QTableWidgetItem(material_label))

        parse_error = str(selected[0].get("parse_error", "") or "").strip()
        supplier = str(selected[0].get("supplier", "") or selected[0].get("sender", "") or "").strip() or "-"
        inv_no = str(selected[0].get("invoice_number", "") or selected[0].get("attachment_name", "") or "").strip() or "-"
        invoice_id = str(selected[0].get("invoice_id", "") or "").strip() or "-"
        inv_date = str(selected[0].get("invoice_date", "") or "").strip() or "-"
        source_path = str(selected[0].get("source_path", "") or "").strip() or "-"
        attachment_name = str(selected[0].get("attachment_name", "") or "").strip() or "-"
        try:
            exported_material_count = int(selected[0].get("exported_material_count", 0) or 0)
        except Exception:
            exported_material_count = 0
        if exported_material_count <= 0:
            exported_material_ids = selected[0].get("exported_material_ids", [])
            if isinstance(exported_material_ids, list):
                exported_material_count = len(
                    [str(value or "").strip() for value in exported_material_ids if str(value or "").strip()]
                )
        try:
            imported_last = int(selected[0].get("last_export_imported_lines", 0) or 0)
        except Exception:
            imported_last = 0
        try:
            skipped_last = int(selected[0].get("last_export_skipped_lines", 0) or 0)
        except Exception:
            skipped_last = 0
        try:
            total_net = sum(float(inv.get("total_net", 0.0) or 0.0) for inv in selected)
        except Exception:
            total_net = 0.0
        try:
            total_gross = sum(float(inv.get("total_gross", 0.0) or 0.0) for inv in selected)
        except Exception:
            total_gross = 0.0
        try:
            total_vat = sum(float(inv.get("total_vat", 0.0) or 0.0) for inv in selected)
        except Exception:
            total_vat = max(0.0, total_gross - total_net)
        try:
            amount_due = sum(float(inv.get("amount_due", 0.0) or 0.0) for inv in selected)
        except Exception:
            amount_due = 0.0
        currency = str(selected[0].get("currency", "PLN") or "PLN").strip().upper() or "PLN"
        price_basis = str(selected[0].get("price_basis", "") or "").strip().lower() or "unknown"
        extraction_method = str(selected[0].get("extraction_method", "") or "").strip().lower() or ("text" if bool(selected[0].get("has_text", False)) else "unknown")
        ocr_conf = float(selected[0].get("ocr_confidence", 0.0) or 0.0)
        ai_used = bool(selected[0].get("ai_fallback_used", False))
        try:
            ai_conf = float(selected[0].get("ai_confidence", 0.0) or 0.0)
        except Exception:
            ai_conf = 0.0
        ai_model = str(selected[0].get("ai_model", "") or "").strip() or "-"
        ai_error = str(selected[0].get("ai_error", "") or "").strip()
        needs_review = bool(selected[0].get("needs_review", False))
        supplier_template = str(selected[0].get("supplier_template", "") or "").strip() or "-"
        unknown_units = [str(x or "").strip() for x in selected[0].get("unknown_units", []) if str(x or "").strip()]
        parser_template = 0
        parser_fallback = 0
        parser_generic = 0
        for row_data in all_items_full:
            src = str(row_data.get("parse_source", "") or "generic").strip().lower()
            if src.startswith("template:"):
                parser_template += 1
            elif src.startswith("fallback:"):
                parser_fallback += 1
            else:
                parser_generic += 1
        duplicate_reason = str(selected[0].get("duplicate_reason", "") or "").strip()
        duplicate_of = str(selected[0].get("duplicate_of_invoice_id", "") or "").strip()
        buyer_nip = str(selected[0].get("buyer_nip", "") or "").strip()
        is_msi = bool(selected[0].get("is_msi_project_invoice", False))
        nip_label = "OK" if is_msi else (f"NIE ({buyer_nip})" if buyer_nip else "Brak NIP")

        info = []
        if multi:
            mismatched = sum(
                1
                for inv in selected
                if not bool(inv.get("is_msi_project_invoice", False)) and str(inv.get("buyer_nip", "") or "").strip()
            )
            missing_nip = sum(1 for inv in selected if not str(inv.get("buyer_nip", "") or "").strip())
            info.extend(
                [
                    f"Wybrano faktur: {len(selected)}",
                    f"Pozycji widok/lacznie: {len(all_items)}/{len(all_items_full)}",
                    f"Netto: {total_net:.2f} {currency}",
                    f"VAT: {total_vat:.2f} {currency}",
                    f"Brutto: {total_gross:.2f} {currency}",
                    f"Do zaplaty: {amount_due:.2f} {currency}",
                    f"NIP niezgodny: {mismatched}",
                    f"Brak NIP: {missing_nip}",
                    f"Parser: T={parser_template} | F={parser_fallback} | G={parser_generic}",
                ]
            )
        else:
            info.extend(
                [
                    f"Faktura: {inv_no}",
                    f"ID faktury: {invoice_id}",
                    f"Dostawca: {supplier}",
                    f"Data: {inv_date}",
                    f"Zalacznik PDF: {attachment_name}",
                    f"Zrodlo pliku: {source_path}",
                    f"Pozycji widok/lacznie: {len(all_items)}/{len(all_items_full)}",
                    f"Netto: {total_net:.2f} {currency}",
                    f"VAT: {total_vat:.2f} {currency}",
                    f"Brutto: {total_gross:.2f} {currency}",
                    f"Do zaplaty: {amount_due:.2f} {currency}",
                    f"Powiazane materialy: {exported_material_count} | ostatni eksport +{imported_last}/-{skipped_last}",
                    f"Cena typ: {price_basis}",
                    f"Template dostawcy: {supplier_template}",
                    f"Filtr parsera: {self.cb_item_parser_filter.currentText()}",
                    f"Odczyt: {extraction_method} ({ocr_conf:.2f})",
                    f"Fallback AI: {'TAK' if ai_used else 'NIE'} | model: {ai_model} | conf: {ai_conf:.2f}",
                    f"Weryfikacja: {'TAK' if needs_review else 'NIE'}",
                    f"Template parser: T={parser_template} | F={parser_fallback} | G={parser_generic}",
                    f"Jednostki nieznane: {', '.join(unknown_units) if unknown_units else 'brak'}",
                    f"MSI NIP: {nip_label}",
                ]
            )
        if duplicate_reason:
            label = f"Duplikat: {duplicate_reason}"
            if duplicate_of:
                label += f" -> {duplicate_of}"
            info.append(label)
        if parse_error:
            info.append(f"Blad odczytu PDF: {parse_error}")
        if ai_error:
            info.append(f"Blad fallback AI: {ai_error}")
        self.lab_invoice_details.setText(" | ".join(info))

    def _check_mail(self) -> None:
        try:
            summary = sync_invoices_from_mail(
                worker_name=self._worker_name,
                max_messages=20,
                send_telegram_notifications=True,
            )
            local_checked, local_created, local_updated, local_errors = self._scan_downloads_folder()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Baza faktur",
                f"Nie udalo sie sprawdzic maila.\n\nSzczegoly: {exc}",
            )
            return

        self.refresh_data()
        invoices = self._store.list_invoices()
        msi_ok = sum(1 for row in invoices if bool(row.get("is_msi_project_invoice", False)))
        msi_mismatch = sum(
            1
            for row in invoices
            if not bool(row.get("is_msi_project_invoice", False)) and str(row.get("buyer_nip", "") or "").strip()
        )
        msi_missing = sum(
            1
            for row in invoices
            if not bool(row.get("is_msi_project_invoice", False)) and not str(row.get("buyer_nip", "") or "").strip()
        )
        units_overview = self._units_summary_text()

        msg = (
            f"Mail - zalaczniki PDF sprawdzone: {summary.checked_files}\n"
            f"Mail - nowe faktury: {summary.created_invoices}\n"
            f"Mail - juz istnialy (zaktualizowane): {summary.updated_invoices}\n"
            f"PDF bez tekstu: {summary.without_text}\n"
            f"Bledy odczytu mail: {summary.parse_errors}\n"
            f"\nFolder Downloads - PDF sprawdzone: {local_checked}\n"
            f"Folder Downloads - nowe faktury: {local_created}\n"
            f"Folder Downloads - juz istnialy (zaktualizowane): {local_updated}\n"
            f"Folder Downloads - bledy: {local_errors}\n"
            f"Oczekuje eksportu: {summary.pending_export}\n"
            f"Telegram wyslany: {summary.telegram_notified}\n"
            f"MSI NIP OK: {msi_ok}\n"
            f"NIP niezgodny: {msi_mismatch}\n"
            f"Brak NIP: {msi_missing}\n"
            f"{units_overview}"
        )
        if summary.telegram_error:
            msg += f"\nTelegram blad: {summary.telegram_error}"

        QMessageBox.information(self, "Baza faktur", msg)
        self._set_status("Sprawdzono mail i odswiezono baze faktur.", ok=True)

    def _check_downloads(self) -> None:
        try:
            local_checked, local_created, local_updated, local_errors = self._scan_downloads_folder()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Baza faktur",
                f"Nie udalo sie sprawdzic folderu Downloads.\n\nSzczegoly: {exc}",
            )
            return

        self.refresh_data()
        units_overview = self._units_summary_text()
        msg = (
            f"Folder Downloads - PDF sprawdzone: {local_checked}\n"
            f"Folder Downloads - nowe faktury: {local_created}\n"
            f"Folder Downloads - juz istnialy (zaktualizowane): {local_updated}\n"
            f"Folder Downloads - bledy: {local_errors}\n"
            f"{units_overview}"
        )
        QMessageBox.information(self, "Baza faktur", msg)
        self._set_status("Sprawdzono folder Downloads i odswiezono baze faktur.", ok=True)

    def _scan_downloads_folder(self) -> tuple[int, int, int, int]:
        return sync_invoices_from_local_dirs(
            [
                Path.home() / "Downloads",
                Path(r"C:\Users\mykyt\Downloads"),
            ],
            store=self._store,
            recursive=False,
            max_files=300,
        )

    def _import_pdf(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz faktury PDF",
            "",
            "Pliki PDF (*.pdf)",
        )
        if not files:
            return

        created = 0
        updated = 0
        errors: list[str] = []

        for file_path in files:
            try:
                summary = import_invoice_pdf_file_multi(Path(file_path), store=self._store)
                created += int(summary.created or 0)
                updated += int(summary.updated or 0)
            except Exception as exc:
                errors.append(f"{Path(file_path).name}: {exc}")

        self.refresh_data()
        units_overview = self._units_summary_text()
        message = f"Dodano nowych faktur: {created}\nJuz istnialy (zaktualizowane): {updated}"
        message += f"\n{units_overview}"
        if errors:
            short = "\n".join(errors[:5])
            if len(errors) > 5:
                short += "\n..."
            message += f"\n\nBledy ({len(errors)}):\n{short}"
            QMessageBox.warning(self, "Baza faktur", message)
            self._set_status("Import PDF zakonczony z bledami.", ok=False)
            return

        QMessageBox.information(self, "Baza faktur", message)
        self._set_status("Import PDF zakonczony.", ok=True)

    def _show_units_report(self) -> None:
        stats = collect_invoice_unit_stats(store=self._store)
        if not stats.units:
            QMessageBox.information(self, "Baza faktur", "Brak pozycji faktur do analizy jednostek.")
            return
        lines = [f"- {unit}: {count}" for unit, count in stats.units]
        if len(lines) > 30:
            lines = lines[:30] + [f"... +{len(stats.units) - 30} kolejnych"]
        unknown = ", ".join(stats.unknown_units) if stats.unknown_units else "brak"
        msg = (
            f"Pozycji lacznie: {stats.total_items}\n"
            f"Jednostki wykryte: {len(stats.units)}\n"
            f"Jednostki nieznane: {unknown}\n\n"
            f"Top jednostek:\n" + "\n".join(lines)
        )
        QMessageBox.information(self, "Baza faktur - jednostki", msg)

    def _units_summary_text(self) -> str:
        stats = collect_invoice_unit_stats(store=self._store)
        if not stats.units:
            return "Jednostki: brak danych."
        top = ", ".join(f"{unit}:{count}" for unit, count in stats.units[:8])
        unknown = ", ".join(stats.unknown_units) if stats.unknown_units else "brak"
        return (
            f"Jednostki (top): {top}\n"
            f"Jednostki nieznane: {unknown}"
        )

    def _delete_selected(self) -> None:
        selected = self._selected_invoices()
        if not selected:
            QMessageBox.information(self, "Baza faktur", "Zaznacz co najmniej jedna fakture do usuniecia.")
            return

        selected_ids: list[str] = []
        selected_labels: list[str] = []
        for invoice in selected:
            invoice_id = str(invoice.get("invoice_id", "") or "").strip()
            if not invoice_id or invoice_id in selected_ids:
                continue
            selected_ids.append(invoice_id)
            label = str(invoice.get("invoice_number", "") or invoice.get("attachment_name", "") or invoice_id).strip() or invoice_id
            selected_labels.append(label)

        if not selected_ids:
            QMessageBox.information(self, "Baza faktur", "Nie mozna odczytac ID zaznaczonych faktur.")
            return

        preview = "\n".join(f"- {label}" for label in selected_labels[:6])
        if len(selected_labels) > 6:
            preview += f"\n... +{len(selected_labels) - 6} kolejnych"
        confirm = QMessageBox.question(
            self,
            "Baza faktur",
            (
                f"Czy na pewno usunac zaznaczone faktury: {len(selected_ids)}?\n\n"
                f"{preview}\n\n"
                f"Ta operacja usuwa wpisy z bazy faktur."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        removed_count = 0
        not_found = 0
        errors: list[str] = []
        for invoice_id in selected_ids:
            try:
                removed = self._store.delete_invoice(invoice_id)
            except Exception as exc:
                errors.append(f"{invoice_id}: {exc}")
                continue
            if removed:
                removed_count += 1
            else:
                not_found += 1

        self.refresh_data()
        if errors:
            err_preview = "\n".join(errors[:4])
            if len(errors) > 4:
                err_preview += "\n..."
            QMessageBox.warning(
                self,
                "Baza faktur",
                (
                    f"Usunieto: {removed_count}\n"
                    f"Nie znaleziono: {not_found}\n"
                    f"Bledy: {len(errors)}\n\n"
                    f"{err_preview}"
                ),
            )
            self._set_status("Usuwanie faktur zakonczone z bledami.", ok=False)
            return

        self._set_status(
            f"Usunieto faktur: {removed_count}. Nie znaleziono: {not_found}.",
            ok=True,
        )

    def _export_selected(self) -> None:
        selected = self._selected_invoices()
        if not selected:
            QMessageBox.information(self, "Baza faktur", "Zaznacz co najmniej jedna fakture do eksportu.")
            return

        selected_ids: list[str] = []
        already_exported_count = 0
        for invoice in selected:
            invoice_id = str(invoice.get("invoice_id", "") or "").strip()
            is_exported = bool(invoice.get("exported_to_material", False))
            if is_exported:
                already_exported_count += 1
                continue
            if invoice_id and invoice_id not in selected_ids:
                selected_ids.append(invoice_id)
        if not selected_ids:
            if already_exported_count > 0:
                QMessageBox.information(
                    self,
                    "Baza faktur",
                    "Zaznaczone faktury sa juz wyeksportowane. Eksport wykonujemy tylko 1 raz.",
                )
            else:
                QMessageBox.information(self, "Baza faktur", "Nie mozna odczytac ID zaznaczonych faktur.")
            return

        non_msi = [
            inv
            for inv in selected
            if (not bool(inv.get("exported_to_material", False)))
            and (not bool(inv.get("is_msi_project_invoice", False)))
        ]
        if non_msi:
            mismatch = sum(1 for inv in non_msi if str(inv.get("buyer_nip", "") or "").strip())
            missing = sum(1 for inv in non_msi if not str(inv.get("buyer_nip", "") or "").strip())
            confirm = QMessageBox.question(
                self,
                "Baza faktur",
                (
                    f"Uwaga: {len(non_msi)} zaznaczonych faktur nie ma zgodnego NIP MSI (7123413192).\n"
                    f"NIP niezgodny: {mismatch}, brak NIP: {missing}.\n\n"
                    f"Czy kontynuowac eksport?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        exported_count = 0
        imported_lines = 0
        skipped_lines = 0
        errors: list[str] = []
        for invoice_id in selected_ids:
            try:
                result = export_invoice_to_material_store(invoice_id, invoice_store=self._store)
            except Exception as exc:
                errors.append(f"{invoice_id}: {exc}")
                continue
            exported_count += 1
            imported_lines += int(result.imported_lines or 0)
            skipped_lines += int(result.skipped_lines or 0)

        self.refresh_data()
        if errors:
            short = "\n".join(errors[:5])
            if len(errors) > 5:
                short += "\n..."
            QMessageBox.warning(
                self,
                "Baza faktur",
                (
                    f"Eksport zakonczony z bledami.\n"
                    f"Przetworzono faktur: {exported_count}/{len(selected_ids)}\n"
                    f"Dodano pozycji do magazynu: {imported_lines}\n"
                    f"Pominieto (duplikaty/brak danych): {skipped_lines}\n\n"
                    f"Bledy ({len(errors)}):\n{short}"
                ),
            )
            self._set_status("Eksport zaznaczonych faktur zakonczony z bledami.", ok=False)
            return

        QMessageBox.information(
            self,
            "Baza faktur",
            (
                f"Eksport zakonczony.\n"
                f"Wyeksportowano faktur: {exported_count}\n"
                f"Dodano pozycji do magazynu: {imported_lines}\n"
                f"Pominieto (duplikaty/brak danych): {skipped_lines}\n"
                f"Juz wyeksportowane (pominiete): {already_exported_count}"
            ),
        )
        self._set_status("Wyeksportowano zaznaczone faktury do magazynu (tylko nowe).", ok=True)

    def _export_pending(self) -> None:
        pending_rows = [row for row in self._store.list_invoices() if not bool(row.get("exported_to_material", False))]
        non_msi = [row for row in pending_rows if not bool(row.get("is_msi_project_invoice", False))]
        if non_msi:
            mismatch = sum(1 for row in non_msi if str(row.get("buyer_nip", "") or "").strip())
            missing = sum(1 for row in non_msi if not str(row.get("buyer_nip", "") or "").strip())
            confirm = QMessageBox.question(
                self,
                "Baza faktur",
                (
                    f"Uwaga: w oczekujacych jest {len(non_msi)} faktur bez zgodnego NIP MSI (7123413192).\n"
                    f"NIP niezgodny: {mismatch}, brak NIP: {missing}.\n\n"
                    f"Czy mimo to eksportowac wszystkie oczekujace?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        try:
            invoice_count, imported_lines, skipped_lines = export_pending_invoices_to_material_store(
                invoice_store=self._store
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Baza faktur",
                f"Nie udalo sie wyeksportowac wszystkich faktur.\n\nSzczegoly: {exc}",
            )
            return

        self.refresh_data()
        QMessageBox.information(
            self,
            "Baza faktur",
            (
                f"Wyeksportowano faktur: {invoice_count}\n"
                f"Dodano pozycji do magazynu: {imported_lines}\n"
                f"Pominieto pozycji: {skipped_lines}"
            ),
        )
        self._set_status("Wyeksportowano wszystkie oczekujace faktury.", ok=True)

    def _set_status(self, text: str, ok: bool) -> None:
        self.lab_status.setText(str(text or ""))
        self.lab_status.setStyleSheet("color:#166534;" if ok else "color:#9f1239;")

    @staticmethod
    def _invoice_msi_state(invoice: dict) -> str:
        buyer_nip = str(invoice.get("buyer_nip", "") or "").strip()
        if bool(invoice.get("is_msi_project_invoice", False)):
            return "ok"
        if buyer_nip:
            return "mismatch"
        return "missing"

    @classmethod
    def _invoice_matches_msi_filter(cls, invoice: dict, filter_key: str) -> bool:
        key = str(filter_key or "all").strip().lower()
        state = cls._invoice_msi_state(invoice)
        if key in {"", "all"}:
            return True
        if key == "bad":
            return state in {"mismatch", "missing"}
        if key == "ok":
            return state == "ok"
        if key == "mismatch":
            return state == "mismatch"
        if key == "missing":
            return state == "missing"
        return True

    @staticmethod
    def _invoice_matches_review_filter(invoice: dict, only_review: bool) -> bool:
        if not only_review:
            return True
        return bool(invoice.get("needs_review", False))

    @staticmethod
    def _item_parse_source(item: dict) -> str:
        source = str(item.get("parse_source", "") or "generic").strip().lower()
        if source.startswith("template:"):
            return "template"
        if source.startswith("fallback:"):
            return "fallback"
        return "generic"

    @classmethod
    def _item_matches_parser_filter(cls, item: dict, filter_key: str) -> bool:
        key = str(filter_key or "all").strip().lower()
        source = cls._item_parse_source(item)
        if key in {"", "all"}:
            return True
        if key == "template":
            return source == "template"
        if key == "fallback":
            return source == "fallback"
        if key == "generic":
            return source == "generic"
        if key == "uncertain":
            return source in {"fallback", "generic"}
        return True
