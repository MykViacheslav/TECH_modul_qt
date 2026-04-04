from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.storage.company_expenses_store_json import CompanyExpensesStoreJson, new_expense_id
from src.ui.theme_utils import get_muted_color
from src.ui.theme_utils import get_muted_color

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


DEFAULT_FIXED_EXPENSES: list[str] = [
    "Wynajem",
    "OC samochodow",
    "Wymiana opon",
    "Prad",
    "Leasingi",
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


class TabWydatkiStale(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = CompanyExpensesStoreJson()
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("WYDATKI STALE FIRMY", self)
        title.setStyleSheet("font-size:22px; font-weight:800;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Stale koszty miesieczne firmy. Dodaj pozycje i kwoty. Na koncu widzisz sume razem.",
            self,
        )
        subtitle.setStyleSheet(f"color:{get_muted_color()};")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.tbl = QTableWidget(0, 3, self)
        self.tbl.setStyleSheet(TABLE_TEXT_STYLE)
        self.tbl.setHorizontalHeaderLabels(["ID", "Pozycja", "Kwota [zl]"])
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(False)
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

        sum_frame = QFrame(self)
        sum_frame.setStyleSheet("QFrame { border:1px solid #d9e0ea; border-radius:8px; background:#ffffff; }")
        sum_row = QHBoxLayout(sum_frame)
        sum_row.setContentsMargins(10, 8, 10, 8)
        sum_row.setSpacing(8)
        sum_row.addWidget(QLabel("Suma razem:", self), 0)
        self.lab_sum = QLabel("0.00 zl", self)
        self.lab_sum.setStyleSheet("font-size:16px; font-weight:700;")
        sum_row.addWidget(self.lab_sum, 0)
        sum_row.addStretch(1)
        root.addWidget(sum_frame, 0)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_selected_rows)
        self.btn_reload.clicked.connect(self._reload)
        self.tbl.itemChanged.connect(self._on_item_changed)

        self._reload()

    def _reload(self) -> None:
        rows = self._store.list_items("fixed", DEFAULT_FIXED_EXPENSES)
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
        total = sum(float(row.get("amount", 0.0) or 0.0) for row in rows)
        self.lab_sum.setText(f"{total:.2f} zl")
        self._store.save_items("fixed", rows)

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        if self._is_loading:
            return
        self._recalculate_and_save()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reload()
