from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.worker_models import WorkerDef, new_worker_id, new_worker_pin
from src.storage.worker_store_json import WorkerStoreJson
from src.widgets.worker_qr_dialog import WorkerQrDialog
from src.widgets.worker_qr_export import (
    export_workers_qr_pdf,
    export_workers_qr_pdf_to_default_folder,
    open_workers_qr_export_dir,
)


_COLS = [
    ("ID", "worker_id"),
    ("PIN", "pin_code"),
    ("Imię", "first_name"),
    ("Nazwisko", "last_name"),
    ("Stanowisko", "role"),
    ("Stawka/h", "hourly_rate"),
    ("BHP (data)", "bhp_valid_until"),
    ("Badania", "medical_exam_until"),
    ("Zaliczka", "advance_pln"),
    ("Wypłata", "payout_pln"),
    ("Godz.", "hours_worked"),
    ("Poprawki", "errors_notes"),
]

_COL_HEADERS = [col[0] for col in _COLS]
_COL_FIELDS = [col[1] for col in _COLS]


def _to_str(val: object) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        return f"{val:g}" if val != 0 else ""
    return str(val)


class TabPracownicy(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = WorkerStoreJson()
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Pracownicy")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        self.tbl = QTableWidget(0, len(_COLS))
        self.tbl.setHorizontalHeaderLabels(_COL_HEADERS)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setDefaultSectionSize(32)
        root.addWidget(self.tbl, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.btn_add = QPushButton("+ Dodaj pracownika")
        self.btn_remove = QPushButton("Usuń zaznaczonego")
        self.btn_qr = QPushButton("Pokaż QR")
        self.btn_export_pdf = QPushButton("Eksport PDF")
        self.btn_export_folder = QPushButton("Eksport do folderu")
        self.btn_open_folder = QPushButton("Otwórz folder QR")
        self.btn_save = QPushButton("Zapisz zmiany")
        self.btn_save.setStyleSheet("font-weight: 700;")

        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_remove)
        btns.addWidget(self.btn_qr)
        btns.addWidget(self.btn_export_pdf)
        btns.addWidget(self.btn_export_folder)
        btns.addWidget(self.btn_open_folder)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        root.addLayout(btns)

        hint = QLabel(
            "Stawka/h - zł/godz. | PIN - 6-cyfrowy kod awaryjny do kiosku | "
            "BHP / Badania - wpisz datę ważności (np. 2025-12-31) | "
            "Zaliczka / Wypłata - zł | Godz. - napracowane godziny | Poprawki - notatki"
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.btn_add.clicked.connect(self._add_empty_row)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_qr.clicked.connect(self._show_qr_for_selected)
        self.btn_export_pdf.clicked.connect(self._export_all_qr_pdf)
        self.btn_export_folder.clicked.connect(self._export_all_qr_pdf_to_folder)
        self.btn_open_folder.clicked.connect(self._open_qr_folder)
        self.btn_save.clicked.connect(self._save_all)

        self._load_workers()
        self._resize_columns()

    def _load_workers(self) -> None:
        self._loading = True
        self.tbl.setRowCount(0)
        for worker in self._store.list_workers():
            self._append_row(worker)
        self._loading = False

    def _append_row(self, worker: WorkerDef) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        for col, field_name in enumerate(_COL_FIELDS):
            if field_name == "first_name":
                val = worker.get_first_name()
            elif field_name == "last_name":
                val = worker.get_last_name()
            else:
                val = getattr(worker, field_name, "")
            item = QTableWidgetItem(_to_str(val))
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl.setItem(row, col, item)

    def _add_empty_row(self) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        for col in range(len(_COLS)):
            self.tbl.setItem(row, col, QTableWidgetItem(""))

        id_item = self.tbl.item(row, 0)
        pin_item = self.tbl.item(row, 1)
        if id_item:
            id_item.setText(new_worker_id())
        if pin_item:
            pin_item.setText(new_worker_pin())

        self.tbl.scrollToBottom()
        self.tbl.setCurrentCell(row, 0)

    def _remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.tbl.selectedIndexes()}, reverse=True)
        if not rows:
            return
        answer = QMessageBox.question(
            self,
            "Usuń pracownika",
            f"Usunąć {len(rows)} wiersz(-e)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for row in rows:
            first = (self.tbl.item(row, 2) or QTableWidgetItem("")).text().strip()
            last = (self.tbl.item(row, 3) or QTableWidgetItem("")).text().strip()
            full_name = f"{first} {last}".strip()
            if full_name:
                self._store.delete(full_name)
            self.tbl.removeRow(row)

    def _selected_worker(self) -> WorkerDef | None:
        rows = sorted({idx.row() for idx in self.tbl.selectedIndexes()})
        if not rows:
            return None
        row = rows[0]

        def cell(col: int) -> str:
            item = self.tbl.item(row, col)
            return item.text().strip() if item else ""

        first_name = cell(2)
        last_name = cell(3)
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            return None

        def safe_float(col: int) -> float:
            try:
                return float((cell(col) or "0").replace(",", "."))
            except ValueError:
                return 0.0

        worker = WorkerDef(
            name=full_name,
            worker_id=cell(0) or new_worker_id(),
            pin_code=cell(1) or new_worker_pin(),
            first_name=first_name,
            last_name=last_name,
            role=cell(4),
            hourly_rate=safe_float(5),
            bhp_valid_until=cell(6),
            medical_exam_until=cell(7),
            advance_pln=safe_float(8),
            payout_pln=safe_float(9),
            hours_worked=safe_float(10),
            errors_notes=cell(11),
        )
        if not cell(0):
            self.tbl.item(row, 0).setText(worker.worker_id)
        if not cell(1):
            self.tbl.item(row, 1).setText(worker.pin_code)
        return worker

    def _show_qr_for_selected(self) -> None:
        worker = self._selected_worker()
        if worker is None:
            QMessageBox.information(self, "QR pracownika", "Wybierz pracownika z tabeli.")
            return
        dialog = WorkerQrDialog(worker, self)
        dialog.exec()

    def _export_all_qr_pdf(self) -> None:
        workers = self._store.list_workers()
        if not workers:
            QMessageBox.information(self, "Eksport QR", "Brak pracowników do eksportu.")
            return

        default_name = f"pracownicy_qr_{len(workers)}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport kart QR pracowników",
            default_name,
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return

        output = export_workers_qr_pdf(workers, file_path)
        QMessageBox.information(self, "Eksport QR", f"Zapisano PDF do:\n{output}")

    def _export_all_qr_pdf_to_folder(self) -> None:
        workers = self._store.list_workers()
        if not workers:
            QMessageBox.information(self, "Eksport QR", "Brak pracowników do eksportu.")
            return

        output = export_workers_qr_pdf_to_default_folder(workers)
        QMessageBox.information(self, "Eksport QR", f"Zapisano PDF do folderu:\n{output}")

    def _open_qr_folder(self) -> None:
        if not open_workers_qr_export_dir():
            QMessageBox.warning(self, "Folder QR", "Nie udało się otworzyć folderu QR.")

    def _save_all(self) -> None:
        saved = 0
        errors: list[str] = []

        old_names = set(self._store.list_names())
        new_names: set[str] = set()

        for row in range(self.tbl.rowCount()):
            def cell(col: int) -> str:
                item = self.tbl.item(row, col)
                return item.text().strip() if item else ""

            first_name = cell(2)
            last_name = cell(3)
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                continue

            new_names.add(full_name)

            def safe_float(col: int) -> float:
                try:
                    return float(cell(col)) if cell(col) else 0.0
                except ValueError:
                    return 0.0

            worker = WorkerDef(
                name=full_name,
                worker_id=cell(0) or new_worker_id(),
                pin_code=cell(1) or new_worker_pin(),
                first_name=first_name,
                last_name=last_name,
                role=cell(4),
                hourly_rate=safe_float(5),
                bhp_valid_until=cell(6),
                medical_exam_until=cell(7),
                advance_pln=safe_float(8),
                payout_pln=safe_float(9),
                hours_worked=safe_float(10),
                errors_notes=cell(11),
            )

            result = self._store.overwrite(worker)
            if result.ok:
                saved += 1
            else:
                errors.append(result.message_pl)

        for old_name in old_names - new_names:
            self._store.delete(old_name)

        if errors:
            QMessageBox.warning(self, "Błędy zapisu", "\n".join(errors))
        else:
            QMessageBox.information(self, "Zapisano", f"Zapisano {saved} pracowników.")

    def _resize_columns(self) -> None:
        widths = [70, 80, 90, 110, 120, 80, 110, 100, 80, 80, 70, 150]
        for col, width in enumerate(widths):
            if col < self.tbl.columnCount():
                self.tbl.setColumnWidth(col, width)
