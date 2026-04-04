from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def pick_receptura_rows(
    parent: QWidget | None,
    rows: list[dict[str, Any]],
    *,
    title: str,
    subtitle: str = "",
    allow_multi: bool = True,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(980, 560)
    layout = QVBoxLayout(dialog)

    if subtitle:
        lab = QLabel(subtitle, dialog)
        lab.setWordWrap(True)
        layout.addWidget(lab, 0)

    table = QTableWidget(0, 9, dialog)
    table.setHorizontalHeaderLabels(
        ["ID", "Nazwa", "Typ", "Jedn", "Ilosc", "Cena netto", "VAT %", "Do wyceny", "Do modulu"]
    )
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(
        QAbstractItemView.SelectionMode.ExtendedSelection
        if allow_multi
        else QAbstractItemView.SelectionMode.SingleSelection
    )
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setColumnWidth(0, 90)
    table.setColumnWidth(1, 280)
    table.setColumnWidth(2, 120)
    table.setColumnWidth(3, 70)
    table.setColumnWidth(4, 80)
    table.setColumnWidth(5, 95)
    table.setColumnWidth(6, 70)
    table.setColumnWidth(7, 95)
    table.setColumnWidth(8, 95)

    for payload in rows:
        row = table.rowCount()
        table.insertRow(row)
        id_item = QTableWidgetItem(str(payload.get("id", "") or ""))
        id_item.setData(Qt.ItemDataRole.UserRole, payload)
        table.setItem(row, 0, id_item)
        table.setItem(row, 1, QTableWidgetItem(str(payload.get("name", "") or "")))
        table.setItem(row, 2, QTableWidgetItem(str(payload.get("material_type", "") or "")))
        table.setItem(row, 3, QTableWidgetItem(str(payload.get("unit", "") or "")))
        table.setItem(row, 4, QTableWidgetItem(f"{float(payload.get('quantity', 0.0) or 0.0):.3f}"))
        table.setItem(row, 5, QTableWidgetItem(f"{float(payload.get('price_net', 0.0) or 0.0):.2f}"))
        table.setItem(row, 6, QTableWidgetItem(f"{float(payload.get('vat_percent', 0.0) or 0.0):.2f}"))
        table.setItem(row, 7, QTableWidgetItem("TAK" if bool(payload.get("for_quote", True)) else "NIE"))
        table.setItem(row, 8, QTableWidgetItem("TAK" if bool(payload.get("for_module", True)) else "NIE"))

    if table.rowCount() > 0:
        table.selectRow(0)
    layout.addWidget(table, 1)

    actions = QHBoxLayout()
    actions.addStretch(1)
    btn_cancel = QPushButton("Anuluj", dialog)
    btn_ok = QPushButton("Wybierz", dialog)
    actions.addWidget(btn_cancel, 0)
    actions.addWidget(btn_ok, 0)
    layout.addLayout(actions)

    btn_cancel.clicked.connect(dialog.reject)
    btn_ok.clicked.connect(dialog.accept)

    if dialog.exec() != int(QDialog.DialogCode.Accepted):
        return []

    selected_rows = table.selectionModel().selectedRows() if table.selectionModel() is not None else []
    selected: list[dict[str, Any]] = []
    for model_index in selected_rows:
        row = int(model_index.row())
        item = table.item(row, 0)
        if item is None:
            continue
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict):
            selected.append(dict(payload))
    return selected
