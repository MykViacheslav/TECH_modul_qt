from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.storage.company_expenses_store_json import CompanyExpensesStoreJson, new_expense_id
from src.storage.worker_store_json import WorkerStoreJson


DEFAULT_VARIABLE_EXPENSES: list[str] = [
    "Pensja pracownika",
    "Zakupy materialow",
    "Paliwo",
    "Wynajem mieszkania pracownikom",
    "Delegacja",
    "Zakup chemii",
    "Inne",
]


def _to_float(text: str) -> float:
    raw = str(text or "").strip().replace(" ", "").replace(",", ".")
    raw = raw.replace("zl", "").replace("ZL", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


class TabWydatkiZmienne(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = CompanyExpensesStoreJson()
        self._worker_store = WorkerStoreJson()
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("WYDATKI ZMIENNE", self)
        title.setStyleSheet("font-size:22px; font-weight:800;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Zmienne koszty miesieczne + kalkulacja realnej roboczo-godziny dla aktualnej liczby pracownikow.",
            self,
        )
        subtitle.setStyleSheet("color:#555555;")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.tbl = QTableWidget(0, 3, self)
        self.tbl.setHorizontalHeaderLabels(["ID", "Pozycja", "Kwota [zl]"])
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setColumnWidth(0, 80)
        root.addWidget(self.tbl, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_add = QPushButton("+ Dodaj", self)
        self.btn_remove = QPushButton("- Usun", self)
        self.btn_reload = QPushButton("Odswiez", self)
        actions.addWidget(self.btn_add, 0)
        actions.addWidget(self.btn_remove, 0)
        actions.addWidget(self.btn_reload, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        calc = QFrame(self)
        calc.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:#ffffff; }")
        calc_layout = QVBoxLayout(calc)
        calc_layout.setContentsMargins(10, 10, 10, 10)
        calc_layout.setSpacing(8)

        workforce_row = QHBoxLayout()
        workforce_row.setSpacing(8)
        workforce_row.addWidget(QLabel("Liczba pracownikow:", self), 0)
        self.sp_workers = QSpinBox(self)
        self.sp_workers.setRange(1, 1000)
        workforce_row.addWidget(self.sp_workers, 0)
        workforce_row.addWidget(QLabel("Godzin / pracownika / miesiac:", self), 0)
        self.sp_hours = QDoubleSpinBox(self)
        self.sp_hours.setRange(1.0, 1000.0)
        self.sp_hours.setDecimals(2)
        self.sp_hours.setSuffix(" h")
        workforce_row.addWidget(self.sp_hours, 0)
        self.btn_load_workers = QPushButton("Pobierz z bazy pracownikow", self)
        workforce_row.addWidget(self.btn_load_workers, 0)
        workforce_row.addStretch(1)
        calc_layout.addLayout(workforce_row)

        totals_row = QHBoxLayout()
        totals_row.setSpacing(12)
        self.lab_sum_fixed = QLabel("Suma stalych: 0.00 zl", self)
        self.lab_sum_variable = QLabel("Suma zmiennych: 0.00 zl", self)
        self.lab_sum_total = QLabel("Suma razem: 0.00 zl", self)
        self.lab_sum_total.setStyleSheet("font-weight:700;")
        totals_row.addWidget(self.lab_sum_fixed, 0)
        totals_row.addWidget(self.lab_sum_variable, 0)
        totals_row.addWidget(self.lab_sum_total, 0)
        totals_row.addStretch(1)
        calc_layout.addLayout(totals_row)

        self.lab_hours_total = QLabel("Godzin razem: 0.00 h", self)
        self.lab_real_hour = QLabel("Realna roboczo-godzina: 0.00 zl/h", self)
        self.lab_real_hour.setStyleSheet("font-size:16px; font-weight:800; color:#1f2937;")
        calc_layout.addWidget(self.lab_hours_total, 0)
        calc_layout.addWidget(self.lab_real_hour, 0)
        root.addWidget(calc, 0)

        self.tbl.itemChanged.connect(self._on_item_changed)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_selected_rows)
        self.btn_reload.clicked.connect(self._reload)
        self.sp_workers.valueChanged.connect(self._on_inputs_changed)
        self.sp_hours.valueChanged.connect(self._on_inputs_changed)
        self.btn_load_workers.clicked.connect(self._load_workers_from_store)

        self._reload()

    def _reload(self) -> None:
        rows = self._store.list_items("variable", DEFAULT_VARIABLE_EXPENSES)
        fallback_workers = max(1, len(self._worker_store.list_workers()))
        workers_count = self._store.get_workers_count(fallback=fallback_workers)
        hours = self._store.get_hours_per_worker(fallback=160.0)
        self._is_loading = True
        try:
            self.tbl.setRowCount(0)
            for row_data in rows:
                row = self.tbl.rowCount()
                self.tbl.insertRow(row)
                id_item = QTableWidgetItem(str(row_data.get("expense_id", "") or new_expense_id()))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                name_item = QTableWidgetItem(str(row_data.get("name", "") or ""))
                amount_item = QTableWidgetItem(f"{float(row_data.get('amount', 0.0) or 0.0):.2f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tbl.setItem(row, 0, id_item)
                self.tbl.setItem(row, 1, name_item)
                self.tbl.setItem(row, 2, amount_item)
            self.sp_workers.setValue(int(workers_count))
            self.sp_hours.setValue(float(hours))
        finally:
            self._is_loading = False
        self._recalculate_and_save()

    def _add_row(self) -> None:
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        id_item = QTableWidgetItem(new_expense_id())
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.tbl.setItem(row, 0, id_item)
        self.tbl.setItem(row, 1, QTableWidgetItem("Nowa pozycja"))
        amount_item = QTableWidgetItem("0.00")
        amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl.setItem(row, 2, amount_item)
        self._recalculate_and_save()

    def _remove_selected_rows(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() is not None else []
        if not rows:
            current = self.tbl.currentRow()
            if current >= 0:
                self.tbl.removeRow(current)
        else:
            for model_idx in sorted(rows, key=lambda x: x.row(), reverse=True):
                self.tbl.removeRow(int(model_idx.row()))
        self._recalculate_and_save()

    def _collect_rows(self) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for row in range(self.tbl.rowCount()):
            expense_id = str(self.tbl.item(row, 0).text() if self.tbl.item(row, 0) is not None else "").strip()
            name = str(self.tbl.item(row, 1).text() if self.tbl.item(row, 1) is not None else "").strip()
            amount = _to_float(self.tbl.item(row, 2).text() if self.tbl.item(row, 2) is not None else "0")
            if not name:
                continue
            if not expense_id:
                expense_id = new_expense_id()
            rows.append({"expense_id": expense_id, "name": name, "amount": float(amount)})
        return rows

    def _recalculate_and_save(self) -> None:
        rows = self._collect_rows()
        variable_total = sum(float(row.get("amount", 0.0) or 0.0) for row in rows)
        fixed_total = float(self._store.sum_items("fixed"))
        total = fixed_total + variable_total
        workers = max(1, int(self.sp_workers.value()))
        hours_per_worker = max(1.0, float(self.sp_hours.value()))
        hours_total = workers * hours_per_worker
        real_hour = total / hours_total if hours_total > 0 else 0.0

        self.lab_sum_fixed.setText(f"Suma stalych: {fixed_total:.2f} zl")
        self.lab_sum_variable.setText(f"Suma zmiennych: {variable_total:.2f} zl")
        self.lab_sum_total.setText(f"Suma razem: {total:.2f} zl")
        self.lab_hours_total.setText(f"Godzin razem: {hours_total:.2f} h")
        self.lab_real_hour.setText(f"Realna roboczo-godzina: {real_hour:.2f} zl/h")

        self._store.save_items("variable", rows)
        self._store.save_workforce(workers_count=workers, hours_per_worker=hours_per_worker)

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        if self._is_loading:
            return
        self._recalculate_and_save()

    def _on_inputs_changed(self) -> None:
        if self._is_loading:
            return
        self._recalculate_and_save()

    def _load_workers_from_store(self) -> None:
        count = max(1, len(self._worker_store.list_workers()))
        self.sp_workers.setValue(count)
        self._recalculate_and_save()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reload()

